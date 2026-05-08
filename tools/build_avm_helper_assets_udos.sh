#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/udos_tools"
LABELS="$BUILD_DIR/avmrunc.current.labels"

"$ROOT_DIR/tools/build_avmrunc_udos.sh" >/dev/null

mkdir -p "$BUILD_DIR"
export AVMRUN_LABELS="$LABELS"

"$ROOT_DIR/tools/build_avmrun_native_helper_printstd.sh" >/dev/null
"$ROOT_DIR/tools/build_avmrun_native_helper_printreal.sh" >/dev/null
"$ROOT_DIR/tools/build_avmrun_native_helper_gfx.sh" >/dev/null
"$ROOT_DIR/tools/build_avmrun_native_helper_sidspr.sh" >/dev/null
"$ROOT_DIR/tools/build_avmrun_native_helper_dbf.sh" >/dev/null
"$ROOT_DIR/tools/build_avmrun_native_helper_math.sh" >/dev/null
"$ROOT_DIR/tools/build_avmrun_overlay_printreal.sh" >/dev/null
"$ROOT_DIR/tools/build_avmrun_overlay_realops.sh" >/dev/null
"$ROOT_DIR/tools/build_avmrun_overlay_interp.sh" >/dev/null

printf '%s\n' "$BUILD_DIR"
