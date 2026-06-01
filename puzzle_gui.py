"""
8-Puzzle Solver — Graphical Interface
Lets the user set the starting state, pick an algorithm, then watch the solution animate.
"""

import importlib.util
import os
import random
import threading
import tkinter as tk
from tkinter import messagebox, ttk

# ---------------------------------------------------------------------------
# Load 8_puzzle_solver.py dynamically (filename starts with a digit)
# ---------------------------------------------------------------------------
def _load_solver():
    import sys
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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GOAL_STATE = ("1", "2", "3", "4", "5", "6", "7", "8", "b")
DEFAULT_START = ("1", "2", "3", "4", "b", "5", "6", "7", "8")

TILE_COLORS = {
    "1": "#3498DB", "2": "#2ECC71", "3": "#E67E22",
    "4": "#9B59B6", "5": "#E74C3C", "6": "#1ABC9C",
    "7": "#F39C12", "8": "#2C3E50", "b": "#95A5A6",
}

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
     "Graph DFS with visited pruning. WARNING: path can be thousands of steps long."),
]

BG  = "#1A252F"
PNL = "#2C3E50"
FG  = "#ECF0F1"
ACCENT = "#27AE60"


# ---------------------------------------------------------------------------
# PuzzleBoard widget
# ---------------------------------------------------------------------------
class PuzzleBoard(tk.Frame):
    """3×3 sliding-tile board. Click a numbered tile next to the blank to slide it."""

    def __init__(self, parent, state=None, interactive=True, tile_size=60, **kw):
        kw.setdefault("bg", PNL)
        super().__init__(parent, **kw)
        self.interactive = interactive
        self.tile_size = tile_size
        self.state: list = list(state or DEFAULT_START)
        self._buttons: list[tk.Button] = []
        self._build()

    def _build(self):
        font_size = max(self.tile_size // 3, 12)
        for i in range(9):
            btn = tk.Button(
                self,
                font=("Arial", font_size, "bold"),
                relief="raised", bd=3,
                command=lambda i=i: self._on_click(i),
            )
            btn.grid(row=i // 3, column=i % 3, padx=3, pady=3,
                     ipadx=self.tile_size // 5, ipady=self.tile_size // 5)
            self._buttons.append(btn)
        self._refresh()

    def _on_click(self, idx: int):
        if not self.interactive:
            return
        blank = self.state.index("b")
        r, c = idx // 3, idx % 3
        br, bc = blank // 3, blank % 3
        if abs(r - br) + abs(c - bc) == 1:
            self.state[blank], self.state[idx] = self.state[idx], self.state[blank]
            self._refresh()

    def _refresh(self):
        for i, btn in enumerate(self._buttons):
            t = self.state[i]
            color = TILE_COLORS[t]
            btn.configure(
                text="" if t == "b" else t,
                bg=color,
                fg="white",
                activebackground=color,
                state="normal",
                cursor="hand2" if (self.interactive and t != "b") else "arrow",
            )

    def get_state(self) -> tuple:
        return tuple(self.state)

    def set_state(self, state):
        self.state = list(state)
        self._refresh()

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
        self.state = s
        self._refresh()

    def reset(self):
        self.state = list(DEFAULT_START)
        self._refresh()


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("8-Puzzle Solver")
        self.configure(bg=BG)
        self.resizable(False, False)

        self._path: list = []
        self._step: int = 0
        self._playing: bool = False
        self._play_job = None

        self._build_ui()
        self._on_algo_change()

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        # Title
        tk.Label(self, text="8-Puzzle Solver", font=("Arial", 18, "bold"),
                 bg=BG, fg=FG).pack(pady=(12, 6))

        # ── Top row ──────────────────────────────────────────────────────
        top = tk.Frame(self, bg=BG)
        top.pack(padx=12, pady=4)

        # Starting state panel
        lf_start = self._lf(top, "Starting State")
        lf_start.grid(row=0, column=0, padx=8, sticky="n")

        self._start_board = PuzzleBoard(lf_start, interactive=True, tile_size=58)
        self._start_board.pack(pady=4)

        row_btns = tk.Frame(lf_start, bg=PNL)
        row_btns.pack(pady=(0, 4))
        self._mkbtn(row_btns, "Shuffle", self._start_board.shuffle, "#E67E22").pack(side="left", padx=3)
        self._mkbtn(row_btns, "Reset",   self._start_board.reset,   "#7F8C8D").pack(side="left", padx=3)

        # Algorithm panel
        lf_algo = self._lf(top, "Algorithm")
        lf_algo.grid(row=0, column=1, padx=8, sticky="n")

        self._algo_var = tk.StringVar(value="a_star")
        for label, key, _ in ALGORITHMS:
            tk.Radiobutton(
                lf_algo, text=label,
                variable=self._algo_var, value=key,
                bg=PNL, fg=FG, selectcolor=BG,
                activebackground=PNL, activeforeground=FG,
                font=("Arial", 10),
                command=self._on_algo_change,
            ).pack(anchor="w", pady=1)

        self._algo_desc = tk.Label(lf_algo, text="", wraplength=190, justify="left",
                                   bg=PNL, fg="#BDC3C7", font=("Arial", 9))
        self._algo_desc.pack(anchor="w", pady=(2, 8))

        sep = tk.Frame(lf_algo, bg="#34495E", height=1)
        sep.pack(fill="x", pady=4)

        tk.Label(lf_algo, text="Animation speed:", bg=PNL, fg=FG,
                 font=("Arial", 9)).pack(anchor="w")
        self._speed = tk.IntVar(value=600)
        ttk.Scale(lf_algo, from_=80, to=1600, variable=self._speed,
                  orient="horizontal", length=180).pack(anchor="w")
        tk.Label(lf_algo, text="fast ←──────────→ slow",
                 bg=PNL, fg="#7F8C8D", font=("Arial", 8)).pack(anchor="w")

        self._solve_btn = self._mkbtn(lf_algo, "▶  SOLVE", self._start_solve,
                                      ACCENT, font=("Arial", 13, "bold"),
                                      padx=16, pady=6)
        self._solve_btn.pack(pady=12)

        self._status_var = tk.StringVar(value="Ready.")
        tk.Label(lf_algo, textvariable=self._status_var,
                 bg=PNL, fg=FG, font=("Arial", 9), wraplength=190).pack()

        # Goal state panel (static)
        lf_goal = self._lf(top, "Goal State")
        lf_goal.grid(row=0, column=2, padx=8, sticky="n")

        PuzzleBoard(lf_goal, state=GOAL_STATE, interactive=False, tile_size=58).pack(pady=4)

        # ── Solution viewer ───────────────────────────────────────────────
        lf_sol = self._lf(self, "Solution Viewer")
        lf_sol.pack(padx=12, pady=8, fill="x")

        # Progress row
        prow = tk.Frame(lf_sol, bg=PNL)
        prow.pack(fill="x", pady=(0, 4))

        self._step_lbl = tk.Label(prow, text="Step: — / —", width=16,
                                  bg=PNL, fg=FG, font=("Arial", 10), anchor="w")
        self._step_lbl.pack(side="left", padx=6)

        self._progress = ttk.Progressbar(prow, length=360, mode="determinate")
        self._progress.pack(side="left", padx=4, fill="x", expand=True)

        # Large solution board
        center = tk.Frame(lf_sol, bg=PNL)
        center.pack()
        self._sol_board = PuzzleBoard(center, interactive=False, tile_size=72)
        self._sol_board.pack(pady=6)

        # Navigation buttons
        nav = tk.Frame(lf_sol, bg=PNL)
        nav.pack(pady=4)
        nav_cfg = dict(bg=BG, fg=FG, font=("Arial", 14), padx=8, pady=4,
                       relief="flat", activebackground="#34495E", cursor="hand2")
        tk.Button(nav, text="|◀", command=self._go_first, **nav_cfg).pack(side="left", padx=2)
        tk.Button(nav, text="◀",  command=self._go_prev,  **nav_cfg).pack(side="left", padx=2)
        self._play_btn = tk.Button(nav, text="▶ Play", command=self._toggle_play,
                                   bg="#2980B9", fg=FG, font=("Arial", 13),
                                   padx=10, pady=4, relief="flat",
                                   activebackground="#3498DB", cursor="hand2")
        self._play_btn.pack(side="left", padx=2)
        tk.Button(nav, text="▶",  command=self._go_next,  **nav_cfg).pack(side="left", padx=2)
        tk.Button(nav, text="▶|", command=self._go_last,  **nav_cfg).pack(side="left", padx=2)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #
    def _lf(self, parent, text) -> tk.LabelFrame:
        return tk.LabelFrame(parent, text=text, bg=PNL, fg=FG,
                             font=("Arial", 10, "bold"), padx=8, pady=8)

    def _mkbtn(self, parent, text, cmd, color, **kw) -> tk.Button:
        cfg = dict(bg=color, fg="white", font=("Arial", 10), relief="flat",
                   activebackground=color, cursor="hand2", bd=0)
        cfg.update(kw)
        return tk.Button(parent, text=text, command=cmd, **cfg)

    def _on_algo_change(self):
        key = self._algo_var.get()
        for _, k, desc in ALGORITHMS:
            if k == key:
                self._algo_desc.configure(text=desc)
                break

    # ------------------------------------------------------------------ #
    # Solver                                                               #
    # ------------------------------------------------------------------ #
    def _start_solve(self):
        self._stop_play()
        self._path = []
        self._step = 0
        self._update_viewer()

        start = self._start_board.get_state()
        goal  = GOAL_STATE
        key   = self._algo_var.get()

        self._solve_btn.configure(state="disabled", text="Solving…")
        self._status_var.set("Running…")

        def _run():
            try:
                if key == "bfs":
                    result = _bfs_path(start, goal)
                elif key == "dfs":
                    result = _dfs_path(start, goal, max_trials=200_000)
                elif key == "dfs_bounded":
                    result = _dfs_bounded_path(start, goal, depth_limit=31)
                else:
                    fn = getattr(solver, key)
                    result = fn(start, goal, verbose=False)
            except Exception as exc:
                self.after(0, lambda: self._finish(error=str(exc)))
                return
            self.after(0, lambda: self._finish(result=result))

        threading.Thread(target=_run, daemon=True).start()

    def _finish(self, result=None, error=None):
        self._solve_btn.configure(state="normal", text="▶  SOLVE")

        if error:
            self._status_var.set(f"Error: {error}")
            messagebox.showerror("Error", error)
            return

        if isinstance(result, list) and result:
            self._path = result
            self._step = 0
            moves = len(result) - 1
            self._status_var.set(f"✔ Solved in {moves} move{'s' if moves != 1 else ''}!")
            self._update_viewer()
            if moves > 200:
                messagebox.showinfo(
                    "Long Path",
                    f"This algorithm found a {moves}-step path.\n"
                    "Use the navigation buttons or increase animation speed."
                )
        else:
            self._status_var.set("No solution found.")
            messagebox.showwarning("No Solution",
                                   "No solution exists for this starting state.")

    # ------------------------------------------------------------------ #
    # Solution viewer                                                      #
    # ------------------------------------------------------------------ #
    def _update_viewer(self):
        if not self._path:
            self._step_lbl.configure(text="Step: — / —")
            self._progress.configure(maximum=1, value=0)
            return
        total = len(self._path) - 1
        self._sol_board.set_state(self._path[self._step])
        self._step_lbl.configure(text=f"Step: {self._step} / {total}")
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
            self._update_viewer()

    def _go_next(self):
        if self._path and self._step < len(self._path) - 1:
            self._step += 1
            self._update_viewer()

    def _toggle_play(self):
        if self._playing:
            self._stop_play()
        else:
            if not self._path:
                return
            if self._step >= len(self._path) - 1:
                self._step = 0
            self._playing = True
            self._play_btn.configure(text="⏸ Pause")
            self._tick()

    def _stop_play(self):
        self._playing = False
        self._play_btn.configure(text="▶ Play")
        if self._play_job:
            self.after_cancel(self._play_job)
            self._play_job = None

    def _tick(self):
        if not self._playing:
            return
        if self._step < len(self._path) - 1:
            self._step += 1
            self._update_viewer()
            self._play_job = self.after(self._speed.get(), self._tick)
        else:
            self._stop_play()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    App().mainloop()
