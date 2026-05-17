# Linker

The active linker is `ALINK.PRG`.

Current contract:

- input: project/library object closure
- output: `BIN/<MODULE>.PRG`
- policy: ALINK decides all code/data/helper content required by the final
  launchable program

A separate runtime host is not part of the maintained linker product.
