# Blockers

Current active blockers are direct-PRG linker and compiler capacity issues, not
runtime-runner capacity.

Open items:

- widen ACTC source streaming so large files are not tied to one contiguous RAM
  buffer
- continue moving ACTC and ALINK lookup tables toward REU-backed storage
- keep object metadata stable as language coverage expands
- widen ALINK helper selection without bloating helper-free PRG output
- reduce probe/debug noise once permanent diagnostics cover the same failures

The default proof to protect is:

`ACTC.PRG -> ALINK.PRG -> BIN/MAIN.PRG`
