#!/usr/bin/env bash
set -euo pipefail

cat <<'NOTES'
ActionC64U uses the adjacent CP/M-65 checkout at ../cpm65-u64.

Build notes (print-only; no commands are executed by this script):

1. Install the packages called out by the local CP/M-65 README:

   sudo apt-get update
   sudo apt-get install -y \
     clang g++ make python3 cc1541 cpmtools libfmt-dev fp-compiler \
     moreutils mame srecord 64tass libreadline-dev

2. Install llvm-mos separately.
   Do not guess the path. Choose the actual llvm-mos bin directory on your machine.

3. Build from inside ../cpm65-u64:

   cd /mnt/c/test/action/cpm65-u64
   make LLVM=<path-to-llvm-mos-bin>/ -j$(nproc)

4. Optional emulator-based regression pass from the CP/M-65 tree:

   make LLVM=<path-to-llvm-mos-bin>/ -j$(nproc) +mametest

Expected artifacts after a successful build:
- ../cpm65-u64/bin/cpmemu
- ../cpm65-u64/.obj/*.com
- ../cpm65-u64/diskdefs
NOTES
