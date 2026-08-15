import sys
from wiibalance._direct import _DirectBalanceBoard
from wiibalance._client import _DaemonBalanceBoard
from wiibalance.config import Weights, BoardNotFoundError, DaemonNotRunningError, PlatformNotSupportedError, load_config


# noinspection pep8-naming
def BalanceBoard(address: str | None = None, use_daemon: bool | None = None):
    """
    Factory function that returns either a direct Bluetooth connection
    or a thin client connecting to the background daemon.
    """
    if not sys.platform.startswith('linux'):
        raise PlatformNotSupportedError("WiiBalance only supports Linux systems.")

    conf = load_config()

    # Explicit argument overrides config file
    should_use_daemon = use_daemon if use_daemon is not None else conf.get("daemon_enabled", False)

    if should_use_daemon:
        return _DaemonBalanceBoard()
    else:
        target_address = address or conf.get("address")
        return _DirectBalanceBoard(address=target_address)


# Expose these to users who import wiibalance
__all__ = ["BalanceBoard", "Weights", "BoardNotFoundError", "DaemonNotRunningError", "PlatformNotSupportedError"]
