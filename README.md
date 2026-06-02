# 8-Puzzle Solver (Python)

Python implementation of the 8-puzzle using multiple search strategies.

Main file:

- 8_puzzle_solver.py

## Features

- BFS (tree-style success/fail)
- DFS (visited pruning + safety trial cap)
- DFS with depth bound
- BFS path search
- BFS graph search
- Best-first search
- A* search (misplaced-tiles heuristic)
- Pretty square output for start/goal/path states

Puzzle state format:

- A flat sequence of 9 values
- Blank tile is b (or _ in CLI input)
- Example: 1 2 3 4 b 5 6 7 8

## Install (Linux)

Ubuntu / Linux Mint / Debian:

1. Install Python 3

```bash
sudo apt update
sudo apt install -y python3
```

1. Verify

```bash
python3 --version
```

No external packages are required.

## Quick Start

Run A* with defaults:

```bash
python3 8_puzzle_solver.py
```

Run DFS:

```bash
python3 8_puzzle_solver.py --algorithm dfs \
  --start "1 2 3 4 b 5 6 7 8" \
  --goal "1 b 3 4 2 5 6 7 8"
```

Run DFS bounded:

```bash
python3 8_puzzle_solver.py --algorithm dfs_bounded --depth-limit 20
```

Disable per-trial logs:

```bash
python3 8_puzzle_solver.py --algorithm a_star --quiet
```

## CLI Options

```text
--algorithm      bfs | dfs | dfs_bounded | bfps | btgs | best | a_star
--start          Start state, 9 tokens (default: "1 2 3 4 b 5 6 7 8")
--goal           Goal state, 9 tokens (default: "1 2 3 4 5 6 7 8 b")
--depth-limit    Used by dfs_bounded (default: 15)
--dfs-max-trials Safety cap for dfs (default: 200000)
--quiet          Disable per-trial logs
```

## Return Behavior

- bfs, dfs, dfs_bounded return status strings:
  - SUCCESS
  - FAIL
  - STOPPED_BY_TRIAL_LIMIT (dfs)
- bfps, btgs, best, a_star return solution paths and print each step as a square.

## Algorithm Notes

- BFS tree and DFS tree variants are educational and may explore many states.
- For harder instances, prefer a_star or btgs.
- DFS includes a trial cap to avoid memory blowups.

## Example Targets

```bash
python3 8_puzzle_solver.py --algorithm a_star \
  --start "1 2 3 4 b 5 6 7 8" \
  --goal "2 4 3 1 7 5 6 b 8"
```

```bash
python3 8_puzzle_solver.py --algorithm btgs \
  --start "1 2 3 4 b 5 6 7 8" \
  --goal "1 2 3 4 5 6 7 8 b"
```

# 8-Puzzle Solver GUI (Python)

You can also try the graphical user interface

```bash
python3 8_puzzle_solver_gui.py 
```


# Screenshots

![Alt text](https://github.com/sedzinfo/8-puzzle-problem-python/blob/main/screenshot/8_puzzle_solver.png)