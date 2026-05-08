#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Production runner assets currently come from the AVMRUN build: its labels,
# linked native helper binaries, and compat overlay sidecars.
"$ROOT_DIR/tools/build_avmrun_udos.sh" >/dev/null
