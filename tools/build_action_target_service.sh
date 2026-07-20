#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_DIR="$ROOT_DIR/src/target_idun"
SRC="$SRC_DIR/action_target_service.asm"
INCLUDE="$SRC_DIR/idun_ace_api.inc"
BUILD_DIR="${ACTION_TARGET_BUILD_DIR:-$ROOT_DIR/build/linux_tools}"
BIN="$BUILD_DIR/actsvc"
META_DIR="${ACTION_TARGET_META_DIR:-$ROOT_DIR/build/target_idun}"
LABELS="$META_DIR/actsvc.labels"
REPORT="$META_DIR/actsvc.report"

if ! command -v acme >/dev/null 2>&1; then
    echo "acme is required to build the Idun C64 target service" >&2
    exit 1
fi

mkdir -p "$BUILD_DIR" "$META_DIR"
if [[ "${ACTION_FORCE_REBUILD:-0}" == "1" || ! -f "$BIN" || "$SRC" -nt "$BIN" || "$INCLUDE" -nt "$BIN" || "${BASH_SOURCE[0]}" -nt "$BIN" ]]; then
    TMP_BIN="$BIN.tmp.$$"
    trap 'rm -f "$TMP_BIN"' EXIT
    acme \
        -f plain \
        -I "$SRC_DIR" \
        --strict-segments \
        --symbollist "$LABELS" \
        --report "$REPORT" \
        -o "$TMP_BIN" \
        "$SRC"
    chmod 0644 "$TMP_BIN"
    mv "$TMP_BIN" "$BIN"
    trap - EXIT
fi

echo "$BIN"
