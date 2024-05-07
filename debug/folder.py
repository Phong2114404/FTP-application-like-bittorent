import socket, math
import json, hashlib
import threading, queue
import sys
import os
import tqdm

PIECE_SIZE = 2 ** 20

class InvalidPathError(Exception):
    pass

class File:
    def __init__(self, path:str, file_hash=None, name = None, parent_folder=None, status='Downloaded'):
        path = path.replace("\\", "/").strip()
        if not os.path.exists(path): raise InvalidPathError(f"The new path \"{path}\" is not a valid path.")
        if name is None: self.name = os.path.basename(path)
        else:            self.name = name
        
        self.path = path
        self.size = os.path.getsize(path)
        self.local_size = self.size
        self.pieces = math.ceil(self.size/PIECE_SIZE)
        self.treeview_id = None
        
        if file_hash is None:
            self.file_hash = self._calculate_hash(self.path)
        else:
            self.file_hash = file_hash
            
        self.parent_folder = parent_folder
        self.status = status
        
    def __eq__(self, other):
        if isinstance(other, File):
            if (self.name == other.name) and (self.file_hash == other.file_hash):
                return True
            else: 
                return False
        return False

    def set_treeview_id(self, new_id):
        self.treeview_id = new_id

    def remove_path(self):
        self.path = None

    def change_file(self, file):
        self = file
        return self
    
    def change_status(self, status):
        self.status = status

    def set_path(self, new_path):
        # Normalize the new path and ensure it ends with a slash
        new_path = new_path.replace("\\", "/").strip()
        # if not os.path.exists(new_path): raise InvalidPathError(f"The new path \"{new_path}\" is not a valid path.")
        new_path = os.path.join(os.path.normpath(new_path), '')
        
        # Update the file's path
        self.path = os.path.join(new_path, self.name)
        self.path = self.path.replace("\\", "/").strip()

    def _calculate_hash(self, file_path) -> str:
        sha1 = hashlib.sha1()
        hash_sum = ""
        with open(file_path, 'rb') as file:
            piece_offset = 0
            piece = file.read(PIECE_SIZE)
            while piece:
                hash_sum = sha1.update(piece)
                piece_offset += len(piece)
                piece = file.read(PIECE_SIZE)
        hash_sum = sha1.hexdigest()
        return hash_sum
    
    def detach_parent(self):
        if self.parent_folder:
            self.parent_folder.files.remove(self)
            self.parent_folder = None
class Folder:
    def __init__(self, path:str, name = None, parent_folder=None, status ="Downloaded"):
        path = path.replace("\\", "/").strip()
        if not os.path.isdir(path):
            raise InvalidPathError(f"The path \"{path}\" is not a valid directory.")
        
        if name is None: self.name = os.path.basename(os.path.normpath(path)) +"/"
        else:            
            if(name[-1] != "/"):
                name += "/"
            self.name = name
        
        self.path = path
        self.size = 0
        self.local_size = 0
        self.parent_folder = parent_folder
        self.child_folders = []
        self.files = []
        self.status = status
        self.treeview_id = None
        
        self._initialize_folder_structure()

    def __eq__(self, other):
        if isinstance(other, Folder):
            # Compare folder names
            if self.name != other.name or self.size != other.size:
                return False
            else:
                return True
        else:
            return False
    
    def set_treeview_id(self, new_id):
        self.treeview_id = new_id

    def _initialize_folder_structure(self):
        for root, dirs, files in os.walk(self.path):
            # Skip files if the current root is not the folder's path
            if os.path.normpath(root) != os.path.normpath(self.path):
                continue

            # Add folders
            for dir_name in dirs:
                folder_path = os.path.join(root, dir_name)
                folder = Folder(folder_path, parent_folder=self, status=self.status)
                self.add_folder(folder)
            
            # Add files
            for file_name in files:
                file_path = os.path.join(root, file_name)
                file_hash = self._calculate_hash(file_path)
                file = File(file_path, file_hash=file_hash,  name=file_name, parent_folder=self, status=self.status)
                self.add_file(file)

    def add_file(self, file):
        file.path = f"{self.path}/{file.name}"
        file.parent_folder = self
        self.files.append(file)

    def add_folder(self, folder):
        folder.path = f"{self.path}/{folder.name}"
        folder.parent_folder = self
        self.child_folders.append(folder)

    def remove_path(self):
        # Set the folder's path to None
        self.path = None
        # Set the path of each file in this folder to None
        for file in self.files:
            file.remove_path()
        # Recursively set the path of each child folder to None
        for folder in self.child_folders:
            folder.remove_path()

    def change_folder(self, folder):
        self = folder
        return self
    
    def update_folder(self, new_path):
        if self.status == "Downloaded":
            return
        
        for folder in self.child_folders:
            folder.update_folder(new_path)
        
        for file in self.files:
            if file.status != "Downloaded":
                return
        
        all_child_folders_downloaded = all(folder.status == "Downloaded" for folder in self.child_folders)
        if all_child_folders_downloaded and self.status != "Downloaded":
            self.status = "Downloaded"
            self.set_path(new_path)
            
        # Check if the parent folder exists and update its status if needed
        if self.parent_folder is not None and self.parent_folder != self:
            self.parent_folder.update_folder(new_path)

    def change_status(self, status):
        # Set the folder's path to None
        self.status = status
        # Set the path of each file in this folder to None
        for file in self.files:
            file.change_status(status)
        # Recursively set the path of each child folder to None
        for folder in self.child_folders:
            folder.change_status(status)
    
    def set_path(self, new_path):
        # Normalize the new path and ensure it ends with a slash
        new_path = new_path.replace("\\", "/").strip()
        # if not os.path.isdir(new_path): raise InvalidPathError(f"The path \"{new_path}\" is not a valid directory.")
        new_path = os.path.join(os.path.normpath(new_path), '')
        # Update the folder's path
        self.path = os.path.join(new_path, self.name)
        self.path = self.path.replace("\\", "/").strip()
        
        # Update the paths of all files in this folder
        for file in self.files:
            file.set_path(self.path)
        
        # Recursively update the paths of all child folders
        for folder in self.child_folders:
            folder.set_path(self.path)
    
    def _calculate_hash(self, file_path)->str:
        sha1 = hashlib.sha1()
        hash_sum = ""
        with open(file_path, 'rb') as file:
            piece_offset = 0
            piece = file.read(PIECE_SIZE)
            while piece:
                hash_sum = sha1.update(piece)
                piece_offset += len(piece)
                piece = file.read(PIECE_SIZE)
        hash_sum = sha1.hexdigest()
        return hash_sum

    def get_subfolder(self, subfolder_path: str):
        subfolder_path = subfolder_path.replace("\\", "/").strip().rstrip('/')
        subfolder_names = subfolder_path.split("/")
        current_folder = self

        if(len(subfolder_names) != 0):
            subfolder_names.remove(subfolder_names[0])

        for subfolder_name in subfolder_names:
            found_subfolder = None
            for folder in current_folder.child_folders:
                if subfolder_name in folder.name:
                    found_subfolder = folder
                    break

            if found_subfolder:
                current_folder = found_subfolder
            else:
                return None  # Subfolder not found

        if isinstance(current_folder, Folder):
            return current_folder
        else: 
            return None
        
    def get_file(self, file_path:str, hash=None):
        if file_path:
            file_path = file_path.replace("\\", "/").strip()
            if file_path != file_path.rstrip('/'): return None
            
            parts = file_path.split('/')
            file_name = parts[-1]
            subfolder_names = parts[:-1]
            
            #First layer
            for file in self.files:
                if (file.name == file_name) and isinstance(file, File) and ((hash is None) or (file.file_hash == hash)):
                    return file
            if(len(subfolder_names) != 0):
                subfolder_names.remove(subfolder_names[0])

            # Traverse the subfolders
            current_folder = self
            found = False
            for subfolder_name in subfolder_names:
                found = False
                for folder in current_folder.child_folders:
                    if subfolder_name in folder.name:
                        current_folder = folder
                        found = True
                        break
            if not found:
                return None  # Subfolder not found

            # Look for the file in the final subfolder
            for file in current_folder.files:
                if (file.name == file_name) and isinstance(file, File) and ((hash is None) or (file.file_hash == hash)):
                    return file  # File found

            return None 
        elif hash:
            for file in self.files:
                if file.file_hash == hash:
                    return file

            # Recursively check all subfolders
            for folder in self.child_folders:
                found_file = folder.get_file(file_path=None, hash=hash)
                if found_file:
                    return found_file

            return None 
    def get_all_files(self):
        all_files = []
        all_files.extend(self.files)

        for child_folder in self.child_folders:
            all_files.extend(child_folder.get_all_files())

        return all_files
    
    def get_all_file_names (self):
        all_files = self.get_all_files()
        file_names = [file.name for file in all_files]
        return file_names
    
    def detach_parent(self):
        if self.parent_folder:
            self.parent_folder.child_folders.remove(self)
            self.parent_folder = None

def tree(folder:Folder, indent='')->str:
    lines = []  # List to hold the lines of the folder structure

    # Function to add lines to the list
    def add_line(text):
        lines.append(text)

    # Recursive function to build the folder structure
    def build_tree(folder:Folder, indent=''):
        add_line(f"{indent}{folder.name}")
        new_indent = indent + '│   '

        for file in folder.files:
            add_line(f"{new_indent}{file.name}")

        for i, child_folder in enumerate(folder.child_folders):
            if i == len(folder.child_folders) - 1:
                sub_indent = indent + '    '
            else:
                sub_indent = indent + '│   '
            build_tree(child_folder, sub_indent)

    build_tree(folder)  # Start building the tree from the root folder
    return '\n'.join(lines)  # Join all the lines into a single string and return

def print_tree(folder:Folder, indent=''):
    # Print the current folder name
    print(f"{indent}{folder.name} {folder.status} {folder.path}")
    new_indent = indent + '│   '

    # Print all the files in the current folder
    for file in folder.files:
        print(f"{new_indent}{file.name} {file.status} {file.path}")

    # Recursively print the child folders
    for i, child_folder in enumerate(folder.child_folders):
        # Check if this is the last child folder to adjust the tree branch symbol
        if i == len(folder.child_folders) - 1:
            sub_indent = indent + '    '
        else:
            sub_indent = indent + '│   '
        print_tree(child_folder, sub_indent)