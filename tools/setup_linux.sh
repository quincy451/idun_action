#!/usr/bin/env bash
set -euo pipefail

RUN=0

usage() {
  cat <<'USAGE'
Usage: ./tools/setup_linux.sh [--print|--run]

Print the native dependencies for Alpine or Debian-family Linux.
--run installs only when this script is deliberately invoked as root.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --print)
      RUN=0
      ;;
    --run)
      RUN=1
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

DISTRO_ID=""
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  DISTRO_ID="${ID:-}"
fi

case "$DISTRO_ID" in
  alpine)
    MANAGER=apk
    CORE_PACKAGES=(bash build-base clang20 make python3 pkgconf sqlite-dev)
    OPTIONAL_PACKAGES=(git py3-pip vice)
    ;;
  debian|ubuntu|linuxmint|pop)
    MANAGER=apt
    CORE_PACKAGES=(build-essential make python3 pkg-config libsqlite3-dev)
    OPTIONAL_PACKAGES=(git python3-pip vice)
    ;;
  *)
    MANAGER=unknown
    CORE_PACKAGES=(C++17-compiler make python3 pkg-config sqlite3-development-files)
    OPTIONAL_PACKAGES=(git pip VICE-x64sc)
    ;;
esac

print_plan() {
  echo "ActionC64U Idun/Linux native dependencies:"
  echo
  if [[ "$MANAGER" == "apk" ]]; then
    printf '  apk add --no-cache'
  elif [[ "$MANAGER" == "apt" ]]; then
    echo "  apt-get update"
    printf '  apt-get install -y'
  else
    printf '  install with your package manager:'
  fi
  printf ' %s' "${CORE_PACKAGES[@]}"
  printf '\n'
  echo
  printf 'Optional (source control, pip, and direct PRG emulation):'
  printf ' %s' "${OPTIONAL_PACKAGES[@]}"
  printf '\n'
}

print_plan
if (( RUN == 0 )); then
  exit 0
fi

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "--run requires root; invoke it explicitly with sudo, doas, or a root shell." >&2
  exit 1
fi

case "$MANAGER" in
  apk)
    apk add --no-cache "${CORE_PACKAGES[@]}"
    ;;
  apt)
    apt-get update
    apt-get install -y "${CORE_PACKAGES[@]}"
    ;;
  *)
    echo "Automatic installation is unavailable for this distribution." >&2
    exit 1
    ;;
esac
