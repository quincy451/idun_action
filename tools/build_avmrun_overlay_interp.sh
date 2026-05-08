#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/udos_tools"
SRC_DIR="$ROOT_DIR/src/tools_udos/avmrun"
SRC="$SRC_DIR/avmrun_overlay_interp.asm"
CFG="$SRC_DIR/avmrun_overlay.cfg"
OBJ="$BUILD_DIR/avmrun_overlay_interp.o"
BIN="$BUILD_DIR/AVMRUN_OVL3.BIN"
LABELS="$BUILD_DIR/avmrun_overlay_interp.labels"
MAP="$BUILD_DIR/avmrun_overlay_interp.map"
DEFAULT_RESIDENT_LABELS="$BUILD_DIR/avmrunc.current.labels"
if [[ ! -f "$DEFAULT_RESIDENT_LABELS" ]]; then
  DEFAULT_RESIDENT_LABELS="$BUILD_DIR/avmrun.current.labels"
fi
RESIDENT_LABELS="${AVMRUN_LABELS:-$DEFAULT_RESIDENT_LABELS}"
RESIDENT_INC="$BUILD_DIR/avmrun_overlay_resident.inc"

mkdir -p "$BUILD_DIR"

python3 "$ROOT_DIR/tools/generate_ca65_label_inc.py" \
  --labels "$RESIDENT_LABELS" \
  --output "$RESIDENT_INC" \
  --prefix AVMRUN_RES_

ca65 -g -o "$OBJ" "$SRC" -I "$SRC_DIR" -I "$BUILD_DIR"
ld65 -C "$CFG" -o "$BIN" "$OBJ" -Ln "$LABELS" -m "$MAP"
printf '%s\n' "$BIN"
