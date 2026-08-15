import socket
import json
from .state import BoardState, BalanceBoard
from .config import Weights, DaemonNotRunningError, SOCKET_PATH


class _DaemonBalanceBoard(BalanceBoard):
    def __init__(self):
        self.read_state()  # ping on init to fail fast if daemon's unreachable

    @staticmethod
    def _send_command(command: str) -> dict:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(SOCKET_PATH)
                client.sendall(json.dumps({"cmd": command}).encode())
                response = json.loads(client.recv(4096).decode())
                if "error" in response:
                    raise RuntimeError(f"Daemon error: {response['error']}")
                return response
        except (FileNotFoundError, ConnectionRefusedError):
            raise DaemonNotRunningError(
                "WiiBalance daemon is not running. Start it or pass use_daemon=False."
            )

    def read_state(self) -> BoardState:
        data = self._send_command("GET_STATE")
        if "error" in data:
            raise RuntimeError(f"Daemon error: {data['error']}")
        return BoardState(
            weights=Weights(**data["weights"]),
            button=data["button"],
            led=data["led"],
            connected=data["connected"],
            battery_raw=data["battery_raw"],
            temperature_raw=data["temperature_raw"],
            reference_temperature=data["reference_temperature"],
        )

    def toggle_led(self) -> None:
        self._send_command("TOGGLE_LED")

    def led_on(self) -> None:
        self._send_command("LED_ON")

    def led_off(self) -> None:
        self._send_command("LED_OFF")

    def disconnect(self) -> None:
        pass  # client doesn't own the physical connection