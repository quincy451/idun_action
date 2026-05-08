#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def normalize(name: str) -> str:
    if name.startswith('.'):
        name = name[1:]
    name = re.sub(r'[^A-Za-z0-9_]', '_', name)
    if not name:
        raise ValueError('empty symbol name')
    if name[0].isdigit():
        name = '_' + name
    return name


def main() -> int:
    parser = argparse.ArgumentParser(description='Convert ld65 labels into ca65 equates')
    parser.add_argument('--labels', required=True, help='ld65 labels file')
    parser.add_argument('--output', required=True, help='output include file')
    parser.add_argument('--prefix', required=True, help='symbol prefix to add to every label')
    args = parser.parse_args()

    lines: list[str] = []
    seen: set[str] = set()
    labels_path = Path(args.labels)
    for raw in labels_path.read_text(encoding='ascii').splitlines():
        parts = raw.split()
        if len(parts) != 3 or parts[0] != 'al':
            continue
        addr_text = parts[1]
        name = parts[2]
        if not name.startswith('.'):
            continue
        addr = int(addr_text, 16)
        symbol = f"{args.prefix}{normalize(name)}"
        if symbol in seen:
            continue
        seen.add(symbol)
        lines.append(f"{symbol} = ${addr:04X}")

    output = Path(args.output)
    output.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='ascii')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
