import socket


class BalanceBoard:
    def __init__(self, address: str):
        self.address = address
        self._recv = None
        self._send = None

    def connect(self):
        self._recv = socket.socket(
            socket.AF_BLUETOOTH,
            socket.SOCK_SEQPACKET,
            socket.BTPROTO_L2CAP,
        )

        self._send = socket.socket(
            socket.AF_BLUETOOTH,
            socket.SOCK_SEQPACKET,
            socket.BTPROTO_L2CAP,
        )

        self._recv.connect((self.address, 0x13))
        self._send.connect((self.address, 0x11))

        self._send_packet("521500")
        self._send_packet("521704A400240018")
        self._send_packet("52120432")

    def disconnect(self):
        if self._recv is not None:
            self._recv.close()

        if self._send is not None:
            self._send.close()

        self._recv = None
        self._send = None

    def _send_packet(self, packet: str):
        self._send.send(bytes.fromhex(packet))

    def receive(self) -> bytes:
        return self._recv.recv(25)
