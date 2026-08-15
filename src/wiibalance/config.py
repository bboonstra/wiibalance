import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "wiibalance"
CONFIG_PATH = CONFIG_DIR / "config.json"
SOCKET_PATH = "/tmp/wiibalance.sock"

DEFAULT_CONFIG = {"daemon_enabled": False, "address": None, "units": "metric"}

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            conf = json.loads(CONFIG_PATH.read_text())
            for key, value in DEFAULT_CONFIG.items():
                if key not in conf:
                    conf[key] = value
            return conf
        except json.JSONDecodeError:
            pass
    return DEFAULT_CONFIG

def write_config(config: dict):
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=4))


DEVICE_NAME = "Nintendo RVL-WBC-01"

COMMAND_REPORTING = bytes.fromhex("52120434")
COMMAND_STATUS = bytes.fromhex("521500")
COMMAND_CALIBRATION = bytes.fromhex("521704A400240018")
COMMAND_TEMP_CALIBRATION = bytes.fromhex("521704A400600002")
COMMAND_LED = lambda state: bytes.fromhex(f"5211{state:x}0")

TYPE_STATUS = 0x20
TYPE_CALIBRATION = 0x21
TYPE_DATA = 0x34

PSM_SEND = 0x11
PSM_RECV = 0x13

POSITION_TOP_RIGHT = 0
POSITION_BOTTOM_RIGHT = 1
POSITION_TOP_LEFT = 2
POSITION_BOTTOM_LEFT = 3


class BoardNotFoundError(Exception):
    pass


class DaemonNotRunningError(Exception):
    pass


class PlatformNotSupportedError(Exception):
    pass

class CriticallyLowBatteryError(Exception):
    pass


@dataclass(kw_only=True)
class Weights:
    top_right: float
    top_left: float
    bottom_right: float
    bottom_left: float

    raw_top_right: int
    raw_top_left: int
    raw_bottom_right: int
    raw_bottom_left: int

    @property
    def center_of_pressure(self) -> tuple[float, float]:
        """
        Calculate a normalized center of pressure.

        X:
            -1 = left
            +1 = right

        Y:
            -1 = bottom
            +1 = top
        """

        total = self.total

        if total <= 0:
            return 0.0, 0.0

        left = self.top_left + self.bottom_left
        right = self.top_right + self.bottom_right

        top = self.top_left + self.top_right
        bottom = self.bottom_left + self.bottom_right

        x = (right - left) / total
        y = (top - bottom) / total

        return x, y

    @property
    def total(self) -> float:
        return self.top_right + self.top_left + self.bottom_right + self.bottom_left

    def to_dict(self) -> dict:
        return {
            "top_right": self.top_right,
            "top_left": self.top_left,
            "bottom_right": self.bottom_right,
            "bottom_left": self.bottom_left,
            "raw_top_right": self.raw_top_right,
            "raw_top_left": self.raw_top_left,
            "raw_bottom_right": self.raw_bottom_right,
            "raw_bottom_left": self.raw_bottom_left,
        }
