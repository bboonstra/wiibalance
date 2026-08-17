import argparse
import json
import subprocess
import sys
import time
from wiibalance import create_balance_board, PlatformNotSupportedError
from .config import read_config
from ._display import LiveDisplay
from .config import write_config
from .daemon import setup_daemon, teardown_daemon


def main():
    parser = argparse.ArgumentParser(prog="wiibalance", description="Wii Balance Board CLI")

    # Shared parser for global flags like address and daemon control
    shared_parser = argparse.ArgumentParser(add_help=False)
    daemon_group = shared_parser.add_mutually_exclusive_group()
    daemon_group.add_argument("--daemon", action="store_true", default=None, help="Force daemon mode")
    daemon_group.add_argument("--no-daemon", action="store_false", dest="daemon", help="Force direct Bluetooth mode")
    shared_parser.add_argument("-a", "--address", type=str, default=None,
                               help="Bluetooth MAC address of the Wii Balance Board")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Daemon commands (inherit shared_parser so -a/--address and daemon flags work)
    daemon_parser = subparsers.add_parser("daemon", parents=[shared_parser], help="Manage the background daemon")
    daemon_parser.add_argument("action", choices=["setup", "status", "start", "stop", "restart", "remove"])

    # Interaction commands (inherits shared_parser so -a/--address and daemon flags work here too)
    subparsers.add_parser("weight", parents=[shared_parser], help="Read current total weight")

    subparsers.add_parser("cop", parents=[shared_parser], help="Read current center of pressure")

    battery_parser = subparsers.add_parser("battery", parents=[shared_parser], help="Read current battery level")
    battery_parser.add_argument("--bars", action="store_true", help="Show battery bars instead of percentage")

    led_parser = subparsers.add_parser("led", parents=[shared_parser], help="Toggle the board LED")
    led_parser.add_argument("--on", action="store_true", help="Turn LED on")
    led_parser.add_argument("--off", action="store_true", help="Turn LED off")

    live_parser = subparsers.add_parser("live", parents=[shared_parser], help="Stream live stats from the board")
    live_parser.add_argument("--json", action="store_true", help="Output stream as JSON lines")

    subparsers.add_parser("disconnect", parents=[shared_parser], help="Disconnect from the board")

    conf_parser = subparsers.add_parser("config", help="Configure the daemon")
    conf_parser.add_argument("action", choices=["set", "get", "reset"])
    conf_parser.add_argument("key", type=str, nargs="?", help="Configuration key")
    conf_parser.add_argument("value", type=str, nargs="?", help="Configuration value")

    args = parser.parse_args()

    if not sys.platform.startswith('linux'):
        raise PlatformNotSupportedError("WiiBalance only supports Linux systems.")

    # Route commands
    if args.command == "daemon":
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
            board = create_balance_board(address=args.address, use_daemon=args.daemon)
            state = board.read_state()
            print(f"{state.weights.total:.2f}{"lb" if read_config().get('units') == 'imperial' else 'kg'}")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "cop":
        try:
            board = create_balance_board(address=args.address, use_daemon=args.daemon)
            state = board.read_state()
            print(f"{state.weights.center_of_pressure}")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "battery":
        try:
            board = create_balance_board(address=args.address, use_daemon=args.daemon)
            state = board.read_state()
            if args.bars:
                print(f"{state.battery_bars}")
            else:
                print(f"{state.battery_percent:.2f}%")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "led":
        try:
            board = create_balance_board(address=args.address, use_daemon=args.daemon)
            if args.on:
                board.led_on()
                print("LED turned on")
                return
            elif args.off:
                board.led_off()
                print("LED turned off")
                return
            else:
                board.toggle_led()
                print(f"LED turned {board.read_state().led and 'on' or 'off'}")
                return
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "live":
        try:
            board = create_balance_board(address=args.address, use_daemon=args.daemon)
            dashboard = LiveDisplay()

            while True:
                state = board.read_state()
                weights = state.weights
                cop_x, cop_y = weights.center_of_pressure

                if args.json:
                    # UNCHANGED shape/keys — stays compatible with existing consumers
                    data = {
                        "raw": weights.total,
                        "compensated": state.calibrated_weight,
                        "top_left": weights.top_left,
                        "top_right": weights.top_right,
                        "bottom_left": weights.bottom_left,
                        "bottom_right": weights.bottom_right,
                        "center_of_pressure_x": cop_x,
                        "center_of_pressure_y": cop_y,
                        "button": state.button,
                        "battery": state.battery_percent,
                        "battery_bars": state.battery_bars,
                        "led": state.led,
                        "unit": "lb" if read_config().get('units') == 'imperial' else 'kg',
                        "timestamp": time.time(),
                    }
                    print(json.dumps(data))
                else:
                    dashboard.render(state)

                time.sleep(0.05)  # ~20 FPS refresh rate

        except KeyboardInterrupt:
            return
        except Exception as e:
            print(f"\nError: {e}")

    elif args.command == "config":
        try:
            config = read_config()
            if args.action == "set":
                if not args.key:
                    print("Error: a key is required for set action")
                    return
                config[args.key] = args.value
                write_config(config)
                print(f"Updated config:\n{json.dumps(read_config(), indent=4)}")

            elif args.action == "get":
                if not args.key:
                    print(json.dumps(config, indent=4))
                    return
                print(config.get(args.key, "(not set)"))

            elif args.action == "reset":
                if args.key:
                    del config[args.key]
                else:
                    config.clear()
                write_config(config)
                print(f"Updated config:\n{json.dumps(read_config(), indent=4)}")

        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "disconnect":
        try:
            board = create_balance_board(address=args.address, use_daemon=args.daemon)
            board.disconnect()
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
