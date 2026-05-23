"""
8-puzzle solver in Python.

Algorithms included:
- BFS (tree-style, success/fail)
- DFS (with visited pruning and trial cap)
- DFS bounded
- BFS path search
- BFS graph search
- Best-first (path length cost)
- A* (path length + misplaced-tiles heuristic)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import argparse
import heapq
from typing import Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple

State = Tuple[str, ...]
Path = List[State]

DEFAULT_START: State = ("1", "2", "3", "4", "b", "5", "6", "7", "8")
DEFAULT_GOAL: State = ("1", "2", "3", "4", "5", "6", "7", "8", "b")

DFS_MAX_TRIALS = 200_000
DEFAULT_DEPTH_LIMIT = 15


@dataclass(order=True)
class PrioritizedPath:
    cost: int
    path: Path


def parse_state(text: str) -> State:
    tokens = text.replace(",", " ").split()
    if len(tokens) != 9:
        raise ValueError("State must have exactly 9 items.")
    normalized = ["b" if t in {"_", "B", "b"} else t for t in tokens]
    if normalized.count("b") != 1:
        raise ValueError("State must contain exactly one blank tile: b")
    return tuple(normalized)


def pretty_state(state: State) -> str:
    rows = []
    rows.append("+---+---+---+")
    for r in range(3):
        row = state[r * 3 : r * 3 + 3]
        row_text = "|" + "|".join(f"{('_' if x == 'b' else x):^3}" for x in row) + "|"
        rows.append(row_text)
        rows.append("+---+---+---+")
    return "\n".join(rows)


def print_path(path: Path) -> None:
    print(f"Path length: {len(path) - 1} move(s)")
    for i, state in enumerate(path):
        print(f"\nStep {i}")
        print(pretty_state(state))


def children_of(state: State) -> List[State]:
    pos = state.index("b")
    row, col = divmod(pos, 3)
    result: List[State] = []

    def swap(new_pos: int) -> State:
        items = list(state)
        items[pos], items[new_pos] = items[new_pos], items[pos]
        return tuple(items)

    if col > 0:
        result.append(swap(pos - 1))
    if col < 2:
        result.append(swap(pos + 1))
    if row > 0:
        result.append(swap(pos - 3))
    if row < 2:
        result.append(swap(pos + 3))
    return result


def misplaced_tiles(state: State, goal: State) -> int:
    return sum(1 for a, b in zip(state, goal) if a != b)


def bfs(start: State, goal: State, verbose: bool = True) -> str:
    queue: Deque[State] = deque([start])
    trials = 0
    while queue:
        node = queue.popleft()
        if node == goal:
            return "SUCCESS"
        trials += 1
        if verbose:
            print(f"[BFS trial {trials}] {node}")
        queue.extend(children_of(node))
    return "FAIL"


def dfs(start: State, goal: State, max_trials: int = DFS_MAX_TRIALS, verbose: bool = True) -> str:
    stack: List[State] = [start]
    seen: Set[State] = set()
    trials = 0

    while stack:
        node = stack.pop()
        if node in seen:
            continue
        if node == goal:
            return "SUCCESS"

        seen.add(node)
        trials += 1
        if trials > max_trials:
            return "STOPPED_BY_TRIAL_LIMIT"
        if verbose:
            print(f"[DFS trial {trials}] {node}")

        kids = [k for k in children_of(node) if k not in seen]
        stack.extend(kids)

    return "FAIL"


def dfs_bounded(start: State, goal: State, depth_limit: int = DEFAULT_DEPTH_LIMIT, verbose: bool = True) -> str:
    stack: List[Tuple[State, int]] = [(start, 0)]
    seen_best_depth: Dict[State, int] = {}
    trials = 0

    while stack:
        node, depth = stack.pop()
        if node == goal:
            return "SUCCESS"
        if depth > depth_limit:
            continue

        prev_depth = seen_best_depth.get(node)
        if prev_depth is not None and prev_depth <= depth:
            continue
        seen_best_depth[node] = depth

        trials += 1
        if verbose:
            print(f"[DFS-bounded trial {trials}] depth={depth} {node}")

        for child in children_of(node):
            stack.append((child, depth + 1))

    return "FAIL"


def make_new_paths(children: Iterable[State], parent: Path) -> List[Path]:
    return [[child] + parent for child in children]


def make_new_paths_rcp(children: Iterable[State], parent: Path) -> List[Path]:
    parent_set = set(parent)
    return [[child] + parent for child in children if child not in parent_set]


def bfps(start: State, goal: State, verbose: bool = True) -> Optional[Path]:
    queue: Deque[Path] = deque([[start]])
    trials = 0

    while queue:
        path = queue.popleft()
        node = path[0]
        if node == goal:
            return list(reversed(path))

        trials += 1
        if verbose:
            print(f"[BFS-path trial {trials}] {node}")

        queue.extend(make_new_paths(children_of(node), path))

    return None


def btgs(start: State, goal: State, verbose: bool = True) -> Optional[Path]:
    queue: Deque[Path] = deque([[start]])
    visited: Set[State] = set()
    trials = 0

    while queue:
        path = queue.popleft()
        node = path[0]
        if node == goal:
            return list(reversed(path))

        if node in visited:
            continue
        visited.add(node)

        trials += 1
        if verbose:
            print(f"[BFS-graph trial {trials}] {node}")

        for child in children_of(node):
            if child not in visited and child not in path:
                queue.append([child] + path)

    return None


def best(start: State, goal: State, verbose: bool = True) -> Optional[Path]:
    open_heap: List[PrioritizedPath] = [PrioritizedPath(cost=0, path=[start])]
    visited: Set[State] = set()
    trials = 0

    while open_heap:
        current = heapq.heappop(open_heap)
        node = current.path[0]
        if node == goal:
            return list(reversed(current.path))
        if node in visited:
            continue
        visited.add(node)

        trials += 1
        if verbose:
            print(f"[Best-first trial {trials}] {node}")

        for child in children_of(node):
            if child in visited or child in current.path:
                continue
            new_path = [child] + current.path
            heapq.heappush(open_heap, PrioritizedPath(cost=len(new_path), path=new_path))

    return None


def a_star(start: State, goal: State, verbose: bool = True) -> Optional[Path]:
    open_heap: List[PrioritizedPath] = [PrioritizedPath(cost=misplaced_tiles(start, goal), path=[start])]
    g_score: Dict[State, int] = {start: 0}
    trials = 0

    while open_heap:
        current = heapq.heappop(open_heap)
        node = current.path[0]
        g = len(current.path) - 1

        if node == goal:
            return list(reversed(current.path))
        if g > g_score.get(node, 10**9):
            continue

        trials += 1
        if verbose:
            print(f"[A* trial {trials}] {node}")

        for child in children_of(node):
            if child in current.path:
                continue
            tentative_g = g + 1
            if tentative_g < g_score.get(child, 10**9):
                g_score[child] = tentative_g
                new_path = [child] + current.path
                f = tentative_g + misplaced_tiles(child, goal)
                heapq.heappush(open_heap, PrioritizedPath(cost=f, path=new_path))

    return None


def run_algorithm(
    algorithm: str,
    start: State,
    goal: State,
    verbose: bool,
    depth_limit: int,
    dfs_max_trials: int,
) -> None:
    if algorithm == "bfs":
        print(bfs(start, goal, verbose=verbose))
    elif algorithm == "dfs":
        print(dfs(start, goal, max_trials=dfs_max_trials, verbose=verbose))
    elif algorithm == "dfs_bounded":
        print(dfs_bounded(start, goal, depth_limit=depth_limit, verbose=verbose))
    elif algorithm == "bfps":
        path = bfps(start, goal, verbose=verbose)
        if path is None:
            print("FAIL")
        else:
            print_path(path)
    elif algorithm == "btgs":
        path = btgs(start, goal, verbose=verbose)
        if path is None:
            print("FAIL")
        else:
            print_path(path)
    elif algorithm == "best":
        path = best(start, goal, verbose=verbose)
        if path is None:
            print("FAIL")
        else:
            print_path(path)
    elif algorithm == "a_star":
        path = a_star(start, goal, verbose=verbose)
        if path is None:
            print("FAIL")
        else:
            print_path(path)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="8-puzzle solver in Python")
    parser.add_argument(
        "--algorithm",
        choices=["bfs", "dfs", "dfs_bounded", "bfps", "btgs", "best", "a_star"],
        default="a_star",
        help="Search algorithm to run",
    )
    parser.add_argument(
        "--start",
        default="1 2 3 4 b 5 6 7 8",
        help="Start state as 9 tokens, e.g. '1 2 3 4 b 5 6 7 8'",
    )
    parser.add_argument(
        "--goal",
        default="1 2 3 4 5 6 7 8 b",
        help="Goal state as 9 tokens",
    )
    parser.add_argument(
        "--depth-limit",
        type=int,
        default=DEFAULT_DEPTH_LIMIT,
        help="Depth limit used by dfs_bounded",
    )
    parser.add_argument(
        "--dfs-max-trials",
        type=int,
        default=DFS_MAX_TRIALS,
        help="Safety cap used by dfs",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable per-trial logs",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    start = parse_state(args.start)
    goal = parse_state(args.goal)

    print("=== 8-Puzzle Solver (Python) ===")
    print(f"Algorithm: {args.algorithm}")
    print("Start:")
    print(pretty_state(start))
    print("Goal:")
    print(pretty_state(goal))

    run_algorithm(
        algorithm=args.algorithm,
        start=start,
        goal=goal,
        verbose=(not args.quiet),
        depth_limit=args.depth_limit,
        dfs_max_trials=args.dfs_max_trials,
    )


if __name__ == "__main__":
    main()
