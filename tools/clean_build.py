#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    build = root / "build"
    if build.is_dir():
        shutil.rmtree(build)
    print(build)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
