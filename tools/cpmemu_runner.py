#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from typing import Sequence

LOWERCASE_83 = re.compile(r"^[a-z0-9]{1,8}(?:\.[a-z0-9]{1,3})?$")


@dataclass(frozen=True)
class Cpm65Paths:
    repo_root: Path
    cpm_root: Path
    cpmemu: Path
    diskdefs: Path


class RunnerError(RuntimeError):
    pass


def resolve_paths() -> Cpm65Paths:
    repo_root = Path(__file__).resolve().parents[1]
    cpm_root = repo_root.parent / "cpm65-u64"
    cpmemu = cpm_root / "bin" / "cpmemu"
    diskdefs = cpm_root / "diskdefs"
    return Cpm65Paths(repo_root=repo_root, cpm_root=cpm_root, cpmemu=cpmemu, diskdefs=diskdefs)


def enforce_lowercase_83(value: str, *, label: str) -> None:
    candidate = value
    if ":" in candidate:
        _, candidate = candidate.split(":", 1)
    candidate = Path(candidate).name
    if not candidate:
        raise RunnerError(f"{label} is empty; CP/M filenames must be all-lowercase 8.3 names")
    if not LOWERCASE_83.fullmatch(candidate):
        raise RunnerError(
            f"{label} '{value}' is not a lowercase 8.3 name. "
            "cpmemu only exposes all-lowercase 8.3 filenames to CP/M programs."
        )


def looks_like_cpm_filename(value: str) -> bool:
    if ":" in value:
        return True
    if "/" in value or "\\" in value:
        return True
    return "." in value


def probe_capabilities(cpmemu: Path) -> set[str]:
    if not cpmemu.is_file():
        return set()

    try:
        result = subprocess.run(
            [str(cpmemu), "-h"],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return set()

    help_text = (result.stdout or "") + (result.stderr or "")
    capabilities: set[str] = set()
    if "-p DRIVE=PATH" in help_text:
        capabilities.add("drive-map")
    if "-d" in help_text:
        capabilities.add("debug")
    if "-m NUM" in help_text:
        capabilities.add("memory-top")
    return capabilities


def build_command(
    paths: Cpm65Paths,
    program: str,
    program_args: Sequence[str],
    drive_maps: Sequence[str],
    *,
    debug: bool,
    cwd: Path,
    use_diskdefs_arg: bool,
) -> list[str]:
    if not paths.cpmemu.is_file():
        raise RunnerError(
            f"Missing cpmemu binary at {paths.cpmemu}. Build ../cpm65-u64 first; see docs/cpmemu.md."
        )
    if not paths.diskdefs.is_file():
        raise RunnerError(f"Missing diskdefs file at {paths.diskdefs}.")

    capabilities = probe_capabilities(paths.cpmemu)
    command = [str(paths.cpmemu)]

    if debug:
        if "debug" not in capabilities:
            raise RunnerError("This cpmemu build does not advertise debugger support via -h.")
        command.append("-d")

    for mapping in drive_maps:
        if "drive-map" not in capabilities:
            raise RunnerError(
                "Drive mapping was requested, but this cpmemu build does not advertise -p DRIVE=PATH support."
            )
        if len(mapping) < 3 or mapping[1] != "=":
            raise RunnerError(f"Invalid drive mapping '{mapping}'. Expected syntax like A=/path/to/files.")
        drive_letter = mapping[0]
        host_path = mapping[2:]
        if not drive_letter.isalpha() or len(drive_letter) != 1:
            raise RunnerError(f"Invalid drive mapping '{mapping}'. Drive must be a single letter.")
        if not Path(host_path).exists():
            raise RunnerError(f"Drive mapping path does not exist: {host_path}")
        command.extend(["-p", f"{drive_letter.upper()}={Path(host_path).resolve()}"])

    program_path = Path(program)
    if not program_path.is_absolute():
        program_path = (cwd / program_path).resolve()
    if not program_path.is_file():
        raise RunnerError(f"Program not found: {program_path}")
    enforce_lowercase_83(program_path.name, label="program")

    final_args = list(program_args)
    if use_diskdefs_arg:
        diskdefs_name = paths.diskdefs.name
        enforce_lowercase_83(diskdefs_name, label="diskdefs")
        final_args.append(diskdefs_name)

    for index, arg in enumerate(final_args, start=1):
        if looks_like_cpm_filename(arg):
            enforce_lowercase_83(arg, label=f"arg{index}")

    command.append(str(program_path))
    command.extend(final_args)
    return command


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CP/M-65 programs through cpmemu.")
    parser.add_argument("program", help="Path to the .com program to run")
    parser.add_argument("args", nargs="*", help="Arguments to pass through to the CP/M program")
    parser.add_argument(
        "--cwd",
        default=None,
        help="Host working directory for cpmemu (defaults to ../cpm65-u64 so diskdefs is visible)",
    )
    parser.add_argument(
        "--drive",
        action="append",
        default=[],
        metavar="DRIVE=PATH",
        help="Map a cpmemu drive letter to a host path when -p support is available",
    )
    parser.add_argument(
        "--diskdefs-arg",
        action="store_true",
        help="Append the located diskdefs filename as a CP/M argument",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Start cpmemu in debugger mode if the local build advertises -d",
    )
    parser.add_argument(
        "--print-command",
        action="store_true",
        help="Print the resolved command line before execution",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    paths = resolve_paths()
    cwd = Path(args.cwd).resolve() if args.cwd else paths.cpm_root

    if not cwd.exists() or not cwd.is_dir():
        print(f"error: invalid cpmemu working directory: {cwd}", file=sys.stderr)
        return 2

    try:
        command = build_command(
            paths,
            args.program,
            args.args,
            args.drive,
            debug=args.debug,
            cwd=cwd,
            use_diskdefs_arg=args.diskdefs_arg,
        )
    except RunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.print_command:
        print("Resolved command:", " ".join(command), file=sys.stderr)
        print(f"Host cwd: {cwd}", file=sys.stderr)

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        print(f"error: failed to launch cpmemu: {exc}", file=sys.stderr)
        return 2

    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
