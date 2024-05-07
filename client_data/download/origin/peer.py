import socket
import json
import threading
import sys
import os
import tqdm
import hashlib
import numpy as np
import asyncio
PIECE_SIZE = 1024*1024

class Peer:
    # init peer
    def __init__(self, tracker_host, tracker_port, my_ip, my_port, files):
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.my_ip = my_ip
        self.my_port = my_port
        self.files = files
        self.download_rates = []
        self.part_data_lock = threading.Lock()

        sizes, hashes = [],[]
        for file in files:
            sizes.append(os.path.getsize(file))
            part_hash = self.create_hash_file(file)
            hashes.append(part_hash)

        self.hashes = hashes
        self.sizes = sizes

        # connect to tracker
        self.register_with_tracker()

        # socket to connect other peer
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.my_ip, self.my_port))
        self.server_socket.listen()
        
        threading.Thread(target=self.accept_connections, daemon=False).start()

    def register_with_tracker(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((self.tracker_host, self.tracker_port))
            message = json.dumps({
                'command': 'register',
                'files': self.files,
                'ip': self.my_ip,
                'port': self.my_port,
                'sizes': self.sizes,
                'hashes': self.hashes
            })
            client_socket.send(message.encode())

    #Tạo tổng hash của file_name
    def create_hash_file(self, file_name):
        hash_sum = ""
        with open(file_name, 'rb') as file:
            piece_offset = 0
            piece = file.read(PIECE_SIZE)
            while piece:
                piece_hash = hashlib.sha256(piece).hexdigest()
                hash_sum += piece_hash
                piece_offset += len(piece)
                piece = file.read(PIECE_SIZE)

        return hash_sum
    
    def create_hash_data(self, data):
        sum_hash = ""
        offset = 0
        
        while offset < len(data):
            piece = data[offset:offset+PIECE_SIZE]
            piece_hash = hashlib.sha256(piece).hexdigest()
            sum_hash += piece_hash
            offset += PIECE_SIZE
        
        return sum_hash
    
# lấy info peer từ tracker, yêu cầu kết nối và nhận file:
    # lấy info peer
    def request_peer_info(self, filename):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((self.tracker_host, self.tracker_port))
            message = json.dumps({'command': 'request', 'file': filename})
            client_socket.send(message.encode())
            response = client_socket.recv(1024*1024)
            if not response:
                print("No data received")
                return None
            try:
                return json.loads(response.decode())
            except json.JSONDecodeError:
                print("Failed to decode JSON from response")
                return None


    # receive file (dữ liệu nhận ghi vào filename)
    def download_piece(self, ip_sender, port_sender, filename, start, end, part_data):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip_sender, port_sender))

            
            message = f"{filename}:{start}:{end}"
            s.send(message.encode())

            # Await confirmation before continuing
            response = s.recv(1024).decode()
            if response == "done":
                print(f"Start: {start}, End: {end} sent successfully.")
            else:
                print("Failed to send data correctly.")

            arr = []
            done = False
            progress = tqdm.tqdm(unit="B", unit_scale=True, unit_divisor=1000, total=int(end-start))
            
            
            # Nhận dữ liệu từ sender
            buffer_size = 1024*1024
            while not done:
                # part_bytes = b""
                data = s.recv(buffer_size)
                if data[-5:] == b"<END>":
                    done = True
                    # part_bytes = data[:-5]
                    arr.append(data[:-5])
                else:
                    # part_bytes = data
                    arr.append(data)
                # arr.append(part_bytes)
                progress.update(len(data))
            
            # for file_data in arr:
            #     file_bytes += file_data
            print(f"start merge piece")

            file_path = f"{start}.bin"
            
            with open(file_path, 'wb') as file_part:
                for item in arr:
                    file_part.write(item)
            file_part.close()
            print(f"Successfully wrote array to file: {file_path}")
            
        
            # Ghi dữ liệu piece
            print('start add with lock')

            with self.part_data_lock:
                part_data.append((start, file_path))

            print('end add with lock')
            # file.write(file_bytes)

        except Exception as e:
            print(f"Error in download_file: {e}")
        finally:
            s.close()


    # def download_piece(self, ip_sender, port_sender, filename, start, end, part_data):
    #     try:
    #         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #         s.connect((ip_sender, port_sender))

    #         message = f"{filename}:{start}:{end}"
    #         s.send(message.encode())

    #         response = s.recv(1024).decode()
    #         if response == "done":
    #             print(f"Start: {start}, End: {end} sent successfully.")
    #         else:
    #             print("Failed to send data correctly.")

    #         file_bytes = bytearray()
    #         done = False
    #         progress = tqdm.tqdm(unit="B", unit_scale=True, unit_divisor=1024, total=int(end-start))

    #         buffer_size = 1024 * 1024  # 1 MB buffer
    #         while not done:
    #             data = s.recv(buffer_size)
    #             if data[-5:] == b"<END>":
    #                 done = True
    #                 file_bytes.extend(data[:-5])
    #             else:
    #                 file_bytes.extend(data)
    #             progress.update(len(data))

    #         with self.part_data_lock:
    #             part_data.append((start, bytes(file_bytes)))  # Convert bytearray back to bytes
    #     except Exception as e:
    #         print(f"Error in download_piece: {e}")
    #     finally:
    #         s.close()


    
# lắng nghe, chấp nhận kết nối và gửi file: 
    # chấp nhận kết nối
    def accept_connections(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            threading.Thread(target=self.upload_file, args=(client_socket,), daemon=False).start()
        # while True:
        #     client_socket, addr = self.server_socket.accept()
        #     if len(self.download_rates) < 4:
        #         threading.Thread(target=self.upload_file, args=(client_socket,), daemon=False).start()
    # send file
    def upload_file(self, client_socket):
        try:

            data = client_socket.recv(1024).decode()
            if data:
                parts = data.split(':')  # Split the received data by ':'
                if len(parts) == 3:
                    filename, start_str, end_str = parts
                    print(f"Filename: {filename}")
                    start = int(start_str)  
                    end = int(end_str)      
                    print(f"Start: {start}, End: {end}, Type of start: {type(start)}")

                    # Send confirmation back to sender
                    client_socket.send("done".encode())
                else:
                    print("Received data is not formatted correctly.")
                    client_socket.send("error".encode())
            else:
                print("No data received.")

            if filename in self.files:
                with open(filename, 'rb') as file:
                    file.seek(start)
                    numbytes = end - start
                    buffer_size = 1024*1024
                    while numbytes:
                        data = file.read(min(numbytes, buffer_size))
                        client_socket.send(data)
                        numbytes -= len(data)
                    client_socket.send(b"<END>")
                # file.close()

        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()
    def download_file(self, file_name, part_data):
        peer_info = self.request_peer_info(file_name)
        
        if peer_info:
            size, pieces, hash = 0,0,''
            
            for p in peer_info['peers']:
                print(p['ip'], " ", p['port'], " ", p['file'], " ", p['size'])
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
            data = b''
            threads = []

            if (n == 1):
                # mặc định 3 luồng xử lí cùng, có thể chỉnh sửa nhập input cho number thread
                number_thread = 3
                if (pieces < number_thread):
                    start_piece, end_piece = [],[]
                    for i in range(pieces):
                        start_piece.append(i)
                        end_piece.append(i+1)
                    for i in range(pieces):
                        thread = threading.Thread(target=self.download_piece, args=(ip_list[0], port_list[0], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data))
                        threads.append(thread)
                        thread.start()
                    for thread in threads:
                        thread.join()
                else:
                    chunk_size = pieces // number_thread  # Kích thước của mỗi khoảng
                    remainder = pieces % number_thread  # Phần dư

                    start_piece = [i * chunk_size + min(i, remainder) for i in range(number_thread)]  # Mảng start_byte
                    end_piece = [(i + 1) * chunk_size + min(i + 1, remainder) for i in range(number_thread)]  # Mảng end_byte

                    print(f"Downloading file from {ip_list[0]}:{port_list[0]}")
                    for i in range(number_thread):
                        if i < number_thread - 1:
                            thread = threading.Thread(target=self.download_piece, args=(ip_list[0], port_list[0], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data))
                        else:
                            if lastpiece_size == 0:
                                thread = threading.Thread(target=self.download_piece, args=(ip_list[0], port_list[0], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data))
                            else:
                                thread = threading.Thread(target=self.download_piece, args=(ip_list[0], port_list[0], file_name, start_piece[i]*PIECE_SIZE, (end_piece[i]-1)*PIECE_SIZE + lastpiece_size, part_data))
                        threads.append(thread)
                        thread.start()
                
                    for thread in threads:
                        thread.join()
            
            else:
                if(pieces < n):
                    start_piece, end_piece = [],[]
                    for i in range(pieces):
                        start_piece.append(i)
                        end_piece.append(i+1)
                    for i in range(pieces):
                        thread = threading.Thread(target=self.download_piece, args=(ip_list[i], port_list[i], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data))
                        threads.append(thread)
                        thread.start()
                    for thread in threads:
                        thread.join()
                else:
                    chunk_size = pieces // n  # Kích thước của mỗi khoảng
                    remainder = pieces % n  # Phần dư

                    start_piece = [i * chunk_size + min(i, remainder) for i in range(n)]  # Mảng start_byte
                    end_piece = [(i + 1) * chunk_size + min(i + 1, remainder) for i in range(n)]  # Mảng end_byte

                    for i in range(len(ip_list)):
                        print(f"Downloading file from {ip_list[i]}:{port_list[i]}")
                        if i < len(ip_list) - 1:
                            thread = threading.Thread(target=self.download_piece, args=(ip_list[i], port_list[i], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data))
                        else:
                            if lastpiece_size == 0:
                                thread = threading.Thread(target=self.download_piece, args=(ip_list[i], port_list[i], file_name, start_piece[i]*PIECE_SIZE, end_piece[i]*PIECE_SIZE, part_data))
                            else:
                                thread = threading.Thread(target=self.download_piece, args=(ip_list[i], port_list[i], file_name, start_piece[i]*PIECE_SIZE, (end_piece[i]-1)*PIECE_SIZE + lastpiece_size, part_data))
                        threads.append(thread)
                        thread.start()
                        
                
                    for thread in threads:
                        thread.join()

#---------------------------------------------------------------------------------------------
            part_data.sort(key=lambda x: x[0])

            # data = b"".join([part[1] for part in part_data])

            # sum_hash = self.create_hash_data(data)
            
            # # if sum_hash == hash:
            print("start write file")
            
            with open(file_name, 'wb') as result_file:
                for _ , file_bin in part_data:
                    with open(file_bin, 'rb') as file_read:
                        while True:
                            chunk = file_read.read(1024*1024)
                            if not chunk:
                                break
                            result_file.write(chunk)
                    os.remove(file_bin)
            result_file.close()
            
            print(f"File {file_name} has been downloaded.")
        else:
            print("No peer found with the requested file.")

    def manage_downloads(self, requested_files):
        threads = []

        for file_name in requested_files:
            thread = threading.Thread(target=self.download_file, args=(file_name,[]))

            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        print(f"All files have been downloaded.",end='\n')

        for speed in self.download_rates:
            print(speed[0]," ",speed[1], end='\n')

    
if __name__ == "__main__":
    my_ip = sys.argv[1]
    my_port = int(sys.argv[2])
    files = sys.argv[3].split(',')

    peer = Peer('10.0.21.105', 9999, my_ip, my_port, files)

    # if the peer need to download a file
    if len(sys.argv) > 4:
        requested_files = sys.argv[4].split(',')
        peer.manage_downloads(requested_files)

    input("Press any key to exit... ")