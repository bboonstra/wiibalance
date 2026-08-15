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

Installing WiiBalance is incredibly easy :)

```bash
pip install wiibalance
```

## CLI Usage

You'll want to install the WiiBalance daemon so that you don't have to re-pair your board after every command. Identify
your board by its Bluetooth address and run the following command:

```bash
$ wiibalance daemon setup -a <address>
```

Now, you can use the CLI!

### Live Demo

To display a cool-looking visualization of the Wii Balance Board's current state, run

```bash
$ wiibalance live
```

You can also use `--json` to get a clean JSON representation of the current state.

### Read Weight

```bash
$ wiibalance weight
Total Weight: 0.82
```

### Read Position

```bash
$ wiibalance cop
Center of Pressure: (1.0, 1.0)
```

The center of pressure is the point where the user's weight "is" on the board. It is mapped -1 to 1 left to right (X)
and -1 to 1 bottom to top (Y) such that (0, 0) is the center of the board.

### Control LED
```bash
$ wiibalance led --on
$ wiibalance led --off
$ wiibalance led # toggle
```
Pretty straightforward.

### Daemon

The WiiBalance daemon manages your board connection in the background. It provides six commands:

- `setup` - Configure the daemon with your board's Bluetooth address (run once)
- `remove` - Remove the daemon configuration

The following commands are convenient wrappers around systemctl:

- `status` - Check if the daemon is running
- `start` - Start the daemon service
- `stop` - Stop the daemon service
- `restart` - Restart the daemon service

```bash
$ wiibalance daemon status
$ wiibalance daemon start
```

## Python Usage

```python
>>> from wiibalance import BalanceBoard
>>> board = BalanceBoard("<INSERT ADDRESS>")
>>> print(w)
BoardState(weights=Weights(topright=0.6427765237020316, topleft=0.0, bottomright=0.14455782312925172, bottomleft=0.0, raw_topright=16760, raw_topleft=19841, raw_bottomright=20064, raw_bottomleft=3400), button=False, led=True, connected=True, battery_raw=112, temperature_raw=26, reference_temperature=None)
>>> board.disconnect()
>>> exit()
```

## Issues & Contributing
Please open an issue or submit a pull request! :)