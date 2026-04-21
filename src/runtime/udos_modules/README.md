# UDOS Runtime AVO Modules

This directory contains target-side text `AVO1` runtime modules that UDOS
`ALINK.PRG` can parse from `LIB/`.

The sibling `src/runtime/modules/` directory is the host/reference JSON-style AVO
format used by the Python linker. Keep the two formats separate until the host
and UDOS object readers converge.

Current status:

- `rt_f_add.avo` is a partial REAL add helper. It preserves the current stack
  contract and implements the exact right-hand zero identity case:
  `x + +0.0 = x`. Other inputs still return REAL32 zero, so it is not the final
  IEEE-754 addition implementation.
