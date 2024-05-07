import socket
import threading, os
import json, pickle
import math
from folder import *

TRACKER_IP = socket.gethostbyname(socket.gethostname())
TRACKER_PORT = 9999
PIECE_SIZE = 2 ** 20

class Tracker:
    def __init__(self, host=TRACKER_IP, port=TRACKER_PORT):
        self.host = host
        self.port = port
        self.peers = {}  # Dictionary to hold peer information

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Tracker running on {self.host}:{self.port}")
        while True:
            client_socket, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket, addr)).start()

    def get_host(self):
        return self.host
    
    def get_port(self):
        return self.port
    
    def get_peers(self):
        return self.peers

    def handle_client(self, client_socket, addr):
        try:
            while True:
                try:
                    data = client_socket.recv(PIECE_SIZE)
                except:
                    self.peers.pop(addr)
                    print(self.peers)
                    return
                
                if not data:
                    print(f"Connection closed by {addr}")
                    break

                data = json.loads(data.decode())
                command = data['command']

                if command == 'register':
                    self.peers[addr] = {
                        'container': data['container'],
                        'ip': data['ip'],
                        'port': data['port'],
                    }
                    response = (f"Registered {addr} with container: {data['container']}, IP: {data['ip']}, Port: {data['port']}")
                    print(response)
                    client_socket.send(response.encode())
                elif command == 'request':
                    
                    filename = data['file']
                    file_hash = data['hash']
                    available_peers = []
                    
                    if(os.path.isabs(filename)):
                        pass
                    else:
                        if(filename[-1:] == "/"):
                            for peer_addr, peer_info in self.peers.items():
                                for conts in peer_info['container']:
                                    if(filename in conts.name):
                                        file_list = conts.get_all_files()
                                        
                                    else:
                                        if (isinstance(c, Folder)):
                                            path = conts.get_subfolder(filename)
                                            if(path is not None):
                                                file_list = path.get_all_files()
                                    
                                    if file_list is not None:
                                        for f in file_list:
                                            available_peers.append(
                                            {
                                                'ip': peer_info['ip'],
                                                'port': peer_info['port'],
                                                'file': f,
                                                'hash': f.file_hash,
                                                'size': f.size,
                                                'pieces': f.pieces
                                            })
                                        break
                        
                        else:
                            for peer_addr, peer_info in self.peers.items():
                                for conts in peer_info['container']:
                                    if(filename in conts.name):
                                        if(file_hash == conts.file_hash):
                                            available_peers.append(
                                            {
                                                'ip': peer_info['ip'],
                                                'port': peer_info['port'],
                                                'file': conts,
                                                'hash': conts.file_hash,
                                                'size': conts.size,
                                                'pieces': conts.pieces
                                            })
                                            break
                                    else:
                                        if(isinstance(conts, Folder)):
                                            path = conts.get_file(filename)
                                            
                                            if(path is not None):
                                                if(file_hash == path.file_hash):
                                                    available_peers.append(
                                                    {
                                                        'ip': peer_info['ip'],
                                                        'port': peer_info['port'],
                                                        'file': path,
                                                        'hash': path.file_hash,
                                                        'size': path.size,
                                                        'pieces': path.pieces
                                                    })
                                                break
                                    
                    response = pickle.dumps({"peers": available_peers})
                    client_socket.send(response)

                elif command == 'list':
                    available_files = []
                    for peer_addr, peer_info in self.peers.items():
                        for cont in peer_info['container']:
                            
                            flag = True
                            for a in available_files:
                                if(a.name == cont.name and a.file_hash == cont.file_hash):
                                    flag = False
                                    break
                            if(flag):
                                available_files.append(cont)
                            
                    response = pickle.dumps(available_files)
                    client_socket.sendall(response)

                elif command == 'upload':
                    flag = True
                    res = ""
                    try:
                        client_socket.send("received".encode())
                        res = client_socket.recv(PIECE_SIZE)
                        
                        data = pickle.loads(res)
                        
                        cont = data['metainfo']
                        
                        for c in self.peers[addr]['container']:
                            if(c.path == cont.path):
                                try: 
                                    id = self.peers[addr]['container'].index(c)
                                    self.peers[addr]['container'][id] = cont
                                    flag = False
                                    res = "0"
                                    break
                                except:
                                    pass

                            elif(isinstance(c, Folder)):
                                if(isinstance(cont, File)):
                                    path = c.get_file(cont.path)
                                    if(path is not None):
                                        c.get_file(cont.path).change_file(cont)
                                        flag = False
                                        res = "0"
                                        break
                                elif(isinstance(cont, Folder)):
                                    path = c.get_subfolder(cont.path)
                                    if(path is not None):
                                        c.get_subfolder(cont.path).change_folder(cont)
                                        flag = False
                                        res = "0"
                                        break
                                
                        if(flag):
                            res = "True"
                            self.peers[addr]['container'].append(cont)
                        
                        client_socket.send(res.encode())
                        
                        client_socket.recv(1024)
                        
                        client_socket.send("Server has received your file.".encode())
                    except Exception as e:
                        print(e)
                        client_socket.send("Error".encode())
                        
                        client_socket.recv(1024)
                        
                        client_socket.send("Server can't received your file.".encode())

                elif command == 'help':
                    response = ""
                    response += "list: List all shared files.\n"
                    response += "upload <filename>: Upload file(s)/folder to the server. Ex: upload a,b.txt\n"
                    response += "download <file>: Download file(s)/folder from other peer(s). Ex: download a,b.txt\n"
                    response += "logout: Disconnect from the server.\n"
                    response += "help: List all the commands."
                    
                    client_socket.send(response.encode())

                elif command == 'logout':
                    try:
                        self.peers.pop(addr)
                        
                        response = "Disconnected from the server."
                        
                        client_socket.send(response.encode())
                        return
                    except:
                        response = "There is an error while logging out."
                    
                elif command == "request again":
                    filename = data['file']
                    file_hash = data['hash']
                    available_peers = []
                    if(os.path.isabs(filename)):
                        pass
                    else:
                        if(filename[-1:] == "/"):
                            for peer_addr, peer_info in self.peers.items():
                                for conts in peer_info['container']:
                                    if(filename in conts.name):
                                        file_list = conts.get_all_files()
                                        
                                    else:
                                        if (isinstance(c, Folder)):
                                            path = conts.get_subfolder(filename)
                                            if(path is not None):
                                                file_list = path.get_all_files()
                                    
                                    if file_list is not None:
                                        for f in file_list:
                                            available_peers.append(
                                            {
                                                'ip': peer_info['ip'],
                                                'port': peer_info['port']
                                            })
                                        break
                        else:
                            for peer_addr, peer_info in self.peers.items():
                                for conts in peer_info['container']:
                                    if(filename in conts.name):
                                        if(file_hash == conts.file_hash):
                                            available_peers.append(
                                            {
                                                'ip': peer_info['ip'],
                                                'port': peer_info['port']
                                            })
                                            break
                                    else:
                                        if(isinstance(conts, Folder)):
                                            path = conts.get_file(filename)
                                            
                                            if(path is not None):
                                                if(file_hash == path.file_hash):
                                                    available_peers.append(
                                                    {
                                                        'ip': peer_info['ip'],
                                                        'port': peer_info['port']
                                                    })
                                                break
                    
                    response = pickle.dumps({"peers": available_peers})
                    client_socket.send(response)
                else:
                    pass
        except ConnectionResetError:
            print(f"Connection was forcibly closed by {addr}")
        except socket.error as e:
            print(f"Socket error: {e}")
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()

if __name__ == "__main__":
    tracker = Tracker()
    tracker.start_server()
