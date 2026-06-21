#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def project_root(root: Path) -> Path:
    return root.parent


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def build_release_image(*, no_build: bool) -> tuple[Path, Path]:
    root = repo_root()
    top = project_root(root)
    udos_root = top / "udos"
    source_image = udos_root / "build" / "udos-release.d64"

    if not udos_root.is_dir():
        raise RuntimeError(f"missing sibling UDOS tree: {udos_root}")

    if not no_build:
        run(["make", "release"], cwd=udos_root)

    if not source_image.is_file():
        raise RuntimeError(f"missing UDOS release image: {source_image}")

    build_dir = root / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    out_image = build_dir / "actionc64u_c64.d64"
    out_listing = build_dir / "actionc64u_c64.dir.txt"
    shutil.copy2(source_image, out_image)

    c1541 = shutil.which("c1541")
    if c1541:
        listing = run([c1541, str(out_image), "-list"], cwd=root).stdout
    else:
        listing = "c1541 unavailable; copied UDOS release image without disk listing\n"
    out_listing.write_text(listing, encoding="ascii", errors="replace")

    return out_image, out_listing


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the ActionC64U UDOS release disk image")
    parser.add_argument("--no-build", action="store_true", help="reuse ../udos/build/udos-release.d64")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        image, listing = build_release_image(no_build=args.no_build)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(image)
    print(listing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
