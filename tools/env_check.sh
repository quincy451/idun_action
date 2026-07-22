#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STRICT=0

usage() {
  cat <<'USAGE'
Usage: ./tools/env_check.sh [--strict]

Advisory environment check for the ActionC64U Idun/Linux fork.
  --strict   exit non-zero when any required dependency is missing
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict)
      STRICT=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

required_missing=0
optional_missing=0

print_header() {
  printf '%-8s %-8s %-24s %s\n' "STATUS" "REQUIRED" "CHECK" "DETAIL"
  printf '%-8s %-8s %-24s %s\n' "------" "--------" "-----" "------"
}

record_result() {
  local required_flag="$1"
  local label="$2"
  local status="$3"
  local detail="$4"

  printf '%-8s %-8s %-24s %s\n' "$status" "$required_flag" "$label" "$detail"

  if [[ "$status" == "FAIL" ]]; then
    if [[ "$required_flag" == "yes" ]]; then
      required_missing=$((required_missing + 1))
    else
      optional_missing=$((optional_missing + 1))
    fi
  fi
}

command_path() {
  command -v "$1" 2>/dev/null || true
}

check_command() {
  local label="$1"
  local required_flag="$2"
  local command_name="$3"
  local install_hint="$4"
  local path
  path="$(command_path "$command_name")"

  if [[ -n "$path" ]]; then
    record_result "$required_flag" "$label" "PASS" "$path"
  else
    record_result "$required_flag" "$label" "FAIL" "$install_hint"
  fi
}

check_any_command() {
  local label="$1"
  local required_flag="$2"
  local install_hint="$3"
  shift 3

  local found=()
  local name path
  for name in "$@"; do
    path="$(command_path "$name")"
    if [[ -n "$path" ]]; then
      found+=("$name=$path")
    fi
  done

  if [[ ${#found[@]} -gt 0 ]]; then
    record_result "$required_flag" "$label" "PASS" "${found[*]}"
  else
    record_result "$required_flag" "$label" "FAIL" "$install_hint"
  fi
}

check_all_commands() {
  local label="$1"
  local required_flag="$2"
  local install_hint="$3"
  shift 3

  local found=()
  local missing=()
  local name path
  for name in "$@"; do
    path="$(command_path "$name")"
    if [[ -n "$path" ]]; then
      found+=("$name=$path")
    else
      missing+=("$name")
    fi
  done

  if [[ ${#missing[@]} -eq 0 ]]; then
    record_result "$required_flag" "$label" "PASS" "${found[*]}"
  else
    record_result "$required_flag" "$label" "FAIL" "$install_hint (missing: ${missing[*]})"
  fi
}

check_pytest() {
  local metadata_output
  if metadata_output="$(python3 - <<'PY' 2>/dev/null
from importlib import metadata
print(metadata.version('pytest'))
PY
)"; then
    record_result "yes" "pytest" "PASS" "installed package version ${metadata_output}"
    return
  fi

  local shim_output
  if shim_output="$(cd "$ROOT_DIR" && python3 -m pytest --version 2>/dev/null)"; then
    record_result "yes" "pytest" "PASS" "repo-local fallback available (${shim_output}); install with: python3 -m pip install --user pytest for a non-shim environment"
    return
  fi

  record_result "yes" "pytest" "FAIL" "install with: python3 -m pip install --user pytest"
}

check_pkg_config_module() {
  local label="$1"
  local required_flag="$2"
  local module="$3"
  local install_hint="$4"
  if command -v pkg-config >/dev/null 2>&1 && pkg-config --exists "$module"; then
    record_result "$required_flag" "$label" "PASS" "$(pkg-config --modversion "$module")"
  else
    record_result "$required_flag" "$label" "FAIL" "$install_hint"
  fi
}

print_header
check_command "make" "yes" "make" "install package: make"
check_command "python3" "yes" "python3" "install package: python3"
check_any_command "C++ compiler" "yes" "install build-essential or clang" \
  g++ clang++ clang++-20 clang++-19 clang++-18 clang++-17 clang++-16
check_command "pkg-config" "yes" "pkg-config" "install package: pkg-config"
check_pkg_config_module "SQLite 3 headers/libs" "yes" "sqlite3" "install package: sqlite-dev (Alpine) or libsqlite3-dev (Debian/Ubuntu)"
check_pytest
check_command "git" "no" "git" "install package: git"
check_command "pip3" "no" "pip3" "install package: py3-pip or python3-pip"
check_command "VICE x64sc" "no" "x64sc" "install VICE for direct generated-PRG validation"

printf '\nSummary: %d required missing, %d optional missing.\n' "$required_missing" "$optional_missing"
if (( required_missing > 0 )); then
  echo "Required dependencies are missing. Run ./tools/setup_linux.sh for install guidance."
fi
if (( optional_missing > 0 )); then
  echo "Optional dependencies are missing. They are not required for the Linux tool build."
fi

if (( STRICT == 1 && required_missing > 0 )); then
  exit 1
fi
