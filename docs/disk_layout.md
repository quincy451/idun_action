# Idun Workspace Layout

The historical disk-image layout is not used by this fork. The active native
Linux workspace is:

- `TOOLS/`: Linux compiler, linker, editor, debugger front end, and project tools
- `SRC/`: Action source files
- `PLAYGROUND/`: flat example copies for current-directory compile/link testing
- `OBJ/`: compiler object files
- `BIN/`: linked C64 `.PRG` files and `.DBG` sidecars
- `LIB/`: Action interfaces plus standalone 6502 runtime objects
- `DOC/`: generated operator and runtime-status notes

The tools support both layouts. If the invocation directory contains
`<MODULE>.ACT`, ACTC reads it and writes `<MODULE>.OBJ` beside it; ALINK reads
that object and writes `<MODULE>.PRG` and `<MODULE>.DBG` beside it. Otherwise,
the nearest `ACTION.PROJ` selects the structured `SRC/OBJ/BIN` directories.
This rule prevents an installed command from silently ignoring a same-named
file in the current directory.

There is no `UDOSDIR.TXT` catalog. Linux filesystem APIs provide directory
and file operations directly. The maintained runnable target artifact remains
`BIN/<MODULE>.PRG`, or `<MODULE>.PRG` in flat mode.
