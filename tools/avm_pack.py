#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import struct
import sys
import tempfile

MAGIC = b"AVM1"
VERSION_V1 = 1
VERSION_V2 = 2
HEADER_V1 = struct.Struct("<4sBHHB")
HEADER_V2 = struct.Struct("<4sBHHBH")
AVM_FLAG_ACHERON = 0x01

OPCODE_PUSH8 = 0x10
OPCODE_PUSH16 = 0x11
OPCODE_STORE = 0x12
OPCODE_LOAD = 0x13
OPCODE_ADD = 0x14
OPCODE_SUB = 0x15
OPCODE_EQ = 0x16
OPCODE_NE = 0x17
OPCODE_JZ = 0x18
OPCODE_JMP = 0x19
OPCODE_DUP = 0x1A
OPCODE_DROP = 0x1B
OPCODE_LT = 0x1C
OPCODE_GT = 0x1D
OPCODE_BAND = 0x1E
OPCODE_BOR = 0x1F
OPCODE_BXOR = 0x20
OPCODE_SHL1 = 0x21
OPCODE_SHR1 = 0x22
OPCODE_NATIVE = 0x2D
OPCODE_CALL = 0x45
OPCODE_JUMP = 0x46
OPCODE_RET = 0x48
OPCODE_CALLN = 0x49
OPCODE_CLRP = 0x5C
OPCODE_SETP8 = 0x5D
OPCODE_SETP16 = 0x61

INTRINSICS = {
    "print": 0xFF00,
    "printe": 0xFF10,
    "exit": 0xFF20,
    "printi": 0xFF30,
    "printie": 0xFF31,
    "reu_alloc": 0xFF40,
    "reu_free": 0xFF41,
    "reu_peek8": 0xFF42,
    "reu_poke8": 0xFF43,
    "reu_peek16": 0xFF44,
    "reu_poke16": 0xFF45,
    "conin": 0xFF50,
    "conout": 0xFF51,
    "fopenr": 0xFF60,
    "fcloser": 0xFF61,
    "fread8": 0xFF62,
    "fopenw": 0xFF63,
    "fclosew": 0xFF64,
    "fwrite8": 0xFF65,
    "fdelete": 0xFF66,
}

ZERO_ARG_OPS = {
    "native": OPCODE_NATIVE,
    "clrp": OPCODE_CLRP,
    "ret": OPCODE_RET,
    "add": OPCODE_ADD,
    "sub": OPCODE_SUB,
    "eq": OPCODE_EQ,
    "ne": OPCODE_NE,
    "dup": OPCODE_DUP,
    "drop": OPCODE_DROP,
    "lt": OPCODE_LT,
    "gt": OPCODE_GT,
    "band": OPCODE_BAND,
    "bor": OPCODE_BOR,
    "bxor": OPCODE_BXOR,
    "shl1": OPCODE_SHL1,
    "shr1": OPCODE_SHR1,
}

BYTE_OPS = {
    "push8": OPCODE_PUSH8,
    "store": OPCODE_STORE,
    "load": OPCODE_LOAD,
    "setp8": OPCODE_SETP8,
}

WORD_OPS = {
    "push16": OPCODE_PUSH16,
    "call": OPCODE_CALL,
    "jump": OPCODE_JUMP,
    "setp16": OPCODE_SETP16,
    "calln": OPCODE_CALLN,
    "jz": OPCODE_JZ,
    "jmp": OPCODE_JMP,
}


@dataclass(frozen=True)
class AvmFile:
    version: int
    payload: bytes
    entry_offset: int
    flags: int = 0
    code_len: int | None = None


@dataclass(frozen=True)
class Fixup:
    offset: int
    size: int
    symbol: str
    lineno: int


@dataclass
class AssemblyState:
    payload: bytearray
    labels: dict[str, int]
    fixups: list[Fixup]
    entry_symbol: str | None
    entry_offset: int | None
    code_len: int | None


def parse_number(token: str) -> int:
    token = token.strip()
    if token.startswith("$"):
        return int(token[1:], 16)
    return int(token, 0)


def strip_comments(raw_line: str) -> str:
    in_string = False
    quote = ""
    escaped = False
    out: list[str] = []

    for ch in raw_line:
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if in_string:
            out.append(ch)
            if ch == "\\":
                escaped = True
            elif ch == quote:
                in_string = False
            continue
        if ch in {"'", '"'}:
            in_string = True
            quote = ch
            out.append(ch)
            continue
        if ch in {"#", ";"}:
            break
        out.append(ch)

    return "".join(out).strip()


def split_operands(text: str) -> list[str]:
    operands: list[str] = []
    current: list[str] = []
    in_string = False
    quote = ""
    escaped = False

    for ch in text:
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if in_string:
            current.append(ch)
            if ch == "\\":
                escaped = True
            elif ch == quote:
                in_string = False
            continue
        if ch in {"'", '"'}:
            in_string = True
            quote = ch
            current.append(ch)
            continue
        if ch == ",":
            operand = "".join(current).strip()
            if operand:
                operands.append(operand)
            current = []
            continue
        current.append(ch)

    operand = "".join(current).strip()
    if operand:
        operands.append(operand)
    return operands


def parse_operands(text: str) -> tuple[str, list[str]]:
    if not text:
        return "", []
    parts = text.split(None, 1)
    op = parts[0].lower()
    operands = split_operands(parts[1]) if len(parts) > 1 else []
    return op, operands


def parse_string_literal(token: str, *, lineno: int) -> bytes:
    token = token.strip()
    if token and token[0] not in {'"', "'"}:
        try:
            return token.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(f"line {lineno}: strings must be ASCII") from exc
    try:
        value = ast.literal_eval(token)
    except (SyntaxError, ValueError) as exc:
        raise ValueError(f"line {lineno}: invalid string literal: {token}") from exc
    if not isinstance(value, str):
        raise ValueError(f"line {lineno}: expected string literal, got {token}")
    try:
        return value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"line {lineno}: strings must be ASCII") from exc


def parse_value(token: str) -> int | str:
    try:
        return parse_number(token)
    except ValueError:
        lowered = token.strip().lower()
        if lowered in INTRINSICS:
            return INTRINSICS[lowered]
        return token.strip()


def define_label(state: AssemblyState, label: str, *, lineno: int) -> None:
    if not label or any(ch.isspace() for ch in label):
        raise ValueError(f"line {lineno}: invalid label: {label!r}")
    if label in state.labels:
        raise ValueError(f"line {lineno}: duplicate label: {label}")
    state.labels[label] = len(state.payload)


def append_u8(state: AssemblyState, value: int, *, lineno: int) -> None:
    if not 0 <= value <= 0xFF:
        raise ValueError(f"line {lineno}: byte out of range: {value}")
    state.payload.append(value)


def append_u16_or_fixup(state: AssemblyState, value: int | str, *, lineno: int) -> None:
    if isinstance(value, int):
        if not 0 <= value <= 0xFFFF:
            raise ValueError(f"line {lineno}: word out of range: {value}")
        state.payload.extend((value & 0xFF, (value >> 8) & 0xFF))
        return

    state.fixups.append(Fixup(offset=len(state.payload), size=2, symbol=value, lineno=lineno))
    state.payload.extend((0, 0))


def encode_text(source: str) -> tuple[bytes, int, int | None]:
    state = AssemblyState(
        payload=bytearray(),
        labels={},
        fixups=[],
        entry_symbol=None,
        entry_offset=None,
        code_len=None,
    )

    for lineno, raw_line in enumerate(source.splitlines(), start=1):
        line = strip_comments(raw_line)
        if not line:
            continue

        while True:
            colon = line.find(":")
            if colon <= 0:
                break
            candidate = line[:colon].strip()
            if not candidate or any(ch.isspace() for ch in candidate):
                break
            define_label(state, candidate, lineno=lineno)
            line = line[colon + 1 :].strip()
            if not line:
                break
        if not line:
            continue

        op, operands = parse_operands(line)
        if not op:
            continue

        if op == "entry":
            if len(operands) != 1:
                raise ValueError(f"line {lineno}: entry requires one label or offset")
            value = parse_value(operands[0])
            if isinstance(value, int):
                state.entry_offset = value
            else:
                state.entry_symbol = value
            continue

        if op == "code":
            if len(operands) != 1:
                raise ValueError(f"line {lineno}: code requires one size operand")
            value = parse_value(operands[0])
            if not isinstance(value, int):
                raise ValueError(f"line {lineno}: code requires a numeric operand")
            if not 0 <= value <= 0xFFFF:
                raise ValueError(f"line {lineno}: code size out of range")
            state.code_len = value
            continue

        if op in {"byte", "db"}:
            if not operands:
                raise ValueError(f"line {lineno}: {op} requires at least one byte")
            for token in operands:
                value = parse_value(token)
                if not isinstance(value, int):
                    raise ValueError(f"line {lineno}: {op} requires numeric operands")
                append_u8(state, value, lineno=lineno)
            continue

        if op in {"hex", "byteshex"}:
            if len(operands) != 1:
                raise ValueError(f"line {lineno}: {op} requires exactly one hex blob")
            blob = operands[0].strip()
            if len(blob) % 2 != 0:
                raise ValueError(f"line {lineno}: {op} requires an even number of hex digits")
            try:
                payload = bytes.fromhex(blob)
            except ValueError as exc:
                raise ValueError(f"line {lineno}: invalid hex blob") from exc
            state.payload.extend(payload)
            continue

        if op in {"stringz", "asciz"}:
            if len(operands) != 1:
                raise ValueError(f"line {lineno}: {op} requires exactly one string literal")
            state.payload.extend(parse_string_literal(operands[0], lineno=lineno))
            state.payload.append(0)
            continue

        if op in ZERO_ARG_OPS:
            if operands:
                raise ValueError(f"line {lineno}: {op} takes no operands")
            state.payload.append(ZERO_ARG_OPS[op])
            continue

        if op in BYTE_OPS:
            if len(operands) != 1:
                raise ValueError(f"line {lineno}: {op} requires one byte operand")
            value = parse_value(operands[0])
            if not isinstance(value, int):
                raise ValueError(f"line {lineno}: {op} requires a numeric operand")
            state.payload.append(BYTE_OPS[op])
            append_u8(state, value, lineno=lineno)
            continue

        if op in WORD_OPS:
            if len(operands) != 1:
                raise ValueError(f"line {lineno}: {op} requires one word operand")
            state.payload.append(WORD_OPS[op])
            append_u16_or_fixup(state, parse_value(operands[0]), lineno=lineno)
            continue

        raise ValueError(f"line {lineno}: unsupported opcode/directive: {op}")

    for fixup in state.fixups:
        if fixup.symbol not in state.labels:
            raise ValueError(f"line {fixup.lineno}: unknown symbol: {fixup.symbol}")
        value = state.labels[fixup.symbol]
        state.payload[fixup.offset] = value & 0xFF
        state.payload[fixup.offset + 1] = (value >> 8) & 0xFF

    if state.entry_symbol is not None:
        if state.entry_symbol not in state.labels:
            raise ValueError(f"unknown entry symbol: {state.entry_symbol}")
        entry_offset = state.labels[state.entry_symbol]
    elif state.entry_offset is not None:
        entry_offset = state.entry_offset
    else:
        entry_offset = 0

    if not 0 <= entry_offset <= len(state.payload):
        raise ValueError("entry offset must point inside the payload")

    if state.code_len is not None and state.code_len > len(state.payload):
        raise ValueError("code size must not exceed payload length")

    return bytes(state.payload), entry_offset, state.code_len


def pack_avm(
    payload: bytes,
    *,
    entry_offset: int,
    flags: int = 0,
    version: int | None = None,
    code_len: int | None = None,
) -> bytes:
    if version is None:
        version = VERSION_V2 if code_len is not None else VERSION_V1
    if not 0 <= version <= 0xFF:
        raise ValueError("version must fit in one byte")
    if not 0 <= flags <= 0xFF:
        raise ValueError("flags must fit in one byte")
    if len(payload) > 0xFFFF:
        raise ValueError("payload too large for AVM header")
    if not 0 <= entry_offset <= len(payload):
        raise ValueError("entry offset must point inside the payload")
    if version == VERSION_V1:
        if code_len is not None and code_len != len(payload):
            raise ValueError("version 1 cannot encode a code length shorter than the payload")
        return HEADER_V1.pack(MAGIC, version, len(payload), entry_offset, flags) + payload
    if version == VERSION_V2:
        if code_len is None:
            code_len = len(payload)
        if not 0 <= code_len <= len(payload):
            raise ValueError("code length must point inside the payload")
        return HEADER_V2.pack(MAGIC, version, len(payload), entry_offset, flags, code_len) + payload
    raise ValueError(f"unsupported AVM version: {version}")


def unpack_avm(data: bytes) -> AvmFile:
    if len(data) < HEADER_V1.size:
        raise ValueError("file too short for AVM header")
    magic = data[:4]
    version = data[4]
    if magic != MAGIC:
        raise ValueError(f"bad magic: {magic!r}")
    if version == VERSION_V1:
        magic, version, payload_len, entry_offset, flags = HEADER_V1.unpack_from(data)
        code_len = payload_len
        header_size = HEADER_V1.size
    elif version == VERSION_V2:
        if len(data) < HEADER_V2.size:
            raise ValueError("file too short for AVM v2 header")
        magic, version, payload_len, entry_offset, flags, code_len = HEADER_V2.unpack_from(data)
        if code_len > payload_len:
            raise ValueError("code length beyond payload length")
        header_size = HEADER_V2.size
    else:
        raise ValueError(f"unsupported version: {version}")
    payload = data[header_size : header_size + payload_len]
    if len(payload) != payload_len:
        raise ValueError("truncated payload")
    if entry_offset > payload_len:
        raise ValueError("entry offset beyond payload length")
    return AvmFile(version=version, payload=payload, entry_offset=entry_offset, flags=flags, code_len=code_len)


def run_selftest() -> int:
    payload, entry_offset, code_len = encode_text(
        """
        entry start
        code $0d
        start:
          setp16 msg
          calln print
          push16 42
          calln printie
          calln exit
        msg:
          stringz "OK"
        """
    )
    packed = pack_avm(payload, entry_offset=entry_offset, code_len=code_len)
    unpacked = unpack_avm(packed)
    if (
        unpacked.payload != payload
        or unpacked.entry_offset != entry_offset
        or unpacked.code_len != code_len
    ):
        print("selftest failed: roundtrip mismatch", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "selftest.avm"
        out_path.write_bytes(packed)
        reread = unpack_avm(out_path.read_bytes())
        if reread.payload != payload or reread.entry_offset != entry_offset or reread.code_len != code_len:
            print("selftest failed: disk roundtrip mismatch", file=sys.stderr)
            return 1

    print("avm_pack selftest OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pack raw bytes or AVM assembly text into ActionC64U .avm files")
    parser.add_argument("input", nargs="?", help="input payload file")
    parser.add_argument("-o", "--output", help="output .avm file")
    parser.add_argument("--entry-offset", type=parse_number, default=None, help="entry offset within the payload")
    parser.add_argument("--flags", type=parse_number, default=0, help="header flags byte to store in the packed AVM")
    parser.add_argument("--text", action="store_true", help="treat input as AVM assembly-like text")
    parser.add_argument("--selftest", action="store_true", help="run pack/unpack self-test and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if not args.input or not args.output:
        parser.error("input and --output are required unless --selftest is used")

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.is_file():
        parser.error(f"input file not found: {input_path}")

    if args.text:
        payload, inferred_entry, inferred_code = encode_text(input_path.read_text())
        entry_offset = args.entry_offset if args.entry_offset is not None else inferred_entry
        code_len = inferred_code
    else:
        payload = input_path.read_bytes()
        entry_offset = args.entry_offset if args.entry_offset is not None else 0
        code_len = None

    packed = pack_avm(payload, entry_offset=entry_offset, flags=args.flags, code_len=code_len)
    output_path.write_bytes(packed)
    print(f"wrote {output_path} ({len(payload)} payload bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
