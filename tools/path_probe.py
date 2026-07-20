#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    targets = {
        "repository": root,
        "linux C++ source": root / "src" / "tools_linux" / "action_workspace_tools.cpp",
        "6502 runtime library": root / "src" / "runtime" / "modules",
        "Linux build script": root / "tools" / "build_linux_tools.sh",
        "Idun export script": root / "tools" / "export_idun_workspace.py",
    }

    missing = []
    for label, path in targets.items():
        resolved = path.resolve()
        exists = resolved.exists()
        print(f"{label:10} {'PASS' if exists else 'FAIL'} {resolved}")
        if not exists:
            missing.append((label, resolved))

    if missing:
        print(
            "Missing required Idun fork paths. Restore this repository as one "
            "self-contained checkout; no adjacent CP/M-65 or UDOS tree is required.",
            file=sys.stderr,
        )
        return 1

    print("All required local paths resolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
