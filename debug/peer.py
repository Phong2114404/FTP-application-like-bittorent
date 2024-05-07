import tkinter as tk
import socket, math, pickle
import json, hashlib
import threading, queue
from folder import *
import os
import tqdm, time

TRACKER_IP = ''
TRACKER_PORT = None
MY_IP = socket.gethostbyname(socket.gethostname())
PIECE_SIZE = 2 ** 20
FORMAT = 'utf-8'
MAX_LISTEN = 100
DOWNLOAD_PATH = "./download/"

class Peer:
    # init peer
    def __init__(self):
        self.tracker_host = None
        self.tracker_port = None
        self.my_ip = None
        self.my_port = None
        self.container = []
        self.gui = None
        self.file_list_lock = threading.Lock()
        self.part_data_lock = threading.Lock()


    def login(self, tracker_host, tracker_port, my_ip, my_port, files=[]):
        self.tracker_host = tracker_host
        self.tracker_port = int(tracker_port)
        self.my_ip = my_ip
        self.my_port = int(my_port)
        self.container = files
        self.file_list_lock = threading.Lock()
        self.part_data_lock = threading.Lock()

    def get_tracker_host(self):
        return self.tracker_host
    
    def get_tracker_port(self):
        return self.tracker_port
    
    def get_my_ip(self):
        return self.my_ip
    
    def get_my_port(self):
        return self.my_port
    
    def get_container(self):
        return self.container

    def connect_tracker(self):
        try:
            self.client_to_tracker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_to_tracker.connect((self.tracker_host, self.tracker_port))
            print("Connect to tracker successfully.")
            return True
        except:
            print("Can't connect to tracker")
            return False

    def register_with_tracker(self):
        try:
            message = json.dumps({
                'command': 'register',
                'container': self.container,
                'ip': self.my_ip,
                'port': self.my_port,
            })
            self.client_to_tracker.send(message.encode())
            self.client_to_tracker.recv(PIECE_SIZE)
            threading.Thread(target=self.pulsecheck, args=(self.client_to_tracker, ), daemon=True).start()
        except Exception as e:
            print(f"Failed to connect or send data to the tracker: {e}")    

    # Kiểm tra peer còn onl hay không
    def pulsecheck(self, client_socket):
        try:
            while True:
                heartbeat_msg = json.dumps({'command': 'alive'})
                client_socket.send(heartbeat_msg.encode())
                time.sleep(10)  # interval can be adjusted
        except Exception as e:
            print(f"Failed to connect tracker: {e}")
        finally:
            client_socket.close()
            print("Connection to tracker has been closed.")

    #Tạo tổng hash của file_name
    def create_hash_file(self, file_name):
        sha1 = hashlib.sha1()
        hash_sum = ""
        with open(file_name, 'rb') as file:
            piece_offset = 0
            piece = file.read(PIECE_SIZE)
            while piece:
                hash_sum = sha1.update(piece)
                piece_offset += len(piece)
                piece = file.read(PIECE_SIZE)
        hash_sum = sha1.hexdigest()
        return hash_sum
    
    
    # lấy info peer từ tracker:
    def request_peerS_info(self, filename, file_hash, command):
        message = json.dumps({'command': command, 'file': filename, 'hash': file_hash})
        
        with self.part_data_lock:
            self.client_to_tracker.send(message.encode())
            response = self.client_to_tracker.recv(PIECE_SIZE)
        if not response:
            print("No data received")
            return None
        try:
            return pickle.loads(response)
        except Exception as e:
            print(e)
            return None
        
    # receive file (dữ liệu nhận ghi vào filename)
    def download_piece(self, ip_sender, port_sender, filename, start, end, part_data, hash, status):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip_sender, port_sender))

            # Sending filename, start, and end as a single message separated by a special character
            message = f"{filename}*{start}*{end}*{hash}"
            
            s.send(message.encode())

            # Await confirmation before continuing
            response = s.recv(PIECE_SIZE).decode()
            if response == "done":
                print(f"Start: {start}, End: {end} sent successfully.")
            else:
                print("Failed to send data correctly.")

            done = False
            progress = tqdm.tqdm(unit="B", unit_scale=True, unit_divisor=1000, total=int(end-start))
            
            # Nhận dữ liệu từ sender
            buffer_size = PIECE_SIZE
            
            disconnect = False
            file_path = f"{filename}_{start}.bin"
            file_path = file_path.replace("/","_")
            
            with open(file_path, 'wb') as file_part:
                while not done:
                    data = s.recv(buffer_size)
                    
                    if not data:
                        disconnect = True
                        
                        break
                    
                    if data[-5:] == b"<END>":
                        
                        done = True
                        file_part.write(data[:-5])
                    else:
                        
                        file_part.write(data)
                    
                    progress.update(len(data))
                    
            file_part.close()

            if disconnect == False:
                print(f"Successfully wrote to file: {file_path}")
                print('start add with lock')
                with self.part_data_lock:
                    status.append((start, end, "Completed"))
                    part_data.append((start, file_path))
                print('end add with lock')
            else:
                os.remove(file_path)
                with self.part_data_lock:
                    status.append((start, end, "Failed"))
                print(f"Error in download_file: ")

        except Exception as e:
            os.remove(file_path)
            with self.part_data_lock:
                status.append((start, end, "Failed"))
            print(f"Error in download_file: {e}")
        finally:
            s.close()

        
# lắng nghe, chấp nhận kết nối và gửi file:
    # chấp nhận kết nối
    def accept_connections(self):
        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_peer, args=(client_socket,), daemon=False).start()
            except Exception as e:
                print(f"Failed to accept a connection: {e}")
                break

    # send file
    def handle_peer(self, client_socket):
        try:
            data = client_socket.recv(PIECE_SIZE).decode()
            # print(data)
            if data:
                parts = data.split('*')  # Split the received data by ':'
                if len(parts) == 4:
                    filename, start_str, end_str, hash = parts
                    print(f"Filename: {filename}, hash: {hash}")
                    start = int(start_str)  # Convert start to integer
                    end = int(end_str)      # Convert end to integer
                    print(f"Start: {start}, End: {end}, Type of start: {type(start)}")

                    # Send confirmation back to sender
                    client_socket.send("done".encode())
                else:
                    print("Received data is not formatted correctly.")
                    client_socket.send("error".encode())
            else:
                print("No data received.")

            path=""
            for c in self.container:
                if(isinstance(c, Folder)):
                    file = c.get_file(filename)
                    if(file is not None):
                        if(file.file_hash == hash):
                            path = file.path
                            break
                else:
                    if(filename in c.name and hash == c.file_hash):
                        path = c.path
                        break
                
            if(path != ""):
                with open(path, 'rb') as file:
                    file.seek(start)
                    numbytes = end - start
                    buffer_size = 1024*1024
                    while numbytes:
                        data = file.read(min(numbytes, buffer_size))
                        if not data:
                            break
                        client_socket.send(data)
                        numbytes -= len(data)
                    client_socket.send(b"<END>")
            else:
                client_socket.send(b"<END>")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()

    def normalize_path(self, path):
        return os.path.normpath(path).replace('\\', "/")

    def create_metainfo(self, file_paths):
        metainfo = []
        
        file_paths = file_paths.split(",")

        for file_path in file_paths:
            file_path = self.normalize_path(os.path.abspath(file_path))

            if os.path.isdir(file_path):
                # Multiple-file mode
                temp_path = os.path.basename(file_path)
                
                folder = Folder(path=file_path, name=temp_path)
                print_tree(folder)
                
                with self.file_list_lock:
                    self.container.append(folder)
                metainfo.append({
                    'folder': True,
                    'container': folder
                })
            
            elif os.path.isfile(file_path):
                file = File(file_path)
                with self.file_list_lock:
                    self.container.append(file)
                metainfo.append({
                    'folder': 'False',
                    'container': file
                })

            else:
                print("Invalid input path.")
                return None

        return metainfo
    
    def update_contain(self, contain):
        for i in range(len(self.container)):
            if(isinstance(contain, File)):
                if(contain.name == self.container[i].name):
                    
                    if(self.container[i].status == "Downloaded"):
                        return
                    else:
                        if(self.container[i].path == None):
                            self.container[i].set_path(os.path.abspath(DOWNLOAD_PATH))
                        self.container[i].change_status(contain.status)
                else:
                    if(isinstance(self.container[i], Folder)):
                        path = self.container[i].get_file(contain.name)
                    else:
                        path = None
                    
                    if(path is not None):
                        if(path.status == "Downloaded"):
                            return
                        else:
                            if(path.path == None):
                                self.container[i].get_file(contain.name).set_path(os.path.abspath(DOWNLOAD_PATH))
                            self.container[i].get_file(contain.name).change_status(contain.status)
            elif(isinstance(contain, Folder)):
                if(contain.name == self.container[i].name):
                    
                    if(self.container[i].status == "Downloaded"):
                        return
                    else:
                        if(self.container[i].path == None):
                            self.container[i].set_path(os.path.abspath(DOWNLOAD_PATH))
                        self.container[i].change_status(contain.status)
                else:
                    if(isinstance(self.container[i], Folder)):
                        path = self.container[i].get_subfolder(contain.name)
                    else:
                        path = None
                    
                    if(path is not None):
                        if(path.status == "Downloaded"):
                            return
                        else:
                            if(path.path == None):
                                self.container[i].set_path(os.path.abspath(DOWNLOAD_PATH))
                            self.container[i].change_status(contain.status)
            
    def update_file_list(self):
        for i in range(len(self.container)):
            if(isinstance(self.container[i], Folder)):
                self.container[i].update_folder(os.path.abspath(DOWNLOAD_PATH))
            
    def request_file_list(self):
        message = json.dumps({'command': 'list'})
            
        self.client_to_tracker.send(message.encode())
        
        response = self.client_to_tracker.recv(PIECE_SIZE)
        
        try:
            share_list = pickle.loads(response)
        except Exception as e:
            print(f"Error unpickling data: {e}")
        
        for i in range(len(share_list)):
            try:
                
                id = self.container.index(share_list[i])
                
                if(id > -1):
                    share_list[i] = self.container[id]
                    if os.path.exists(self.container[id].path):
                        share_list[i].change_status("Downloaded")
            except Exception as e:
                print(e)
                share_list[i].change_status("")
                share_list[i].remove_path()
            
        self.container=share_list
        return share_list
    
    def upload_folder(self, folder: Folder): #TODO: Gửi folder lên tracker
        message = json.dumps({'command': 'upload'}).encode()
        
        self.client_to_tracker.send(message)
        res = self.client_to_tracker.recv(PIECE_SIZE).decode()
        if(res == "received"):

            message = pickle.dumps({'metainfo': folder})
            
            self.client_to_tracker.sendall(message)

            flag = self.client_to_tracker.recv(1024).decode()
            
            if(flag == "True"):
                self.container.append(folder)
            self.client_to_tracker.send("a".encode())
        
    
    def upload_file (self, file: File): #TODO: GỬI FILE
        message = json.dumps({'command': 'upload'}).encode()
        
        self.client_to_tracker.send(message)
        res = self.client_to_tracker.recv(PIECE_SIZE).decode()
        if(res == "received"):

            message = pickle.dumps({'metainfo': file})
            
            self.client_to_tracker.sendall(message)
            
            flag = self.client_to_tracker.recv(1024).decode()
            
            if(flag == "True"):
                self.container.append(file)
            self.client_to_tracker.send("a".encode())

    def request_download_file(self, file_name: str, hash: str):
        
        temp_list = []
        hash_list = []
        out = False
        
        for i in range(len(self.container)):
        
            if(file_name in self.container[i].name and hash == self.container[i].file_hash):
                if(self.container[i].status == "Downloaded"):
                    out = True
                    break
                else:
                    self.container[i].change_status("Downloading")
                    temp_list.append(file_name)
                    hash_list.append(hash)
                    break
            else:
                if(isinstance(self.container[i], Folder)):
                    path = self.container[i].get_file(file_name)
                    
                    if(path is not None):
                        if(path.status == "Downloaded"):
                            out = True
                            break
                        else:
                            path.change_status("Downloading")
                            temp_list.append(path.name)
                            
                            hash_list.append(path.file_hash)
                            break
        if(out):
            print(f"You already have {file_name}.")
            return
        
        self.manage_downloads(temp_list, hash_list)
    
    def request_download_folder(self, folder_name:str):
        path = os.path.join(DOWNLOAD_PATH, folder_name)
        
        try:
            if(os.path.exists(os.path.dirname(path)) == False):
                os.mkdir(os.path.dirname(path))
        except:
            os.makedirs(os.path.dirname(path))

        temp_list = []
        hash_list = []
        out = False

        for i in range(len(self.container)):
            file_list = None
            if(folder_name in self.container[i].name):
                if(self.container[i].status == "Downloaded"):
                    out = True
                    break
                else:
                    self.container[i].change_status("Downloading")
                    file_list = self.container[i].get_all_files()
                
            else:
                if (isinstance(self.container[i], Folder)):
                    path = self.container[i].get_subfolder(folder_name)
                    if(path is not None):
                        if(path.status == "Downloaded"):
                            out = True
                            break
                        path.change_status("Downloading")
                        file_list = path.get_all_files()
            
            if(file_list is not None):
                for f in file_list:
                    temp_list.append(f)
                break
            
        if(out):
            print(f"You already have {folder_name}.")
            return
        
        filename = []
        for f in temp_list:
            name = f.name
            root_folder = f.parent_folder
            temp_folder = f.parent_folder
            
            while root_folder is not None:
                
                name = f"{root_folder.name}{name}"
                
                root_folder = temp_folder.parent_folder
                temp_folder = root_folder
            
            filename.append(name)
            hash_list.append(f.file_hash)
            
        self.manage_downloads(filename, hash_list)
        with self.file_list_lock:
            self.update_file_list()
        
    def sen_process(self, data, q):
        global_response = ""
        
        cmd_id = data.find(" ")

        if(cmd_id < 0):
            cmd = data
            remain_data = ""
        else:
            cmd = data[:cmd_id].strip().lower()
            remain_data = data[cmd_id + 1:]
        
        if cmd == "help":
            message = json.dumps({'command': 'help'})
            
            self.client_to_tracker.send(message.encode())
            
            res = self.client_to_tracker.recv(PIECE_SIZE).decode()

            global_response = res
        elif cmd == "logout":
            message = json.dumps({'command': 'logout'})
            
            self.client_to_tracker.send(message.encode())
            
            res = self.client_to_tracker.recv(PIECE_SIZE).decode()
            
            global_response = res
            q.put(global_response)
            if self.gui: 
                self.gui.event_generate("<<CONSOLE>>")
            return
        elif cmd == "list":
            
            share_list = self.request_file_list()
            for share in share_list:
                if(type(share) == File):
                    global_response += share.name
                else:
                    global_response += tree(share)
                global_response += "\n"
            
        elif cmd == "upload":
            file_paths = remain_data

            file_paths = file_paths.split(",")

            for file_path in file_paths:
                file_path = self.normalize_path(os.path.abspath(file_path))

                if os.path.isdir(file_path):
                    # Multiple-file mode
                    temp_path = os.path.basename(file_path)
                    folder = Folder(path=file_path, name=temp_path)

                    print_tree(folder)
                    self.upload_folder(folder)
                    
                elif os.path.isfile(file_path):
                    file = File(file_path)
                    self.upload_file(file)

                else:
                    print("Invalid input path.")
                    continue
                response = self.client_to_tracker.recv(PIECE_SIZE).decode()
                print(response)
                
            global_response = response

        elif cmd == "download":
            filename = remain_data.split("*")[0]
            
            filename = filename.split(",")
            try:
                hash_list = remain_data.split("*")[1]
                hash_list = hash_list.split(",")
            except:
                print("No hash input")
                hash_list = []
             
            temp_list = []
            remove_list = []
            out = False
            
            for file in filename:
                
                if(file[-1:] == "/"):
                    
                    for i in range(len(self.container)):
                        
                        file_list = None
                        if(file in self.container[i].name):
                            if(self.container[i].status == "Downloaded"):
                                out = True
                                break
                            else:
                                
                                self.container[i].change_status("Downloading")
                                file_list = self.container[i].get_all_files()
                            
                        else:
                            if (isinstance(self.container[i], Folder)):
                                
                                path = self.container[i].get_subfolder(file)
                                if(path is not None):
                                    
                                    if(path.status == "Downloaded"):
                                        out = True
                                        break
                                    path.change_status("Downloading")
                                    file_list = path.get_all_files()
                                    
                        if(file_list is not None):
                            
                            for f in file_list:
                                temp_list.append(f)
                                
                            remove_list.append(file)
                            break
                        
                    if(out):
                        remove_list.append(file)
                        print(f"You already have {file}.")
                        continue

                else:
                    for i in range(len(self.container)):
                        if(file in self.container[i].name):
                            if(self.container[i].status == "Downloaded"):
                                out = True
                                break
                            else:
                                self.container[i].change_status("Downloading")
                                temp_list.append(self.container[i])
                                remove_list.append(file)
                                break
                        else:
                            if(isinstance(self.container[i], Folder)):
                                path = self.container[i].get_file(file)
                                
                                if(path is not None):
                                    if(path.status == "Downloaded"):
                                        out = True
                                        break
                                    else:
                                        path.change_status("Downloading")
                                        temp_list.append(path)
                                        remove_list.append(file)
                                        break
                    
                    if(out):
                        remove_list.append(file)
                        print(f"You already have {file}.")
                        continue

            for r in remove_list:
                filename.remove(r)
            
            for f in temp_list:
                name = f.name
                root_folder = f.parent_folder
                temp_folder = f.parent_folder
                
                while root_folder is not None:
                    name = f"{root_folder.name}{name}"
                    
                    root_folder = temp_folder.parent_folder
                    temp_folder = root_folder
                
                filename.append(name)
                hash_list.append(f.file_hash)
            
            self.manage_downloads(filename, hash_list)
            with self.file_list_lock:
                self.update_file_list()
            
            global_response = ""
        else:
            global_response = "pass"
            
        q.put(global_response)
        if self.gui: 
            self.gui.event_generate("<<CONSOLE>>")

    def sen(self):
        while True:
            data = input("> ")
            
            q = queue.Queue()
            thrSen = threading.Thread(target=self.sen_process, args=(data, q))
            thrSen.start()
            
            answer = q.get()
            print(answer)
            if(answer == "Disconnected from the server."):
                break
    
    def download_file(self, file_name, file_hash=""):
        peer_info = self.request_peerS_info(file_name, file_hash, "request")
        
        if peer_info['peers']:
            size, pieces, hash = 0,0,''
            status, part_data = [], []
            
            for p in peer_info['peers']:
                print(p['ip'], " ", p['port'], " ", p['file'], " ", p['size'], p['pieces'])
                size = p['size']
                pieces = p['pieces']
                hash = p['hash']

            ip_list = []
            port_list = []
            lastpiece_size = size % PIECE_SIZE
            for p in peer_info['peers']:
                ip_list.append(p['ip'])
                port_list.append(p['port'])
            
            n = len(ip_list)
            
            threads = []
            start_time = time.time()

            if (n == 1):
                
                number_thread = 3
                if (pieces < number_thread):
                    start_piece, end_piece = [],[]
                    for i in range(pieces):
                        start_piece.append(i)
                        end_piece.append(i+1)
                    for i in range(pieces):
                        thread = threading.Thread(target=self.download_piece, args=(ip_list[0], port_list[0], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data, file_hash, status))
                        threads.append(thread)
                        thread.start()
                    
                else:
                    chunk_size = pieces // number_thread  # Kích thước của mỗi khoảng
                    remainder = pieces % number_thread  # Phần dư

                    start_piece = [i * chunk_size + min(i, remainder) for i in range(number_thread)]  # Mảng start_byte
                    end_piece = [(i + 1) * chunk_size + min(i + 1, remainder) for i in range(number_thread)]  # Mảng end_byte

                    print(f"Downloading file from {ip_list[0]}:{port_list[0]}")
                    for i in range(number_thread):
                        if i < number_thread - 1:
                            thread = threading.Thread(target=self.download_piece, args=(ip_list[0], port_list[0], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data, file_hash, status))
                        else:
                            if lastpiece_size == 0:
                                thread = threading.Thread(target=self.download_piece, args=(ip_list[0], port_list[0], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data, file_hash, status))
                            else:
                                thread = threading.Thread(target=self.download_piece, args=(ip_list[0], port_list[0], file_name, start_piece[i]*PIECE_SIZE, (end_piece[i]-1)*PIECE_SIZE + lastpiece_size, part_data, file_hash, status))
                        threads.append(thread)
                        thread.start()
                        
            else:
                if(pieces < n):
                    start_piece, end_piece = [],[]
                    for i in range(pieces):
                        start_piece.append(i)
                        end_piece.append(i+1)
                    for i in range(pieces):
                        thread = threading.Thread(target=self.download_piece, args=(ip_list[i], port_list[i], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data, file_hash, status))
                        threads.append(thread)
                        thread.start()
                    
                else:
                    chunk_size = pieces // n  # Kích thước của mỗi khoảng
                    
                    remainder = pieces % n  # Phần dư

                    start_piece = [i * chunk_size + min(i, remainder) for i in range(n)]  # Mảng start_byte
                    end_piece = [(i + 1) * chunk_size + min(i + 1, remainder) for i in range(n)]  # Mảng end_byte
                    
                    for i in range(len(ip_list)):
                        print(f"Downloading file from {ip_list[i]}:{port_list[i]}")
                        if i < len(ip_list) - 1:
                            thread = threading.Thread(target=self.download_piece, args=(ip_list[i], port_list[i], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data, file_hash, status))
                        else:
                            if lastpiece_size == 0:
                                thread = threading.Thread(target=self.download_piece, args=(ip_list[i], port_list[i], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data, file_hash, status))
                            else:
                                thread = threading.Thread(target=self.download_piece, args=(ip_list[i], port_list[i], file_name, start_piece[i]*PIECE_SIZE, (end_piece[i]-1)*PIECE_SIZE + lastpiece_size, part_data, file_hash, status))
                        threads.append(thread)
                        thread.start()
                        
            for thread in threads:
                thread.join()

            done = True
            fail_start, fail_end = [],[]
            
            for stt in status:
                if stt[2] == "Failed":
                    done = False
                    fail_start.append(stt[0])
                    fail_end.append(stt[1])
            fail_len = len(fail_start) 
            
            if done == False:
                while not done:
                    new_info = self.request_peerS_info(file_name, file_hash, "request again")
                    if new_info and new_info['peers']:
                        new_threads = []
                        status = []
                        new_ip_list = []
                        new_port_list = []

                        for np in new_info['peers']:
                            new_ip_list.append(np['ip'])
                            new_port_list.append(np['port'])
                        new_len = len(new_ip_list)

                        if new_len < fail_len:
                            k = 0
                            for index in range(fail_len):
                                new_thread = threading.Thread(target=self.download_piece, args=(new_ip_list[k], new_port_list[k], file_name, fail_start[index], fail_end[index] , part_data, file_hash, status))
                                k += 1
                                if k == new_len:
                                    k = 0
                                new_threads.append(new_thread)
                                new_thread.start()
                        else:
                            k = 0
                            for index in range(fail_len):
                                new_thread = threading.Thread(target=self.download_piece, args=(new_ip_list[k], new_port_list[k], file_name, fail_start[index], fail_end[index] , part_data, file_hash, status))
                                k += 1
                                new_threads.append(new_thread)
                                new_thread.start()
                        for newthread in new_threads:
                            newthread.join()

                        done = True
                        fail_start, fail_end = [],[]
                        for newstt in status:
                            if newstt[2] == "Failed":
                                done = False
                                fail_start.append(newstt[0])
                                fail_end.append(newstt[1])
                        fail_len = len(fail_start)
                    else:
                        print("No peer found with the requested file.")
                        break

            if done == True:
                part_data.sort(key=lambda x: x[0])
                try:
                    file = p['file']
                    file.name = file_name
                    
                    sha1 = hashlib.sha1()
                    hash_sum = ""
                    
                    path = os.path.join(DOWNLOAD_PATH, file_name)
                    
                    try:
                        if(os.path.exists(os.path.dirname(path)) == False):
                            os.mkdir(os.path.dirname(path))
                    except:
                        os.makedirs(os.path.dirname(path))
                    with open(path, 'wb') as result_file:
                        
                        if(len(part_data) == 0):
                            path = os.path.join(DOWNLOAD_PATH, file_name)
                            
                            try:
                                if(os.path.exists(os.path.dirname(path)) == False):
                                    os.mkdir(os.path.dirname(path))
                            except:
                                os.makedirs(os.path.dirname(path))
                            
                            with self.file_list_lock:
                                file.status = f"Downloaded"
                                self.update_contain(file)
                            
                            hash_sum = sha1.update("".encode())
                            hash_sum = sha1.hexdigest()
                        for _ , file_bin in part_data:
                            
                            with open(file_bin, 'rb') as file_read:
                                while True:
                                    
                                    chunk = file_read.read(PIECE_SIZE)
                                    
                                    if not chunk:
                                        
                                        with self.part_data_lock:
                                            file.status = f"Downloaded"
                                            self.update_contain(file)
                                        break
                                    else:
                                        
                                        hash_sum = sha1.update(chunk)
                                        
                                        result_file.write(chunk)
                                        
                                        percent = round(float(result_file.tell() / size * 100))
                                        if(percent == 100):
                                            file.status = f"Downloaded"
                                        else:
                                            file.status = f"Downloading: {percent}"
                                        
                                        with self.part_data_lock:
                                            self.update_contain(file)
                                    hash_sum = sha1.hexdigest()
                                    
                            os.remove(file_bin)
                    result_file.close()

                    end_time = time.time()

                    total_time = round(end_time - start_time, 2)
                    
                    if(hash_sum == hash):
                        print(f"File {file_name} has been downloaded within {total_time}.")
                    else:
                        print(f"Hash difference.")
                except Exception as e:
                    print(e)
            
        else:
            print("No peer found with the requested file.")

    def manage_downloads(self, requested_files, hash_list):
        threads = []
        
        for file_name in requested_files:
            thread = threading.Thread(target=self.download_file, args=(file_name, hash_list[requested_files.index(file_name)]))

            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        print(f"Download finish.")
        
    def run(self, gui:tk.Tk, tk_to_peer_q:queue.Queue, peer_to_tk_q:queue.Queue) -> None: #similar to send, wait for a command
        q = queue.Queue()
        self.gui = gui
        while True:
            message = tk_to_peer_q.get() #block here
            print (message)
            if message is None:  # None is our signal to exit the thread
                break
            
            elif message == "CONNECT":
                result = self.connect_tracker()
                if(result):
                    self.register_with_tracker()
                    
                    if(os.path.exists(DOWNLOAD_PATH) == False):
                        os.mkdir(DOWNLOAD_PATH)
                
                    self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.server_socket.bind((self.my_ip, self.my_port))
                    self.server_socket.listen(MAX_LISTEN)
                    
                    threading.Thread(target=self.accept_connections, daemon=True).start()
                peer_to_tk_q.put(result)
                gui.event_generate("<<ReceiveLogin>>", when="tail")
                
            elif message == "CONSOLE":
                message = tk_to_peer_q.get() #block here
                if self.gui:
                    thrSen = threading.Thread(target=self.sen_process, args=(message, peer_to_tk_q))
                    thrSen.start()
                
            elif message == "GET LIST":
                with self.file_list_lock:
                    self.container = self.request_file_list()
                
                gui.event_generate("<<DisplayList>>", when="tail")
                
            elif message == "SHARE FOLDER":
                new_folder = tk_to_peer_q.get()
                with self.file_list_lock:
                    self.upload_folder(new_folder)
                    print(self.client_to_tracker.recv(1024).decode())

                gui.event_generate("<<DisplayList>>", when="tail")

            elif message == "SHARE FILE":
                new_file = tk_to_peer_q.get()
                with self.file_list_lock:
                    self.upload_file(new_file)
                    print(self.client_to_tracker.recv(1024).decode())

                gui.event_generate("<<DisplayList>>", when="tail")

            elif message == "DOWNLOAD FILE":
                file_hash, file_name = tk_to_peer_q.get()
                self.request_download_file(file_name=file_name, hash=file_hash)

            elif message == 'DOWNLOAD FOLDER':
                folder_name = tk_to_peer_q.get()
                self.request_download_folder(folder_name)
            else:
                pass
    
if __name__ == "__main__":
    TRACKER_IP = input("Please enter Tracker's IP you want to connect:")
    TRACKER_PORT = input("Please enter port of the Tracker above:")
    my_port = input("Please enter your port number:")
    
    peer = Peer()
    peer.login(TRACKER_IP, TRACKER_PORT, MY_IP, my_port)

    peer.sen()
    print("End Peer.")
