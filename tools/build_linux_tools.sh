#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/linux_tools"
SRC="$ROOT_DIR/src/tools_linux/action_workspace_tools.cpp"
FORMATTER_SRC="$ROOT_DIR/src/tools_linux/action_formatter.cpp"
FORMATTER_HEADER="$ROOT_DIR/src/tools_linux/action_formatter.hpp"
GRAPHICS_SRC="$ROOT_DIR/src/tools_linux/action_graphics_editor.cpp"
GRAPHICS_HEADER="$ROOT_DIR/src/tools_linux/action_graphics_editor.hpp"
HELP_SRC="$ROOT_DIR/src/tools_linux/action_help_editor.cpp"
HELP_HEADER="$ROOT_DIR/src/tools_linux/action_help_editor.hpp"
CODE_MAP_SRC="$ROOT_DIR/src/tools_linux/action_code_map.cpp"
CODE_MAP_HEADER="$ROOT_DIR/src/tools_linux/action_code_map.hpp"
TARGET_PROTOCOL_SRC="$ROOT_DIR/src/tools_linux/action_target_protocol.cpp"
TARGET_PROTOCOL_HEADER="$ROOT_DIR/src/tools_linux/action_target_protocol.hpp"
TARGET_CLIENT_SRC="$ROOT_DIR/src/tools_linux/action_target_client.cpp"
TARGET_CLIENT_HEADER="$ROOT_DIR/src/tools_linux/action_target_client.hpp"
PROFILER_SRC="$ROOT_DIR/src/tools_linux/action_profiler.cpp"
PROFILER_HEADER="$ROOT_DIR/src/tools_linux/action_profiler.hpp"
HELP_CATALOG="$ROOT_DIR/resources/action_help.json"
HELP_BUILDER="$ROOT_DIR/tools/build_action_help.py"
BIN="$BUILD_DIR/action-workspace-tools"
memory_kib="${ACTION_MEMORY_KIB:-}"
if [[ -z "$memory_kib" && -r /proc/meminfo ]]; then
    memory_kib="$(awk '/^MemTotal:/ { print $2; exit }' /proc/meminfo)"
fi

if [[ -n "${CXX:-}" ]]; then
    CXX="$CXX"
else
    CXX=g++
    if [[ -n "$memory_kib" && "$memory_kib" -lt 524288 ]]; then
        for candidate in clang++ clang++-20 clang++-19 clang++-18 clang++-17 clang++-16; do
            if command -v "$candidate" >/dev/null 2>&1; then
                CXX="$candidate"
                break
            fi
        done
    fi
fi
read -r -a SQLITE_CFLAGS <<<"$(pkg-config --cflags sqlite3)"
read -r -a SQLITE_LIBS <<<"$(pkg-config --libs sqlite3)"
if [[ -n "${CXXFLAGS:-}" ]]; then
    read -r -a COMPILE_FLAGS <<<"$CXXFLAGS"
else
    COMPILE_FLAGS=(-std=c++17 -Wall -Wextra -Werror -O0)
fi
read -r -a LINK_FLAGS <<<"${LDFLAGS:-}"

mkdir -p "$BUILD_DIR"
python3 "$HELP_BUILDER" \
    --source "$HELP_CATALOG" \
    --output "$BUILD_DIR/action-help.sqlite3" >&2

if [[ "${ACTION_FORCE_REBUILD:-0}" == "1" || ! -x "$BIN" || "$SRC" -nt "$BIN" || "$FORMATTER_SRC" -nt "$BIN" || "$FORMATTER_HEADER" -nt "$BIN" || "$GRAPHICS_SRC" -nt "$BIN" || "$GRAPHICS_HEADER" -nt "$BIN" || "$HELP_SRC" -nt "$BIN" || "$HELP_HEADER" -nt "$BIN" || "$CODE_MAP_SRC" -nt "$BIN" || "$CODE_MAP_HEADER" -nt "$BIN" || "$TARGET_PROTOCOL_SRC" -nt "$BIN" || "$TARGET_PROTOCOL_HEADER" -nt "$BIN" || "$TARGET_CLIENT_SRC" -nt "$BIN" || "$TARGET_CLIENT_HEADER" -nt "$BIN" || "$PROFILER_SRC" -nt "$BIN" || "$PROFILER_HEADER" -nt "$BIN" || "${BASH_SOURCE[0]}" -nt "$BIN" ]]; then
    LOW_MEMORY="${ACTION_LOW_MEMORY:-auto}"
    IS_GCC=0
    if "$CXX" --version 2>/dev/null | head -n 1 | grep -Eqi 'g\+\+|gcc'; then
        IS_GCC=1
    fi
    if [[ "$LOW_MEMORY" == "auto" ]]; then
        if (( IS_GCC == 0 )); then
            LOW_MEMORY=off
        elif [[ -n "$memory_kib" && "$memory_kib" -lt 524288 ]]; then
            LOW_MEMORY=extreme
        elif [[ -n "$memory_kib" && "$memory_kib" -lt 786432 ]]; then
            LOW_MEMORY=on
        else
            LOW_MEMORY=off
        fi
    fi
    if (( IS_GCC == 1 )); then
        if [[ "$LOW_MEMORY" == "on" ]]; then
            COMPILE_FLAGS+=(
                -ftrack-macro-expansion=0
                --param ggc-min-expand=1
                --param ggc-min-heapsize=4096
            )
        elif [[ "$LOW_MEMORY" == "extreme" ]]; then
            COMPILE_FLAGS+=(
                -ftrack-macro-expansion=0
                --param ggc-min-expand=0
                --param ggc-min-heapsize=65536
            )
        fi
    fi

    TMP_BIN="$BIN.tmp.$$"
    COMPILER_TMP="$BUILD_DIR/.compiler-tmp.$$"
    mkdir -p "$COMPILER_TMP"
    trap 'rm -f "$TMP_BIN"; rm -rf "$COMPILER_TMP"' EXIT
    if (( IS_GCC == 1 )) && [[ "$LOW_MEMORY" == "extreme" ]]; then
        echo "Using the SSH-safe Pi Zero build mode; this native compile is intentionally slow." >&2
        echo "For release builds, prefer make build-aarch64 on a larger Docker host." >&2
    fi
    echo "Compiling ActionC64U Linux tools with $CXX (low-memory=$LOW_MEMORY)..." >&2
    TMPDIR="$COMPILER_TMP" "$CXX" \
        "${COMPILE_FLAGS[@]}" \
        "${SQLITE_CFLAGS[@]}" \
        "$SRC" "$FORMATTER_SRC" "$GRAPHICS_SRC" "$HELP_SRC" "$CODE_MAP_SRC" "$TARGET_PROTOCOL_SRC" "$TARGET_CLIENT_SRC" "$PROFILER_SRC" \
        -o "$TMP_BIN" \
        "${LINK_FLAGS[@]}" \
        "${SQLITE_LIBS[@]}"
    chmod +x "$TMP_BIN"
    mv "$TMP_BIN" "$BIN"
    rm -rf "$COMPILER_TMP"
    trap - EXIT
    echo "Compiled $BIN" >&2
fi

for tool in actnew actadd actwork actsrc actfile actchk actdir actcopy actdel actmkdir actrmdir actmove actren actwrite actinfo actmon actdbg actprof acttree tree xcopy deltree actspc actsprite actbitmap actedit acthelp act2save actsave actc alink; do
    ln -sf action-workspace-tools "$BUILD_DIR/$tool"
done

ACTION_TARGET_BUILD_DIR="$BUILD_DIR" \
    bash "$ROOT_DIR/tools/build_action_target_service.sh" >&2

echo "$BUILD_DIR"
