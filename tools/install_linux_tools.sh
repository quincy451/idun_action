#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -d "$SCRIPT_DIR/TOOLS" ]]; then
  ROOT_DIR="$SCRIPT_DIR"
else
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
TOOLS_DIR=""
BIN_DIR="${HOME:?HOME is not set}/.local/bin"

TOOL_NAMES=(
  actnew actadd actwork actsrc actfile actchk actdir actcopy actdel
  actmkdir actrmdir actmove actren actwrite actinfo actmon actdbg actprof
  acttree tree xcopy deltree actspc actsprite actbitmap actedit acthelp act2save actsave actc alink
)

usage() {
  printf '%s\n' \
    "Usage: bash tools/install_linux_tools.sh [--tools DIR] [--bin-dir DIR]" \
    "" \
    "Install user-level symlinks for the native Linux commands." \
    "The defaults are build/idun-action/TOOLS and \$HOME/.local/bin."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tools)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      TOOLS_DIR=$2
      shift 2
      ;;
    --bin-dir)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      BIN_DIR=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$TOOLS_DIR" ]]; then
  if [[ -d "$ROOT_DIR/TOOLS" ]]; then
    TOOLS_DIR="$ROOT_DIR/TOOLS"
  elif [[ -d "$ROOT_DIR/build/idun-action/TOOLS" ]]; then
    TOOLS_DIR="$ROOT_DIR/build/idun-action/TOOLS"
  else
    TOOLS_DIR="$ROOT_DIR/build/linux_tools"
  fi
fi

[[ -d "$TOOLS_DIR" ]] || {
  printf 'Linux tools directory not found: %s\n' "$TOOLS_DIR" >&2
  exit 1
}
TOOLS_DIR="$(cd "$TOOLS_DIR" && pwd -P)"
mkdir -p "$BIN_DIR"
BIN_DIR="$(cd "$BIN_DIR" && pwd -P)"
[[ "$TOOLS_DIR" != "$BIN_DIR" ]] || {
  printf 'Install directory must differ from the tools directory.\n' >&2
  exit 1
}

for name in "${TOOL_NAMES[@]}"; do
  [[ -x "$TOOLS_DIR/$name" ]] || {
    printf 'Missing Linux command: %s/%s\n' "$TOOLS_DIR" "$name" >&2
    exit 1
  }
done

for name in "${TOOL_NAMES[@]}"; do
  ln -sfn "$TOOLS_DIR/$name" "$BIN_DIR/$name"
done

printf 'Installed %d Action Linux commands in %s\n' "${#TOOL_NAMES[@]}" "$BIN_DIR"
case ":$PATH:" in
  *":$BIN_DIR:"*)
    printf 'PATH already contains %s\n' "$BIN_DIR"
    ;;
  *)
    printf 'Add this to your shell profile, then log in again:\n'
    printf '  export PATH="%s:$PATH"\n' "$BIN_DIR"
    ;;
esac
printf 'Run hash -r in an existing Bash session before using the new commands.\n'
