import sys
from collections import deque
import re

from .config import load_config
from wiibalance.state import BoardState

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def visible_len(s: str) -> int:
    return len(_ANSI_RE.sub("", s))


def center_visible(s: str, width: int) -> str:
    pad = width - visible_len(s)
    if pad <= 0:
        return s
    left = pad // 2
    right = pad - left
    return (" " * left) + s + (" " * right)


class C:
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GREY = "\033[90m"
    BR_GREEN = "\033[92m"
    BR_YELLOW = "\033[93m"
    BR_RED = "\033[91m"


def battery_color(pct):
    if pct >= 60:
        return C.BR_GREEN
    if pct >= 25:
        return C.BR_YELLOW
    return C.BR_RED


def battery_bar(pct, width=10):
    filled = int(round(width * max(0, min(100, pct)) / 100))
    bar = "█" * filled + "░" * (width - filled)
    return f"{battery_color(pct)}{bar}{C.RESET}"


SPARK_CHARS = " ▁▂▃▄▅▆▇█"


def sparkline(values, width=20):
    """Render a mini history graph from a deque of floats."""
    vals = list(values)[-width:]
    if len(vals) < 2:
        return " " * width
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    out = []
    for v in vals:
        idx = int((v - lo) / span * (len(SPARK_CHARS) - 1))
        out.append(SPARK_CHARS[idx])
    return "".join(out).rjust(width)


def quadrant_heat(value, scale, width=6):
    """Render one quadrant as a horizontal intensity bar, 0.scale."""
    frac = 0.0 if scale <= 0 else max(0.0, min(1.0, value / scale))
    filled = int(round(width * frac))
    bar = "█" * filled + "·" * (width - filled)
    # color by load: light/med/heavy
    color = C.GREEN if frac < 0.4 else (C.YELLOW if frac < 0.75 else C.RED)
    return f"{color}{bar}{C.RESET}"


class LiveDisplay:
    """Owns terminal redraw state and rolling history for the live view."""

    NUM_LINES = 15  # keep in sync with the block rendered in .render()

    GRID_COLS, GRID_ROWS = 11, 5  # higher-res than the old 5x3

    def __init__(self, history_len=40, trail_len=6):
        self._prev_line_count = None
        self._frame = 0
        self.weight_history = deque(maxlen=history_len)
        self.cop_trail = deque(maxlen=trail_len)  # most recent last

    def _grid(self, cop_x, cop_y):
        cols, rows = self.GRID_COLS, self.GRID_ROWS
        grid = [["·" for _ in range(cols)] for _ in range(rows)]

        # trail, oldest -> faintest, newest -> brightest 'O'
        trail_glyphs = [f"{C.GREY}.{C.RESET}", f"{C.GREY}o{C.RESET}",
                        f"{C.DIM}o{C.RESET}", f"{C.CYAN}o{C.RESET}",
                        f"{C.BR_YELLOW}O{C.RESET}"]
        for i, (tx, ty) in enumerate(self.cop_trail):
            col = int(round((min(max(tx, -1.0), 1.0) + 1) / 2 * (cols - 1)))
            row = int(round((1 - min(max(ty, -1.0), 1.0)) / 2 * (rows - 1)))
            col = max(0, min(cols - 1, col))
            row = max(0, min(rows - 1, row))
            glyph_idx = min(i, len(trail_glyphs) - 1)
            grid[row][col] = trail_glyphs[glyph_idx]

        # current position always on top, bold and bright
        col = int(round((min(max(cop_x, -1.0), 1.0) + 1) / 2 * (cols - 1)))
        row = int(round((1 - min(max(cop_y, -1.0), 1.0)) / 2 * (rows - 1)))
        col = max(0, min(cols - 1, col))
        row = max(0, min(rows - 1, row))
        grid[row][col] = f"{C.BOLD}{C.BR_RED}●{C.RESET}"

        return grid

    def _stability_label(self):
        if len(self.cop_trail) < 3:
            return f"{C.GREY}measuring…{C.RESET}"
        xs = [p[0] for p in self.cop_trail]
        ys = [p[1] for p in self.cop_trail]
        spread = (max(xs) - min(xs)) + (max(ys) - min(ys))
        if spread < 0.06:
            return f"{C.BR_GREEN}steady{C.RESET}"
        if spread < 0.20:
            return f"{C.BR_YELLOW}shifty{C.RESET}"
        return f"{C.BR_RED}wobbly{C.RESET}"

    def render(self, state: BoardState):
        self.weight_history.append(state.weights.total or 0.0)
        cop_x, cop_y = state.weights.center_of_pressure
        self.cop_trail.append((cop_x, cop_y))

        grid = self._grid(cop_x, cop_y)
        spark = sparkline(self.weight_history, width=20)
        max_quad = max(state.weights.top_left, state.weights.top_right,
                       state.weights.bottom_left, state.weights.bottom_right, 1.0)
        btn = f"{C.BR_YELLOW}{C.BOLD}PRESSED{C.RESET}" if state.button else f"{C.GREY}up{C.RESET}     "
        weight_unit = "lb" if load_config().get('units') == 'imperial' else 'kg'

        body = [
            f"┌────────────────────────────────────────────┐\033[K",
            f"│ {C.BOLD}Weight{C.RESET} {state.weights.total:7.2f} {weight_unit}   "
            f"{C.GREY}[{spark}]{C.RESET} │\033[K",
            f"│ CoP  x{C.CYAN}{cop_x:+5.2f}{C.RESET} "
            f"y{C.CYAN}{cop_y:+5.2f}{C.RESET}   "
            f"Stability: {self._stability_label()}     │\033[K",
            f"│ Battery {battery_bar(state.battery_percent)} {min(state.battery_percent, 100):3d}%   "
            f"Button: {btn}  │\033[K",
            f"├────────────────────────────────────────────┤\033[K",
            f"│ TL {quadrant_heat(state.weights.top_left, max_quad)}  "
            f"TR {quadrant_heat(state.weights.top_right, max_quad)}"
            f"   {state.weights.top_left:5.1f}{weight_unit} {state.weights.top_right:5.1f}{weight_unit}     │\033[K",
            f"│ BL {quadrant_heat(state.weights.bottom_left, max_quad)}  "
            f"BR {quadrant_heat(state.weights.bottom_right, max_quad)}"
            f"   {state.weights.bottom_left:5.1f}{weight_unit} {state.weights.bottom_right:5.1f}{weight_unit}     │\033[K",
            f"├────────────────────────────────────────────┤\033[K",
            f"│{'[FRONT]'.center(44)}│\033[K",
        ]
        for row in grid:
            row_str = ' '.join(row)
            body.append(f"│{center_visible(row_str, 44)}│\033[K")
        body.append(f"│{'[BACK]'.center(44)}│\033[K")
        body.append(f"└────────────────────────────────────────────┘\033[K")
        body.append(f"  {C.GREY}(Press Ctrl+C to exit){C.RESET}\033[K")

        # Move up by exactly what the *previous* frame actually printed,
        # not a hardcoded constant — and land at column 0 so drift can't
        # accumulate horizontally either.
        if self._frame > 0:
            sys.stdout.write(f"\033[{self._prev_line_count}A\r")

        sys.stdout.write("\n".join(body) + "\n")
        sys.stdout.flush()

        self._prev_line_count = len(body)
        self._frame += 1
