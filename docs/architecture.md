# Architecture

ActionC64U is now a UDOS-native Action-style toolchain.

Active flow:

- `ACTC.PRG` compiles source into `OBJ/*.OBJ` object files.
- `ALINK.PRG` resolves the object closure and emits `BIN/<MODULE>.PRG`.
- UDOS launches the linked PRG directly.

The linked PRG must contain the entry path, selected runtime helpers, and all
program-owned code/data needed for execution. A separate runtime host is not
part of the maintained architecture.
