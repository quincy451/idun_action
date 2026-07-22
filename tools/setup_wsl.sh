#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "setup_wsl.sh is a compatibility name; using the generic Linux setup helper." >&2
exec "$SCRIPT_DIR/setup_linux.sh" "$@"
