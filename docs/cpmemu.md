# CP/M-65 Host Harness with cpmemu

## Purpose in ActionC64U

ActionC64U uses the adjacent `../cpm65-u64/bin/cpmemu` binary as the first
headless execution target for CP/M-65 programs. This keeps early testing fast
and scriptable before we move to full-system C64 validation under VICE.

The local CP/M-65 README describes `cpmemu` as a user-mode emulator and
debugger. The documented example is:

```bash
./bin/cpmemu .obj/dump.com diskdefs
```

That example matters here because it demonstrates the intended host workflow:
load a `.com` program from the build tree and point it at a lower-case 8.3 file
that exists in the current directory.

## Local Runner in This Repo

Use the ActionC64U wrapper from this repo root:

```bash
python3 tools/cpmemu_runner.py .obj/dump.com --diskdefs-arg
```

Behavior:

- defaults the host working directory to `../cpm65-u64`
- resolves `../cpm65-u64/bin/cpmemu`
- verifies `../cpm65-u64/diskdefs` exists
- supports drive mapping via repeated `--drive A=/some/path` when the local
  `cpmemu -h` output advertises `-p DRIVE=PATH`
- fails fast if program names or filename-like arguments are not lower-case 8.3

Useful options:

- `--cwd /path/to/dir`: run `cpmemu` from a specific host directory
- `--drive A=/path/to/files`: map a CP/M drive when supported by the local build
- `--debug`: start in the `cpmemu` debugger when the local build advertises `-d`
- `--print-command`: show the resolved host command line before execution

## Hello.COM Smoke Test

ActionC64U includes a minimal smoke program under
`src/tools_cpm/hello/hello.asm`. The preferred bootstrap path is:

1. build CP/M-65 so `bin/cpmemu` exists
2. build or otherwise surface `asm.com`
3. assemble `hello.asm` under `cpmemu`
4. run the resulting `hello.com`

That native `asm.com` flow is still the long-term target, but it is not yet
guaranteed in this workspace because `cpmemu` is currently missing here.

For now, `./tools/build_hello.sh` does this:

- prefers native assembly via `cpmemu` plus `asm.com`
- falls back to `mos-cpm65-clang` with a tiny host-buildable source when the
  native assembler path is unavailable
- writes the output to `build/hello.com`

Commands:

```bash
./tools/build_hello.sh
python3 tools/cpmemu_runner.py --cwd build hello.com
```

Expected output contains:

```text
HELLO FROM ACTIONC64U
```

## Building CP/M-65

If `../cpm65-u64/bin/cpmemu` is missing, build the adjacent CP/M-65 checkout.
From the local `../cpm65-u64/README.md` and `Makefile`:

- `llvm-mos` is required
- the `Makefile` expects `LLVM=<path-to-llvm-mos-bin>/`
- useful Debian/Ubuntu packages include:
  - `cc1541`
  - `cpmtools`
  - `libfmt-dev`
  - `fp-compiler`
  - `moreutils`
  - `mame`
  - `srecord`
  - `64tass`
  - `libreadline-dev`

Print the exact reminder commands from this repo with:

```bash
./tools/build_cpm65_notes.sh
```

Typical build sequence:

```bash
cd /mnt/c/test/action/cpm65-u64
make LLVM=<path-to-llvm-mos-bin>/ -j$(nproc)
```

Expected outputs:

- `../cpm65-u64/bin/cpmemu`
- `../cpm65-u64/.obj/*.com`
- `../cpm65-u64/diskdefs`

## Common Failure Modes

### `bin/cpmemu` does not exist

The adjacent CP/M-65 tree has not been built yet, or the build failed before the
host tools stage finished. Run `./tools/build_cpm65_notes.sh` and then build
inside `../cpm65-u64` with a real `LLVM=<path>/` value.

### `llvm-mos` path is wrong

The CP/M-65 `Makefile` defaults `LLVM` to `/opt/pkg/llvm-mos/bin`, but you
should only use that path if it really matches your machine. Pass the actual
llvm-mos `bin` directory explicitly.

### `diskdefs` or input files are not found

`cpmemu` defaults drive `A:` to the current host directory. Either run the
process from the directory that contains the lower-case 8.3 files you need, or
use `--drive A=/path/to/files` if the local build supports drive mapping.

### Filename rejected by ActionC64U's wrapper

This repo intentionally rejects program names and filename-like arguments that
are not all-lowercase 8.3. The local CP/M-65 README warns that `cpmemu` can only
access all-lowercase 8.3 filenames from the current directory.

### `cpmemu -h` exits non-zero

That is acceptable for now. The current upstream help path prints usage text but
may still return a non-zero exit status. Our tests treat visible usage/help text
as a successful probe.
