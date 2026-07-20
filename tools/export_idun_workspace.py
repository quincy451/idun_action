#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


LINUX_TOOL_NAMES = (
    "actnew",
    "actadd",
    "actwork",
    "actsrc",
    "actfile",
    "actchk",
    "actdir",
    "actcopy",
    "actdel",
    "actmkdir",
    "actrmdir",
    "actmove",
    "actren",
    "actwrite",
    "actinfo",
    "actmon",
    "actdbg",
    "actprof",
    "acttree",
    "tree",
    "xcopy",
    "deltree",
    "actspc",
    "actsprite",
    "actbitmap",
    "actedit",
    "acthelp",
    "act2save",
    "actsave",
    "actc",
    "alink",
)

TARGET_SERVICE_NAMES = ("actsvc",)

ACTIVE_EXAMPLES = (
    "asmblock_demo.act",
    "dbf1_demo.act",
    "gfx1_demo.act",
    "gfx_resource_demo.act",
    "hello.act",
    "if.act",
    "input1_demo.act",
    "math.act",
    "math1_demo.act",
    "ovl_demo.act",
    "prime_real.act",
    "real_cmp.act",
    "real_demo.act",
    "real_math.act",
    "reu_demo.act",
    "reu_dbf_sort.act",
    "sidspr1_demo.act",
)

ACTIVE_RESOURCES = (
    "marker.abm",
    "player.spr",
)

ACTIVE_SOURCE_LIBRARIES = (
    "dbf1.act",
    "gfx1.act",
    "input1.act",
    "math1.act",
    "sidspr1.act",
)

PORTING_NOTES = (
    "new_math_func.txt",
    "new_gfx_func.txt",
)

EXPORT_MARKER = ".actionc64u-idun-export"


def copy_named_files(source_dir: Path, target_dir: Path, names: tuple[str, ...]) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        source = source_dir / name
        if not source.is_file():
            raise FileNotFoundError(f"missing active source file: {source}")
        shutil.copy2(source, target_dir / source.name.upper())


def runtime_object_is_placeholder(path: Path) -> bool:
    lines = [line.strip() for line in path.read_text(encoding="ascii").splitlines() if line.strip()]
    if len(lines) < 2 or lines[0].upper() != "OBJ1" or not lines[1].startswith("{"):
        return False
    try:
        record = json.loads(lines[1])
        module = record["module"].encode("ascii")
        payload = bytes.fromhex(record["payload_hex"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError(f"malformed runtime object: {path}") from error
    return payload == module + b"\0"


def build_linux_tools(root: Path) -> Path:
    result = subprocess.run(
        ["bash", str(root / "tools" / "build_linux_tools.sh")],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)
    return Path(result.stdout.strip().splitlines()[-1])


def export_linux_tools(source_dir: Path, tools_dir: Path) -> None:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"missing Linux tools directory: {source_dir}")
    tools_dir.mkdir(parents=True, exist_ok=True)
    for name in LINUX_TOOL_NAMES:
        source = source_dir / name
        if not source.exists():
            raise FileNotFoundError(f"missing Linux tool: {source}")
        target = tools_dir / name
        if target.exists() or target.is_symlink():
            target.unlink()
        if source.is_symlink():
            link_target = source.resolve()
            shutil.copy2(link_target, target)
        else:
            shutil.copy2(source, target)
        target.chmod(target.stat().st_mode | 0o755)
    for name in TARGET_SERVICE_NAMES:
        source = source_dir / name
        if not source.is_file():
            raise FileNotFoundError(f"missing C64 target service: {source}")
        target = tools_dir / name
        if target.exists() or target.is_symlink():
            target.unlink()
        shutil.copy2(source, target)
        target.chmod(target.stat().st_mode & ~0o111)


def export_docs(
    docs_dir: Path,
    exported_runtime: list[str],
    skipped_runtime: list[str],
) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "README.txt").write_text(
        (
            "ActionC64U Idun/Linux workspace\n"
            "\n"
            "TOOLS contains Linux executables that run on the Idun cartridge's "
            "Raspberry Pi side. SRC contains Action source. OBJ contains compiler "
            "objects. BIN contains generated C64 .PRG files. LIB contains "
            "linkable 6502 runtime modules used by the final .PRG. RES contains "
            "compiler-embedded sprite and bitmap assets. PLAYGROUND "
            "contains flat copies of the examples for current-directory use.\n"
            "\n"
            "The workspace does not require UDOS. Build-time tools are Linux "
            "processes; generated .PRG files remain Commodore programs. The "
            "top-level ACTION.PROJ already tracks every shipped SRC example, "
            "so TOOLS/actc hello and TOOLS/alink hello work in this directory. "
            "Run ./install-user.sh once to make the Linux commands available on "
            "the user PATH. In PLAYGROUND, actc reads <module>.ACT and writes "
            "<module>.OBJ in that same directory; alink writes <module>.PRG and "
            "<module>.DBG there too.\n"
        ),
        encoding="ascii",
    )
    (docs_dir / "operator.txt").write_text(
        (
            "Default workflow:\n"
            "\n"
            "0. Optionally run ./install-user.sh, log in again (or run hash -r), "
            "and invoke actc, actedit, actspc, actsprite, actbitmap, and alink "
            "without a TOOLS/ prefix.\n"
            "1. Put Action source under SRC/ for a structured project. For a "
            "flat current-directory workflow, enter PLAYGROUND/ or put "
            "<module>.ACT directly in the current directory. Local source wins "
            "and all OBJ/PRG/DBG outputs stay beside it.\n"
            "2. Run TOOLS/actnew <project> to create a project.\n"
            "3. Run TOOLS/actadd <module> inside a project to add modules.\n"
            "4. Run TOOLS/actwork, TOOLS/actsrc, TOOLS/actfile, and TOOLS/actchk "
            "for project inspection.\n"
            "5. Run TOOLS/actspc <file-or-filespec> [...] to atomically format "
            "one or more Action files. Quoted wildcards such as '*.act' are "
            "expanded by ACTSPC, including uppercase .ACT files.\n"
            "6. Run TOOLS/actc <module> and TOOLS/alink <module>; ALINK emits "
            "BIN/<module>.PRG for the Commodore.\n"
            "7. Run TOOLS/actedit <module> index, find <text>, or symbols for "
            "SQLite-backed source navigation. Rebuildable editor state lives "
            "under .action/workspace.sqlite3. On a terminal, the built-in editor "
            "provides Ctrl-S save, Ctrl-Q quit, F1 "
            "context help, F2 editor-command help, F3 complete language "
            "reference, F4 library/feature/example browsing, F5 definitions, "
            "F6 ACTSPC formatting, F7 references, F8 graphics-resource editing, "
            "history, "
            "and Ctrl-click navigation. The cursor is a blinking block over an "
            "inverse-video cell. Plain actedit uses an uncolored display; add "
            "tui for syntax highlighting. ACTEDIT never launches EDITOR or an "
            "external editor. Ctrl-B marks a block; Ctrl-A selects all; Ctrl-C, "
            "Ctrl-X, and Ctrl-V copy, cut, and paste; mouse dragging also "
            "selects text. The "
            "compile, build, and debug modes drive the native tool pipeline. "
            "PRIME_REAL.ACT demonstrates REAL square-root prime testing. "
            "REU_DBF_SORT.ACT demonstrates stable command-line DBF sorting "
            "with one through ten START,LENGTH,A|D specifications and an REU "
            "swap buffer. ASMBLOCK_DEMO.ACT demonstrates scoped 6502 "
            "instructions, Action symbols, and local labels. "
            "GFX_RESOURCE_DEMO.ACT declares external SPRITE and BITMAP files "
            "from RES/. Put the cursor on a RESOURCE declaration and press F8; "
            "arrows move, Space or 0-3 paints, C clears, Ctrl-S saves, and "
            "Ctrl-Q exits ACTSPRITE/ACTBITMAP.\n"
            "8. Run TOOLS/acthelp <keyword-or-function> for the same external "
            "SQLite help catalog used by ACTEDIT. Search with acthelp search "
            "<text>; DOC/action-help.sqlite3 remains outside C64 memory.\n"
            "9. TOOLS/actmon edit, compile, build, or debug <module> exposes "
            "the same project workflow.\n"
            "10. Run TOOLS/actdbg <module> source <address>, line <line>, or "
            "symbols [filter] to inspect linked source maps. break <line>, "
            "breaks, and clear <id> manage prepared breakpoints under "
            ".action/debug.sqlite3. The live mode launches the bundled C64 "
            "target service through Idun for register, memory, run/halt, "
            "instruction step, and persistent-breakpoint control. Use "
            "live -- argument ... or the live args command to populate "
            "MAIN(CARD argc,CARD ARRAY argv).\n"
            "11. Run TOOLS/actprof <module> live [seconds] for sampled source-level "
            "profiling, or import <samples> [interval-us] and report [run-id]. "
            "Runs live in .action/profile.sqlite3 and use ALINK's "
            ".action/code-map.sqlite3 for function and statement attribution.\n"
        ),
        encoding="ascii",
    )
    (docs_dir / "runtime-status.txt").write_text(
        (
            "Active UDOS-free 6502 runtime modules\n"
            "\n"
            + "\n".join(exported_runtime)
            + "\n\nLegacy placeholders not exported\n\n"
            + "\n".join(skipped_runtime)
            + "\n\n"
            "BYTE/CARD/INT/REAL arrays, typed pointers and indirect parameters, "
            "length-prefixed BYTE strings, "
            "frame-preserved local routine parameters, and BYTE/CARD/INT/REAL user "
            "functions are active compiler forms. Function calls can appear in "
            "expressions; local scalar, array, REAL, and temporary state is "
            "preserved across recursive calls, with depth limited by the C64 "
            "hardware stack. "
            "REAL and signed INT source lowering is active. REAL uses full-domain "
            "IEEE-754 binary32 standalone helpers with gradual underflow, "
            "round-to-nearest ties-to-even core arithmetic, correctly rounded "
            "square root, and exact decimal formatting. REU BYTE ARRAY allocation "
            "and 8/16-bit peek/poke are active "
            "through direct C64 REU hardware modules. REU free/copy/32-bit "
            "operations remain unavailable. OVERLAY blocks are active as "
            "resident program-owned PRG sections; dynamic load/unload is not "
            "active. DBF1 compiler lowering and link-selected DBF modules are "
            "active. DBF files are staged in one allocator-owned REU block and "
            "loaded/saved through standalone C64 KERNAL adapters. The generated "
            "DBF path is proven in headless VICE with D64 I/O; physical "
            "Idun/C64/REU validation remains pending.\n"
        ),
        encoding="ascii",
    )


def export_runtime_modules(root: Path, lib_dir: Path) -> tuple[list[str], list[str]]:
    source_dir = root / "src" / "runtime" / "modules"
    exported: list[str] = []
    skipped: list[str] = []
    lib_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(source_dir.glob("*.obj")):
        if runtime_object_is_placeholder(source):
            skipped.append(source.name.upper())
            continue
        target_name = source.name.upper()
        shutil.copy2(source, lib_dir / target_name)
        exported.append(target_name)
    return exported, skipped


def export_help_database(source_dir: Path, docs_dir: Path) -> None:
    source = source_dir / "action-help.sqlite3"
    if not source.is_file():
        raise FileNotFoundError(f"missing generated help database: {source}")
    shutil.copy2(source, docs_dir / "action-help.sqlite3")


def prepare_output_directory(root: Path, out_root: Path) -> None:
    root = root.resolve()
    out_root = out_root.resolve()
    if out_root == Path(out_root.anchor) or out_root == root or out_root in root.parents:
        raise RuntimeError(f"refusing unsafe export output: {out_root}")
    if out_root.exists():
        default_build_root = (root / "build").resolve()
        inside_build = default_build_root in out_root.parents
        if not inside_build and not (out_root / EXPORT_MARKER).is_file():
            raise RuntimeError(
                f"refusing to replace unmarked export directory: {out_root}"
            )
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)
    (out_root / EXPORT_MARKER).write_text(
        "ActionC64U Idun/Linux generated workspace\n",
        encoding="ascii",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export an Idun/Linux ActionC64U workspace")
    parser.add_argument(
        "--output",
        default="build/idun-action",
        help="output directory for the Linux-side Action workspace",
    )
    parser.add_argument(
        "--no-build-tools",
        action="store_true",
        help="copy existing build/linux_tools outputs instead of rebuilding",
    )
    parser.add_argument(
        "--tools-source",
        help="copy an existing tool build directory (for example build/linux_tools-aarch64)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    out_root = Path(args.output).resolve()
    if args.tools_source and args.no_build_tools:
        parser.error("--tools-source and --no-build-tools are mutually exclusive")
    if args.tools_source:
        source_tools = Path(args.tools_source).resolve()
    elif args.no_build_tools:
        source_tools = root / "build" / "linux_tools"
    else:
        source_tools = build_linux_tools(root)
    try:
        prepare_output_directory(root, out_root)
    except RuntimeError as exc:
        parser.error(str(exc))

    tools_dir = out_root / "TOOLS"
    src_dir = out_root / "SRC"
    playground_dir = out_root / "PLAYGROUND"
    obj_dir = out_root / "OBJ"
    bin_dir = out_root / "BIN"
    lib_dir = out_root / "LIB"
    docs_dir = out_root / "DOC"
    res_dir = out_root / "RES"

    for directory in (src_dir, playground_dir, obj_dir, bin_dir, lib_dir, res_dir):
        directory.mkdir(parents=True, exist_ok=True)

    (out_root / "ACTION.PROJ").write_text(
        "ACTION PROJECT\n"
        + "".join(f"{Path(name).name.upper()}\n" for name in ACTIVE_EXAMPLES),
        encoding="ascii",
    )

    export_linux_tools(source_tools, tools_dir)
    copy_named_files(root / "examples", src_dir, ACTIVE_EXAMPLES)
    copy_named_files(root / "examples", playground_dir, ACTIVE_EXAMPLES)
    copy_named_files(root / "examples" / "assets", res_dir, ACTIVE_RESOURCES)
    copy_named_files(root / "examples" / "assets", playground_dir, ACTIVE_RESOURCES)
    copy_named_files(root / "lib", lib_dir, ACTIVE_SOURCE_LIBRARIES)
    exported_runtime, skipped_runtime = export_runtime_modules(root, lib_dir)
    export_docs(docs_dir, exported_runtime, skipped_runtime)
    copy_named_files(root / "docs", docs_dir, PORTING_NOTES)
    export_help_database(source_tools, docs_dir)
    installer = out_root / "install-user.sh"
    shutil.copy2(root / "tools" / "install_linux_tools.sh", installer)
    installer.chmod(installer.stat().st_mode | 0o755)

    print(out_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
