#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/udos_tools"
SRC_DIR="$ROOT_DIR/src/tools_udos/avmrun"
SRC="$SRC_DIR/avmrun_native_helper_gfx.asm"
CFG="$SRC_DIR/avmrun_native_helper_gfx.cfg"
OBJ="$BUILD_DIR/avmrun_native_helper_gfx.o"
BIN="$BUILD_DIR/RT_GFX1_HELPER.BIN"
LABELS="$BUILD_DIR/avmrun_native_helper_gfx.labels"
MAP="$BUILD_DIR/avmrun_native_helper_gfx.map"

mkdir -p "$BUILD_DIR"

ca65 -g -o "$OBJ" "$SRC" -I "$SRC_DIR"
ld65 -C "$CFG" -o "$BIN" "$OBJ" -Ln "$LABELS" -m "$MAP"
printf '%s\n' "$BIN"
