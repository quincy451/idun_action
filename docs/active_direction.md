# Active Project Direction

This project has pivoted away from CP/M-65 as an execution target.

The active product path is:

- UDOS as the standalone Commodore 64 Ultimate shell/runtime
- Action tooling as UDOS-aware `.PRG` programs
- C64 Ultimate ROM/Ultimate DOS services through the UDOS resident service layer
- direct linked `.PRG` output as the only maintained runtime artifact

The active code paths are:

- `../udos/src/asm/udos_resident.asm`
- `../udos/tools/run_action_*.py`
- `src/tools_udos/`
- `tools/build_*_udos.sh`
- `tools/export_udos_workspace.py`

The CP/M-65 compiler/linker/bootstrap code and the old VM toolchain have been
removed. Repository code should not add new runtime-runner flows. Action-linked
programs now target direct 6502 `.PRG` output, and the UDOS resident shell is
native 6502 rather than a VM bytecode host.

## Active Verification Gates

Use UDOS gates as the source of truth:

```sh
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc-alink-launch
```

Treat `vice-action-alink` as the default direct-native linker gate that emits
`BIN/MAIN.PRG`.
Treat `vice-action-actc-alink-launch` as the helper-free higher-level default.
Treat `vice-action-actc-alink-launch-printmath` as a green named direct
launch gate for the imported `printmath` shape.

Use narrower UDOS gates when working on a specific tool:

```sh
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actadd
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-act2save
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actcopy
```

## Development Rules

- Prefer `src/tools_udos` over deleted CP/M-era compiler/linker paths.
- Prefer `tools/build_*_udos.sh`; do not reintroduce CP/M `.COM` build scripts.
- Do not treat `cpmemu` success as proof that the active target works.
- Do not add new CP/M or runtime-runner features.

## Current Design Inputs

Optional runtime/library work should follow the link-selected helper direction:
helpers are selected by the linker and carried by the final `.PRG`, not by a
separate runtime program.

Current concrete API inputs:

- graphics/resource datatype direction:
  - `docs/graphics_ideas.txt`
- SID and sprite helper direction:
  - `docs/sid_and_sprite_ideas.txt`
- first Action-facing math binding sketch:
  - `docs/math1_bindings_draft.act`
- DBF-style database API sketch:
  - `docs/dbf_test.c`
- concrete helper-family ABI draft:
  - `docs/helper_family_abi_draft.md`
- first Action-facing SID/sprite binding sketch:
  - `docs/sidspr1_bindings_draft.act`

These are design inputs for optional helper families. They should not be
implemented as permanent runner-global features.

## Current Next Work

The current practical path is:

1. Keep the UDOS external-tool ABI load/save/copy/delete/rename services stable.
2. Remove temporary probe/debug noise once permanent diagnostics cover the same
   failures.
3. Continue widening `ACTC.PRG` object emission.
4. Continue widening `ALINK.PRG` object resolution and final direct-PRG
   generation.
5. Keep the native `ALINK -> MAIN.PRG` path green.
6. Keep moving optional feature helpers toward link-only runtime modules.
7. Build on the resident REU stage/read services and convert ACTC toward the
   REU-backed source-streaming plan in `docs/actc_source_streaming_plan.md` so
   source size is no longer tied to one contiguous buffer.
8. Move large ACTC/ALINK lookup payloads into REU-backed tables after source
   paging is stable.
9. Keep `ACTC.PRG -> ALINK.PRG -> MAIN.PRG` green under UDOS.
10. Treat graphics, SID/sprite, DBF, math, TCP, and 80-column support as
    optional raw-6502 helper families with thin language bindings, not as
    new permanent runner-global behavior.
11. Use `docs/helper_family_abi_draft.md` as the current concrete contract for
    the first optional helper-family wave, with `SIDSPR1` as the preferred
    first implementation family.
