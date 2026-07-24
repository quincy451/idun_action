#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    targets = [
        root / "build",
        root / ".pytest_cache",
        *sorted(root.rglob("__pycache__"), reverse=True),
    ]
    for target in targets:
        if target.is_dir():
            shutil.rmtree(target)
            print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
