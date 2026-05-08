# ActionC64U - Action! Commodore 64 Ultimate Edition

ActionC64U is a clean-room Action!-style toolchain project for the Commodore 64.

The active project path is UDOS-native. Action tools are built as standalone
`.PRG` programs that run under the sibling `../udos` shell/runtime and use the
UDOS resident service layer to reach Commodore 64 Ultimate ROM/Ultimate DOS
services.

The older CP/M-65 bootstrap path remains in this repository as historical
reference material only. It is not the active implementation target and should
not drive feature work. See [docs/active_direction.md](./docs/active_direction.md).

The current UDOS-facing alpha ships:

- `ALINK.PRG`: UDOS-native linker; the default live gate now emits direct `.PRG` output
- `ACTC.PRG`: UDOS-native compiler front end
- `AVMRUN.PRG`: legacy/compat VM runner for `.AVM` payloads
- `ACTMON.PRG`: monitor-style front end
- workspace/project helper tools under `src/tools_udos/`
- dead-strip linkable runtime modules
- a reproducible UDOS release/workspace image plus VICE verification

## Prerequisites

Required local sibling trees:

- `../udos`
- `../acheronvm`

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

WSL setup notes live in [docs/setup_wsl.md](/mnt/c/test/action/actionc64u/docs/setup_wsl.md).

## Active UDOS Verification

Use the sibling UDOS repo as the source of truth for current development:

```sh
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc-alink-launch
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink-compat
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc-alink-launch-printmath
```

These gates build the UDOS release image, install the Action `.PRG` tools, boot
UDOS under VICE, and validate the real tool path. The helper-free higher-level
default is:

```text
ACTC.PRG -> ALINK.PRG -> MAIN.PRG
```

The AVM-bearing path remains separate:

```text
ACTC.PRG -> ALINK.PRG -> AVMRUN.PRG
```

The lower-level default linker gate is `make -C ../udos vice-action-alink`,
which now verifies `ALINK.PRG -> BIN/MAIN.PRG`. The separate
`vice-action-alink-compat` target is the legacy AVM-specific replay gate.
The older `vice-action-alink-avmrun` name remains only as a compatibility
alias.

## Build UDOS Tools

Build individual UDOS-native tools:

```sh
./tools/build_actc_udos.sh
./tools/build_alink_udos.sh
./tools/build_avmrun_udos.sh
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

- host compiler/linker behavior
- legacy CP/M-65 bootstrap/reference checks
- UDOS workspace export checks
- VICE verification when `x64sc` is installed

Host tests are useful, but they are not the current target proof. UDOS VICE
gates above are authoritative for current toolchain work.

## Legacy CP/M Reference

The CP/M-65 path is preserved as reference material. Build it only when
intentionally maintaining the older bootstrap:

```sh
./tools/build_alink.sh
./tools/build_actc.sh
./tools/build_vmrun.sh
./tools/build_actmon.sh
```

Legacy outputs include:

- `build/alink.com`
- `build/actc.com`
- `build/vm.com`
- `build/actmon.com`

## Export A UDOS Workspace

Build a UDOS-compatible Action workspace tree with guides, sample sources,
sample `AVM1` payloads, and runtime manifests:

```sh
python3 tools/export_udos_workspace.py
```

Default output:

- `build/udos-action-fs/IMAGES/ACTION.DNP`

This export is the current bridge artifact from the Action tool repo into the
UDOS shell/runtime.

## Legacy CP/M Release Image

The old CP/M release-image scripts remain for historical comparison only:

```sh
python3 tools/build_release_image.py
python3 tools/verify_release.py
```

Do not use these as the current project success criteria.

## One-Command Smoke Pass

For current development, prefer the UDOS VICE gates listed above over the
historical `tools/smoke.sh` path.

## Documentation Map

Key docs:

- [docs/actc_roadmap.md](/mnt/c/test/action/actionc64u/docs/actc_roadmap.md)
- [docs/alink_roadmap.md](/mnt/c/test/action/actionc64u/docs/alink_roadmap.md)
- [docs/active_direction.md](/mnt/c/test/action/actionc64u/docs/active_direction.md)
- [docs/cpmemu.md](/mnt/c/test/action/actionc64u/docs/cpmemu.md)
- [docs/vice.md](/mnt/c/test/action/actionc64u/docs/vice.md)
- [docs/spec.md](/mnt/c/test/action/actionc64u/docs/spec.md)
- [docs/linker.md](/mnt/c/test/action/actionc64u/docs/linker.md)
- [docs/real32.md](/mnt/c/test/action/actionc64u/docs/real32.md)
- [docs/reu.md](/mnt/c/test/action/actionc64u/docs/reu.md)
- [docs/overlays.md](/mnt/c/test/action/actionc64u/docs/overlays.md)
- [docs/disk_layout.md](/mnt/c/test/action/actionc64u/docs/disk_layout.md)
- [docs/release.md](/mnt/c/test/action/actionc64u/docs/release.md)
- [docs/action_matrix.md](/mnt/c/test/action/actionc64u/docs/action_matrix.md)
- [docs/udos_resume.md](/mnt/c/test/action/actionc64u/docs/udos_resume.md)
- [docs/blockers.md](/mnt/c/test/action/actionc64u/docs/blockers.md)
- [docs/prompt_chain.md](/mnt/c/test/action/actionc64u/docs/prompt_chain.md)

## Prompt Chain

The repo was built through `prompt-1.txt` through `prompt-18.txt` from the
workspace root. The workflow is documented in
[docs/prompt_chain.md](/mnt/c/test/action/actionc64u/docs/prompt_chain.md).
