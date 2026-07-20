# Linux Setup

The Idun fork is self-contained. It does not require an adjacent CP/M-65 tree,
UDOS checkout, disk image, or cross-development workspace.

## Required Build Tools

- Bash
- a C++17 compiler (`g++` or Clang; Clang 20 is preferred on the Pi Zero)
- `make`
- Python 3
- `pkg-config`
- SQLite 3 development headers and library

Headless VICE `x64sc` is optional. When present, the test suite executes a
generated C64 PRG directly; no physical C64 is required.

Print distribution-specific installation guidance:

```sh
bash tools/setup_linux.sh
```

On the Idun cartridge's Alpine Linux, the core package command is:

```sh
apk add --no-cache bash build-base clang20 make python3 pkgconf sqlite-dev
```

On Debian or Ubuntu:

```sh
apt-get install -y build-essential make python3 pkg-config libsqlite3-dev
```

The setup helper never elevates itself. Its optional `--run` mode must be
invoked deliberately from a root shell or through `sudo`/`doas`.

## Verify And Build

```sh
bash tools/env_check.sh --strict
python3 tools/path_probe.py
make all
```

`make all` builds the Linux multicall executable, runs only the active Idun
tests, validates/builds the external SQLite help catalog, and exports a
ready-to-use workspace under `build/idun-action/`.

Install user-level command symlinks without root access:

```sh
make install-user
hash -r
```

The default destination is `$HOME/.local/bin`. The exported workspace also
contains a self-contained `install-user.sh`. If that directory is not already
on `PATH`, the installer prints the exact profile line to add.

Run `build/linux_tools/acthelp IF` for command-line language help. In an
exported workspace, tools automatically find `DOC/action-help.sqlite3`; set
`ACTION_HELP_DB` only when deliberately using a catalog from another location.

## Low-RAM Pi Builds

Below 512 MiB, the normal build script automatically prefers an installed
versioned Clang executable such as Alpine's `clang++-20`. On the verified
416 MiB Pi Zero 2 W the current expanded source build completes in roughly four
minutes. The final system check found the Pi's existing 2 GiB swapfile active;
the build does not create or manage swap. If Clang is unavailable, the script
falls back to an SSH-safe but very slow GCC mode. Compiler temporary files are
placed under `build/linux_tools/` instead of a RAM-backed `/tmp`, and the final
binary is replaced atomically only after a successful link.

To force a clean native rebuild and run every active gate on the Pi:

```sh
ACTION_FORCE_REBUILD=1 make all
```

A larger Docker host can also produce a static Alpine/aarch64 executable:

```sh
make build-aarch64
```

That target downloads an x86-hosted aarch64-musl cross-toolchain and Alpine
aarch64 SQLite development packages from Alpine's HTTPS repository. It writes
the self-contained multicall executable and command symlinks to
`build/linux_tools-aarch64/`. Neither Docker nor SQLite shared libraries are
needed on the Pi to run the resulting static executable.
