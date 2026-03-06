# Current Blockers

The current workspace does not yet have the toolchain pieces needed to build and
run `vmhello.com` end to end.

## Missing Here Now

- missing command: ca65
- missing command: ld65
- missing file: Acheron generated include (/mnt/c/test/action/actionc64u/../acheronvm/bin/acheron.inc)
- missing file: Acheron runtime object (/mnt/c/test/action/actionc64u/../acheronvm/obj/acheron.o)
- missing file: CP/M-65 cpmemu (/mnt/c/test/action/actionc64u/../cpm65-u64/bin/cpmemu)

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
