# Linux Tool Port Status

This is the authoritative process-conversion inventory for the Idun fork.
Every build-time or workspace command runs as a normal Linux process. Generated
programs and their selected runtime helpers remain native 6502 code.

| Historical command | Idun/Linux command | Status |
| --- | --- | --- |
| ACTC | `actc` | Native C++ compiler; current-directory source writes a sibling `.OBJ`, otherwise uses project `SRC/OBJ` |
| ALINK | `alink` | Native C++ linker; writes sibling or project `BIN` C64 `PRG`/`DBG` output and atomically rebuilds the SQLite semantic code map |
| ACTEDIT | `actedit` | Current-file-first highlighted terminal editor with a high-visibility cursor, F1-F4 help/reference, F5 definitions, F6 formatting, F7 references, internal block clipboard, Ctrl-click navigation, history, scripted edits, and compile/build/debug workflow |
| New Linux support command | `actspc` | Atomic, idempotent Action indentation/spacing formatter for files and wildcard sets |
| New Linux support command | `acthelp` | Exact/list/search access to the external language, builtin, constant, and library catalog |
| ACTDBG | `actdbg` + `actsvc` | Linux source/debug console plus a resident, UDOS-free Idun C64 service for target upload, registers, memory, run/halt, instruction step, persistent software breakpoints, events, and PC samples |
| New Linux support command | `actprof` | Imported or live sampled profiling, attributed by process/function/statement and persisted in SQLite |
| ACTMON | `actmon` | Project status plus edit/compile/build/debug dispatch |
| ACTNEW, ACTADD | `actnew`, `actadd` | Project and module creation |
| ACTWORK, ACTSRC, ACTFILE, ACTCHK | same lowercase names | Project inspection and validation |
| ACTDIR, ACTCOPY, ACTDEL | same lowercase names | Host filesystem operations |
| ACTMKDIR, ACTRMDIR | same lowercase names | Host directory operations |
| ACTMOVE / ACTREN | `actmove` / `actren` | Shared host move implementation |
| ACTWRITE, ACTINFO | same lowercase names | Host write and tool information |
| TREE.OVL / ACTTREE | `tree` / `acttree` | Recursive host tree listing |
| XCOPY.OVL | `xcopy` | Recursive host copy with self-copy protection |
| DELTREE.OVL | `deltree` | Recursive host deletion with root/current/ancestor protection |
| ACT2SAVE / ACTSAVE | `act2save` / `actsave` | Compatibility aliases for `alink` |

`STAGEINFO` is not an unfinished port. Its 6502 source was deleted with the
retired AVM runner path; only an orphan historical linker configuration remains.
Its old REU staging diagnostics have no role in a Linux filesystem workflow.

The multicall sources are under `src/tools_linux/`; the target service is
`src/target_idun/action_target_service.asm`.
`tools/build_linux_tools.sh` creates one executable and the command-name
symlinks listed above. `tools/export_idun_workspace.py` installs those
executables with only active standalone 6502 runtime objects, plus the external
help database under `DOC/`, flat examples under `PLAYGROUND/`, and a user-level
installer for `$HOME/.local/bin`. Preserved `src/tools_udos/` sources are
retired and are excluded from every active build/test/export entry point.
