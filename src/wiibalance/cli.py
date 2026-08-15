import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from wiibalance import BalanceBoard, PlatformNotSupportedError
from wiibalance._direct import _DirectBalanceBoard

CONFIG_DIR = Path.home() / ".config" / "wiibalance"
CONFIG_PATH = CONFIG_DIR / "config.json"

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

def main():
    parser = argparse.ArgumentParser(prog="wiibalance", description="Wii Balance Board CLI")

    # Shared parser for global flags like address and daemon control
    shared_parser = argparse.ArgumentParser(add_help=False)
    daemon_group = shared_parser.add_mutually_exclusive_group()
    daemon_group.add_argument("--daemon", action="store_true", default=None, help="Force daemon mode")
    daemon_group.add_argument("--no-daemon", action="store_false", dest="daemon", help="Force direct Bluetooth mode")
    shared_parser.add_argument("-a", "--address", type=str, default=None, help="Bluetooth MAC address of the Wii Balance Board")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Service commands (inherit shared_parser so -a/--address and daemon flags work)
    service_parser = subparsers.add_parser("service", parents=[shared_parser], help="Manage the background daemon")
    service_parser.add_argument("action", choices=["setup", "status"])

    # Interaction commands (inherits shared_parser so -a/--address and daemon flags work here too)
    subparsers.add_parser("weight", parents=[shared_parser], help="Read current total weight")
    subparsers.add_parser("cop", parents=[shared_parser], help="Read current center of pressure")
    subparsers.add_parser("led", parents=[shared_parser], help="Toggle the board LED")
    live_parser = subparsers.add_parser("live", parents=[shared_parser], help="Stream live stats from the board")
    live_parser.add_argument("--json", action="store_true", help="Output stream as JSON lines")
    args = parser.parse_args()

    if not sys.platform.startswith('linux'):
        raise PlatformNotSupportedError("WiiBalance only supports Linux systems.")

    # Route commands
    if args.command == "service":
        if args.action == "setup":
            setup_daemon(address=args.address)
        elif args.action == "status":
            subprocess.run(["systemctl", "--user", "status", "wiibalanced.service"])

    elif args.command == "weight":
        try:
            board = BalanceBoard(address=args.address, use_daemon=args.daemon)
            print(f"Total Weight: {board.weights.total:.2f}")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "cop":
        try:
            board = BalanceBoard(address=args.address, use_daemon=args.daemon)
            print(f"Center of Pressure: {board.weights.center_of_pressure}")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "led":
        try:
            board = BalanceBoard(address=args.address, use_daemon=args.daemon)
            board.toggle_led()
            print("LED toggled.")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "live":
        try:
            board = BalanceBoard(address=args.address, use_daemon=args.daemon)
            while True:
                weights = board.weights
                cop_x, cop_y = weights.center_of_pressure

                if args.json:
                    data = {
                        "total": round(weights.total, 2),
                        "topleft": round(weights.topleft, 2),
                        "topright": round(weights.topright, 2),
                        "bottomleft": round(weights.bottomleft, 2),
                        "bottomright": round(weights.bottomright, 2),
                        "center_of_pressure_x": cop_x,
                        "center_of_pressure_y": cop_y,
                        "button": board.button,
                        "battery": board.battery
                    }
                    print(json.dumps(data))
                else:
                    # Map CoP range [-1.0, 1.0] to a 5-column by 3-row grid index
                    # X: -1 (left) to +1 (right) -> columns 0 to 4
                    # Y: -1 (back) to +1 (front) -> rows 0 (front) to 2 (back)
                    GRID_COLS, GRID_ROWS = 5, 3

                    col = int(round(min(max(cop_x, -1.0), 1.0) * 2) + 2)
                    row = int(round(-min(max(cop_y, -1.0), 1.0) * 1) + 1)  # Invert Y for screen rendering

                    # Re-clamp after rounding so a future scale/offset change can't index out of bounds
                    col = max(0, min(GRID_COLS - 1, col))
                    row = max(0, min(GRID_ROWS - 1, row))

                    # Build the 3-row text grid (5:3 visual box representation)
                    grid_rows = [["·", "·", "·", "·", "·"] for _ in range(GRID_ROWS)]
                    grid_rows[row][col] = "O"

                    # Guard against missing/late sensor data so one bad frame doesn't kill the loop
                    total_weight = getattr(weights, "total", 0.0) or 0.0
                    battery_pct = getattr(board, "battery", 0) or 0

                    # Render text dashboard cleanly using ANSI cursor restore (\033[u)
                    # Note: \033[u requires a matching \033[s (save cursor) earlier, once, before the loop starts.
                    output = (
                        f"\033[u"  # Restore cursor to saved top position
                        f"┌─────────────────────────┐\033[K\n"
                        f"│  Weight: {total_weight:6.2f} kg      │\033[K\n"
                        f"│  CoP X: {cop_x:+5.2f} Y: {cop_y:+5.2f}   │\033[K\n"
                        f"│  Battery: {battery_pct:3d}%           │\033[K\n"
                        f"├─────────────────────────┤\033[K\n"
                        f"│       [FRONT]           │\033[K\n"
                        f"│     {grid_rows[0][0]} {grid_rows[0][1]} {grid_rows[0][2]} {grid_rows[0][3]} {grid_rows[0][4]}           │\033[K\n"
                        f"│     {grid_rows[1][0]} {grid_rows[1][1]} {grid_rows[1][2]} {grid_rows[1][3]} {grid_rows[1][4]}  [CoP]    │\033[K\n"
                        f"│     {grid_rows[2][0]} {grid_rows[2][1]} {grid_rows[2][2]} {grid_rows[2][3]} {grid_rows[2][4]}           │\033[K\n"
                        f"│       [BACK]            │\033[K\n"
                        f"└─────────────────────────┘\033[K\n"
                        f"  (Press Ctrl+C to exit)\033[K"
                    )
                    sys.stdout.write(output)
                    sys.stdout.flush()

                time.sleep(0.05) # ~20 FPS refresh rate

        except KeyboardInterrupt:
            return
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()