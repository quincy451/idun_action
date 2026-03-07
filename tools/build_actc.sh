#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"
SRC="$ROOT_DIR/src/tools_cpm/actc/actc.c"
OUT_COM="$BUILD_DIR/actc.com"
LLVM_BIN="$($ROOT_DIR/tools/find_llvm_mos.sh)"

mkdir -p "$BUILD_DIR"
"$LLVM_BIN/mos-cpm65-clang" -Os -o "$OUT_COM" "$SRC"
echo "Built $OUT_COM"
