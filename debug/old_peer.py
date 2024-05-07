import socket
import json
import threading
import sys
import os
import tqdm

TRACKER_IP = '172.17.26.111'
TRACKER_PORT = 9999
SIZE = 1024
FORMAT = 'utf-8'

class Peer:
    # init peer
    def __init__(self, tracker_host, tracker_port, my_ip, my_port, files):
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.my_ip = my_ip
        self.my_port = my_port
        self.files = files

        sizes =[]
        for file in files:
            sizes.append(os.path.getsize(file))
        self.sizes = sizes
        

        # connect to tracker
        self.register_with_tracker()

        # socket to connect other peer
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.my_ip, self.my_port))
        self.server_socket.listen()
        
        # while True:   
        #     client_socket, addr = self.server_socket.accept()
        threading.Thread(target=self.accept_connections, daemon=False).start()

    def register_with_tracker(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((self.tracker_host, self.tracker_port))
            message = json.dumps({
                'command': 'register',
                'files': self.files,
                'ip': self.my_ip,
                'port': self.my_port,
                'sizes': self.sizes
            })
            client_socket.send(message.encode())
    
# lấy info peer từ tracker, yêu cầu kết nối và nhận file:
    # lấy info peer
    def request_peer_info(self, filename):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((self.tracker_host, self.tracker_port))
            message = json.dumps({'command': 'request', 'file': filename})
            client_socket.send(message.encode())
            response = client_socket.recv(1024)
            if not response:
                print("No data received")
                return None
            try:
                return json.loads(response.decode())
            except json.JSONDecodeError:
                print("Failed to decode JSON from response")
                return None


    # receive file (dữ liệu nhận ghi vào filename)
    def download_file(self, ip_sender, port_sender, filename, start, end):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip_sender, port_sender))

            # s.send(filename.encode())

            # s.recv(1024)

            # s.send(str(start).encode())

            # s.recv(1024)

            # s.send(str(end).encode())

            # print(start, " ", end)

            # Sending filename, start, and end as a single message separated by a special character
            message = f"{filename}:{start}:{end}"
            s.send(message.encode())

            # Await confirmation before continuing
            response = s.recv(1024).decode()
            if response == "done":
                print(f"Start: {start}, End: {end} sent successfully.")
            else:
                print("Failed to send data correctly.")

            # received_file_name = s.recv(1024).decode()
            # print(received_file_name," ")

            # file_size = s.recv(1024).decode()
            # print(file_size," ")

            # file = open(received_file_name, "wb")

            file_bytes = b""

            done = False

            progress = tqdm.tqdm(unit="B", unit_scale=True, unit_divisor=1000, 
                                 total=int(end-start))
            
            while not done:
                data = s.recv(1024)
                if data[-5:] == b"<END>":
                    done = True
                    file_bytes += data[:-5]
                else:
                    file_bytes += data
                progress.update(1024)

            with part_data_lock:
                part_data.append(file_bytes)

            # file.write(file_bytes)

        except Exception as e:
            print(f"Error in download_file: {e}")
        finally:
            s.close()

    
# lắng nghe, chấp nhận kết nối và gửi file:
    # chấp nhận kết nối
    def accept_connections(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_peer, args=(client_socket,), daemon=False).start()

    # send file
    def handle_peer(self, client_socket):
        try:
            # filename = client_socket.recv(1024).decode()
            # print(filename)

            # client_socket.send("done".encode())

            # start = client_socket.recv(1024).decode()

            # client_socket.send("done".encode())

            # end = client_socket.recv(1024).decode()
            
            # print(start," ", end)
            # print(type(start))

            data = client_socket.recv(1024).decode()
            if data:
                parts = data.split(':')  # Split the received data by ':'
                if len(parts) == 3:
                    filename, start_str, end_str = parts
                    print(f"Filename: {filename}")
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

            if filename in self.files:
                # file_size = os.path.getsize(filename)
                # client_socket.sendall(f"{filename:<1024}".encode())
                # client_socket.sendall(f"{file_size:<1024}".encode())
                with open(filename, 'rb') as file:
                    file.seek(start)
                    numbytes = end - start
                    data = file.read(numbytes)
                    client_socket.sendall(data)
                    client_socket.send(b"<END>")
                file.close()

        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()

    def sen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((self.tracker_host, self.tracker_port))
            while True:
                print("startloop")
                data = client.recv(SIZE).decode(FORMAT)
                print(data)
                data = data.split("@")
                cmd, msg = data[0], data[1]

                if cmd == "DISCONNECTED":
                    print(f"[SERVER]: {msg}")
                    break
                elif cmd == "OK":
                    print(f"{msg}")
                
                elif cmd == "GIVE":
                    print(f"{msg}")
                    otherPeer = msg.split(",")

                    peerName = otherPeer[0]
                    peerName = peerName.replace("'", "")
                    peerPort = int(otherPeer[1])
                    
                    print(peerName)
                    print(peerPort)
                    # peerName = "localhost"
                    thrClient = threading.Thread(target=peer_client, args=(peerName, peerPort, data[2]))
                    thrClient.start()

                # if(cmd != "FIND") :
                # print("bef")
                data = input("> ")
                # print(data)
                data = data.split(" ")
                # print(data)
                cmd = data[0]
                # print(cmd)
                # print("af")

                if cmd == "HELP":
                    client.send(cmd.encode(FORMAT))
                elif cmd == "LOGOUT":
                    client.send(cmd.encode(FORMAT))
                    break
                elif cmd == "PEERS":
                    client.send(cmd.encode(FORMAT))
                elif cmd == "REQ":
                    client.send(f"{cmd}@{data[1]}".encode(FORMAT))
                    # client.send(f"{cmd}@'{data[1]}', {data[2]}".encode(FORMAT))
                    # thrClient = threading.Thread(target=peer_client, args=(data[1], int(data[2])))
                    # thrClient.start()

                elif cmd == "LIST":
                    message = json.dumps({'command': 'LIST'})
                    client.send(message.encode())
                    response = client.recv(1024)
                    print(json.loads(response.decode()))
                elif cmd == "DELETE":
                    client.send(f"{cmd}@{data[1]}".encode(FORMAT))
                elif cmd == "UPLOAD":
                    filename = data[1]

                    # filepath = os.path.join(PEER_PATH, filename)

                    # with open(f"{filepath}", "rb") as f:
                    #     text = f.read()

                    # filename = filepath.split("/")[-1]
                    # filesize = os.path.getsize(filepath)

                    # send_data = f"{cmd}@{filename}@{filesize}"
                    send_data = f"{cmd}@{filename}"
                    client.send(send_data.encode(FORMAT))

                    # mes = client.recv(SIZE).decode(FORMAT)
                    # print(mes)
                    
                    # if start == "Start uploading..":
                    #     print(start)
                    #     if(text) :
                    #         client.sendall(text)
                    #         print(client.recv(SIZE).decode(FORMAT))
                    #     client.send("<END>".encode(FORMAT))

                    #     f.close()
                    
                elif cmd == "DOWNLOAD":
                    filename = data[1]

                    peerIp = data[2]
                    peerport = data[3]

                    # peername = peername.split(",")

                    # peerIp = peername[0]
                    # peerport = int(peername[1])
                    client.send(f"{cmd}@{filename}:{peerIp} {peerport}".encode(FORMAT))

                    # print(client.recv(1024).decode(FORMAT))
                    file_list[filename] = client.recv(1024).decode(FORMAT)

                    # filename = data[1]

                    # filepath = os.path.join(PEER_PATH, filename)

                    # send_data = f"{cmd}@{filename}"
                    # client.send(send_data.encode(FORMAT))

                    # start = client.recv(SIZE).decode(FORMAT)
                    # mes, size = start.split('@')
                    # client.send(mes.encode(FORMAT))
                    
                    # if mes == "Start downloading..":
                    #     print(mes)
                    #     file_byte = b""

                    #     done = False

                    #     progress = tqdm.tqdm(unit = "B", unit_scale = True, unit_divisor = 1000,
                    #                         total = int(size))

                    #     while not done:
                    #         # print("Down..")
                    #         data = client.recv(SIZE)
                    #         # print(file_byte)
                            
                    #         if data[-5:] == b"<END>":
                    #             file_byte += data[:-5]
                    #             done = True
                    #             client.send("OK".encode(FORMAT))
                    #         else:
                    #             # print(data)
                    #             file_byte += data
                    #             # client.send("OK".encode(FORMAT))
                    #         # print("end if")
                    #         progress.update(SIZE)
                    #         # print("end 1 loop")

                    #     with open(filepath, "wb") as f:
                    #         f.write(file_byte)

                    #     client.send("Finished Downloading.".encode(FORMAT))  
                else:
                    print("pass")
                    client.send("pass".encode())

                print("endloop")

            print("Disconnected from the server.")

    def server_upload():
        pass

    def Down_from_1_peer(filename, peer_id, num_peer, ip, port):
        pass

    def down_1file_from_multi_peer(filename, num_piece, num_peer, dict_ip_port):
        pass

    def Download_multifile(filename,  num_piece, num_peer, dict_ip_port):
        pass

    
if __name__ == "__main__":
    my_ip = sys.argv[1]
    my_port = int(sys.argv[2])
    files = sys.argv[3].split(',')

    peer = Peer(TRACKER_IP, TRACKER_PORT, my_ip, my_port, files)
    print(peer.files," ",peer.sizes)

    # if the peer need to download a file
    if len(sys.argv) > 4:
        requested_file = sys.argv[4]
        peer_info = peer.request_peer_info(requested_file)
        if peer_info:
            for p in peer_info['peers']:
                print(p['ip'], " ", p['port'], " ", p['file'], " ", p['size'])
                size = p['size']
                pieces = p['pieces']

            ip_list = []
            port_list = []
            lastpiece_size = size % 1024
            for p in peer_info['peers']:
                ip_list.append(p['ip'])
                port_list.append(p['port'])
            
            n = len(ip_list)
            chunk_size = pieces // n  # Kích thước của mỗi khoảng
            remainder = pieces % n  # Phần dư

            # Mảng start_byte
            start_piece = [i * chunk_size + min(i, remainder) for i in range(n)]  
            # Mảng end_byte
            end_piece = [(i + 1) * chunk_size + min(i + 1, remainder) for i in range(n)]  

            data = b''
            part_data = []
            part_data_lock = threading.Lock()
            threads = []
            print("ok!")
            for i in range(len(ip_list)):
                print(f"Downloading file from {ip_list[i]}:{port_list[i]}")
                if i < len(ip_list) - 1:
                    thread = threading.Thread(target=peer.download_file, args=(ip_list[i], port_list[i], requested_file, start_piece[i]*1024, end_piece[i]*1024))
                else:
                    thread = threading.Thread(target=peer.download_file, args=(ip_list[i], port_list[i], requested_file, start_piece[i]*1024, (end_piece[i]-1)*1024 + lastpiece_size))
                
                threads.append(thread)
                thread.start()
                
                # threading.Thread(target=peer.download_file, args=(ip_list[i], port_list[i], requested_file, start_byte[i], end_byte[i])).start()
            
            for thread in threads:
                thread.join()
            
            print("hasagi")

            with part_data_lock:
                for i, result in enumerate(part_data):
                    data += result
            
            file = open(requested_file, "wb")
            file.write(data)

            file.close()
            print(f"File {requested_file} has been downloaded.")
        else:
            print("No peer found with the requested file.")

    

    input("alive: ")