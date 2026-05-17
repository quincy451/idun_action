# UDOS Resume

Current state after the runtime pivot:

- UDOS resident is native 6502 and builds as `udos.prg`.
- Action tools are UDOS-native PRG programs.
- `ACTC.PRG` writes project objects.
- `ALINK.PRG` writes direct linked PRG output.
- The active end-to-end proof launches `BIN/MAIN.PRG` directly under UDOS/VICE.

Useful gates:

- `make -C udos resident`
- `make -C udos vice-resident`
- `make -C udos vice-action-alink`
- `make -C udos vice-action-actc-alink-launch`

Current runtime direction:

ALINK owns the final executable image. Optional runtime families must become
link-selected helper modules, not separate launch programs.
