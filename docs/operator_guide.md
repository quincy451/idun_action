# Operator Guide

Current Idun/Linux workflow:

1. Build Linux tools with `bash tools/build_linux_tools.sh`. Run
   `make install-user` (or the export's `./install-user.sh`) once to expose all
   Linux commands under `$HOME/.local/bin`; run `hash -r` in an existing Bash
   session.
2. Create a project with `build/linux_tools/actnew <project>`.
3. Put source in `<project>/SRC/<MODULE>.ACT`.
4. Use `actadd`, `actwork`, `actsrc`, `actfile`, and `actchk` inside the project
   for workspace management.
5. Run `actspc <file-or-filespec> [...]` to format Action sources in place.
   It accepts ordinary files, shell-expanded lists, and quoted wildcards such
   as `actspc '*.act'` or `actspc 'SRC/*.act'`. Matching is deterministic and
   treats the `.act` extension case-insensitively. ACTSPC validates all
   filespecs first, writes changed files atomically, preserves permissions and
   strings/comment text, and reports unchanged files without rewriting them.
6. Use Linux `actc` and `alink` to write `OBJ/<MODULE>.OBJ` and
   `BIN/<MODULE>.PRG`. A successful link also writes
   `.action/code-map.sqlite3` transactionally.
   For flat use, put `<MODULE>.ACT` directly in the invocation directory.
   That local file takes precedence and ACTC/ALINK keep `.OBJ`, `.PRG`, and
   `.DBG` outputs in the same directory. The exported `PLAYGROUND/` is ready
   for this workflow. With no local module, commands search upward for
   `ACTION.PROJ`; `ACTION_PROJECT` can select one explicitly.
7. Use `actedit <module> index`, `actedit <module> find <text>`, and
   `actedit <module> symbols` for project source navigation. The rebuildable
   index is stored in `.action/workspace.sqlite3`. In the terminal editor, F1
   opens contextual keyword/library help, F2 opens a complete editor-command
   reference, F3 browses every cataloged language feature, and F4 browses
   libraries, their features, and an example for each feature. F5 goes to a
   definition, F6 applies ACTSPC formatting to the current unsaved buffer, F7
   selects a reference, F8 opens ACTSPRITE or ACTBITMAP for the RESOURCE
   declaration on the cursor line, and Alt-left/right traverses
   navigation history, and Ctrl-click goes to a definition. The current cursor
   cell uses inverse video under a blinking block. Run `actedit <module>` for
   ACTEDIT's own uncolored
   terminal mode, suitable for a C64 display, or add `tui` to enable syntax
   highlighting. ACTEDIT never launches `$EDITOR` or another external editor.
   `compile`, `build`, and `debug` modes drive the matching workflows. As with
   ACTC, a same-named `.ACT` file in the invocation directory wins over
   `SRC/<MODULE>.ACT`.
   `PLAYGROUND/PRIME_REAL.ACT` demonstrates REAL square-root prime testing;
   `PLAYGROUND/REU_DBF_SORT.ACT` demonstrates stable in-place DBF sorting with
   one through ten command-line `START,LENGTH,A|D` keys and an REU-backed
   record swap buffer. `PLAYGROUND/ASMBLOCK_DEMO.ACT` demonstrates scoped 6502
   assembly and local labels.

   Block text operations are internal to ACTEDIT and persist for the current
   editor session. Ctrl-B sets or clears an anchor; cursor movement extends the
   selection. Ctrl-A selects the whole buffer, Ctrl-C copies, Ctrl-X cuts, and
   Ctrl-V pastes. Typing, Backspace, or Delete replaces/removes a selection;
   Escape clears it without changing text. A left-button drag creates the same
   kind of selection, while Ctrl-click remains definition lookup. F6 formats
   the in-memory buffer and marks it dirty; Ctrl-S is still required to save.
   Graphics declarations use `SPRITE|MSPRITE|BITMAP|MBITMAP name=RESOURCE
   "file"`; F8 creates a missing asset under project `RES/`. In the graphics
   editor, arrows move, Space or 0-3 paints, C clears, Ctrl-S saves, and Ctrl-Q
   exits. The same editors are available directly as `actsprite` and
   `actbitmap`. See `docs/new_gfx_func.txt` for formats and the GFX1 API.
8. Use `actdbg <module> source <address>`, `line <line>`, or `symbols [filter]`
   to inspect linked source information. `break <line>`, `breaks`, and
   `clear <id>` manage prepared breakpoints in `.action/debug.sqlite3`. Run
   `actdbg <module> live` for the Idun session console; `help` lists live
   register, memory, run/halt, breakpoint, event, and sampling commands.
   While the target is running, use `wait` for events or `halt` before issuing
   any memory, register, breakpoint, or sampling command. A parameterized
   Action `MAIN` receives target arguments with
   `actdbg <module> live -- argument ...`; inside an existing live console,
   use `args argument ...` before `run`. `argc` includes the module name.
9. Run `actprof <module> live [seconds]` for Idun PC sampling. For repeatable
   offline analysis, use `import <sample-file> [interval-us]` and
   `report [run-id]`. Profiles are stored in `.action/profile.sqlite3` and are
   attributed through ALINK's code map.
10. The live commands launch `TOOLS/actsvc` on the C64 through `idunsh`; the
   Linux client uploads `BIN/<MODULE>.PRG` only after the service has relocated
   outside the target image. Uploads below `$0200`, into the resident service,
   or beyond `$CFFF` are rejected before target memory is changed.

`actmon edit|compile|build|debug <module>` provides the same integrated
project workflow from the Linux monitor command.

The linked `.PRG` is the final runnable C64 program. Build tools are Linux
processes and must not rely on UDOS command chaining or UDOS service calls.
The target supports IRQ-based run/halt, persistent software breakpoints,
instruction `step`, and periodic PC samples. A breakpoint hit restores its
instruction, then step-over (explicitly or as part of `run`) executes it once
and reinstalls the patch. These paths are simulator- and assembled-6510-harness
tested; physical Idun transport validation remains. ACTPROF drains the
100-address target buffer in roughly one-second halt/read/resume batches and
records the PAL or NTSC sampling interval reported by the C64.

## Attached Idun/C64 Ultimate preflight

Before using either live command, verify the C64 Ultimate settings supplied in
`/usr/share/idun/Idun_c64u_run_first.cfg`. In particular, Idun requires:

- `Turbo Control = C64U Turbo Registers`, CPU speed `8`, badline timing
  enabled, and `SuperCPU Detect (D0BC)` enabled;
- the Ultimate command interface and REU disabled; and
- the SwiftLink/ACIA mapping disabled. An ACIA at `$DE00` directly collides
  with Idun's data port.

The Idun cartridge mode switch must select the C64 firmware
(`idun64.binary`). With a healthy cartridge, this preflight must complete
before ACTDBG is started:

```sh
timeout 15 idunsh -o drives
```

If the C64 remains at BASIC and that command times out, the failure is below
`actsvc`; do not diagnose the debugger protocol yet. Restarting `cartmon` in
the foreground should show a successful `init.binary` download followed by an
`idun64.binary` download for a C64 reboot. If it instead reports
`i2c write failed` and `sudo i2cdetect -y 1` finds no cartridge control device,
power down safely and reseat or power-cycle the cartridge control connection.
Linux cannot assert the required cartridge/C64 state while that I2C device is
absent.
