#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/udos_tools"
SRC="$ROOT_DIR/tools/tool_abi_harness.c"
LIB6502_DIR="$ROOT_DIR/../cpm65-u64/third_party/lib6502"
OUT="$BUILD_DIR/tool_abi_harness"

mkdir -p "$BUILD_DIR"

cc -std=c99 -O2 -Wall -Wextra \
  -I"$LIB6502_DIR" \
  "$SRC" "$LIB6502_DIR/lib6502.c" \
  -o "$OUT"

printf '%s\n' "$OUT"
