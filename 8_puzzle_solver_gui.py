"""
8-Puzzle Solver — Graphical Interface
Lets the user set the starting state, pick an algorithm, then watch the solution animate.

Only the Python standard library is used (tkinter). Click a tile next to the empty slot to slide it,
or press Shuffle; choose a search algorithm and press Solve, which reports the moves, the time and
the number of states the algorithm explored. The window starts in the light or dark theme of the
system, and the button at the top right switches it. Keyboard: Enter solves, Space plays
or pauses, Left / Right step through the solution, Home / End jump to its start / end, T switches the
theme.
"""

import importlib.util
import os
import random
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, ttk

# ---------------------------------------------------------------------------
# Load 8_puzzle_solver.py dynamically (filename starts with a digit)
# ---------------------------------------------------------------------------
def _load_solver():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "8_puzzle_solver.py")
    spec = importlib.util.spec_from_file_location("puzzle_solver", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["puzzle_solver"] = mod  # required so @dataclass can resolve cls.__module__
    spec.loader.exec_module(mod)
    return mod

solver = _load_solver()

# ---------------------------------------------------------------------------
# Path-tracking wrappers for algorithms that originally return only a status
# ---------------------------------------------------------------------------
def _bfs_path(start, goal):
    """Tree BFS that records the full path to each state."""
    from collections import deque
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        if node == goal:
            return path
        for child in solver.children_of(node):
            queue.append((child, path + [child]))
    return None


def _dfs_path(start, goal, max_trials=200_000):
    """Graph DFS (visited pruning) that records the full path."""
    stack = [(start, [start])]
    visited = set()
    trials = 0
    while stack:
        node, path = stack.pop()
        if node in visited:
            continue
        if node == goal:
            return path
        visited.add(node)
        trials += 1
        if trials > max_trials:
            return None
        for child in solver.children_of(node):
            if child not in visited:
                stack.append((child, path + [child]))
    return None


def _dfs_bounded_path(start, goal, depth_limit=31):
    """Depth-limited DFS that records the full path.
    Default depth limit is 31 — the maximum for any solvable 8-puzzle.
    """
    stack = [(start, [start], 0)]
    seen_best: dict = {}
    while stack:
        node, path, depth = stack.pop()
        if node == goal:
            return path
        if depth >= depth_limit:
            continue
        if seen_best.get(node, depth_limit + 1) <= depth:
            continue
        seen_best[node] = depth
        for child in solver.children_of(node):
            stack.append((child, path + [child], depth + 1))
    return None


def _run_counting(search):
    """
    Run search() and count the states it explored: every algorithm expands a state by asking the
    solver for its children, so solver.children_of is wrapped with a counter while it runs (one
    search runs at a time). Returns (result, explored states, generated children).
    """
    counts = {"explored": 0, "generated": 0}
    original = solver.children_of

    def counting_children_of(state):
        children = original(state)
        counts["explored"] += 1
        counts["generated"] += len(children)
        return children

    solver.children_of = counting_children_of
    try:
        result = search()
    finally:
        solver.children_of = original
    return result, counts["explored"], counts["generated"]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GOAL_STATE = ("1", "2", "3", "4", "5", "6", "7", "8", "b")
DEFAULT_START = ("1", "2", "3", "4", "b", "5", "6", "7", "8")

# (display_label, key, description)
ALGORITHMS = [
    ("A* Search",        "a_star",
     "Optimal. Uses path cost + misplaced-tiles heuristic."),
    ("Best-First",       "best",
     "Greedy by path length. Fast but not always optimal."),
    ("BFS Graph Search", "btgs",
     "BFS with visited-set. Avoids cycles, finds shortest path."),
    ("BFS Path Search",  "bfps",
     "Tree BFS with full path tracking. No cycle detection."),
    ("BFS (tree)",       "bfs",
     "Tree BFS without a visited-set. Can be very slow on hard states."),
    ("DFS Bounded",      "dfs_bounded",
     "Depth-limited DFS (limit = 31). Path is usually non-optimal."),
    ("DFS",              "dfs",
     "Graph DFS with visited pruning. Warning: the path can be thousands of steps long."),
]
ALGORITHM_NAMES = {key: label for label, key, _ in ALGORITHMS}

# Palettes. Dark: a slate page, slightly lighter cards, ivory tiles on a recessed tray. Light: a pale
# page, white cards, white tiles on a grey tray. In both, tiles already in their goal position are
# tinted green and indigo marks the selection, the progress and the main actions.
DARK = {
    "bg": "#0F172A", "card": "#1E293B", "border": "#334155", "hover": "#273449", "selected": "#273449",
    "tray": "#0B1220", "slot": "#141E30", "chip": "#0B1220",
    "text": "#E2E8F0", "strong": "#FFFFFF", "muted": "#94A3B8", "faint": "#64748B",
    "accent": "#6366F1", "accent_hover": "#818CF8", "on_accent": "#FFFFFF",
    "success": "#22C55E", "danger": "#F87171",
    "button": "#334155", "button_hover": "#475569", "button_text": "#FFFFFF",
    "tile": "#F1F5F9", "tile_hover": "#FFFFFF", "tile_text": "#0F172A", "tile_shadow": "#05080F",
    "tile_ok": "#DCFCE7", "tile_ok_hover": "#F0FDF4", "tile_ok_text": "#15803D",
}
LIGHT = {
    "bg": "#F1F5F9", "card": "#FFFFFF", "border": "#E2E8F0", "hover": "#F8FAFC", "selected": "#EEF2FF",
    "tray": "#CBD5E1", "slot": "#D9E1EB", "chip": "#F1F5F9",
    "text": "#0F172A", "strong": "#0F172A", "muted": "#475569", "faint": "#94A3B8",
    "accent": "#4F46E5", "accent_hover": "#6366F1", "on_accent": "#FFFFFF",
    "success": "#16A34A", "danger": "#DC2626",
    "button": "#E2E8F0", "button_hover": "#CBD5E1", "button_text": "#0F172A",
    "tile": "#FFFFFF", "tile_hover": "#F8FAFC", "tile_text": "#0F172A", "tile_shadow": "#94A3B8",
    "tile_ok": "#DCFCE7", "tile_ok_hover": "#F0FDF4", "tile_ok_text": "#15803D",
}
P = dict(DARK)  # the palette in use


def _system_prefers_dark():
    """The light or dark setting of the system (Windows, macOS, GNOME); dark when it cannot be read."""
    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
        if sys.platform == "darwin":
            out = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"],
                                 capture_output=True, text=True, timeout=2)
            return "dark" in out.stdout.lower()
        out = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                             capture_output=True, text=True, timeout=2)
        if out.returncode == 0:
            return "dark" in out.stdout.lower()
    except Exception:
        pass
    return True


def _pick_family(root, candidates, fallback="TkDefaultFont"):
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return name
    return tkfont.nametofont(fallback).actual("family")


def _rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    """A rectangle with rounded corners, as a smoothed polygon."""
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y1 + r,
              x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
              x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **kw)


# ---------------------------------------------------------------------------
# PuzzleBoard widget
# ---------------------------------------------------------------------------
class PuzzleBoard(tk.Canvas):
    """3×3 sliding-tile board drawn on a canvas. Click a tile next to the empty slot to slide it."""

    def __init__(self, parent, state=None, interactive=True, tile_size=60, scale=1.0, font_family=None,
                 on_change=None):
        self.tile = int(tile_size * scale)
        self.gap = max(4, int(tile_size * scale * 0.11))
        self.radius = int(self.tile * 0.16)
        self.size = 3 * self.tile + 4 * self.gap
        super().__init__(parent, width=self.size, height=self.size, bg=P["card"], highlightthickness=0, bd=0)
        self.interactive = interactive
        self.on_change = on_change
        self.font = (font_family or "TkDefaultFont", max(int(self.tile * 0.30), 10), "bold")
        self.state: list = list(state or DEFAULT_START)
        self._anim_job = None
        self._hover = None
        _rounded_rect(self, 0, 0, self.size, self.size, int(self.radius * 1.4), fill=P["tray"], outline="")
        for i in range(9):
            x, y = self._cell_xy(i)
            _rounded_rect(self, x, y, x + self.tile, y + self.tile, self.radius, fill=P["slot"], outline="")
        self._draw_tiles()
        if interactive:
            self.tag_bind("tile", "<Button-1>", self._on_click)
            self.tag_bind("tile", "<Enter>", self._on_enter)
            self.tag_bind("tile", "<Leave>", self._on_leave)

    # -------------------------------------------------------------- drawing
    def _cell_xy(self, index):
        r, c = divmod(index, 3)
        return self.gap + c * (self.tile + self.gap), self.gap + r * (self.tile + self.gap)

    def _draw_tiles(self):
        self.delete("tile")
        for index, value in enumerate(self.state):
            if value == "b":
                continue
            x, y = self._cell_xy(index)
            tag = f"t{value}"
            shadow = max(2, self.tile // 22)
            _rounded_rect(self, x, y + shadow, x + self.tile, y + self.tile + shadow, self.radius,
                          fill=P["tile_shadow"], outline="", tags=("tile", tag, "shadow"))
            _rounded_rect(self, x, y, x + self.tile, y + self.tile, self.radius,
                          fill=P["tile"], outline="", tags=("tile", tag, "body"))
            self.create_text(x + self.tile / 2, y + self.tile / 2, text=value, font=self.font,
                             fill=P["tile_text"], tags=("tile", tag, "label"))
        self._recolor()

    def _recolor(self):
        """Green tiles in their goal position; the hovered movable tile lighter."""
        for index, value in enumerate(self.state):
            if value == "b":
                continue
            in_place = GOAL_STATE[index] == value
            body = P["tile_ok"] if in_place else P["tile"]
            if self.interactive and value == self._hover and self._movable(index):
                body = P["tile_ok_hover"] if in_place else P["tile_hover"]
            for item in self.find_withtag(f"t{value}"):
                tags = self.gettags(item)
                if "body" in tags:
                    self.itemconfigure(item, fill=body)
                elif "label" in tags:
                    self.itemconfigure(item, fill=P["tile_ok_text"] if in_place else P["tile_text"])

    def _movable(self, index):
        blank = self.state.index("b")
        return abs(index // 3 - blank // 3) + abs(index % 3 - blank % 3) == 1

    # -------------------------------------------------------------- interaction
    def _tile_under_pointer(self):
        for tag in self.gettags("current"):
            if tag.startswith("t") and tag != "tile":
                return tag[1:]
        return None

    def _on_click(self, _event):
        value = self._tile_under_pointer()
        if value is None or self._anim_job:
            return
        index = self.state.index(value)
        if self._movable(index):
            new = list(self.state)
            blank = new.index("b")
            new[blank], new[index] = new[index], new[blank]
            self.set_state(new, animate=True, duration=120)
            if self.on_change:
                self.on_change()

    def _on_enter(self, _event):
        self._hover = self._tile_under_pointer()
        movable = self._hover is not None and self._movable(self.state.index(self._hover))
        self.configure(cursor="hand2" if movable else "")
        self._recolor()

    def _on_leave(self, _event):
        self._hover = None
        self.configure(cursor="")
        self._recolor()

    # -------------------------------------------------------------- state
    def get_state(self) -> tuple:
        return tuple(self.state)

    def set_state(self, state, animate=False, duration=150):
        """Show a state; a single slide from the current state glides into place when animate."""
        new = list(state)
        self.finish_animation()
        old = self.state
        moved = None
        if animate and old != new:
            changed = [i for i in range(9) if old[i] != new[i]]
            old_blank, new_blank = old.index("b"), new.index("b")
            adjacent = abs(old_blank // 3 - new_blank // 3) + abs(old_blank % 3 - new_blank % 3) == 1
            if len(changed) == 2 and adjacent:
                moved = new[old_blank]  # the tile now where the empty slot was
        if moved is None or moved == "b":
            self.state = new
            self._draw_tiles()
            return
        start_xy = self._cell_xy(old.index(moved))
        end_xy = self._cell_xy(new.index(moved))
        self.state = new
        self._recolor()
        self._animate(moved, start_xy, end_xy, duration)

    def _animate(self, value, start_xy, end_xy, duration):
        tag = f"t{value}"
        frames = max(int(duration / 15), 1)
        dx, dy = end_xy[0] - start_xy[0], end_xy[1] - start_xy[1]
        position = [0.0, 0.0]

        def step(k=1):
            t = k / frames
            eased = 1 - (1 - t) ** 3  # ease-out cubic
            target = (dx * eased, dy * eased)
            self.move(tag, target[0] - position[0], target[1] - position[1])
            position[0], position[1] = target
            if k < frames:
                self._anim_job = self.after(15, step, k + 1)
            else:
                self._anim_job = None

        self.tag_raise(tag)
        step()

    def finish_animation(self):
        """End a running slide at once (before a new state, or before the board is destroyed)."""
        if self._anim_job:
            self.after_cancel(self._anim_job)
            self._anim_job = None
            self._draw_tiles()

    def shuffle(self, n_moves: int = 150):
        """Random-walk from GOAL — always produces a solvable state."""
        s = list(GOAL_STATE)
        prev_blank = -1
        for _ in range(n_moves):
            blank = s.index("b")
            br, bc = blank // 3, blank % 3
            neighbors = [
                (br + dr) * 3 + (bc + dc)
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                if 0 <= br + dr < 3 and 0 <= bc + dc < 3
            ]
            # Avoid immediately reversing the last move
            candidates = [n for n in neighbors if n != prev_blank] or neighbors
            choice = random.choice(candidates)
            s[blank], s[choice] = s[choice], s[blank]
            prev_blank = blank
        self.set_state(s)
        if self.on_change:
            self.on_change()

    def reset(self):
        self.set_state(DEFAULT_START)
        if self.on_change:
            self.on_change()


# ---------------------------------------------------------------------------
# Small flat widgets
# ---------------------------------------------------------------------------
class FlatButton(tk.Label):
    """A flat button (a label, which looks the same on every platform) with hover and disabled states."""

    def __init__(self, parent, text, command, primary=True, font=None, padx=14, pady=7):
        bg, hover, fg = ((P["accent"], P["accent_hover"], P["on_accent"]) if primary
                         else (P["button"], P["button_hover"], P["button_text"]))
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font, padx=padx, pady=pady, cursor="hand2")
        self._bg, self._hover, self._fg = bg, hover, fg
        self.command = command
        self.enabled = True
        self.bind("<Enter>", lambda e: self.enabled and self.configure(bg=self._hover))
        self.bind("<Leave>", lambda e: self.enabled and self.configure(bg=self._bg))
        self.bind("<Button-1>", lambda e: self.enabled and self.command and self.command())

    def set_enabled(self, enabled, text=None):
        self.enabled = enabled
        self.configure(bg=self._bg if enabled else P["border"], fg=self._fg if enabled else P["muted"],
                       cursor="hand2" if enabled else "")
        if text is not None:
            self.configure(text=text)


class Slider(tk.Canvas):
    """A horizontal slider: a rounded track, filled up to a round knob; click or drag to set it."""

    def __init__(self, parent, variable, from_, to, command=None, scale=1.0):
        self.knob = int(8 * scale)
        self.track = max(4, int(6 * scale))
        # a small requested width: packed with fill="x", it takes the width of its card
        super().__init__(parent, width=int(120 * scale), height=2 * self.knob + 6, bg=P["card"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.variable, self.lo, self.hi, self.command = variable, from_, to, command
        self.scale_factor = scale
        self.hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._set_from_event)
        self.bind("<B1-Motion>", self._set_from_event)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))

    def _set_hover(self, on):
        self.hover = on
        self._draw()

    def _set_from_event(self, event):
        pad = self.knob + 2
        width = max(self.winfo_width() - 2 * pad, 1)
        fraction = min(max((event.x - pad) / width, 0), 1)
        self.variable.set(int(round(self.lo + fraction * (self.hi - self.lo))))
        self._draw()
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        pad = self.knob + 2
        width, y = self.winfo_width(), self.winfo_height() / 2
        fraction = (float(self.variable.get()) - self.lo) / (self.hi - self.lo)
        x = pad + fraction * (width - 2 * pad)
        self.create_line(pad, y, width - pad, y, width=self.track, capstyle="round", fill=P["tray"])
        self.create_line(pad, y, x, y, width=self.track, capstyle="round", fill=P["accent"])
        r = self.knob + (1 if self.hover else 0)
        self.create_oval(x - r, y - r, x + r, y + r, fill="white", outline=P["accent"],
                         width=max(2, int(2 * self.scale_factor)))


class OptionList(tk.Frame):
    """A vertical list of choices; the chosen one is highlighted with an accent bar."""

    def __init__(self, parent, options, variable, command, font, bold_font):
        super().__init__(parent, bg=P["card"])
        self.variable, self.command = variable, command
        self.font, self.bold_font = font, bold_font
        self.rows = {}
        for label, key in options:
            row = tk.Frame(self, bg=P["card"], cursor="hand2")
            row.pack(fill="x", pady=1)
            bar = tk.Frame(row, bg=P["card"], width=3)
            bar.pack(side="left", fill="y")
            text = tk.Label(row, text=label, bg=P["card"], fg=P["text"], font=font, anchor="w",
                            padx=10, pady=5)
            text.pack(side="left", fill="x", expand=True)
            for widget in (row, bar, text):
                widget.bind("<Button-1>", lambda e, k=key: self.select(k))
                widget.bind("<Enter>", lambda e, k=key: self._hover(k, True))
                widget.bind("<Leave>", lambda e, k=key: self._hover(k, False))
            self.rows[key] = (row, bar, text)
        self._paint()

    def select(self, key):
        self.variable.set(key)
        self._paint()
        self.command()

    def _hover(self, key, on):
        if key == self.variable.get():
            return
        row, bar, text = self.rows[key]
        color = P["hover"] if on else P["card"]
        for widget in (row, bar, text):
            widget.configure(bg=color)

    def _paint(self):
        for key, (row, bar, text) in self.rows.items():
            selected = key == self.variable.get()
            background = P["selected"] if selected else P["card"]
            row.configure(bg=background)
            bar.configure(bg=P["accent"] if selected else background)
            text.configure(bg=background, fg=P["strong"] if selected else P["muted"],
                           font=self.bold_font if selected else self.font)


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self, dark=None):
        super().__init__()
        self.title("8-Puzzle Solver")
        self.resizable(False, False)
        # pixel sizes follow the screen's DPI (1.0 at 96 dpi)
        self.ui_scale = max(1.0, float(self.tk.call("tk", "scaling")) / (96 / 72))

        family = _pick_family(self, ["Segoe UI", "Inter", "SF Pro Text", "Helvetica Neue", "Noto Sans",
                                     "Ubuntu", "Cantarell", "DejaVu Sans"])
        self.family = family
        self.f_title = (family, 20, "bold")
        self.f_sub = (family, 10)
        self.f_head = (family, 9, "bold")
        self.f_body = (family, 10)
        self.f_body_bold = (family, 10, "bold")
        self.f_small = (family, 9)
        self.f_stat = (family, 15, "bold")
        self.f_button = (family, 11, "bold")

        # the state of the window, kept when the theme is switched and the widgets are rebuilt
        self._algo_var = tk.StringVar(value="a_star")
        self._speed = tk.IntVar(value=600)
        self._start_state = DEFAULT_START
        self._path: list = []
        self._step: int = 0
        self._playing: bool = False
        self._play_job = None
        self._solving = False
        self._stats = {"moves": "—", "explored": "—", "time": "—", "algorithm": "—"}
        self._status = ("Ready.", "muted")
        self._outer = None

        self.dark = _system_prefers_dark() if dark is None else dark
        self._apply_theme()
        self._bind_keys()

    def S(self, pixels):
        return int(pixels * self.ui_scale)

    # ------------------------------------------------------------------ #
    # Theme                                                                #
    # ------------------------------------------------------------------ #
    def _apply_theme(self):
        """Use the palette of self.dark and (re)build the widgets with it, keeping the state."""
        if self._outer is not None:
            self._start_state = self._start_board.get_state()
            for board in (self._start_board, self._goal_board, self._sol_board):
                board.finish_animation()
            self._outer.destroy()
        P.clear()
        P.update(DARK if self.dark else LIGHT)
        self.configure(bg=P["bg"])
        self._style()
        self._build_ui()
        self._dark_title_bar(self.dark)

    def toggle_theme(self):
        playing = self._playing
        self._stop_play()
        self.dark = not self.dark
        self._apply_theme()
        if playing:
            self._toggle_play()

    def _dark_title_bar(self, dark):
        """Windows 10/11: a title bar in the color of the theme."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            value = ctypes.c_int(1 if dark else 0)
            for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (and its older number)
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value),
                                                              ctypes.sizeof(value)) == 0:
                    break
            # redraw the frame: SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0020)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #
    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Step.Horizontal.TProgressbar", troughcolor=P["tray"], background=P["accent"],
                        bordercolor=P["tray"], lightcolor=P["accent"], darkcolor=P["accent"],
                        thickness=self.S(8))

    def _card(self, parent, title):
        card = tk.Frame(parent, bg=P["card"], highlightthickness=1, highlightbackground=P["border"],
                        padx=self.S(16), pady=self.S(14))
        tk.Label(card, text=title.upper(), bg=P["card"], fg=P["faint"], font=self.f_head).pack(
            anchor="w", pady=(0, self.S(10)))
        return card

    def _build_ui(self):
        S = self.S
        card = P["card"]
        outer = tk.Frame(self, bg=P["bg"], padx=S(22), pady=S(18))
        outer.pack()
        self._outer = outer

        # Header: title on the left, the theme button on the right
        header = tk.Frame(outer, bg=P["bg"])
        header.pack(fill="x", pady=(0, S(14)))
        titles = tk.Frame(header, bg=P["bg"])
        titles.pack(side="left")
        tk.Label(titles, text="8-Puzzle Solver", font=self.f_title, bg=P["bg"], fg=P["text"]).pack(anchor="w")
        tk.Label(titles, text="Set a starting state, choose a search algorithm, and watch it solve.",
                 font=self.f_sub, bg=P["bg"], fg=P["muted"]).pack(anchor="w")
        self._theme_btn = FlatButton(header, "☀  Light" if self.dark else "☾  Dark", self.toggle_theme,
                                     primary=False, font=self.f_body_bold, padx=S(12), pady=S(5))
        self._theme_btn.pack(side="right", anchor="n", pady=(S(4), 0))

        # ── Top row ──────────────────────────────────────────────────────
        top = tk.Frame(outer, bg=P["bg"])
        top.pack(fill="x")

        # Starting state
        card_start = self._card(top, "Starting state")
        card_start.grid(row=0, column=0, sticky="nsew", padx=(0, S(12)))
        self._start_board = PuzzleBoard(card_start, state=self._start_state, interactive=True, tile_size=56,
                                        scale=self.ui_scale, font_family=self.family,
                                        on_change=self._on_start_change)
        self._start_board.pack()
        row_btns = tk.Frame(card_start, bg=card)
        row_btns.pack(fill="x", pady=(S(12), 0))
        FlatButton(row_btns, "Shuffle", self._start_board.shuffle, primary=False,
                   font=self.f_body_bold).pack(side="left", expand=True, fill="x", padx=(0, S(4)))
        FlatButton(row_btns, "Reset", self._start_board.reset, primary=False,
                   font=self.f_body_bold).pack(side="left", expand=True, fill="x", padx=(S(4), 0))
        self._start_info = tk.Label(card_start, text="", bg=card, fg=P["muted"], font=self.f_small,
                                    justify="left")
        self._start_info.pack(anchor="w", pady=(S(8), 0))

        # Algorithm
        card_algo = self._card(top, "Algorithm")
        card_algo.grid(row=0, column=1, sticky="nsew", padx=(0, S(12)))
        OptionList(card_algo, [(label, key) for label, key, _ in ALGORITHMS], self._algo_var,
                   self._on_algo_change, self.f_body, self.f_body_bold).pack(fill="x")
        self._algo_desc = tk.Label(card_algo, text="", wraplength=S(220), justify="left",
                                   bg=card, fg=P["muted"], font=self.f_small)
        self._algo_desc.pack(anchor="w", pady=(S(8), S(10)))

        speed_row = tk.Frame(card_algo, bg=card)
        speed_row.pack(fill="x")
        tk.Label(speed_row, text="Animation speed", bg=card, fg=P["text"], font=self.f_small).pack(side="left")
        self._speed_lbl = tk.Label(speed_row, text="", bg=card, fg=P["muted"], font=self.f_small)
        self._speed_lbl.pack(side="right")
        self._speed_slider = Slider(card_algo, self._speed, 80, 1600, command=self._show_speed,
                                    scale=self.ui_scale)
        self._speed_slider.pack(fill="x", pady=(S(4), 0))
        ends = tk.Frame(card_algo, bg=card)
        ends.pack(fill="x")
        tk.Label(ends, text="fast", bg=card, fg=P["faint"], font=self.f_small).pack(side="left")
        tk.Label(ends, text="slow", bg=card, fg=P["faint"], font=self.f_small).pack(side="right")
        self._show_speed()

        self._solve_btn = FlatButton(card_algo, "▶  Solve", self._start_solve, font=self.f_button, pady=S(9))
        self._solve_btn.pack(fill="x", pady=(S(14), S(8)))
        if self._solving:
            self._solve_btn.set_enabled(False, "Solving…")
        self._status_lbl = tk.Label(card_algo, text="", bg=card, fg=P["muted"], font=self.f_small,
                                    wraplength=S(220), justify="left")
        self._status_lbl.pack(anchor="w")
        self._set_status(*self._status)

        # Goal state
        card_goal = self._card(top, "Goal state")
        card_goal.grid(row=0, column=2, sticky="nsew")
        self._goal_board = PuzzleBoard(card_goal, state=GOAL_STATE, interactive=False, tile_size=56,
                                       scale=self.ui_scale, font_family=self.family)
        self._goal_board.pack()
        tk.Label(card_goal, text="Green tiles are already in\ntheir goal position.", bg=card, fg=P["muted"],
                 font=self.f_small, justify="left").pack(anchor="w", pady=(S(12), 0))

        # ── Solution viewer ───────────────────────────────────────────────
        card_sol = self._card(outer, "Solution")
        card_sol.pack(fill="x", pady=(S(14), 0))

        body = tk.Frame(card_sol, bg=card)
        body.pack(fill="x")
        self._sol_board = PuzzleBoard(body, interactive=False, tile_size=78, scale=self.ui_scale,
                                      font_family=self.family)
        self._sol_board.pack(side="left")

        side = tk.Frame(body, bg=card)
        side.pack(side="left", fill="both", expand=True, padx=(S(22), 0))

        stats = tk.Frame(side, bg=card)
        stats.pack(fill="x")
        stats.columnconfigure((0, 1), weight=1, uniform="stat")
        self._stat_labels = {}
        for i, (key, caption) in enumerate((("moves", "Moves"), ("explored", "States explored"),
                                            ("time", "Time"), ("algorithm", "Algorithm"))):
            self._stat_labels[key] = self._stat(stats, caption, row=i // 2, column=i % 2)
        self._show_stats()

        step_row = tk.Frame(side, bg=card)
        step_row.pack(fill="x", pady=(S(18), S(6)))
        tk.Label(step_row, text="Step", bg=card, fg=P["muted"], font=self.f_small).pack(side="left")
        self._step_lbl = tk.Label(step_row, text="— / —", bg=card, fg=P["text"], font=self.f_body_bold)
        self._step_lbl.pack(side="right")
        self._progress = ttk.Progressbar(side, mode="determinate", style="Step.Horizontal.TProgressbar")
        self._progress.pack(fill="x")

        nav = tk.Frame(side, bg=card)
        nav.pack(pady=(S(16), 0))
        nav_cfg = dict(primary=False, font=(self.family, 14, "bold"), padx=S(14), pady=S(4))
        FlatButton(nav, "«", self._go_first, **nav_cfg).pack(side="left", padx=S(3))
        FlatButton(nav, "‹", self._go_prev, **nav_cfg).pack(side="left", padx=S(3))
        self._play_btn = FlatButton(nav, "▶  Play", self._toggle_play, font=self.f_button, padx=S(18),
                                    pady=S(7))
        self._play_btn.pack(side="left", padx=S(3))
        FlatButton(nav, "›", self._go_next, **nav_cfg).pack(side="left", padx=S(3))
        FlatButton(nav, "»", self._go_last, **nav_cfg).pack(side="left", padx=S(3))

        tk.Label(side, text="Enter solve  ·  Space play/pause  ·  ← → step  ·  Home/End  ·  T theme",
                 bg=card, fg=P["faint"], font=self.f_small).pack(pady=(S(14), 0))

        self._on_algo_change()
        self._on_start_change()
        self._update_viewer()

    def _stat(self, parent, caption, row, column):
        chip = tk.Frame(parent, bg=P["chip"], padx=self.S(12), pady=self.S(8))
        chip.grid(row=row, column=column, sticky="nsew",
                  padx=(0, self.S(4)) if column == 0 else (self.S(4), 0), pady=(0 if row == 0 else self.S(8), 0))
        tk.Label(chip, text=caption, bg=P["chip"], fg=P["faint"], font=self.f_small).pack(anchor="w")
        value = tk.Label(chip, text="—", bg=P["chip"], fg=P["text"], font=self.f_stat)
        value.pack(anchor="w")
        return value

    def _bind_keys(self):
        self.bind("<Return>", lambda e: self._start_solve())
        self.bind("<space>", lambda e: self._toggle_play())
        self.bind("<Left>", lambda e: self._go_prev())
        self.bind("<Right>", lambda e: self._go_next())
        self.bind("<Home>", lambda e: self._go_first())
        self.bind("<End>", lambda e: self._go_last())
        self.bind("<KeyPress-t>", lambda e: self.toggle_theme())
        self.bind("<KeyPress-T>", lambda e: self.toggle_theme())

    def _show_speed(self):
        self._speed_lbl.configure(text=f"{int(float(self._speed.get()))} ms / move")

    def _show_stats(self, **values):
        self._stats.update(values)
        for key, label in self._stat_labels.items():
            label.configure(text=self._stats[key])

    def _on_start_change(self):
        state = self._start_board.get_state()
        self._start_state = state
        if not self._path:  # until something is solved, the solution board shows the starting state
            self._sol_board.set_state(state)
        misplaced = sum(1 for a, b in zip(state, GOAL_STATE) if a != b and a != "b")
        self._start_info.configure(
            text="Click a tile next to the empty slot to slide it.\n"
                 + ("Already solved." if misplaced == 0 else f"{misplaced} tile{'s' if misplaced != 1 else ''} "
                    "out of place."))

    def _on_algo_change(self):
        key = self._algo_var.get()
        for _, k, desc in ALGORITHMS:
            if k == key:
                self._algo_desc.configure(text=desc)
                break

    def _set_status(self, text, kind="muted"):
        """kind is muted, success or danger: a color of the palette, so that it follows the theme."""
        self._status = (text, kind)
        self._status_lbl.configure(text=text, fg=P[kind])

    # ------------------------------------------------------------------ #
    # Solver                                                               #
    # ------------------------------------------------------------------ #
    def _start_solve(self):
        if self._solving:
            return
        self._stop_play()
        self._path = []
        self._step = 0
        self._update_viewer()

        start = self._start_board.get_state()
        goal = GOAL_STATE
        key = self._algo_var.get()

        self._solving = True
        self._solve_btn.set_enabled(False, "Solving…")
        self._set_status(f"Running {ALGORITHM_NAMES[key]}…")
        self._show_stats(moves="…", explored="…", time="…", algorithm=ALGORITHM_NAMES[key])

        def _search():
            if key == "bfs":
                return _bfs_path(start, goal)
            if key == "dfs":
                return _dfs_path(start, goal, max_trials=200_000)
            if key == "dfs_bounded":
                return _dfs_bounded_path(start, goal, depth_limit=31)
            return getattr(solver, key)(start, goal, verbose=False)

        def _run():
            began = time.perf_counter()
            try:
                result, explored, _generated = _run_counting(_search)
            except Exception as exc:
                message = str(exc)
                self.after(0, lambda: self._finish(error=message))
                return
            elapsed = time.perf_counter() - began
            self.after(0, lambda: self._finish(result=result, elapsed=elapsed, explored=explored))

        threading.Thread(target=_run, daemon=True).start()

    def _finish(self, result=None, error=None, elapsed=None, explored=None):
        self._solving = False
        self._solve_btn.set_enabled(True, "▶  Solve")

        if error:
            self._set_status(f"Error: {error}", "danger")
            self._show_stats(moves="—", explored="—", time="—")
            messagebox.showerror("Error", error)
            return

        if elapsed is not None:
            self._show_stats(time=f"{elapsed * 1000:.0f} ms" if elapsed < 1 else f"{elapsed:.2f} s")
        if explored is not None:
            self._show_stats(explored=f"{explored:,}")
        if isinstance(result, list) and result:
            self._path = result
            self._step = 0
            moves = len(result) - 1
            self._show_stats(moves=f"{moves:,}")
            self._set_status(f"✔  Solved in {moves:,} move{'s' if moves != 1 else ''}, "
                             f"exploring {explored:,} state{'s' if explored != 1 else ''}.", "success")
            self._update_viewer()
            if moves > 200:
                messagebox.showinfo(
                    "Long Path",
                    f"This algorithm found a {moves}-step path.\n"
                    "Use the navigation buttons or increase animation speed."
                )
        else:
            self._show_stats(moves="—")
            self._set_status("No solution found.", "danger")
            messagebox.showwarning("No Solution",
                                   "No solution exists for this starting state.")

    # ------------------------------------------------------------------ #
    # Solution viewer                                                      #
    # ------------------------------------------------------------------ #
    def _update_viewer(self, animate=False):
        if not self._path:
            self._step_lbl.configure(text="— / —")
            self._progress.configure(maximum=1, value=0)
            self._sol_board.set_state(self._start_board.get_state())
            return
        total = len(self._path) - 1
        duration = min(180, int(self._speed.get() * 0.6))
        self._sol_board.set_state(self._path[self._step], animate=animate, duration=duration)
        self._step_lbl.configure(text=f"{self._step} / {total}")
        self._progress.configure(maximum=max(total, 1), value=self._step)

    def _go_first(self):
        if self._path:
            self._step = 0
            self._update_viewer()

    def _go_last(self):
        if self._path:
            self._step = len(self._path) - 1
            self._update_viewer()

    def _go_prev(self):
        if self._path and self._step > 0:
            self._step -= 1
            self._update_viewer(animate=True)

    def _go_next(self):
        if self._path and self._step < len(self._path) - 1:
            self._step += 1
            self._update_viewer(animate=True)

    def _toggle_play(self):
        if self._playing:
            self._stop_play()
        else:
            if not self._path:
                return
            if self._step >= len(self._path) - 1:
                self._step = 0
                self._update_viewer()
            self._playing = True
            self._play_btn.configure(text="‖  Pause")
            self._tick()

    def _stop_play(self):
        self._playing = False
        self._play_btn.configure(text="▶  Play")
        if self._play_job:
            self.after_cancel(self._play_job)
            self._play_job = None

    def _tick(self):
        if not self._playing:
            return
        if self._step < len(self._path) - 1:
            self._step += 1
            self._update_viewer(animate=True)
            self._play_job = self.after(self._speed.get(), self._tick)
        else:
            self._stop_play()


def _enable_dpi_awareness():
    """Sharp text on high-DPI Windows screens (Tk is otherwise scaled up as a blurry bitmap)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    _enable_dpi_awareness()
    App().mainloop()
