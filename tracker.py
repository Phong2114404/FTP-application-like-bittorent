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
                # print(addr)
                try:
                    data = client_socket.recv(PIECE_SIZE)
                except:
                    print(self.peers)
                    self.peers.pop(addr)
                    print(self.peers)
                    return
                
                # print(data)
                # data = client_socket.recv(PIECE_SIZE)
                if not data:
                    print(f"Connection closed by {addr}")
                    break

                data = json.loads(data.decode())
                command = data['command']

                if command == 'register':

                    # pieces = []
                    # for c in data['container']:
                    #     temp = math.ceil(c.get_size()/PIECE_SIZE)
                    #     c.set_pieces(temp)

                    self.peers[addr] = {
                        # 'folders': [],
                        # 'files': data['files'],
                        'container': data['container'],
                        'ip': data['ip'],
                        'port': data['port'],
                        # 'sizes': data['sizes'],
                        # 'hashes': data['hashes'],
                        # 'pieces': pieces
                    }
                    response = (f"Registered {addr} with container: {data['container']}, IP: {data['ip']}, Port: {data['port']}")
                    client_socket.send(response.encode())
                elif command == 'request':
                    print(data)
                    filename = data['file']
                    file_hash = data['hash']
                    available_peers = []
                    # print(filename[-2:])
                    if(os.path.isabs(filename)):
                        pass
                    else:
                        if(filename[-1:] == "/"):
                            print("req fol")
                            for peer_addr, peer_info in self.peers.items():
                                for conts in peer_info['container']:
                                    # print(file)
                                    # a="a\\sda"
                                    # a.startswith()
                                    # print(file.startswith(filename))
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
                                                # 'hash': peer_info['hashes'][peer_info['files'].index(file)],
                                                # 'size': peer_info['sizes'][peer_info['files'].index(file)],
                                                # 'pieces': peer_info['pieces'][peer_info['files'].index(file)]
                                            })
                                        break
                                    # print(conts)
                                    # print(1)
                                    # for c in conts:
                                    #     c = json.loads(c)
                                    #     print(c)
                                    #     print(2)
                                    #     if c['name'] == filename:
                                            # available_peers.append(
                                            # {
                                            #     'ip': peer_info['ip'],
                                            #     'port': peer_info['port'],
                                            #     'file': c.get_name(),
                                            #     # 'hash': peer_info['hashes'][peer_info['files'].index(file)],
                                            #     # 'size': peer_info['sizes'][peer_info['files'].index(file)],
                                            #     # 'pieces': peer_info['pieces'][peer_info['files'].index(file)]
                                            # })
                        else:
                            print("req file")
                            for peer_addr, peer_info in self.peers.items():
                                for conts in peer_info['container']:
                                    # print(file)
                                    # a="a\\sda"
                                    # a.startswith()
                                    # print(file.startswith(filename))
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
                                                # 'hash': peer_info['hashes'][peer_info['files'].index(file)],
                                                # 'size': peer_info['sizes'][peer_info['files'].index(file)],
                                                # 'pieces': peer_info['pieces'][peer_info['files'].index(file)]
                                            })
                                            break
                                    else:
                                        if(isinstance(conts, Folder)):
                                            print(conts.name)
                                            print(conts.files[0].name)
                                            path = conts.get_file(filename)
                                            print("______")
                                            print(path)
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
                                                        # 'hash': peer_info['hashes'][peer_info['files'].index(file)],
                                                        # 'size': peer_info['sizes'][peer_info['files'].index(file)],
                                                        # 'pieces': peer_info['pieces'][peer_info['files'].index(file)]
                                                    })
                                                break
                                    # if(filename in conts.name or conts.get_file(filename) is not None):
                                        # if(file_hash == conts.hash):
                                        #     available_peers.append(
                                        #     {
                                        #         'ip': peer_info['ip'],
                                        #         'port': peer_info['port'],
                                        #         'file': conts,
                                        #         'hash': conts.hash,
                                        #         'size': conts.size,
                                        #         'pieces': conts.pieces
                                        #         # 'hash': peer_info['hashes'][peer_info['files'].index(file)],
                                        #         # 'size': peer_info['sizes'][peer_info['files'].index(file)],
                                        #         # 'pieces': peer_info['pieces'][peer_info['files'].index(file)]
                                        #     })

                                    # print(conts)
                                    # print(1)
                                    # for c in conts:
                                    #     c = json.loads(c)
                                    #     print(c)
                                    #     print(2)
                                    #     if c['name'] == filename:
                                    #         available_peers.append(
                                    #         {
                                    #             'ip': peer_info['ip'],
                                    #             'port': peer_info['port'],
                                    #             'file': c.get_name(),
                                    #             # 'hash': peer_info['hashes'][peer_info['files'].index(file)],
                                    #             # 'size': peer_info['sizes'][peer_info['files'].index(file)],
                                    #             # 'pieces': peer_info['pieces'][peer_info['files'].index(file)]
                                    #         })
                            # available_peers = [
                            #     {
                            #         'ip': peer_info['ip'],
                            #         'port': peer_info['port'],
                            #         'file': filename,
                            #         # 'hash': peer_info['hashes'][peer_info['files'].index(filename)],
                            #         # 'size': peer_info['sizes'][peer_info['files'].index(filename)],
                            #         # 'pieces': peer_info['pieces'][peer_info['files'].index(filename)]
                            #     }
                            #     for peer_addr, peer_info in self.peers.items() if filename in peer_info['files']
                            # ]
                    print(available_peers)
                    # response = json.dumps({"peers": available_peers}).encode()
                    response = pickle.dumps({"peers": available_peers})
                    client_socket.send(response)

                elif command == 'list':
                    available_files = []
                    for peer_addr, peer_info in self.peers.items():
                        for cont in peer_info['container']:
                            # if(c.get_type() == 'file'):
                            print(cont.name)
                            # temp = cont.get_all_file_names()
                            # print(temp)
                            available_files.append(cont)
                            # conts = json.loads(conts)
                            # print(conts)
                            # print(type(conts))
                            
                            # print(1)
                            # for c in conts:
                            #     c = json.loads(c)
                            #     print(c)
                            #     print(type(c))
                            #     print(2)
                            #     try:
                            #         available_files.index(c['name'])
                            #     except:
                            #         available_files.append(c['name'])
                    print(available_files)
                    # response = json.dumps(available_files).encode()
                    response = pickle.dumps(available_files)
                    # print("in")
                    client_socket.sendall(response)

                elif command == 'upload':
                    flag = True
                    res = ""
                    try:
                        client_socket.send("received".encode())
                        res = client_socket.recv(PIECE_SIZE)
                        # print(res)
                        data = pickle.loads(res)
                        print(data['metainfo'])
                        # for meta in data['metainfo']:
                            # print(meta['container'])
                            # print(type(meta['container']))
                            
                        cont = data['metainfo']
                        print(cont.path)
                        for c in self.peers[addr]['container']:
                            print(c.path)
                            if(c.path == cont.path):
                                try: 
                                    id = self.peers[addr]['container'].index(c)
                                    print(f"haha {id}")
                                    self.peers[addr]['container'][id] = cont
                                    flag = False
                                    res = "0"
                                    break
                                except:
                                    print("????")

                            elif(isinstance(c, Folder)):
                                if(isinstance(cont, File)):
                                    print(5)
                                    path = c.get_file(cont.path)
                                    if(path is not None):
                                        c.get_file(cont.path).change_file(cont)
                                        print(path.file_hash)
                                        flag = False
                                        res = "0"
                                        break
                                elif(isinstance(cont, Folder)):
                                    print(6)
                                    path = c.get_subfolder(cont.path)
                                    if(path is not None):
                                        c.get_subfolder(cont.path).change_folder(cont)
                                        print(path.file_hash)
                                        flag = False
                                        res = "0"
                                        break
                                
                        if(flag):
                            print(10)
                            res = "True"
                            self.peers[addr]['container'].append(cont)
                        # print(cont.file_hash)
                            # if(meta['folder'] == 'True'):
                            #     for fol in cont.child_folders:
                            #         pass

                            # else:
                            #     pass


                            # if(metainfo['container'].get_type() == 'folder'):
                                # for metainfo in data['metainfo']:

                            # self.peers[addr]['container'].append(metainfo['container'])
                            # print(metainfo)

                                # for file in metainfo['files']:
                                #     print(1)
                                #     self.peers[addr]['hashes'].append(metainfo['hashes'][metainfo['files'].index(file)])
                                #     self.peers[addr]['sizes'].append(metainfo['sizes'][metainfo['files'].index(file)])
                                #     print(1)
                                #     self.peers[addr]['pieces'].append(metainfo['num_pieces'][metainfo['files'].index(file)])
                                #     print(1)
                                #     file = os.path.join(metainfo['name'], file)
                                #     file = os.path.normpath(file).replace("\\", "/")
                                #     # print(1)
                                #     self.peers[addr]['files'].append(file)
                                #     print(file)
                            # else:
                            #     # metainfo = data['metainfo']
                            #     print(metainfo)
                            #     self.peers[addr]['hashes'].append(metainfo['hashes'])
                            #     self.peers[addr]['sizes'].append(metainfo['sizes'])
                            #     print(metainfo['sizes'])
                            #     self.peers[addr]['pieces'].append(metainfo['num_pieces'])
                            #     print(metainfo['num_pieces'])
                            #     file = metainfo['files']
                            #     # file = os.path.join(metainfo['name'], file)
                            #     # print(1)
                            #     self.peers[addr]['files'].append(file)
                            #     print(file)
                        
                        print(self.peers[addr])
                        print(1)
                        
                        
                        client_socket.send(res.encode())
                        print(2)
                        client_socket.recv(1024)
                        print("end")
                        client_socket.send("Server has received your file.".encode())
                    except Exception as e:
                        print(e)
                        print(7)
                        client_socket.send("Error".encode())
                        print(8)
                        client_socket.recv(1024)
                        print(9)
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
                    print(1)
                    try:
                        print(2)
                        self.peers.pop(addr)
                        print(3)
                        response = "Disconnected from the server."
                        print(5)
                        client_socket.send(response.encode())
                        print(6)
                        return
                    except:
                        print(4)
                        response = "There is an error while logging out."
                    
                elif command == "request again":
                    print(data)
                    filename = data['file']
                    file_hash = data['hash']
                    available_peers = []
                    if(os.path.isabs(filename)):
                        pass
                    else:
                        if(filename[-1:] == "/"):
                            print("req fol")
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
                                                # 'file': f,
                                            })
                                        break
                        else:
                            print("req file")
                            for peer_addr, peer_info in self.peers.items():
                                for conts in peer_info['container']:
                                    if(filename in conts.name):
                                        if(file_hash == conts.file_hash):
                                            available_peers.append(
                                            {
                                                'ip': peer_info['ip'],
                                                'port': peer_info['port']
                                                # 'file': conts,
                                            })
                                            break
                                    else:
                                        if(isinstance(conts, Folder)):
                                            print(conts.name)
                                            # print(conts.files[0].name)
                                            path = conts.get_file(filename)
                                            print("______")
                                            print(path)
                                            if(path is not None):
                                                if(file_hash == path.file_hash):
                                                    available_peers.append(
                                                    {
                                                        'ip': peer_info['ip'],
                                                        'port': peer_info['port']
                                                        # 'file': path,
                                                        # 'hash': path.file_hash,
                                                        # 'size': path.size,
                                                        # 'pieces': path.pieces
                                                    })
                                                break
                    print(available_peers)
                    # response = json.dumps({"peers": available_peers}).encode()
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
            # self.peers.pop(addr, None)  # Remove the peer from the dictionary
            # print(f"Peer {addr} disconnected and removed.")
            # for a, b in self.peers.items():
            #     print(b['ip']," ",b['port'],end='\n')

if __name__ == "__main__":
    tracker = Tracker()
    tracker.start_server()
