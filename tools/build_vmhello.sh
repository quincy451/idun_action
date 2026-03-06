#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACHERON_DIR="$ROOT_DIR/../acheronvm"
CPM_DIR="$ROOT_DIR/../cpm65-u64"
BUILD_DIR="$ROOT_DIR/build"
BLOCKERS_DOC="$ROOT_DIR/docs/blockers.md"
OUT_COM="$BUILD_DIR/vmhello.com"

mkdir -p "$BUILD_DIR"

missing=()
notes=()

need_cmd() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    missing+=("missing command: $name")
  fi
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

need_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    missing+=("missing file: $label ($path)")
  fi
}

write_blockers() {
  local missing_text="- none recorded"
  if [[ ${#missing[@]} -gt 0 ]]; then
    missing_text="$(printf '%s\n' "${missing[@]}" | sed 's/^/- /')"
  fi

  {
    printf '# Current Blockers\n\n'
    printf 'The current workspace does not yet have the toolchain pieces needed to build and\n'
    printf 'run `vmhello.com` end to end.\n\n'
    printf '## Missing Here Now\n\n'
    printf '%s\n\n' "$missing_text"
    cat <<'EOF_DOC'
## Commands to Unblock

Install the cc65 toolchain on Debian/Ubuntu so `ca65` and `ld65` exist:

```bash
sudo apt-get update
sudo apt-get install -y cc65
```

Build the local AcheronVM runtime and generated include file:

```bash
cd /mnt/c/test/action/acheronvm
make acheron
```

Build the local CP/M-65 tree so `bin/cpmemu` exists:

```bash
cd /mnt/c/test/action/cpm65-u64
make LLVM=<path-to-llvm-mos-bin>/ -j$(nproc)
```

If you want the llvm-mos fallback path available too, ensure
`mos-cpm65-clang` is on `PATH` or set:

```bash
export LLVM=<path-to-llvm-mos-bin>/
```

## Remaining Integration Task

Once those dependencies are present, this repo still needs a verified CP/M-65
link recipe that combines the AcheronVM runtime with a relocatable `.com`
program image. The staged `src/vm/vmhello/vmhello.asm` source captures the
intended execution flow, and `tools/build_vmhello.sh` reports the exact
prerequisites before that final link step can be automated safely.
EOF_DOC
  } > "$BLOCKERS_DOC"
}

if have_cmd ca65 && have_cmd ld65; then
  if [[ ! -f "$ACHERON_DIR/bin/acheron.inc" || ! -f "$ACHERON_DIR/obj/acheron.o" ]]; then
    if ! make -C "$ACHERON_DIR" acheron >/dev/null 2>&1; then
      notes+=("attempted 'make -C $ACHERON_DIR acheron' but it did not complete")
    fi
  fi
fi

need_cmd ca65
need_cmd ld65
if ! have_cmd mos-cpm65-clang; then
  notes+=("optional fallback missing: mos-cpm65-clang")
fi
need_file "$ACHERON_DIR/bin/acheron.inc" "Acheron generated include"
need_file "$ACHERON_DIR/obj/acheron.o" "Acheron runtime object"
if [[ ! -x "$CPM_DIR/bin/cpmemu" ]]; then
  missing+=("missing file: CP/M-65 cpmemu ($CPM_DIR/bin/cpmemu)")
fi

if [[ ${#missing[@]} -gt 0 ]]; then
  write_blockers
  printf '%s\n' "${missing[@]}" >&2
  if [[ ${#notes[@]} -gt 0 ]]; then
    printf '%s\n' "${notes[@]}" >&2
  fi
  echo "See $BLOCKERS_DOC for exact unblock commands." >&2
  exit 2
fi

cat >&2 <<'EOF_MSG'
All external prerequisites are now present, but the final automated CP/M-65 link
recipe for vmhello is not yet finalized in this repo.
See docs/blockers.md for the current integration note.
EOF_MSG
write_blockers
rm -f "$OUT_COM"
exit 2
