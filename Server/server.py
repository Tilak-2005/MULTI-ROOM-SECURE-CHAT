import socket
import threading
from room_manager import RoomManager
from protocol import parse_message

HOST = "0.0.0.0"
PORT = 5000

room_manager = RoomManager()

clients = {}
usernames = {}


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
        username = conn.recv(1024).decode().strip()

        clients[username] = conn
        usernames[conn] = username

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

            elif command == "FILE":

                room = args[0]
                filename = args[1]
                size = int(args[2])

                print(f"Receiving file {filename} ({size} bytes)")

                filedata = receive_exact(conn, size)

                header = f"FILE|{filename}|{size}\n".encode()

                for client in room_manager.rooms.get(room, []):

                    if client != conn:

                        client.send(header + filedata)

                print("File forwarded")

            elif command == "LEAVE":

                room = args[0]
                room_manager.leave_room(room, conn)

    except Exception as e:
        print("Error:", e)

    finally:

        username = usernames.get(conn, "Unknown")
        print(f"Disconnected: {username}")

        conn.close()


def start_server():

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.bind((HOST, PORT))
    server.listen()

    print(f"Server running on port {PORT}")

    while True:

        conn, addr = server.accept()

        thread = threading.Thread(
            target=handle_client,
            args=(conn, addr)
        )

        thread.start()


if __name__ == "__main__":
    start_server()
