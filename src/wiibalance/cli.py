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
    live_parser = subparsers.add_parser("live", help="Stream live stats from the board")
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
                cop_x, cop_y = weights.cop

                if args.json:
                    data = {
                        "total": round(weights.total, 2),
                        "topleft": round(weights.topleft, 2),
                        "topright": round(weights.topright, 2),
                        "bottomleft": round(weights.bottomleft, 2),
                        "bottomright": round(weights.bottomright, 2),
                        "cop_x": cop_x,
                        "cop_y": cop_y,
                        "button": board.button,
                        "battery": board.battery
                    }
                    print(json.dumps(data))
                else:
                    output = (
                        f"\r[Total: {weights.total:6.2f}kg] | "
                        f"(X: {cop_x:+.2f}, Y: {cop_y:+.2f}) | "
                        f"Button: {board.button} | Battery: {board.battery}% "
                        f"\033[K"
                    )
                    sys.stdout.write(output)
                    sys.stdout.flush()

                time.sleep(0.05) # ~20 FPS refresh rate

        except KeyboardInterrupt:
            print("\nExiting live stream.")
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()