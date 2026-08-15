import argparse
import json
import subprocess
import sys
import time
from wiibalance import BalanceBoard, PlatformNotSupportedError
from wiibalance._display import LiveDisplay
from wiibalance.daemon import setup_daemon, teardown_daemon


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
    service_parser.add_argument("action", choices=["setup", "status", "start", "stop", "restart", "remove"])

    # Interaction commands (inherits shared_parser so -a/--address and daemon flags work here too)
    subparsers.add_parser("weight", parents=[shared_parser], help="Read current total weight")
    subparsers.add_parser("cop", parents=[shared_parser], help="Read current center of pressure")
    led_parser = subparsers.add_parser("led", parents=[shared_parser], help="Toggle the board LED")
    led_parser.add_argument("--on", action="store_true", help="Turn LED on")
    led_parser.add_argument("--off", action="store_true", help="Turn LED off")
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
        elif args.action == "start":
            subprocess.run(["systemctl", "--user", "start", "wiibalanced.service"])
        elif args.action == "stop":
            subprocess.run(["systemctl", "--user", "stop", "wiibalanced.service"])
        elif args.action == "restart":
            subprocess.run(["systemctl", "--user", "restart", "wiibalanced.service"])
        elif args.action == "remove":
            teardown_daemon()

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
            if args.on:
                board.led_on()
                print("LED turned on.")
                return
            elif args.off:
                board.led_off()
                print("LED turned off.")
                return
            else:
                board.toggle_led()
                print(f"LED is now {board.led and 'on' or 'off'}")
            print("LED toggled.")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "live":
        try:
            board = BalanceBoard(address=args.address, use_daemon=args.daemon)
            dashboard = LiveDisplay()

            while True:
                weights = board.weights
                cop_x, cop_y = weights.center_of_pressure
                battery_pct = getattr(board, "battery", 0) or 0

                if args.json:
                    # UNCHANGED shape/keys — stays compatible with existing consumers
                    data = {
                        "total": round(weights.total, 2),
                        "topleft": round(weights.topleft, 2),
                        "topright": round(weights.topright, 2),
                        "bottomleft": round(weights.bottomleft, 2),
                        "bottomright": round(weights.bottomright, 2),
                        "center_of_pressure_x": cop_x,
                        "center_of_pressure_y": cop_y,
                        "button": board.button,
                        "battery": battery_pct,
                    }
                    print(json.dumps(data))
                else:
                    dashboard.render(weights, cop_x, cop_y, board.button, battery_pct)

                time.sleep(0.05)  # ~20 FPS refresh rate

        except KeyboardInterrupt:
            return
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()