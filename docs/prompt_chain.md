# Prompt Chain Archive

ActionC64U was originally bootstrapped through `prompt-1.txt` through
`prompt-18.txt` from the workspace root. Those prompt files are historical
inputs, not the active implementation workflow.

Do not replay the prompt chain to continue current development. Continue from
the checked-out source tree, current status docs, and active UDOS verification
gates.

## Active Workflow

From the workspace root:

```sh
make test
```

For end-to-end UDOS/VICE validation:

```sh
make -C udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc
make -C udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink
make -C udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc-alink-launch
make -C udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-alink-prg-object-code-matrices
make -C udos PROOF_DEPS= RESIDENT_DEPS= RELEASE_DEPS= vice-action-actc-alink-launch-runtime-matrices
```

## Active Target

The maintained tool path is:

```text
ACTC.PRG -> OBJ/<MODULE>.OBJ -> ALINK.PRG -> BIN/<MODULE>.PRG
```

The linked output is a direct 6502 `.PRG`; there is no separate runtime runner.
Runtime families are link-selected `RT_*.OBJ` modules included only when
reachable code imports them.

## Repo Guidance

Use these current docs instead:

- [AGENTS.md](../AGENTS.md)
- [README.md](../README.md)
- [active_direction.md](active_direction.md)
- [actc_status.md](actc_status.md)
- [alink_status.md](alink_status.md)
