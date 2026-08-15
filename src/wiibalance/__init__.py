import json
import sys
from pathlib import Path
from wiibalance._direct import _DirectBalanceBoard
from wiibalance._client import _DaemonBalanceBoard
from wiibalance.models import Weights, BoardNotFoundError, DaemonNotRunningError, PlatformNotSupportedError

CONFIG_PATH = Path.home() / ".config" / "wiibalance" / "config.json"

def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {"daemon_enabled": False, "address": None}

def BalanceBoard(address: str | None = None, use_daemon: bool | None = None):
    """
    Factory function that returns either a direct Bluetooth connection
    or a thin client connecting to the background daemon.
    """
    if not sys.platform.startswith('linux'):
        raise PlatformNotSupportedError("WiiBalance only supports Linux systems.")

    config = _load_config()

    # Explicit argument overrides config file
    should_use_daemon = use_daemon if use_daemon is not None else config.get("daemon_enabled", False)

    if should_use_daemon:
        return _DaemonBalanceBoard()
    else:
        target_address = address or config.get("address")
        return _DirectBalanceBoard(address=target_address)

# Expose these to users who import wiibalance
__all__ = ["BalanceBoard", "Weights", "BoardNotFoundError", "DaemonNotRunningError"]