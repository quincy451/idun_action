# Current Blockers

The main active runtime blocker is `AVMRUN` payload-window pressure.

- The historical target is a `49152`-byte binary `AVM1` payload window.
- The current proven compat execution ceiling is `0x9EC0` (`40640`) bytes via
  `AVMRUNC.PRG`.
- The current proven production helper-safe load boundary is `0xA8B0`
  (`43184`) bytes via `AVMRUN.PRG`, below the restored high `PRINTREAL` helper
  window at `$F000`.
- Restoring a larger payload window without abandoning the current helper-family
  model is now an explicit runner-diet/layout task, not a solved contract.

## Active Path

The active runtime path is the standalone UDOS toolchain for the C64 Ultimate
environment. Work should target the UDOS resident, the `src/tools_udos/`
programs, and the host-side UDOS/Vice harnesses.

## Current Gates

Use these from `/mnt/c/test/action/udos` when validating compiler/linker
progress:

```bash
make PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc
make PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink
make PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink-compat
make PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-compat-shellmin
make PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-compat-shelladd
make PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-compat-shelladd-trace
```

Current higher-level direct and compat boundary:

- `vice-action-actc-alink-launch-printmath` is green again as the named
  direct-launch VICE gate for the imported `printmath` shape.
- `vice-action-actc-alink-compat-printmath` remains only the helper-bearing
  compat replay gate.
- `vice-action-compat-shellmin` is green as the trivial shell-launched
  `AVMRUNC -> AVM` sanity replay.
- `vice-action-compat-shelladd` is green again on the rebuilt release image
  and returns to `B:DNP/PROJ3>` under the public multi-attempt gate.
- `vice-action-compat-shelladd-trace` remains the main resident-side trace for
  this boundary.
- `vice-action-alink` is green again as the default direct-native linker gate:
  - it launches `ALINK.PRG` from the Action workspace
  - it emits `BIN/MAIN.PRG`
  - it returns to `B:DNP/PROJ3>` without routing through `MAIN.AVM` /
    `AVMRUN.PRG`

## Legacy Reference

The CP/M-65 directories and `.COM` flows are legacy/reference material only.
They are not blockers for the current UDOS-native compiler, linker, or runtime
tool work unless a future task explicitly asks to mine that code for reference.
