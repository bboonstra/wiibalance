import socket
import json
import os
import threading
from wiibalance._direct import _DirectBalanceBoard

SOCKET_PATH = "/tmp/wiibalance.sock"

class WiiBalanceDaemon:
    def __init__(self):
        print("Initializing Bluetooth connection...")
        self.board = _DirectBalanceBoard()

        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        self.server.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o666) # Allow all local users to interact
        self.server.listen(5)

    def handle_client(self, conn):
        with conn:
            try:
                data = conn.recv(1024)
                if not data:
                    return

                request = json.loads(data.decode())
                command = request.get("cmd")

                if command == "GET_STATE":
                    response = {
                        "weights": self.board.weights.to_dict(),
                        "button": self.board.button,
                        "battery": self.board.battery,
                        "connected": self.board.connected
                    }
                    conn.sendall(json.dumps(response).encode())

                elif command == "LED_ON":
                    self.board.led_on()
                    conn.sendall(json.dumps({"status": "ok"}).encode())

                elif command == "LED_OFF":
                    self.board.led_off()
                    conn.sendall(json.dumps({"status": "ok"}).encode())

                elif command == "TOGGLE_LED":
                    self.board.toggle_led()
                    conn.sendall(json.dumps({"status": "ok"}).encode())

            except Exception as e:
                error_resp = json.dumps({"error": str(e)})
                conn.sendall(error_resp.encode())

    def run(self):
        print(f"Daemon listening on {SOCKET_PATH}...")
        try:
            while True:
                conn, _ = self.server.accept()
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
        except KeyboardInterrupt:
            print("Shutting down daemon...")
            self.board.disconnect()
            os.remove(SOCKET_PATH)

if __name__ == "__main__":
    WiiBalanceDaemon().run()