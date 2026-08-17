# WiiBoard CLI

This documentation details usage of the WiiBoard CLI.

If you haven't
already, [set up and pair your Wii Balance Board for the first time.](https://github.com/bboonstra/wiibalance#initial-setup)

## Daemon Setup

For the most convenient usage of WiiBoard, you'll want to install the WiiBoard daemon. Setup is easy:

```bash
wiibalance daemon setup
```

This will install the daemon and set it up to run on startup.

Now that it's installed, press the red SYNC button on the Wii Balance Board and run `wiibalance daemon pair`. This will
create a persistent connection to the daemon.

If your Wii Balance Board runs out of battery, the daemon stops running, etc., you will need to press the red SYNC
button and run `wiibalance daemon pair` again.

## Command Reference

This is an exhaustive list of commands. The full set is also available by running `wiibalance --help`.

### Live Output

WiiBalance's best feature is its live output viewer, which neatly displays all data from the board in a single window.
Run this command:

```bash
wiibalance live
```

The output will look like this:
![Live Output](https://bboonstra.dev/wiibalance.gif)

If you're programming an application, use the `--json` flag to get a JSON output instead.

Sample output:

```json
{
  "raw": 8.073645153657681,
  "compensated": -1,
  "top_left": 0.21371428571428572,
  "top_right": 4.8352144469525955,
  "bottom_left": 0.9719953325554259,
  "bottom_right": 2.052721088435374,
  "center_of_pressure_x": 0.7062765093824965,
  "center_of_pressure_y": 0.25071851352781244,
  "button": false,
  "battery": 100,
  "battery_bars": 4,
  "led": true,
  "unit": "kg",
  "timestamp": 1786983011.4141629
}
```

### Reading Weight

To get a simple measurement of the weight on the Wii Balance Board, run:

```bash
wiibalance weight
```

The default unit is kg. This can be [configured](#config).

Sample output: `20.93kg`

### Battery

To get the current battery level, run:

```bash
wiibalance battery
```

This returns a percentage value. Please note that the Wii Balance Board only reports a battery level in increments of
25%, so the possible values returned are `0%`, `25%`, `50%`, `75%`, and `100%`. If you use the `--bars` flag instead,
the output will be returned as a value between 0 and 4, which is the actual reading from the board.

### Center of Pressure

The Center of Pressure (`cop`) is a measurement of the center of mass's position on the board relative to the center of
the board.

```bash
wiibalance cop
```

This command will return a tuple of the form `(x, y)` where x is mapped on `(-1, 1)` left-to-right and y is mapped on
`(-1, 1)` bottom-to-top. This means that the center of the board is at `(0, 0)`.

Sample output: `(-0.5009396754810874, 1.0)`

### LED

To turn the LED on or off, use one of the following commands:

```bash
wiibalance led on
wiibalance led off
wiibalance led # to toggle
```

Note that when WiiBalance connects to the board, whether through the daemon or directly, the LED is turned on to
indicate that the board is connected.

Sample output: `LED turned on`

### Disconnect

To disconnect from the Wii Balance Board, run:

```bash
wiibalance disconnect
```

The Bluetooth connection will be closed and the board state will be reset. If using the daemon, it will remain running
and listening on the socket, ready to reconnect automatically on the next command.

### Config

There are currently three configuration options, configurable with `get`, `set`, and `reset`:

```bash
$ wiibalance config get
{
    "daemon_enabled": true,
    "address": "00:23:CC:31:19:EC",
    "units": "metric"
}

$ wiibalance config set units imperial
Updated config:
{
    "daemon_enabled": true,
    "address": "00:23:CC:31:19:EC",
    "units": "imperial"
}

$ wiibalance config reset
Updated config:
{
    "daemon_enabled": false,
    "address": null,
    "units": "metric"
}
```

If `daemon_enabled` is set to true, cli commands will be sent to the daemon unless `--no-daemon` is specified. If
`address`
is set, it will be used by default for all commands unless `--address` is specified. If `units` is set to imperial,
weight will be returned in pounds; otherwise, it will be returned in kilograms.

Config is stored in `~/.config/wiibalance/config.json`.