#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math
import shutil
import subprocess

ROOT = Path("/mnt/c/test/action/actionc64u")
UDOS_ROOT = ROOT.parent / "udos"
EXPERIMENTS = ROOT / "experiments" / "program_size"
BUILD = ROOT / "build" / "program_size"
TOOLS = ROOT / "build" / "udos_tools"
BASE_FS = UDOS_ROOT / "build" / "udos-release-fs-manual-pipeline-44"
CFG = EXPERIMENTS / "c64raw.cfg"
LARGE_CFG = EXPERIMENTS / "c64raw_large.cfg"
RUNNER = TOOLS / "AVMRUN.PRG"
HARNESS = TOOLS / "tool_abi_harness"
ACTC_PRG = TOOLS / "ACTC_HARNESS.PRG"
ALINK_PRG = TOOLS / "ALINK.PRG"
AVMRUNC_PRG = TOOLS / "AVMRUNC.PRG"
SERVICES_INC = TOOLS / "udos_services.inc"
ACTC_LABELS = TOOLS / "actc_harness.current.labels"
ALINK_LABELS = TOOLS / "alink.current.labels"
AVMRUNC_LABELS = TOOLS / "avmrunc.current.labels"
LOAD_ADDR = bytes([0x00, 0x10])


@dataclass(frozen=True)
class RawBench:
    stem: str
    avm_name: str
    avm_payload: int
    description: str
    shared_runtime_leverage: str


@dataclass(frozen=True)
class FairBench:
    name: str
    description: str
    native_source: Path
    action_source: Path
    native_stem: str
    built_avo_name: str
    built_avm_name: str


@dataclass(frozen=True)
class LargeBench:
    name: str
    description: str
    calls: int


RAW_BENCHES = [
    RawBench("hello", "AVM_HELLO_E.AVM", 15, "literal string print", "print"),
    RawBench("sum100_only", "AVM_SUM100_ONLY.AVM", 40, "pure 1..100 sum, no output", "none"),
    RawBench("sum100", "AVM_SUM100_PRINT.AVM", 44, "1..100 sum plus integer print", "print"),
    RawBench("filecopy", "AVM_FILECOPY_ONLY.AVM", 77, "byte copy SOURCE.TXT -> COPYOUT.TXT", "fileio"),
    RawBench("count_digits", "AVM_COUNT_DIGITS.AVM", 86, "count digit bytes in DIGITS.TXT and print total", "fileio+print"),
]

FAIR_BENCH = FairBench(
    name="local_call74",
    description="compiled local proc increments INT X; MAIN calls it 74 times; no print/file helpers",
    native_source=EXPERIMENTS / "asm_local_call74.asm",
    action_source=EXPERIMENTS / "local_call74.act",
    native_stem="local_call74",
    built_avo_name="compiled_local_call74.avo",
    built_avm_name="COMPILED_LOCAL_CALL74.AVM",
)

LARGE_BENCHES = [
    LargeBench(
        name="bigcall_nodata_30k",
        description="no-data local call chain scaled to about 30 KB of final code",
        calls=10000,
    ),
    LargeBench(
        name="bigcall_nodata_40k",
        description="no-data local call chain scaled to about 40 KB of final code",
        calls=13328,
    ),
]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def ensure_prg(stem: str) -> Path:
    bin_path = BUILD / f"{stem}.bin"
    prg_path = BUILD / f"{stem}.prg"
    if not prg_path.exists() and bin_path.exists():
        prg_path.write_bytes(LOAD_ADDR + bin_path.read_bytes())
    return prg_path


def harness_native_steps(prg_path: Path) -> int:
    summary = json.loads(
        run(
            [
                str(HARNESS),
                "--prg",
                str(prg_path),
                "--workspace",
                str(BASE_FS),
                "--services-inc",
                str(SERVICES_INC),
                "--entry-addr",
                "0x1000",
                "--max-steps",
                "50000000",
            ]
        ).stdout
    )
    if summary["exit_status"] != 0:
        raise RuntimeError(f"native harness failed for {prg_path.name}: {summary['console']!r}")
    return summary["steps"]


def harness_tool(prg: Path, workspace: Path, cmdline: str, labels: Path) -> dict:
    summary = json.loads(
        run(
            [
                str(HARNESS),
                "--prg",
                str(prg),
                "--workspace",
                str(workspace),
                "--cmdline",
                cmdline,
                "--services-inc",
                str(SERVICES_INC),
                "--labels",
                str(labels),
                "--max-steps",
                "4000000",
            ]
        ).stdout
    )
    return summary


def harness_tool_allow_failure(
    prg: Path,
    workspace: Path,
    cmdline: str,
    labels: Path,
    max_steps: str,
) -> dict:
    result = subprocess.run(
        [
            str(HARNESS),
            "--prg",
            str(prg),
            "--workspace",
            str(workspace),
            "--cmdline",
            cmdline,
            "--services-inc",
            str(SERVICES_INC),
            "--labels",
            str(labels),
            "--max-steps",
            max_steps,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return json.loads(result.stdout)


def action_text(path: Path) -> str:
    text = path.read_text(encoding="ascii")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    return text.replace("\n", "\r") + "\r"


def build_native_bench(bench: FairBench) -> tuple[int, int, int]:
    obj_path = BUILD / f"{bench.native_stem}.o"
    bin_path = BUILD / f"{bench.native_stem}.bin"
    prg_path = BUILD / f"{bench.native_stem}.prg"
    run(["ca65", "-o", str(obj_path), str(bench.native_source)])
    run(["ld65", "-C", str(CFG), "-o", str(bin_path), str(obj_path)])
    prg_path.write_bytes(LOAD_ADDR + bin_path.read_bytes())
    return bin_path.stat().st_size, prg_path.stat().st_size, harness_native_steps(prg_path)


def build_large_native_bench(bench: LargeBench) -> tuple[int, int, int]:
    obj_path = BUILD / f"{bench.name}.o"
    bin_path = BUILD / f"{bench.name}.bin"
    prg_path = BUILD / f"{bench.name}.prg"
    asm_path = BUILD / f"{bench.name}.asm"
    asm_path.write_text(
        '.setcpu "6502"\n\n'
        '.segment "CODE"\n'
        "start:\n"
        + ("    jsr t\n" * bench.calls)
        + "    rts\n\n"
        "t:\n"
        "    rts\n",
        encoding="ascii",
    )
    run(["ca65", "-o", str(obj_path), str(asm_path)])
    run(["ld65", "-C", str(LARGE_CFG), "-o", str(bin_path), str(obj_path)])
    prg_path.write_bytes(LOAD_ADDR + bin_path.read_bytes())
    return bin_path.stat().st_size, prg_path.stat().st_size, harness_native_steps(prg_path)


def prepare_workspace(bench: FairBench) -> Path:
    out_fs = BUILD / f"{bench.name}_fs"
    project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
    shutil.rmtree(out_fs, ignore_errors=True)
    shutil.copytree(BASE_FS, out_fs)
    (project_root / "src").mkdir(exist_ok=True)
    (project_root / "obj").mkdir(exist_ok=True)
    (project_root / "bin").mkdir(exist_ok=True)
    (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
    (project_root / "src" / "main.act").write_text(action_text(bench.action_source), encoding="ascii")
    stale_paths = [
        project_root / "obj" / "MAIN.AVO",
        project_root / "obj" / "main.avo",
        project_root / "bin" / "MAIN.AVM",
        project_root / "bin" / "main.avm",
        project_root / "bin" / "MAIN.DBG",
        project_root / "bin" / "main.dbg",
        project_root / "MAIN.AVM",
        project_root / "main.avm",
        project_root / "MAIN.DBG",
        project_root / "main.dbg",
    ]
    for stale in stale_paths:
        if stale.exists():
            stale.unlink()
    return project_root


def find_last_op(summary: dict, kind: str) -> dict:
    matches = [op for op in summary.get("ops", []) if op.get("kind") == kind]
    if not matches:
        raise RuntimeError(f"missing {kind!r} op in harness summary")
    return matches[-1]


def build_compiled_avm_bench(bench: FairBench) -> tuple[int, int, int]:
    project_root = prepare_workspace(bench)
    actc = harness_tool(ACTC_PRG, project_root, "MAIN", ACTC_LABELS)
    if actc["exit_status"] != 0:
        raise RuntimeError(f"ACTC failed for {bench.name}: {actc['console']!r}")
    actc_save = find_last_op(actc, "save")
    if actc_save["path"] != "OBJ/MAIN.AVO":
        raise RuntimeError(f"unexpected ACTC save path for {bench.name}: {actc_save['path']!r}")

    alink = harness_tool(ALINK_PRG, project_root, "MAIN", ALINK_LABELS)
    if alink["exit_status"] != 0:
        raise RuntimeError(f"ALINK failed for {bench.name}: {alink['console']!r}")

    avmrun = harness_tool(AVMRUNC_PRG, project_root, "BIN/MAIN.AVM", AVMRUNC_LABELS)
    if avmrun["exit_status"] != 0:
        raise RuntimeError(f"AVMRUNC failed for {bench.name}: {avmrun['console']!r}")
    if avmrun.get("console", "") != "":
        raise RuntimeError(f"unexpected AVMRUNC console for {bench.name}: {avmrun['console']!r}")

    avo_path = project_root / "obj" / "main.avo"
    avm_path = project_root / "bin" / "MAIN.AVM"
    out_avo = BUILD / bench.built_avo_name
    out_avm = BUILD / bench.built_avm_name
    shutil.copy2(avo_path, out_avo)
    shutil.copy2(avm_path, out_avm)
    return avo_path.stat().st_size, avm_path.stat().st_size, avmrun["steps"]


def build_large_direct_avm_bench(bench: LargeBench) -> tuple[int, int, int, str]:
    avm_path = BUILD / f"{bench.name}.AVM"
    payload = bytes([72]) + (bytes([69, 0, 0]) * bench.calls) + bytes([73, 32, 255])
    header = bytearray(b"AVM1")
    header.append(1)
    header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
    header.extend((1, 0))
    header.append(1)
    avm_path.write_bytes(bytes(header) + payload)
    summary = harness_tool_allow_failure(
        AVMRUNC_PRG,
        BUILD,
        avm_path.name,
        AVMRUNC_LABELS,
        "50000000",
    )
    return avm_path.stat().st_size, summary["steps"], summary["exit_status"], summary.get("console", "")


def emit_raw_table() -> None:
    runner_size = RUNNER.stat().st_size
    print(f"runner_prg_bytes\t{runner_size}")
    print(
        "raw_name\tdescription\tshared_runtime_leverage\t"
        "native_raw\tnative_prg\tavm_payload\tavm_packed\t"
        "delta_payload_vs_prg\tdelta_packed_vs_prg\tbreak_even_packed"
    )
    for bench in RAW_BENCHES:
        raw = (BUILD / f"{bench.stem}.bin").stat().st_size
        prg = ensure_prg(bench.stem).stat().st_size
        packed = (BUILD / bench.avm_name).stat().st_size
        delta_payload = bench.avm_payload - prg
        delta_packed = packed - prg
        breakeven = math.ceil(runner_size / (prg - packed)) if prg > packed else "-"
        print(
            f"{bench.stem}\t{bench.description}\t{bench.shared_runtime_leverage}\t"
            f"{raw}\t{prg}\t{bench.avm_payload}\t{packed}\t"
            f"{delta_payload}\t{delta_packed}\t{breakeven}"
        )


def emit_fair_table() -> None:
    native_raw, native_prg, native_steps = build_native_bench(FAIR_BENCH)
    compiled_avo, linked_avm, avm_steps = build_compiled_avm_bench(FAIR_BENCH)
    step_ratio = avm_steps / native_steps
    print(
        "fair_name\tdescription\tshared_runtime_leverage\t"
        "native_raw\tnative_prg\tcompiled_avo\tlinked_avm\t"
        "delta_avo_vs_prg\tdelta_avm_vs_prg\t"
        "native_steps\tavm_steps\tavm_step_ratio"
    )
    print(
        f"{FAIR_BENCH.name}\t{FAIR_BENCH.description}\tnone\t"
        f"{native_raw}\t{native_prg}\t{compiled_avo}\t{linked_avm}\t"
        f"{compiled_avo - native_prg}\t{linked_avm - native_prg}\t"
        f"{native_steps}\t{avm_steps}\t{step_ratio:.2f}"
    )


def emit_large_table() -> None:
    print(
        "large_name\tdescription\tshared_runtime_leverage\t"
        "native_raw\tnative_prg\tdirect_avm\t"
        "delta_avm_vs_prg\t"
        "native_steps\tavm_steps_to_harness_boundary\tavm_exit\tavm_console"
    )
    for bench in LARGE_BENCHES:
        native_raw, native_prg, native_steps = build_large_native_bench(bench)
        direct_avm, avm_steps, avm_exit, avm_console = build_large_direct_avm_bench(bench)
        print(
            f"{bench.name}\t{bench.description}\tnone\t"
            f"{native_raw}\t{native_prg}\t{direct_avm}\t"
            f"{direct_avm - native_prg}\t"
            f"{native_steps}\t{avm_steps}\t{avm_exit}\t{avm_console.strip()}"
        )


def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    emit_raw_table()
    print()
    emit_fair_table()
    print()
    emit_large_table()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
