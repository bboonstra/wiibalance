# WiiBoard Python

This documentation details usage of the WiiBoard Python library.

If you haven't
already, [set up and pair your Wii Balance Board for the first time.](https://github.com/bboonstra/wiibalance#initial-setup)

## Create a BalanceBoard

The best way to use WiiBalance is with a `BalanceBoard` object. WiiBalance will automatically create either a direct or
daemon-managed board using the `create_balance_board` function. This is the recommended method of usage.

```python
from wiibalance import create_balance_board

board = create_balance_board()
state = board.read_state()
print(state.weights.total)
# 1.1608352144469525
```

The following useful methods are available on the `BalanceBoard` object:

- `read_state`
- `led_on`
- `led_off`
- `toggle_led`
- `button`
- `weights`

These methods are fairly self-explanatory; feel free to open a PR to add more documentation.

## Using the Daemon

Whenever a BalanceBoard is created, it will attempt to connect to the physical board. To do this, the board must be in
pairing mode, activated by pressing the red SYNC button in the board's battery compartment. To avoid repeating this
process whenever you create a BalanceBoard, you should set up
the [WiiBalance daemon](https://github.com/bboonstra/wiibalance/blob/main/docs/cli.md#daemon-setup). This will create a
background process that stays connected to the board, and your BalanceBoard will connect to the daemon instead.

## Weights

The `Weights` object, returned in `read_state` and by `weights`, contains the following attributes:

- `total`: The total weight on the board
- `top_left`: Weight on this foot of the board
- `top_right`: Weight on this foot of the board
- `bottom_left`: Weight on this foot of the board
- `bottom_right`: Weight on this foot of the board
- `center_of_pressure`: [Position](https://github.com/bboonstra/wiibalance/blob/main/docs/cli.md#center-of-pressure) of weight on board

There are also `raw` variants of each directional weight, which are raw sensor values and NOT weight values.

## Button Callbacks

If you'd like something to happen when the button is pressed, you must have a DirectBalanceBoard object. You can create
this either by calling `create_balance_board` with `use_daemon=false` as an argument and then casting it to
DirectBalanceBoard, or by instantiating a
`DirectBalanceBoard` object directly. A DirectBalanceBoard CANNOT be used while the daemon is managing the board 
connection.

Once you have a DirectBalanceBoard object, you can register a callback function by adding it to the `on_button_press`,
`on_button_release`, or `on_button_change` dicts. The callback function will be called with the button state as an
argument.

```python
from wiibalance import DirectBalanceBoard

board = DirectBalanceBoard()
board.on_button_press = lambda state: print(state)


def do_something(state):
    print(state.weights.total)


board.on_button_release = do_something
```

BalanceBoard workers run in their own threads, so the callbacks will run asynchronously.

## Config

It's recommended to use the [CLI](https://github.com/bboonstra/wiibalance/blob/main/docs/cli.md#config) to configure your board.

If this isn't possible, you can use the `read_config` and `write_config` functions. You can also edit the
`~/.config/wiibalance/config.json` file.
