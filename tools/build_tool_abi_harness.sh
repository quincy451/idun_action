#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/udos_tools"
SRC="$ROOT_DIR/tools/tool_abi_harness.c"
LIB6502_DIR="${LIB6502_DIR:-}"
if [[ -z "$LIB6502_DIR" ]]; then
  for candidate in \
    "$ROOT_DIR/third_party/lib6502" \
    "$ROOT_DIR/../cpm65-u64/third_party/lib6502" \
    "$ROOT_DIR/../action/cpm65-u64/third_party/lib6502"; do
    if [[ -f "$candidate/lib6502.c" && -f "$candidate/lib6502.h" ]]; then
      LIB6502_DIR="$candidate"
      break
    fi
  done
fi
if [[ -z "$LIB6502_DIR" ]]; then
  echo "lib6502 source not found; set LIB6502_DIR" >&2
  exit 1
fi
OUT="$BUILD_DIR/tool_abi_harness"
HARNESS_OBJ="$BUILD_DIR/tool_abi_harness.o"
LIB6502_OBJ="$BUILD_DIR/lib6502.o"

mkdir -p "$BUILD_DIR"

cc -std=c99 -O2 -Wall -Wextra \
  -I"$LIB6502_DIR" \
  -c "$SRC" \
  -o "$HARNESS_OBJ"

cc -std=c99 -O2 -Wall -Wextra -Wno-unused-function \
  -I"$LIB6502_DIR" \
  -c "$LIB6502_DIR/lib6502.c" \
  -o "$LIB6502_OBJ"

cc "$HARNESS_OBJ" "$LIB6502_OBJ" -o "$OUT"

printf '%s\n' "$OUT"
