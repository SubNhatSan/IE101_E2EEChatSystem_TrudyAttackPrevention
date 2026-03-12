import socket
import threading
import tkinter as tk
import json # Phải có để đóng gói gói tin
from tkinter import scrolledtext, simpledialog

# Cấu hình mạng
HOST = '127.0.0.1'
PORT = 9999

class ChatClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("App Chat Đồ Án - Pro Version")
        self.root.geometry("500x600")

        # --- GIAO DIỆN ---
        # 1. Ô hiển thị tin nhắn
        self.chat_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state='disabled')
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # 2. Frame chứa thông tin điều hướng (Receiver & Type)
        nav_frame = tk.Frame(self.root)
        nav_frame.pack(padx=10, pady=5, fill=tk.X)

        tk.Label(nav_frame, text="Gửi tới:").pack(side=tk.LEFT)
        self.receiver_entry = tk.Entry(nav_frame, width=15)
        self.receiver_entry.pack(side=tk.LEFT, padx=5)
        self.receiver_entry.insert(0, "group") # Mặc định là nhắn group

        tk.Label(nav_frame, text="(Nhập 'group' hoặc Tên User)").pack(side=tk.LEFT)

        # 3. Ô nhập tin nhắn chính
        self.msg_entry = tk.Entry(self.root, font=("Arial", 12))
        self.msg_entry.pack(padx=10, pady=5, fill=tk.X)
        self.msg_entry.bind("<Return>", self.send_message)

        # 4. Nút Gửi
        self.send_button = tk.Button(self.root, text="Gửi", command=self.send_message, bg="#2196F3", fg="white")
        self.send_button.pack(padx=10, pady=5)

        # --- LOGIC KẾT NỐI ---
        self.username = simpledialog.askstring("Tên người dùng", "Vui lòng nhập tên của bạn:", parent=self.root)
        if not self.username:
            self.root.destroy()
            return
            
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((HOST, PORT))
            # Bước đăng ký tên với Server (Lệnh đầu tiên)
            self.client_socket.send(self.username.encode('utf-8'))
            
            self.display_message(f"[Hệ thống] Xin chào {self.username}! Gõ 'group' vào ô 'Gửi tới' để chat chung.")
            
            receive_thread = threading.Thread(target=self.receive_message)
            receive_thread.daemon = True
            receive_thread.start()
            
        except Exception as e:
            self.display_message(f"[Lỗi] Không thể kết nối tới Server: {e}")

        self.root.mainloop()

    def display_message(self, message):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + '\n')
        self.chat_area.yview(tk.END)
        self.chat_area.config(state='disabled')

    def send_message(self, event=None):
        msg_text = self.msg_entry.get().strip()
        receiver = self.receiver_entry.get().strip().lower()
        
        if msg_text:
            # Xác định loại tin nhắn
            msg_type = "group" if receiver == "group" else "private"
            
            # ĐÓNG GÓI JSON (Để Server Pro hiểu được)
            packet = {
                "sender": self.username,
                "receiver": receiver,
                "type": msg_type,
                "message": msg_text
            }
            
            try:
                # Chuyển JSON thành String -> Byte
                json_data = json.dumps(packet)
                self.client_socket.send(json_data.encode('utf-8'))
                
                # Hiển thị trên màn hình cá nhân
                target_display = "Phòng chung" if msg_type == "group" else f"Riêng tới {receiver}"
                self.display_message(f"Bạn ({target_display}): {msg_text}")
                
                self.msg_entry.delete(0, tk.END)
            except Exception as e:
                self.display_message("[Lỗi] Không gửi được tin nhắn.")

    def receive_message(self):
        while True:
            try:
                # Nhận dữ liệu JSON từ Server
                data = self.client_socket.recv(1024).decode('utf-8')
                if data:
                    packet = json.loads(data)
                    sender = packet.get("sender")
                    msg = packet.get("message")
                    m_type = packet.get("type", "private")
                    
                    # Định dạng hiển thị
                    if m_type == "group":
                        self.display_message(f"[GROUP] {sender}: {msg}")
                    else:
                        self.display_message(f"[PRIVATE] {sender}: {msg}")
                else:
                    break
            except:
                self.display_message("[Hệ thống] Mất kết nối.")
                break

if __name__ == "__main__":
    ChatClient()