# Current Blockers

No local UDOS-native blocker is recorded right now.

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
make PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink-avmrun
make PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc-alink-avmrun
```

## Legacy Reference

The CP/M-65 directories and `.COM` flows are legacy/reference material only.
They are not blockers for the current UDOS-native compiler, linker, or runtime
tool work unless a future task explicitly asks to mine that code for reference.
