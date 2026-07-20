# Linker

The active linker target is Linux `alink`.

Current contract:

- input: project/library object closure
- output: `BIN/<MODULE>.PRG`
- debug output: `BIN/<MODULE>.DBG` when source/debug records are available
- policy: `alink` decides all code/data/helper content required by the final
  C64 program

`alink` runs as a Linux process on the Idun cartridge. Its product remains a
Commodore 64 `.PRG`, not a Linux executable. Former UDOS services needed by the
final program must be represented as link-selected 6502 helper modules.

The active Idun export includes standalone `RT_PRINT_I.OBJ`, `RT_I_MUL.OBJ`,
and `RT_I_DIV.OBJ` 6502 helpers. `RT_PRINT_I` formats the signed 16-bit value
passed in `A`/`X` and uses C64 KERNAL `CHROUT`. The arithmetic helpers take the
left word in `A`/`X`, read the right word through zero-page pointer `$02/$03`,
and return the low 16-bit result in `A`/`X`. None calls a resident service.

For an Idun workspace containing `LIB/` and a project subdirectory, `alink`
searches both `<project>/LIB` and the workspace-level `LIB`. This keeps runtime
objects shared instead of copying them into every project.

The complete active `GFX1` family uses the documented `A`/`X`/`Y` register ABI
and accesses C64 memory and VIC-II registers directly; it has no UDOS import.

The active `INPUT1` closure consists of native joystick/mouse code and linked
state objects (`RT_JS` and `RT_MS`). Calls such as `JoySeen` and `MouseBtn1`
pull that state and their lower-level helpers through ordinary object imports;
no input code is included when the program does not reference it.

The active SID/sprite modules similarly access SID and VIC-II registers
directly. `RT_SID_STATE`, `RT_SID_FILTER_STATE`, and `RT_SID_VOLUME_STATE` are
ordinary linked data exports selected transitively by helpers that need safe
shadow state for write-only control registers.

`alink` validates export and relocation ranges, rejects duplicate exports,
requires `MAIN` to be the first byte of the root object, and rejects the old
JSON runtime placeholders whose payload is only an ASCII helper name. Dotted
imports still map to underscore filenames, but a helper must contain executable
6502 code before it can enter an Idun export.

OBJ1 relocations may patch a normal little-endian word or one selected low/high
address byte. The byte forms are emitted by ASMBLOCK for `#<symbol` and
`#>symbol`; dependency closure and range validation apply exactly as they do to
word relocations.
