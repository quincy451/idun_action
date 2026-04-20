# Active Project Direction

This project has pivoted away from CP/M-65 as an execution target.

The active product path is:

- UDOS as the standalone Commodore 64 Ultimate shell/runtime
- Action tooling as UDOS-aware `.PRG` programs
- C64 Ultimate ROM/Ultimate DOS services through the UDOS resident service layer
- AcheronVM/AVM as the runtime image format used by `AVMRUN.PRG`

The active code paths are:

- `../udos/src/asm/udos_resident.asm`
- `../udos/tools/run_action_*.py`
- `src/tools_udos/`
- `tools/build_*_udos.sh`
- `tools/export_udos_workspace.py`

The CP/M-65 code remains in the repository only as legacy bootstrap/reference
material. It is not the primary implementation target and should not drive
feature decisions.

Legacy/reference code includes:

- `src/tools_cpm/`
- `tools/build_actc.sh`
- `tools/build_alink.sh`
- `tools/build_vmrun.sh`
- `tools/build_actmon.sh`
- `tools/cpmemu_runner.py`
- tests that launch `.COM` programs through `cpmemu`

## Active Verification Gates

Use UDOS gates as the source of truth:

```sh
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink-avmrun
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc-alink-avmrun
```

Use narrower UDOS gates when working on a specific tool:

```sh
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actadd
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-act2save
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actcopy
make -C ../udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-avmrun
```

## Development Rules

- Prefer `src/tools_udos` over `src/tools_cpm` for compiler/linker/runtime work.
- Prefer `tools/build_*_udos.sh` over CP/M `.COM` build scripts.
- Do not treat `cpmemu` success as proof that the active target works.
- Do not add new CP/M features unless explicitly maintaining historical
  bootstrap/reference behavior.
- If a CP/M-era implementation and a UDOS implementation disagree, the UDOS
  behavior is authoritative for current development.

## Current Next Work

The current practical path is:

1. Keep the UDOS external-tool ABI load/save/copy/delete/rename services stable.
2. Remove temporary probe/debug noise once permanent diagnostics cover the same
   failures.
3. Continue widening `ACTC.PRG` object emission.
4. Continue widening `ALINK.PRG` object resolution and final `AVM1` generation.
5. Keep `ACTC.PRG -> ALINK.PRG -> AVMRUN.PRG` green under UDOS.
