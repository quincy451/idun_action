#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPM_ROOT="$ROOT_DIR/../cpm65-u64"
SRC_DIR="$ROOT_DIR/src/tools_cpm/hello"
BUILD_DIR="$ROOT_DIR/build"
OUT_COM="$BUILD_DIR/hello.com"
NATIVE_SRC="$SRC_DIR/hello.asm"
HOST_FALLBACK_SRC="$SRC_DIR/hello.c"
RUNNER="$ROOT_DIR/tools/cpmemu_runner.py"

mkdir -p "$BUILD_DIR"

find_asm_com() {
  local candidate
  for candidate in \
    "$CPM_ROOT/bin/asm.com" \
    "$CPM_ROOT/.obj/asm.com" \
    "$CPM_ROOT/asm.com"
  do
    if [[ -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

find_mos_clang() {
  if [[ -x "$ROOT_DIR/tools/find_llvm_mos.sh" ]]; then
    local llvm_bin
    llvm_bin="$("$ROOT_DIR/tools/find_llvm_mos.sh" || true)"
    if [[ -n "$llvm_bin" && -x "$llvm_bin/mos-cpm65-clang" ]]; then
      printf '%s\n' "$llvm_bin/mos-cpm65-clang"
      return 0
    fi
  fi

  if [[ -n "${LLVM:-}" ]]; then
    local llvm_bin="${LLVM%/}"
    if [[ -x "$llvm_bin/mos-cpm65-clang" ]]; then
      printf '%s\n' "$llvm_bin/mos-cpm65-clang"
      return 0
    fi
  fi

  if [[ -x /opt/pkg/llvm-mos/bin/mos-cpm65-clang ]]; then
    printf '%s\n' /opt/pkg/llvm-mos/bin/mos-cpm65-clang
    return 0
  fi

  command -v mos-cpm65-clang 2>/dev/null || true
}

build_with_native_asm() {
  local asm_com="$1"
  echo "Using native CP/M-65 assembler path via cpmemu: $asm_com"
  rm -f "$OUT_COM"

  python3 "$RUNNER" \
    --cwd "$CPM_ROOT" \
    --drive "A=$SRC_DIR" \
    --drive "B=$BUILD_DIR" \
    "$asm_com" \
    a:hello.asm \
    b:hello.com

  if [[ ! -f "$OUT_COM" ]]; then
    echo "Native ASM path ran, but $OUT_COM was not produced." >&2
    return 1
  fi
}

build_with_host_toolchain() {
  local cc="$1"
  echo "Using host llvm-mos fallback: $cc"
  rm -f "$OUT_COM"
  "$cc" -Os -o "$OUT_COM" "$HOST_FALLBACK_SRC"
}

ASM_COM="$(find_asm_com || true)"
if [[ -n "$ASM_COM" && -x "$CPM_ROOT/bin/cpmemu" ]]; then
  if build_with_native_asm "$ASM_COM"; then
    echo "Built $OUT_COM via native ASM under cpmemu."
    exit 0
  fi
  echo "Native ASM path failed; falling back to host toolchain if available." >&2
else
  echo "Native ASM path unavailable: missing cpmemu and/or asm.com build artifacts." >&2
fi

MOS_CLANG="$(find_mos_clang || true)"
if [[ -n "$MOS_CLANG" ]]; then
  build_with_host_toolchain "$MOS_CLANG"
  echo "Built $OUT_COM via host llvm-mos toolchain."
  exit 0
fi

echo "No supported hello.com build path is available." >&2
echo "Needed one of:" >&2
echo "  1. ../cpm65-u64/bin/cpmemu plus a built asm.com (native CP/M-65 assembler path)" >&2
echo "  2. mos-cpm65-clang on PATH, or LLVM=<path-to-llvm-mos-bin>/ in the environment" >&2
echo "See docs/cpmemu.md and tools/build_cpm65_notes.sh for setup guidance." >&2
exit 2
