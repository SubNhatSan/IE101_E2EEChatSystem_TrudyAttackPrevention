import socket
import threading
import json # Rất quan trọng để xử lý gói tin JSON

HOST = '127.0.0.1'  # localhost
PORT = 9999

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

# Quản lý theo Dictionary: { "Tên_User": socket_object }
clients = {}

def handle_client(client_socket, address):
    username = None
    try:
        # Bước 1: Nhận tên đăng ký đầu tiên từ Client
        username = client_socket.recv(1024).decode('utf-8')
        if username in clients:
            client_socket.send(json.dumps({"sender": "System", "message": "Tên đã tồn tại!"}).encode('utf-8'))
            client_socket.close()
            return
        
        clients[username] = client_socket
        print(f"[+] {username} ({address}) đã online.")
        
        # Thông báo cho mọi người có người mới vào (Group message)
        announce = json.dumps({"sender": "System", "type": "group", "message": f"{username} đã tham gia phòng chat."})
        broadcast(announce.encode('utf-8'), client_socket)

        # Bước 2: Lắng nghe gói tin JSON
        while True:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                break
                
            packet = json.loads(data)
            msg_type = packet.get('type')
            target = packet.get('receiver')

            if msg_type == "private":
                # NHẮN RIÊNG: Chỉ gửi cho người nhận
                if target in clients:
                    clients[target].send(data.encode('utf-8'))
                else:
                    error_msg = json.dumps({"sender": "System", "message": f"Người dùng {target} không online."})
                    client_socket.send(error_msg.encode('utf-8'))
            
            elif msg_type == "group":
                # NHẮN GROUP: Gửi cho tất cả trừ người gửi
                broadcast(data.encode('utf-8'), client_socket)

    except Exception as e:
        print(f"[!] Lỗi với {username}: {e}")
    finally:
        # Xử lý khi Client thoát
        if username and username in clients:
            del clients[username]
            print(f"[-] {username} đã offline.")
            exit_msg = json.dumps({"sender": "System", "type": "group", "message": f"{username} đã rời phòng chat."})
            broadcast(exit_msg.encode('utf-8'), None)
        client_socket.close()

def broadcast(message, _sender_socket):
    """Gửi tới tất cả client đang online"""
    for name in list(clients.keys()):
        sock = clients[name]
        if sock != _sender_socket:
            try:
                sock.send(message)
            except:
                sock.close()
                del clients[name]

def start_server():
    print(f"[*] Server Messenger đang chạy tại {HOST}:{PORT}...")
    while True:
        client_socket, address = server.accept()
        # Chuyển address vào để log cho dễ
        thread = threading.Thread(target=handle_client, args=(client_socket, address))
        thread.start()

if __name__ == "__main__":
    start_server()