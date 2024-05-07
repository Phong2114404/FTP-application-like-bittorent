import random
import tkinter as tk
from tkinter import ttk
import threading
import socket
import queue
from tkinter import messagebox
from peer import *
# from tracker import *
from tkinter import filedialog
from folder import *

connected_tracker = False
ipv4addr = socket.gethostbyname(socket.gethostname())
port_number = random.randint(49152, 65535)
peer = Peer()

#TODO: SEPERATE LOGIN WINDOW AND MAIN
def timer_trigger():
    root.after(1000, timer_trigger)
    timer_event()

def timer_event():
    #put function here to force it run each 10 ms
    if request_list_flag: request_list()
    
# def upload_folder(): #TODO
def share_folder(): #TODO
    global connected_tracker
    if not connected_tracker:
        messagebox.showerror("Upload Error", "You haven't connected to the Tracker")
        return
    folder_path = filedialog.askdirectory()
    print (f"upload {folder_path}")
    if folder_path:
        folder_name = os.path.basename(folder_path)
        new_folder = Folder(folder_path, name=folder_name, status="Downloaded")
        tk_to_peer_q.put("SHARE FOLDER")
        tk_to_peer_q.put(new_folder)

# def upload_file(): #TODO
def share_file(): #TODO
    global connected_tracker
    if not connected_tracker:
        messagebox.showerror("Upload Error", "You haven't connected to the Tracker")
        return
    file_path = filedialog.askopenfilename()
    if file_path:
        # folder_name = os.path.basename(file_path)
        new_file = File(file_path, status="Downloaded")
        tk_to_peer_q.put("SHARE FILE")
        tk_to_peer_q.put(new_file)

def request_list():
    tk_to_peer_q.put("GET LIST")

def display_list(event=None):
    print("display")
    def update_treeview(tree, folder, parent=''):
        if folder.treeview_id is None:
            if isinstance(folder, Folder):
            # Add the folder to the Treeview
                folder_id = tree.insert(parent, 'end', text=folder.name, values=('',folder.status, 'Folder', folder.path))
                folder.set_treeview_id(folder_id)
                # Add all files in the folder to the Treeview
                for file in folder.files:
                    update_treeview(tree, file, folder.treeview_id)
                # Recursively add subfolders and their files
                for subfolder in folder.child_folders:
                    update_treeview(tree, subfolder, folder.treeview_id)
            elif isinstance(folder, File):
                print("treeview")
                print(folder.path)
                folder_id = tree.insert(parent, 'end', text=folder.name, values=(folder.file_hash, folder.status, 'File', folder.path))
                folder.set_treeview_id(folder_id)
        
        else: #not none
            if isinstance(folder, Folder):
                if(folder.path is not None):
                    tree.item(folder.treeview_id, values=(tree.item(folder.treeview_id, 'values')[0], folder.status, tree.item(folder.treeview_id, 'values')[2], folder.path))
                else:
                    tree.item(folder.treeview_id, values=(tree.item(folder.treeview_id, 'values')[0], folder.status, tree.item(folder.treeview_id, 'values')[2], tree.item(folder.treeview_id, 'values')[3]))
                for file in folder.files:
                    update_treeview(tree, file, folder.treeview_id)
                for subfolder in folder.child_folders:
                    update_treeview(tree, subfolder, folder.treeview_id)
            elif isinstance(folder, File):
                print("treeview not none")
                print(folder.path)
                if(folder.path is not None):
                    tree.item(folder.treeview_id, values=(tree.item(folder.treeview_id, 'values')[0], folder.status, tree.item(folder.treeview_id, 'values')[2], folder.path))
                else:
                    tree.item(folder.treeview_id, values=(tree.item(folder.treeview_id, 'values')[0], folder.status, tree.item(folder.treeview_id, 'values')[2], tree.item(folder.treeview_id, 'values')[3]))
                print(tree.item(folder.treeview_id, 'values')[3])
                # print(tree.item())
            
    global tree
    global peer
    with peer.file_list_lock:
        for folder in peer.container:
            update_treeview(tree, folder)

    
def download_file(path:str):
    tk_to_peer_q.put("DOWNLOAD")
    command = "download " + path
    tk_to_peer_q.put(command)


def get_local_ipv4():
    try:
        # Create a socket to get the local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to a public DNS server
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return None

def send_validate_login(event = None):
    # Dummy validation for demonstration
    global url_entry
    global port_entry
    
    url = url_entry.get()
    try:
        port = int(port_entry.get())
        global peer
        peer.login(tracker_host=url, tracker_port=port, my_ip=ipv4addr, my_port=port_number)
    except ValueError:
        messagebox.showerror("Invalid port number", "The port number must be an integer")
        return
    
    tk_to_peer_q.put("CONNECT")
    # tk_to_peer_q.put((url, port,))

def receive_validate_login(event=None):
    connect_result = peer_to_tk_q.get(block=False)
    global request_list_flag
    global connected_tracker
    if connect_result == True:
        show_main()
        request_list_flag = True
        connected_tracker = True
    else:
        messagebox.showerror("Connect Field", "Cannot connect to the Tracker")
        request_list_flag = False
        connected_tracker = False



def console_execute_command(event=None):
    global console_entry
    command = console_entry.get().strip()
    if command != "":
        text_area_insert (message=command, from_user=True)
        if command == "logout":
            root.destroy()
            return
        tk_to_peer_q.put("CONSOLE")
        tk_to_peer_q.put(command)
        output = peer_to_tk_q.get()
        print ("ABC")
        text_area_insert(message=output, from_user=False)

        
def text_area_insert(message:str, from_user = False):
    global console_entry
    global console_text_area
    if message != "":
        console_text_area.config(state='normal')  # Enable text area temporarily
        if from_user:
            console_text_area.insert(tk.END, f"> {message}\n")
            console_entry.delete(0, tk.END)
        else:
            console_text_area.insert(tk.END, f"{message}\n")
        console_text_area.config(state='disabled')  # Disable text area again
        console_text_area.see(tk.END)


def on_right_click(event):
    # Identify the Treeview item that was clicked
    item_id = tree.identify_row(event.y)
    # print(item_id)
    if item_id:
        # Get the item type (File or Folder) and Status
        item_values = tree.item(item_id, 'values')
        item_status = item_values[1]
        # print(item_status)
        
        # Create a context menu
        context_menu = tk.Menu(tree, tearoff=0)
        
        # Add "Download" command to the context menu
        context_menu.add_command(label="Download", command=lambda: download_files())
        
        # Disable the "Download" option if the item status is "Downloaded"
        if item_status == 'Downloaded' or item_status == 'Downloading':
            context_menu.entryconfig("Download", state=tk.DISABLED)
        
        # Show the context menu at the mouse position
        context_menu.post(event.x_root, event.y_root)


def download_files():
    # Get all selected items
    selected_items = tree.selection()
    for item_id in selected_items:
        file_name = tree.item(item_id, 'text')
        file_hash = tree.item(item_id, 'values')[0]
        file_type = tree.item(item_id, 'values')[2]
        path_parts = []
        current_item = item_id
        # Implement the download logic here
        while True:
            parent_id = tree.parent(current_item)
            if not current_item:  # If there's no parent, we've reached the top
                break
            # Prepend the name of the current item to the path parts
            path_parts.insert(0, tree.item(current_item, 'text'))
            current_item = parent_id
        # Join the parts with underscores to get the desired format
        relative_path = '/'.join(path_parts)
        file_hash = tree.item(item_id, 'values')[0]
        # Print the tuple with hash and relative path
        if file_type == "File":
            tk_to_peer_q.put('DOWNLOAD FILE')
            tk_to_peer_q.put((file_hash, relative_path))
            
        elif file_type == "Folder":
            tk_to_peer_q.put('DOWNLOAD FOLDER')
            tk_to_peer_q.put( relative_path)


def show_main():
    # Switch to main window
    login_frame.place_forget()
    
    main_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
    root.title("Main Window")
    root.geometry("1200x600")
    
def show_login():
    # Switch back to login window
    main_frame.place_forget()
    login_frame.place(relx=0.5, rely=0.5, anchor='center')
    root.title("Login")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Connect to Tracker")
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", lambda: [tk_to_peer_q.put(None), root.destroy()])

    tk_to_peer_q = queue.Queue()
    peer_to_tk_q = queue.Queue()
    backend_thread = threading.Thread(target=peer.run, args=(root, tk_to_peer_q,peer_to_tk_q,), daemon=True )

    
    root.geometry("400x200")
    login_frame = tk.Frame(root)
    login_frame.place(relx=0.5, rely=0.5, anchor='center')
    
    url_label = tk.Label(login_frame, text="Tracker URL:")
    url_label.grid(row=0, column=0, padx=10, pady=5, sticky="e")
    url_entry = tk.Entry(login_frame)
    url_entry.grid(row=0, column=1, padx=10, pady=5)

    # Port label and entry
    port_label = tk.Label(login_frame, text="Tracker Port:")
    port_label.grid(row=1, column=0, padx=10, pady=5, sticky="e")
    port_entry = tk.Entry(login_frame)
    port_entry.grid(row=1, column=1, padx=10, pady=5)

    # Login button
    login_button = tk.Button(login_frame, text="Connect", command=send_validate_login)
    login_button.grid(row=2, columnspan=2, padx=10, pady=10)
    url_entry.bind("<Return>", send_validate_login)
    port_entry.bind("<Return>", send_validate_login)
    



    # Main window frame (hidden by default)
    main_frame = tk.Frame(root)
    tabs = ttk.Notebook(main_frame)
    tabs.place(relx=0, rely=0, relwidth=1, relheight=1)
    console = tk.Frame(tabs)   # first page, which would get widgets gridded into it
    treeview = tk.Frame(tabs)   # second page
    tabs.add(treeview, text='Treeview')
    tabs.add(console, text='Console')
    
    
    #The console tab
    console_text_area = tk.Text(console, height=20, wrap=tk.WORD, state='disabled')
    console_text_area.grid(row=0, column=0, columnspan=2, sticky='nsew', padx=10, pady=10)

    # Create a vertical scroll bar
    console_scrollbar = tk.Scrollbar(console, command=console_text_area.yview)
    console_scrollbar.grid(row=0, column=2, sticky='ns')

    # Configure the grid row and column weights
    console.grid_rowconfigure(0, weight=1)
    console.grid_columnconfigure(0, weight=1)
    console.grid_columnconfigure(1, weight=0)  # Adjust the weight for the send button column

    # Attach the scroll bar to the text area
    console_text_area.config(yscrollcommand=console_scrollbar.set)

    # Create an entry widget for typing commands
    console_entry = tk.Entry(console)
    console_entry.grid(row=1, column=0, sticky='ew', padx=10)
    console_entry.bind("<Return>", console_execute_command)  # Bind the Enter key to execute the command

    # Create a send button
    console_send_button = tk.Button(console, text="Send", command=console_execute_command)
    console_send_button.grid(row=1, column=1, sticky='ew', padx=(0, 10))
        
        
    #config the tabs
    tree = ttk.Treeview(treeview)
    # tree['columns'] = ('Size', 'Type', 'Status')  # Add a new column for status
    tree['columns'] = ('Hash', 'Status', 'Type','Path')
    tree.column('#0', width=150, minwidth=150, stretch=tk.NO)
    tree.column('Hash', width=200, minwidth=200, stretch=tk.NO)
    tree.column('Status', width=120, minwidth=120, stretch=tk.NO)  # Adjust the width as needed
    tree.column('Type', width=100, minwidth=100, stretch=tk.NO)
    tree.column('Path', width=500, minwidth=500, stretch=tk.NO)
    
    tree.heading('#0', text='Name', anchor=tk.W)
    tree.heading('Hash', text='Hash', anchor=tk.W)
    tree.heading('Status', text='Status', anchor=tk.W)  # Add a heading for the new column
    tree.heading('Type', text='Type', anchor=tk.W)
    tree.heading('Path', text='Path', anchor=tk.W)
    # folder1 = tree.insert('', 'end', text='Folder 1', values=('10 KB', 'Folder', 'Downloading'))
    # sub_item1 = tree.insert(folder1, 'end', text='File 1', values=('2 KB', 'Text File', 'Completed'))
    # sub_item2 = tree.insert(folder1, 'end', text='File 2', values=('3 KB', 'Image File', 'In Progress'))

    # folder2 = tree.insert('', 'end', text='Folder 2', values=('20 KB', 'Folder', 'Paused'))
    # sub_item3 = tree.insert(folder2, 'end', text='File 3', values=('5 KB', 'PDF File', 'Queued'))

    # Bind right-click to on_right_click function
    tree.bind("<Button-3>", on_right_click)
    # Vertical scrollbar
    vert_scrollbar = ttk.Scrollbar(tree, orient="vertical", command=tree.yview)
    vert_scrollbar.pack(side='right', fill='y')

    # Horizontal scrollbar
    horiz_scrollbar = ttk.Scrollbar(tree, orient="horizontal", command=tree.xview)
    horiz_scrollbar.pack(side='bottom', fill='x')

    # Configure the treeview
    tree.configure(yscrollcommand=vert_scrollbar.set, xscrollcommand=horiz_scrollbar.set)

    tree.pack(fill="both", expand=True)
    
    
    #add menubar
    # Create a 'File' menu
    menu_bar = tk.Menu(main_frame)

    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Share file", command=share_file)
    file_menu.add_command(label="Share folder", command=share_folder)
    # file_menu.add_command(label="Upload file", command=upload_file)
    # file_menu.add_command(label="Upload folder", command=upload_folder)
    # file_menu.add_command(label="Update list", command=request_list)
    # file_menu.add_separator()
    menu_bar.add_cascade(label="File", menu=file_menu)

    # Create an 'Options' menu
    options_menu = tk.Menu(menu_bar, tearoff=0)
    options_menu.add_command(label="Settings")
    menu_bar.add_cascade(label="Options", menu=options_menu)

    # Create a 'Help' menu
    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="About")
    menu_bar.add_cascade(label="Help", menu=help_menu)

    # Place the menu bar at the top of the window
    root.config(menu=menu_bar)
    
    root.bind("<<ReceiveLogin>>", receive_validate_login)
    root.bind("<<DisplayList>>", display_list)
    #create timer
    root.after(100, timer_trigger)
    request_list_flag = False
    
    backend_thread.start()
    root.mainloop()