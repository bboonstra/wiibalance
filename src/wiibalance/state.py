from dataclasses import dataclass
from typing import Protocol

from .config import Weights


@dataclass(frozen=True, kw_only=True)
class BoardState:
    weights: Weights
    button: bool
    led: bool
    connected: bool
    battery_raw: int  # 0-255, direct from packet
    temperature_raw: int  # 0-255, meaningless without reference_temperature
    reference_temperature: int | None  # None until calibration read completes

    @property
    def battery_bars(self) -> int:
        """Per WiiBrew's documented thresholds — the only battery scale actually specified."""
        b = self.battery_raw
        if b >= 0x82:
            return 4
        if b >= 0x7D:
            return 3
        if b >= 0x78:
            return 2
        if b >= 0x6A:
            return 1
        return 0

    @property
    def battery_percent(self) -> int:
        """Coarse (25% steps) — derived from battery_bars since no max raw value is documented."""
        return self.battery_bars * 25

    @property
    def calibrated_weight(self):
        """Wii Fit's own temperature compensation. -1 until reference_temperature is known."""
        if self.reference_temperature is None:
            return -1
        return 0.999 * self.weights.total * (1.0 - 0.0007 * (self.temperature_raw - self.reference_temperature))


class BalanceBoard(Protocol):
    def read_state(self) -> BoardState: ...

    def led_on(self) -> None: ...

    def led_off(self) -> None: ...

    def toggle_led(self) -> None: ...

    def disconnect(self) -> None: ...
