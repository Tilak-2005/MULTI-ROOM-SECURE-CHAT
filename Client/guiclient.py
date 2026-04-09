import socket
import ssl
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog, simpledialog
import os

HOST = "127.0.0.1"
PORT = 5000
SSL_CERT = "server.crt"

# ---------- SSL SETUP ----------
def create_ssl_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(SSL_CERT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context

ssl_context = create_ssl_context()
raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
raw_sock.connect((HOST, PORT))
client = ssl_context.wrap_socket(raw_sock, server_hostname=HOST)

# ---------- GUI ----------
class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SSL Chat App")

        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD)
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.chat_area.config(state='disabled')

        self.entry = tk.Entry(root)
        self.entry.pack(fill=tk.X, padx=10, pady=5)
        self.entry.bind("<Return>", self.send_message)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Join Room", command=self.join_room).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Send File", command=self.send_file).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Private Msg", command=self.private_msg).pack(side=tk.LEFT, padx=5)

        threading.Thread(target=self.receive_messages, daemon=True).start()

    def display(self, msg):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, msg + "\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)

    def send_message(self, event=None):
        msg = self.entry.get()
        if msg:
            client.send(f"MSG|room1|{msg}".encode())
            self.entry.delete(0, tk.END)

    def join_room(self):
        room = simpledialog.askstring("Room", "Enter room name:")
        if room:
            client.send(f"JOIN|{room}".encode())

    def private_msg(self):
        user = simpledialog.askstring("Private", "Enter username:")
        msg = simpledialog.askstring("Message", "Enter message:")
        if user and msg:
            client.send(f"PRIVATE|{user}|{msg}".encode())

    def send_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            room = simpledialog.askstring("Room", "Enter room:")
            filename = os.path.basename(filepath)
            size = os.path.getsize(filepath)

            client.send(f"FILE|{room}|{filename}|{size}".encode())

            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    client.send(chunk)

    def receive_messages(self):
        while True:
            try:
                data = client.recv(4096)
                if not data:
                    break

                if data.startswith(b"FILE|"):
                    newline = data.index(b"\n")
                    header = data[:newline].decode()
                    parts = header.split("|")

                    filename = parts[1]
                    size = int(parts[2])

                    filedata = data[newline+1:]
                    while len(filedata) < size:
                        filedata += client.recv(4096)

                    os.makedirs("files", exist_ok=True)
                    with open("files/" + filename, "wb") as f:
                        f.write(filedata)

                    self.display(f"[File Received] {filename}")

                else:
                    self.display(data.decode())

            except Exception as e:
                print("Error:", e)
                break

# ---------- START ----------
prompt = client.recv(1024).decode()
username = simpledialog.askstring("Username", prompt)
client.send(username.encode())

root = tk.Tk()
app = ChatGUI(root)
root.mainloop()
