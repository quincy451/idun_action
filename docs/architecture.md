# Architecture

ActionC64U now targets the Idun cartridge Linux environment.

Active flow:

- Linux `actc` compiles the historical Action language surface in
  `SRC/<MODULE>.ACT` into
  `OBJ/<MODULE>.OBJ`, including direct string/integer output and compile-time
  constant branch stripping. The dynamic path emits initialized or
  address-bound `BYTE`/`CARD`/`INT`/`REAL` storage, recursive word and REAL
  expressions, signed or unsigned word comparisons, REAL comparisons, and
  absolute-label structured control flow. It imports helpers such as
  `RT_I_MUL`, `RT_I_DIV`, `RT_PRINT_I`, and selected `RT_F_*` conversion or
  arithmetic objects only when referenced.
- BYTE/CARD/INT/REAL arrays, length-prefixed BYTE strings, typed pointers,
  local routine parameters, and BYTE/CARD/INT/REAL function returns lower to
  ordinary linked storage, register results, and indirect 6502 operations.
  Calls on direct or mutual recursion cycles preserve live local frames and
  stage typed results across frame restoration.
  Linux-side syntax trees and metadata remain dynamically sized; target storage
  is constrained by the C64 address space.
- REU declarations and 8/16-bit accesses lower to direct hardware helpers.
  ALINK selects allocation, state, bounds-resolution, and transfer objects only
  for programs that use REU source forms.
- Overlay bodies are program-owned code sections in the ordinary object and
  PRG. Calls are local relocations; no runtime host or overlay loader is needed
  for the active resident form.
- DBF calls lower to link-selected 6502 database modules. A private REU handle
  stores the staged image, while direct C64 KERNAL adapters load and save files
  on device 8; no fixed UDOS service addresses remain in the linked closure.
- Linux `alink` resolves the object closure and emits `BIN/<MODULE>.PRG` plus
  debug sidecars. OBJ source-file and line records become absolute linked line
  records, and linked source objects contribute symbol-address records. It
  searches project `OBJ`/`LIB` directories and the shared `LIB` directory
  beside an Idun project.
- Linux `actedit` rebuilds project source and symbol indexes transactionally in
  `.action/workspace.sqlite3`; ALINK rebuilds `.action/code-map.sqlite3` for
  definition/reference navigation. Linux `actdbg` resolves addresses, source
  lines, and linked symbols from the sidecar and stores prepared breakpoints in
  `.action/debug.sqlite3`; `actprof` stores attributed runs in
  `.action/profile.sqlite3`. These databases are host-side workspace state and
  are not part of the C64 PRG or its runtime closure.
- The shared UDOS-free C64 resident service supplies bounded memory/register
  access, IRQ halt/run, instruction stepping, persistent software breakpoints,
  and bounded PC sampling to ACTDBG/ACTPROF over the Idun socket transport.
- The Idun cartridge launches `.PRG` output as a Commodore 64 program.

The linked `.PRG` must contain its entry path, selected 6502 runtime helpers,
and all program-owned code/data needed for execution. UDOS is not a runtime host
or build-time service layer for this fork.
