from __future__ import annotations

import socket
import subprocess
import threading
from dataclasses import dataclass


DEVICE_NAME = "Nintendo RVL-WBC-01"

COMMAND_REPORTING = bytes.fromhex("52120432")
COMMAND_STATUS = bytes.fromhex("521500")
COMMAND_CALIBRATION = bytes.fromhex("521704A400240018")
COMMAND_LED = lambda state: bytes.fromhex(f"5211{state:x}0")

TYPE_STATUS = 0x20
TYPE_CALIBRATION = 0x21
TYPE_DATA = 0x32

PSM_SEND = 0x11
PSM_RECV = 0x13

POSITION_TOPRIGHT = 0
POSITION_TOPLEFT = 1
POSITION_BOTTOMRIGHT = 2
POSITION_BOTTOMLEFT = 3


class BoardNotFoundError(Exception):
    pass


@dataclass
class Weights:
    topright: float
    topleft: float
    bottomright: float
    bottomleft: float

    raw_topright: int
    raw_topleft: int
    raw_bottomright: int
    raw_bottomleft: int

    @property
    def total(self) -> float:
        return (
                self.topright
                + self.topleft
                + self.bottomright
                + self.bottomleft
        )


class BalanceBoard:
    def __init__(self, address: str | None = None):
        self.address = address or self.discover()

        if self.address is None:
            raise BoardNotFoundError(
                f"{DEVICE_NAME} not found"
            )

        self.send_sock = None
        self.recv_sock = None

        self.connected = False
        self.led = False
        self.battery = -1

        self.calibration = [
            [10000] * 4,
            [10000] * 4,
            [10000] * 4,
            ]

        self.calibration_completed = [False, False]

        self._weights = Weights(
            0, 0, 0, 0,
            0, 0, 0, 0,
        )

        self._button = False
        self._stop = threading.Event()

        self.connect()
        self.initialize()

        self.worker_thread = threading.Thread(
            target=self._worker,
            daemon=True,
        )
        self.worker_thread.start()

    # ---------------------------------------------------------------
    # Bluetooth
    # ---------------------------------------------------------------

    @staticmethod
    def discover() -> str | None:
        """
        Discover the Balance Board using BlueZ's bluetoothctl.
        """

        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True,
            text=True,
            check=True,
        )

        for line in result.stdout.splitlines():
            parts = line.split(maxsplit=2)

            if len(parts) == 3:
                _, address, name = parts

                if name == DEVICE_NAME:
                    return address

        return None

    @staticmethod
    def _l2cap_socket() -> socket.socket:
        return socket.socket(
            socket.AF_BLUETOOTH,
            socket.SOCK_SEQPACKET,
            socket.BTPROTO_L2CAP,
        )

    def connect(self) -> None:
        self.send_sock = self._l2cap_socket()
        self.recv_sock = self._l2cap_socket()

        try:
            self.recv_sock.connect(
                (self.address, PSM_RECV)
            )

            self.send_sock.connect(
                (self.address, PSM_SEND)
            )

            self.connected = True

        except Exception:
            self.disconnect()
            raise

    def disconnect(self) -> None:
        self._stop.set()
        self.connected = False

        for sock in (self.send_sock, self.recv_sock):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

        self.send_sock = None
        self.recv_sock = None

    # ---------------------------------------------------------------
    # Communication
    # ---------------------------------------------------------------

    def send(self, data: bytes) -> None:
        if self.send_sock is None:
            raise RuntimeError("Board is not connected")

        self.send_sock.send(data)

    def receive(self) -> bytes:
        if self.recv_sock is None:
            raise RuntimeError("Board is not connected")

        return self.recv_sock.recv(25)

    # ---------------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------------

    def initialize(self) -> None:
        self.send(COMMAND_STATUS)
        self.send(COMMAND_CALIBRATION)
        self.send(COMMAND_REPORTING)

        for _ in range(10):
            packet = self.receive()
            self._process_initial_packet(packet)

    def _process_initial_packet(self, packet: bytes) -> None:
        if len(packet) < 2:
            return

        packet_type = packet[1]

        if packet_type == TYPE_STATUS:
            self._parse_status(packet)

        elif packet_type == TYPE_CALIBRATION:
            self._parse_calibration(packet)

    # ---------------------------------------------------------------
    # Status
    # ---------------------------------------------------------------

    def _parse_status(self, packet: bytes) -> None:
        if packet:
            self.battery = packet[-1]

    # ---------------------------------------------------------------
    # Calibration
    # ---------------------------------------------------------------

    def _parse_calibration(self, packet: bytes) -> None:
        """
        Packet structure:

            a1 21 ...

        Calibration data arrives in two packets.
        """

        # The original code effectively extracted the payload
        # beginning at byte 7.
        payload_length = packet[4] // 16 + 1

        data = packet[7:7 + payload_length]

        if len(data) == 16:
            index = 0

            for calibration_set in range(2):
                for position in range(4):
                    self.calibration[
                        calibration_set
                    ][position] = int.from_bytes(
                        data[index:index + 2],
                        "big",
                    )

                    index += 2

            self.calibration_completed[0] = True

        elif len(data) >= 8:
            index = 0

            for position in range(4):
                self.calibration[2][position] = int.from_bytes(
                    data[index:index + 2],
                    "big",
                )

                index += 2

            self.calibration_completed[1] = True

    # ---------------------------------------------------------------
    # Weight conversion
    # ---------------------------------------------------------------

    def _parse_sample(
            self,
            value: int,
            position: int,
    ) -> float:

        zero = self.calibration[0][position]
        seventeen = self.calibration[1][position]
        thirty_four = self.calibration[2][position]

        if value < zero:
            return 0.0

        if value < seventeen:
            return 17.0 * (
                    (value - zero)
                    / (seventeen - zero)
            )

        return 17.0 + 17.0 * (
                (value - seventeen)
                / (thirty_four - seventeen)
        )

    def _parse_sample_packet(
            self,
            packet: bytes,
    ) -> Weights:

        if len(packet) < 12:
            raise ValueError(
                f"Invalid data packet: {packet.hex()}"
            )

        raw = [
            int.from_bytes(
                packet[offset:offset + 2],
                "big",
            )
            for offset in (4, 6, 8, 10)
        ]

        values = [
            self._parse_sample(raw[position], position)
            for position in range(4)
        ]

        return Weights(
            values[0],
            values[1],
            values[2],
            values[3],
            raw[0],
            raw[1],
            raw[2],
            raw[3],
        )

    # ---------------------------------------------------------------
    # Public state
    # ---------------------------------------------------------------

    @property
    def weights(self) -> Weights:
        return self._weights

    @property
    def button(self) -> bool:
        return self._button

    # ---------------------------------------------------------------
    # LED
    # ---------------------------------------------------------------

    def toggle_led(self) -> None:
        self.led = not self.led
        self.send(COMMAND_LED(int(self.led)))

    def led_on(self) -> None:
        self.send(COMMAND_LED(1))
        self.led = True

    def led_off(self) -> None:
        self.send(COMMAND_LED(0))
        self.led = False

    # ---------------------------------------------------------------
    # Worker
    # ---------------------------------------------------------------

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                packet = self.receive()

                if len(packet) < 2:
                    continue

                if packet[1] == TYPE_DATA:
                    self._weights = self._parse_sample_packet(packet)

                    if len(packet) > 3:
                        self._button = bool(
                            packet[3] & 0x08
                        )

            except OSError:
                if not self._stop.is_set():
                    self.connected = False
                break

            except Exception as exc:
                print(
                    f"Balance Board error: {exc}"
                )