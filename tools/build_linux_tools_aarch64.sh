#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ALPINE_IMAGE="${ACTION_ALPINE_IMAGE:-alpine:3.24}"
CROSS_IMAGE="${ACTION_AARCH64_CROSS_IMAGE:-dockcross/linux-arm64-musl:latest}"
SYSROOT="$ROOT_DIR/build/aarch64-sysroot"
BUILD_DIR="$ROOT_DIR/build/linux_tools-aarch64"
BIN="$BUILD_DIR/action-workspace-tools"
HELP_CATALOG="$ROOT_DIR/resources/action_help.json"
HELP_BUILDER="$ROOT_DIR/tools/build_action_help.py"

if ! command -v docker >/dev/null 2>&1; then
    echo "docker is required for the local aarch64-musl build" >&2
    exit 1
fi

mkdir -p "$SYSROOT" "$BUILD_DIR"
python3 "$HELP_BUILDER" \
    --source "$HELP_CATALOG" \
    --output "$BUILD_DIR/action-help.sqlite3" >&2

if [[ ! -f "$SYSROOT/usr/include/sqlite3.h" || ! -f "$SYSROOT/usr/lib/libsqlite3.a" ]]; then
    docker run --rm \
        --platform linux/amd64 \
        --user "$(id -u):$(id -g)" \
        -v "$ROOT_DIR:/work" \
        -w /work \
        "$ALPINE_IMAGE" \
        sh -euc '
            apk --usermode \
                --allow-untrusted \
                --arch aarch64 \
                --root /work/build/aarch64-sysroot \
                --repositories-file /etc/apk/repositories \
                --initdb \
                --no-scripts \
                --no-cache \
                add sqlite-dev sqlite-static
        '
fi

docker run --rm \
    --user "$(id -u):$(id -g)" \
    -v "$ROOT_DIR:/work" \
    -w /work \
    "$CROSS_IMAGE" \
    bash -euc '
        "$CXX" \
            -std=c++17 \
            -Wall \
            -Wextra \
            -Werror \
            -O0 \
            -I/work/build/aarch64-sysroot/usr/include \
            src/tools_linux/action_workspace_tools.cpp \
            src/tools_linux/action_formatter.cpp \
            src/tools_linux/action_graphics_editor.cpp \
            src/tools_linux/action_help_editor.cpp \
            src/tools_linux/action_code_map.cpp \
            src/tools_linux/action_target_protocol.cpp \
            src/tools_linux/action_target_client.cpp \
            src/tools_linux/action_profiler.cpp \
            -static \
            -s \
            -o build/linux_tools-aarch64/action-workspace-tools \
            /work/build/aarch64-sysroot/usr/lib/libsqlite3.a \
            -ldl \
            -lpthread \
            -lm
    '

for tool in actnew actadd actwork actsrc actfile actchk actdir actcopy actdel actmkdir actrmdir actmove actren actwrite actinfo actmon actdbg actprof acttree tree xcopy deltree actspc actsprite actbitmap actedit acthelp act2save actsave actc alink; do
    ln -sf action-workspace-tools "$BUILD_DIR/$tool"
done

ACTION_TARGET_BUILD_DIR="$BUILD_DIR" \
    bash "$ROOT_DIR/tools/build_action_target_service.sh" >&2

echo "$BUILD_DIR"
