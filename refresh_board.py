#!/usr/bin/env python3
"""Run public collector, copy clean JSON to local board repo, commit and push.

Expected sibling layout on Windows Desktop:
  x-virality-finish/   (this repo)
  x-virality-board/    (Pages repo)
"""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "board" / "data.public.json"
BOARD = HERE.parent / "x-virality-board"
DEST = BOARD / "data.json"


def run(cmd, cwd=HERE, check=True):
    print(">", " ".join(map(str, cmd)))
    return subprocess.run(cmd, cwd=cwd, check=check, text=True)


def main():
    if not (HERE / "public_fallback.py").exists():
        print("ERROR: public_fallback.py not found")
        return 2
    if not (BOARD / ".git").exists() or not (BOARD / "index.html").exists():
        print(f"ERROR: board repo not found at {BOARD}")
        return 3

    # Keep both local repos current before generating/publishing.
    run(["git", "pull", "--ff-only"], HERE)
    run(["git", "pull", "--ff-only"], BOARD)

    # Generate clean-epoch public data. public_fallback owns validation policy.
    run([sys.executable, str(HERE / "public_fallback.py"), "--timezone", "Europe/London"], HERE)
    if not SOURCE.exists():
        print(f"ERROR: collector did not create {SOURCE}")
        return 4

    shutil.copy2(SOURCE, DEST)
    print(f"COPIED: {SOURCE} -> {DEST}")

    run(["git", "add", "data.json"], BOARD)
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=BOARD)
    if changed.returncode == 0:
        print("NO CHANGE: board already matches latest collector output")
        return 0

    run(["git", "commit", "-m", "Refresh Connectrom virality board"], BOARD)
    run(["git", "push", "origin", "main"], BOARD)
    print("DONE: GitHub Pages data pushed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
