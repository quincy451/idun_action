# ActionC64U - Action! Commodore 64 Ultimate Edition

ActionC64U is a clean-room Action!-style toolchain project for the Commodore 64.

The active project path is UDOS-native. Action tools are built as standalone
`.PRG` programs that run under the sibling `../udos` shell/runtime and use the
UDOS resident service layer to reach Commodore 64 Ultimate ROM/Ultimate DOS
services.

Retired CP/M-65 notes remain only where explicitly labeled as historical
documentation. They are not an active implementation target and should not drive
feature work. See [docs/active_direction.md](./docs/active_direction.md).

The current UDOS-facing alpha ships:

- `ALINK.PRG`: UDOS-native linker; the default live gate now emits direct `.PRG` output
- `ACTC.PRG`: UDOS-native compiler front end
- `ACTMON.PRG`: monitor-style front end
- workspace/project helper tools under `src/tools_udos/`
- dead-strip linkable runtime modules
- a reproducible UDOS release/workspace image plus VICE verification

## Prerequisites

Required local sibling trees:

- `../udos`

Required host tools:

- `python3`
- `git`
- `make`
- a C compiler and C++ compiler
- `pytest`
- `cc65` tools for UDOS `.PRG` assembly

The repo also carries a minimal `pytest` shim for constrained environments, but
a normal `pytest` install is still recommended.

Release-image and C64/VICE verification tools:

- `c1541`
- `x64sc` from VICE for automated C64 validation

Quick environment check:

```sh
./tools/env_check.sh
```

Strict required-dependency check:

```sh
./tools/env_check.sh --strict
```

WSL setup notes live in [docs/setup_wsl.md](docs/setup_wsl.md).

## Active UDOS Verification

Use the sibling UDOS repo as the source of truth for current development:

```sh
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc-alink-launch
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc-alink-launch-printmath
```

These gates build the UDOS release image, install the Action `.PRG` tools, boot
UDOS under VICE, and validate the real tool path. The helper-free higher-level
default is:

```text
ACTC.PRG -> ALINK.PRG -> MAIN.PRG
```

The lower-level default linker gate is `make -C ../udos vice-action-alink`,
which now verifies `ALINK.PRG -> BIN/MAIN.PRG`.

## Build UDOS Tools

Build individual UDOS-native tools:

```sh
./tools/build_actc_udos.sh
./tools/build_alink_udos.sh
./tools/build_actmon_udos.sh
```

The outputs are written under:

- `build/udos_tools/`

## Host Tests

Run the full host-side suite:

```sh
python3 -m pytest -q
```

This covers:

- UDOS workspace export checks
- VICE verification when `x64sc` is installed
- UDOS-native compiler/linker overlay and capacity checks

Host tests are useful, but they are not the current target proof. UDOS VICE
gates above are authoritative for current toolchain work.

## Export A UDOS Workspace

Build a UDOS-compatible Action workspace tree with guides and sample sources:

```sh
python3 tools/export_udos_workspace.py
```

Default output:

- `build/udos-action-fs/IMAGES/ACTION.DNP`

This export is the current bridge artifact from the Action tool repo into the
UDOS shell.

## Removed Legacy Paths

The older host VM compiler/linker, CP/M runner, and legacy CP/M release-image
scripts have been removed. The maintained target path is the UDOS-native
toolchain and direct `.PRG` output from `ALINK.PRG`.

## Documentation Map

Key current docs:

- [docs/actc_roadmap.md](docs/actc_roadmap.md)
- [docs/alink_roadmap.md](docs/alink_roadmap.md)
- [docs/active_direction.md](docs/active_direction.md)
- [docs/real32.md](docs/real32.md)
- [docs/reu.md](docs/reu.md)
- [docs/disk_layout.md](docs/disk_layout.md)
- [docs/release.md](docs/release.md)
- [docs/action_matrix.md](docs/action_matrix.md)
- [docs/udos_resume.md](docs/udos_resume.md)
- [docs/blockers.md](docs/blockers.md)
- [docs/prompt_chain.md](docs/prompt_chain.md)

## Prompt Chain

The repo was built through `prompt-1.txt` through `prompt-18.txt` from the
workspace root. The workflow is documented in
[docs/prompt_chain.md](docs/prompt_chain.md).
