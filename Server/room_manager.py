import threading

class RoomManager:

    def __init__(self):
        self.rooms = {}
        self.lock = threading.Lock()
        self.sequence = {}

    def join_room(self, room, client):
        with self.lock:
            if room not in self.rooms:
                self.rooms[room] = []
                self.sequence[room] = 0
            self.rooms[room].append(client)

    def leave_room(self, room, client):
        with self.lock:
            if room in self.rooms and client in self.rooms[room]:
                self.rooms[room].remove(client)

    def broadcast(self, room, message, sender=None):
        with self.lock:
            if room not in self.rooms:
                return

            self.sequence[room] += 1
            seq = self.sequence[room]

            full_msg = f"[{seq}] {message}"

            for client in self.rooms[room]:
                if client != sender:
                    try:
                        client.send(full_msg.encode())
                    except:
                        pass