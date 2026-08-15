import socket
import json
from wiibalance.config import Weights, DaemonNotRunningError

SOCKET_PATH = "/tmp/wiibalance.sock"

class _DaemonBalanceBoard:
    def __init__(self):
        # We ping the server on init to ensure it's alive
        self._send_command("GET_STATE")

    @staticmethod
    def _send_command(command: str) -> dict:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(SOCKET_PATH)
                client.sendall(json.dumps({"cmd": command}).encode())

                response_data = client.recv(4096).decode()
                response = json.loads(response_data)

                if "error" in response:
                    raise RuntimeError(f"Daemon error: {response['error']}")

                return response
        except (FileNotFoundError, ConnectionRefusedError):
            raise DaemonNotRunningError(
                "WiiBalance daemon is not running. Start it or pass use_daemon=False."
            )

    @property
    def weights(self) -> Weights:
        data = self._send_command("GET_STATE")
        return Weights(**data["weights"])

    @property
    def button(self) -> bool:
        return self._send_command("GET_STATE")["button"]

    @property
    def battery(self) -> int:
        return self._send_command("GET_STATE")["battery"]

    @property
    def connected(self) -> bool:
        return self._send_command("GET_STATE")["connected"]

    @property
    def led(self) -> bool:
        return self._send_command("GET_STATE")["led"]

    def toggle_led(self) -> None:
        self._send_command("TOGGLE_LED")

    def led_on(self) -> None:
        self._send_command("LED_ON")

    def led_off(self) -> None:
        self._send_command("LED_OFF")

    def disconnect(self) -> None:
        pass # Client doesn't manage the physical connection