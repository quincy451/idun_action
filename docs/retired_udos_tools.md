# Retired UDOS tools

All sources below `src/tools_udos/` are formally retired for this Idun/Linux
fork. They are preserved in place as historical implementation material and
to avoid destroying unfinished work, but no active build, test, export, or
release step may consume them.

The machine-readable inventory is
`resources/retired_udos_tools.json`. It maps every preserved legacy directory
to its active Linux replacement. In particular:

- the old 6502 `ACTEDIT` is replaced entirely by Linux `actedit`;
- the old 6502 `ACTC` and `ALINK` are replaced entirely by Linux `actc` and
  `alink`;
- the old `ACTDBG` user interface and UDOS shell are replaced by Linux
  `actdbg`; only hardware-control responsibilities remain on the C64, in the
  new UDOS-free Idun service `src/target_idun/action_target_service.asm`;
- old project and filesystem commands are replaced by their Linux multicall
  implementations;
- `stageinfo` has no active replacement because its old staging role is not
  part of the Linux filesystem workflow.

Retired sources are not compatibility fallbacks. A missing feature in an
active Linux command must be implemented in `src/tools_linux/`, a standalone
link-selected runtime module, or the Idun target service as appropriate.
