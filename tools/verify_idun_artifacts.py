#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import sys

from export_idun_workspace import LINUX_TOOL_NAMES, TARGET_SERVICE_NAMES


def fail(message: str) -> None:
    raise RuntimeError(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify an Idun workspace export")
    parser.add_argument(
        "--build-tools",
        default="build/linux_tools",
        help="built Linux tool directory used as the export source",
    )
    parser.add_argument(
        "--export",
        default="build/idun-action",
        help="exported Idun workspace directory",
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    build_tools = Path(args.build_tools)
    if not build_tools.is_absolute():
        build_tools = root / build_tools
    export_root = Path(args.export)
    if not export_root.is_absolute():
        export_root = root / export_root
    exported_tools = export_root / "TOOLS"
    multicall = build_tools / "action-workspace-tools"
    built_help = build_tools / "action-help.sqlite3"
    exported_help = export_root / "DOC" / "action-help.sqlite3"
    manifest = export_root / "ACTION.PROJ"
    installer = export_root / "install-user.sh"
    playground = export_root / "PLAYGROUND"

    if not multicall.is_file():
        fail(f"missing multicall executable: {multicall}")
    if not manifest.is_file() or manifest.read_text(encoding="ascii").splitlines()[:1] != [
        "ACTION PROJECT"
    ]:
        fail("export is not a directly usable Action project")
    if not installer.is_file() or installer.stat().st_mode & 0o111 == 0:
        fail("export is missing its executable user installer")
    manifest_entries = manifest.read_text(encoding="ascii").splitlines()[1:]
    if not playground.is_dir() or any(
        not (playground / entry).is_file() for entry in manifest_entries if entry
    ):
        fail("export is missing flat playground examples")
    reference = multicall.read_bytes()
    digest = hashlib.sha256(reference).hexdigest()

    expected = set(LINUX_TOOL_NAMES)
    support_files = {built_help.name}
    built = {
        path.name
        for path in build_tools.iterdir()
        if path.name != multicall.name and path.name not in support_files
    }
    exported = {path.name for path in exported_tools.iterdir()}
    expected_artifacts = expected | set(TARGET_SERVICE_NAMES)
    if built != expected_artifacts:
        fail(f"built command inventory mismatch: {sorted(built ^ expected_artifacts)}")
    if exported != expected_artifacts:
        fail(f"exported command inventory mismatch: {sorted(exported ^ expected_artifacts)}")
    if not built_help.is_file():
        fail(f"missing built help database: {built_help}")
    if not exported_help.is_file() or exported_help.read_bytes() != built_help.read_bytes():
        fail("exported help database differs from built help database")
    with closing(
        sqlite3.connect(f"file:{exported_help}?mode=ro", uri=True)
    ) as database:
        topic_count = database.execute("SELECT count(*) FROM topics").fetchone()[0]
        integrity = database.execute("PRAGMA integrity_check").fetchone()[0]
    if topic_count < 1 or integrity != "ok":
        fail("exported help database failed validation")

    for name in LINUX_TOOL_NAMES:
        built_command = build_tools / name
        exported_command = exported_tools / name
        if not built_command.is_file() or not built_command.samefile(multicall):
            fail(f"built command does not resolve to multicall executable: {name}")
        if not exported_command.is_file():
            fail(f"missing exported command: {name}")
        if exported_command.read_bytes() != reference:
            fail(f"exported command differs from multicall executable: {name}")
        if exported_command.stat().st_mode & 0o111 == 0:
            fail(f"exported command is not executable: {name}")

    for name in TARGET_SERVICE_NAMES:
        built_service = build_tools / name
        exported_service = exported_tools / name
        if not built_service.is_file() or not exported_service.is_file():
            fail(f"missing C64 target service: {name}")
        if exported_service.read_bytes() != built_service.read_bytes():
            fail(f"exported target service differs from build: {name}")
        if built_service.read_bytes()[:8] != bytes.fromhex("4c086dcb06104000"):
            fail(f"invalid Idun tool header: {name}")

    forbidden = [
        path
        for path in export_root.rglob("*")
        if "UDOS" in path.name.upper() or "CPM" in path.name.upper()
    ]
    if forbidden:
        fail(f"forbidden legacy export artifact: {forbidden[0]}")

    print(f"commands={len(LINUX_TOOL_NAMES)}")
    print(f"help_topics={topic_count}")
    print(f"sha256={digest}")
    print("idun_artifacts=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"idun_artifacts=FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
