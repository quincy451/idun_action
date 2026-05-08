#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/udos_tools"
SRC_DIR="$ROOT_DIR/src/tools_udos/avmrun"
SRC="$SRC_DIR/avmrun_native_helper_printreal.asm"
CFG="$SRC_DIR/avmrun_native_helper.cfg"
OBJ="$BUILD_DIR/avmrun_native_helper_printreal.o"
BIN="$BUILD_DIR/RT_PRINT_F_HELPER.BIN"
LABELS="$BUILD_DIR/avmrun_native_helper_printreal.labels"
MAP="$BUILD_DIR/avmrun_native_helper_printreal.map"
RESIDENT_LABELS="${AVMRUN_LABELS:-$BUILD_DIR/avmrun.current.labels}"
RESIDENT_INC="$BUILD_DIR/avmrun_overlay_resident.inc"

mkdir -p "$BUILD_DIR"

python3 "$ROOT_DIR/tools/generate_ca65_label_inc.py" \
  --labels "$RESIDENT_LABELS" \
  --output "$RESIDENT_INC" \
  --prefix AVMRUN_RES_

ca65 -g -o "$OBJ" "$SRC" -I "$SRC_DIR" -I "$BUILD_DIR"
ld65 -C "$CFG" -o "$BIN" "$OBJ" -Ln "$LABELS" -m "$MAP"
printf '%s\n' "$BIN"
