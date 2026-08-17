# WiiBalance

The modern Python controller for the Wii Balance Board.

![Linux](https://img.shields.io/badge/Linux%20Only-1793d1) [![PyPI Version](https://img.shields.io/pypi/v/wiibalance)](https://pypi.org/project/wiibalance/)

![wiibalance](https://bboonstra.dev/wiibalance.gif)

## Features

- Connect to a Wii Balance Board via Bluetooth
- Read sensors, battery, button, and LED states
- Control LED

## Why WiiBalance?

- **Permanent pairing via daemon! Only press sync once**
- Fast and modern
- CLI interface
- Easy to use
- Looks super cool
- Developer friendly

## Installation

Installing WiiBalance is incredibly easy!

Make sure you have [Python 3.10+](https://www.python.org/downloads/) installed. Then, you'll need to install the package
using pip:

```bash
python3 -m pip install --upgrade pip
pip install wiibalance
```

## Initial Setup

To use WiiBalance, you'll need to know the Bluetooth address of your Wii Balance Board. If you've connected to it
before, WiiBalance can discover it for you, but it is heavily recommended to find it manually.

### Manual Pairing

1. Run the following command in your terminal. This will discover the Bluetooth address of your Wii Balance Board.

```bash
bluetoothctl --timeout 20 scan on | grep --line-buffered "RVL-WBC-01"
```

2. While the command above is running, press the red SYNC button on the Wii Balance Board, within the battery
   compartment. You may have to press it more than once.
3. Save the outputted Bluetooth address of the Wii Balance Board (it looks like `XX:XX:XX:XX:XX:XX`) for later use. You
   can then stop the command with `Ctrl+C`.
4. Pair with the board, substituting the Bluetooth address you saved earlier:

```bash
bluetoothctl pair XX:XX:XX:XX:XX:XX
```

You are now ready to use WiiBalance!

## CLI Quickstart

If you just paired with the board, you can jump right into the live demo:

```bash
wiibalance live
```

However, the connection is lost when you finish a command. When you run your next command, you must press the red SYNC
button in the battery compartment again. To fix
this, [set up the daemon](https://github.com/bboonstra/wiibalance/blob/main/docs/cli.md#daemon-setup)!

You can use the `--json` flag to get a stream of computer-readable live data. You can also use `wiibalance weight` to
get the current weight with units.

Full documentation is available [here](https://github.com/bboonstra/wiibalance/blob/main/docs/cli.md).

## Python Quickstart

If you paired [above](#manual-pairing), you're ready to use the library out-of-the-box.

```python
from wiibalance import create_balance_board

board = create_balance_board()
print(board.read_state())
board.disconnect()
exit()
```

Note that, if you are not using the daemon, `create_balance_board` will hang until after you press the red SYNC button
in the battery compartment of the board. You will also need to press the red SYNC button again if you `disconnect` and
attempt to reconnect. To fix this, [set up the daemon](https://github.com/bboonstra/wiibalance/blob/main/docs/cli.md#daemon-setup)!

Full documentation is available [here](https://github.com/bboonstra/wiibalance/blob/main/docs/python.md).

## Issues & Contributing

Please open an issue or submit a pull request! :)