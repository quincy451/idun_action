# ActionC64U Language Guide

The language target is the UDOS-native ActionC64U toolchain.

Build flow:

- source files live under `SRC/`
- `ACTC.PRG` compiles source to `OBJ/`
- `ALINK.PRG` links objects and helpers to `BIN/<MODULE>.PRG`

Runtime features should be represented as language/library bindings that lower
to linker-visible helper imports. ALINK decides which helpers enter the final
PRG.
