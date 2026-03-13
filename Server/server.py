import socket
import ssl
import threading
from room_manager import RoomManager
from protocol import parse_message

HOST = "0.0.0.0"
PORT = 5000

SSL_CERT = "server.crt"
SSL_KEY = "server.key"

room_manager = RoomManager()

clients = {}
usernames = {}


def create_ssl_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=SSL_CERT, keyfile=SSL_KEY)
    # Enforce strong protocols and ciphers
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
    return context


def receive_exact(sock, size):
    data = b""
    while len(data) < size:
        packet = sock.recv(min(4096, size - len(data)))
        if not packet:
            break
        data += packet
    return data


def handle_client(conn, addr):
    print(f"Connected: {addr}")

    try:
        conn.send("Enter username: ".encode())
        raw = conn.recv(1024).decode().strip()

        # Reject empty or duplicate usernames
        if not raw:
            conn.send("ERROR|Username cannot be empty.\n".encode())
            conn.close()
            return

        if raw in clients:
            conn.send("ERROR|Username already taken.\n".encode())
            conn.close()
            return

        username = raw
        clients[username] = conn
        usernames[conn] = username

        print(f"User registered: {username}")

        while True:
            data = conn.recv(4096)
            if not data:
                break

            message = data.decode()
            command, args = parse_message(message)

            if command == "JOIN":
                room = args[0]
                room_manager.join_room(room, conn)
                room_manager.broadcast(room, f"{username} joined {room}")

            elif command == "MSG":
                room = args[0]
                msg = args[1]
                room_manager.broadcast(room, f"{username}: {msg}", conn)

            elif command == "PRIVATE":
                target = args[0]
                msg = args[1]
                if target in clients:
                    clients[target].send(
                        f"[PRIVATE] {username}: {msg}".encode()
                    )
                else:
                    conn.send(f"ERROR|User '{target}' not found.\n".encode())

            elif command == "FILE":
                room = args[0]
                filename = args[1]
                size = int(args[2])

                # Basic validation: reject suspiciously large files (>50 MB)
                if size > 50 * 1024 * 1024:
                    conn.send("ERROR|File too large (max 50 MB).\n".encode())
                    continue

                print(f"Receiving file '{filename}' ({size} bytes) from {username}")
                filedata = receive_exact(conn, size)

                header = f"FILE|{filename}|{size}\n".encode()
                for client in room_manager.rooms.get(room, []):
                    if client != conn:
                        client.send(header + filedata)

                print("File forwarded.")

            elif command == "FILEPRIVATE":
                target = args[0]
                filename = args[1]
                size = int(args[2])

                if size > 50 * 1024 * 1024:
                    conn.send("ERROR|File too large (max 50 MB).\n".encode())
                    continue

                filedata = receive_exact(conn, size)

                if target in clients:
                    header = f"FILE|{filename}|{size}\n".encode()
                    clients[target].send(header + filedata)
                else:
                    conn.send(f"ERROR|User '{target}' not found.\n".encode())

            elif command == "LEAVE":
                room = args[0]
                room_manager.leave_room(room, conn)

    except Exception as e:
        print(f"Error handling {addr}: {e}")

    finally:
        username = usernames.pop(conn, "Unknown")
        clients.pop(username, None)
        print(f"Disconnected: {username}")
        conn.close()


def start_server():
    raw_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    raw_server.bind((HOST, PORT))
    raw_server.listen()

    ssl_context = create_ssl_context()
    server = ssl_context.wrap_socket(raw_server, server_side=True)

    print(f"[SSL] Server running on port {PORT} with TLS 1.2+")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.daemon = True
        thread.start()


if __name__ == "__main__":
    start_server()
