import socket
import threading
from room_manager import RoomManager
from protocol import parse_message

HOST = "0.0.0.0"
PORT = 5000

room_manager = RoomManager()
clients = {}
usernames = {}

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

                filedata = conn.recv(size)

                for client in room_manager.rooms.get(room, []):
                    if client != conn:
                        client.send(
                            f"FILE|{filename}|{size}".encode()
                        )
                        client.send(filedata)

            elif command == "LEAVE":

                room = args[0]
                room_manager.leave_room(room, conn)

    except Exception as e:
        print(e)

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

        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    start_server()