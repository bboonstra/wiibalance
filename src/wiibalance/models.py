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

POSITION_TOPRIGHT = 3
POSITION_TOPLEFT = 2
POSITION_BOTTOMRIGHT = 1
POSITION_BOTTOMLEFT = 0

class BoardNotFoundError(Exception):
    pass

class DaemonNotRunningError(Exception):
    pass

class PlatformNotSupportedError(Exception):
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
    def center_of_pressure(self) -> tuple[float, float]:
        """
        Calculate normalized center of pressure.

        x:
            -1 = left
            +1 = right

        y:
            -1 = bottom
            +1 = top
        """

        total = self.total

        if total <= 0:
            return 0.0, 0.0

        left = self.topleft + self.bottomleft
        right = self.topright + self.bottomright

        top = self.topleft + self.topright
        bottom = self.bottomleft + self.bottomright

        x = (right - left) / total
        y = (top - bottom) / total

        return x, y

    @property
    def total(self) -> float:
        return self.topright + self.topleft + self.bottomright + self.bottomleft

    def to_dict(self) -> dict:
        return {
            "topright": self.topright,
            "topleft": self.topleft,
            "bottomright": self.bottomright,
            "bottomleft": self.bottomleft,
            "raw_topright": self.raw_topright,
            "raw_topleft": self.raw_topleft,
            "raw_bottomright": self.raw_bottomright,
            "raw_bottomleft": self.raw_bottomleft,
        }