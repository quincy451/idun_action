#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

bash tools/env_check.sh --strict
bash tools/build_linux_tools.sh
python3 -m pytest -q
python3 tools/export_idun_workspace.py

echo "Built and verified the self-contained Idun/Linux toolchain."
