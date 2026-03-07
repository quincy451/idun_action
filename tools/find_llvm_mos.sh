#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${LLVM:-}" ]]; then
  llvm_bin="${LLVM%/}"
  if [[ -x "$llvm_bin/mos-cpm65-clang" ]]; then
    printf '%s\n' "$llvm_bin"
    exit 0
  fi
fi

for llvm_bin in \
  "$ROOT_DIR/../.local/llvm-mos/bin" \
  /opt/pkg/llvm-mos/bin
 do
  if [[ -x "$llvm_bin/mos-cpm65-clang" ]]; then
    printf '%s\n' "$llvm_bin"
    exit 0
  fi
done

if command -v mos-cpm65-clang >/dev/null 2>&1; then
  dirname "$(command -v mos-cpm65-clang)"
  exit 0
fi

exit 1
