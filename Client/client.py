import socket
import threading
import os

HOST = "127.0.0.1"
PORT = 5000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))


def receive_exact(sock, size):

    data = b""

    while len(data) < size:
        packet = sock.recv(min(4096, size - len(data)))
        if not packet:
            break
        data += packet

    return data


def receive():

    while True:

        try:

            raw = client.recv(4096)

            if not raw:
                break

            if raw.startswith(b"FILE|"):

                # Header and data are separated by a newline
                newline_pos = raw.index(b"\n")
                header = raw[:newline_pos].decode()
                parts = header.split("|")

                filename = parts[1]
                size = int(parts[2])

                print(f"\nReceiving file: {filename}")

                # Data after the newline may already contain some file bytes
                already_received = raw[newline_pos + 1:]
                remaining = size - len(already_received)
                rest = receive_exact(client, remaining)
                data = already_received + rest

                os.makedirs("files", exist_ok=True)

                with open("files/" + filename, "wb") as f:
                    f.write(data)

                print(f"File saved to files/{filename}")

            else:

                print(raw.decode())

        except Exception as e:
            print(f"[receive error] {e}")
            break


def send():

    while True:

        msg = input()

        if msg.startswith("/join"):

            room = msg.split()[1]
            client.send(f"JOIN|{room}".encode())

        elif msg.startswith("/leave"):

            room = msg.split()[1]
            client.send(f"LEAVE|{room}".encode())

        elif msg.startswith("/pm"):

            parts = msg.split(" ", 2)
            user = parts[1]
            message = parts[2]

            client.send(f"PRIVATE|{user}|{message}".encode())

        elif msg.startswith("/sendfile"):

            parts = msg.split()

            room = parts[1]
            path = parts[2]

            filename = os.path.basename(path)
            size = os.path.getsize(path)

            client.send(f"FILE|{room}|{filename}|{size}".encode())

            with open(path, "rb") as f:
                while True:

                    chunk = f.read(4096)

                    if not chunk:
                        break

                    client.send(chunk)
        elif msg.startswith("/sendfileprivate"):
            parts = msg.split()
            target = parts[1]
            path = parts[2]

            filename = os.path.basename(path)
            size = os.path.getsize(path)

            client.send(f"FILEPRIVATE|{target}|{filename}|{size}\n".encode())

            with open(path, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    client.send(chunk)

        else:

            room = "room1"
            client.send(f"MSG|{room}|{msg}".encode())


# Wait for server's "Enter username: " prompt, then send username
prompt = client.recv(1024).decode()
print(prompt, end="", flush=True)
username = input()
client.send(username.encode())

import time
time.sleep(0.3)  # Small delay to ensure server registers username before any commands

threading.Thread(target=receive, daemon=True).start()

send()
