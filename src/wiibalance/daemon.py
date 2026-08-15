import socket
import json
import os
import subprocess
import threading
from pathlib import Path

from .config import CONFIG_PATH, load_config
from ._direct import _DirectBalanceBoard
from .config import CONFIG_DIR

SOCKET_PATH = "/tmp/wiibalance.sock"


class WiiBalanceDaemon:
    def __init__(self):
        self.board = _DirectBalanceBoard()

        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        self.server.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o666)
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
                        "led": self.board.led,
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

def setup_daemon(address: str | None = None):
    print("Setting up Wii Balance Board Daemon...")

    # 1. Ensure the config dir exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Find the board
    if not address:
        print("Searching for board... (Press the red sync button!)")
        address = _DirectBalanceBoard.discover()
        if address:
            print(f"Found board at {address}")
        else:
            print("Board not found. Try supplying the address manually with --address.")
            return
    else:
        print(f"Using specified address: {address}")


    # 3. Save config
    config = {"daemon_enabled": True, "address": address}
    CONFIG_PATH.write_text(json.dumps(config, indent=4))

    # 4. Write systemd user service
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)

    # We use sys.executable to ensure the daemon uses the same python environment
    import sys
    python_path = sys.executable

    service_file = systemd_dir / "wiibalanced.service"
    service_file.write_text(f"""[Unit]
Description=Wii Balance Board Daemon

[Service]
Type=simple
ExecStart={python_path} -m wiibalance.daemon
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
""")

    # 5. Enable and start the service
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "enable", "--now", "wiibalanced.service"], check=True)
        subprocess.run(["systemctl", "--user", "start", "wiibalanced.service"], check=True)
        print("Success! The WiiBalance Daemon is installed and running in the background.")
        print("You can now run Python scripts without pressing the sync button first; the daemon will automatically reconnect and stay connected.")
        print("Manage the daemon: 'systemctl --user status wiibalanced.service'")
    except subprocess.CalledProcessError:
        print("Error: Could not configure systemd service. Are you running systemd?")

def teardown_daemon():
    if subprocess.run(["systemctl", "--user", "status", "wiibalanced.service"], stdout=subprocess.DEVNULL).returncode != 0:
        print("The WiiBalance Daemon is not installed.")
        return
    print("Removing the Wii Balance Board Daemon...")
    try:
        subprocess.run(["systemctl", "--user", "stop", "wiibalanced.service"])
        subprocess.run(["systemctl", "--user", "disable", "wiibalanced.service"])
        subprocess.run(["systemctl", "--user", "daemon-reload"])
        address = load_config().get("address", None)
        config = {"daemon_enabled": False, "address": address}
        CONFIG_PATH.write_text(json.dumps(config, indent=4))
        print("The WiiBalance Daemon has been removed. You will now need to press the sync button before using any WiiBalance command.")
    except subprocess.CalledProcessError:
        print("Error: Could not remove systemd service. Are you running systemd?")


if __name__ == "__main__":
    WiiBalanceDaemon().run()
