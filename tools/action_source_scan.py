#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import re


CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")


@dataclass(frozen=True)
class ProcSummary:
    name: str
    calls: tuple[str, ...]


@dataclass(frozen=True)
class SourceSummary:
    module_name: str | None
    procs: tuple[ProcSummary, ...]


def preprocess(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def scan_source(text: str) -> SourceSummary:
    lines = preprocess(text)
    module_name: str | None = None
    proc_order: list[str] = []
    proc_body_lines: dict[str, list[str]] = {}

    current_proc: str | None = None
    for line in lines:
        upper = line.upper()
        if current_proc is None and upper.startswith("MODULE "):
            module_name = line.split(None, 1)[1].strip()
            continue
        if upper.startswith("PROC ") and line.endswith(")"):
            proc_name = _parse_proc_name(line)
            proc_order.append(proc_name)
            proc_body_lines[proc_name] = []
            current_proc = proc_name
            continue
        if upper == "ENDPROC":
            current_proc = None
            continue
        if current_proc is not None:
            proc_body_lines[current_proc].append(line)

    proc_names_upper = {name.upper() for name in proc_order}
    summaries: list[ProcSummary] = []
    for proc_name in proc_order:
        seen_calls: set[str] = set()
        ordered_calls: list[str] = []
        for line in proc_body_lines[proc_name]:
            for match in CALL_RE.finditer(line):
                callee = match.group(1)
                callee_upper = callee.upper()
                if callee_upper not in proc_names_upper:
                    continue
                if callee_upper == proc_name.upper():
                    continue
                if callee_upper in seen_calls:
                    continue
                seen_calls.add(callee_upper)
                ordered_calls.append(callee.lower())
        summaries.append(ProcSummary(proc_name.lower(), tuple(ordered_calls)))

    return SourceSummary(module_name=module_name, procs=tuple(summaries))


def _parse_proc_name(line: str) -> str:
    rest = line.split(None, 1)[1].strip()
    name = rest.split("(", 1)[0].strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid PROC declaration: {line!r}")
    return name

