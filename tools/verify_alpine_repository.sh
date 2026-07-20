#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPOSITORY="${1:-$ROOT_DIR/build/alpine-apk/repository}"
TOOLS_SOURCE="${2:-$ROOT_DIR/build/linux_tools-aarch64}"
ALPINE_IMAGE="${ACTION_ALPINE_IMAGE:-alpine:3.24}"

[[ -d "$REPOSITORY/aarch64" ]] || {
    echo "Alpine repository not found: $REPOSITORY" >&2
    exit 1
}
[[ -x "$TOOLS_SOURCE/action-workspace-tools" ]] || {
    echo "AArch64 tools not found: $TOOLS_SOURCE" >&2
    exit 1
}
command -v docker >/dev/null 2>&1 || {
    echo "docker is required to verify the Alpine repository" >&2
    exit 1
}

EXPECTED_COMMANDS="$(
    PYTHONPATH="$ROOT_DIR/tools" python3 -c \
        'from export_idun_workspace import LINUX_TOOL_NAMES; print(" ".join(LINUX_TOOL_NAMES))'
)"
docker run --rm \
    --platform linux/amd64 \
    -e "EXPECTED_COMMANDS=$EXPECTED_COMMANDS" \
    -v "$REPOSITORY:/repository:ro" \
    -v "$TOOLS_SOURCE:/tools:ro" \
    -v "$ROOT_DIR/packaging/alpine/container-verify.sh:/container-verify.sh:ro" \
    "$ALPINE_IMAGE" \
    /bin/sh /container-verify.sh
