# `ACTDBG` Source-Level Debugging Roadmap

Current as of `2026-04-24`.

This document defines the intended source-level debugging direction for the
UDOS-native Action toolchain.

It exists because source debugging is not a small add-on. It changes:

- `ACTC` object emission
- `ALINK` link output and map generation
- runtime/debug execution strategy
- editor/debugger integration

## Goal

Provide a real source-level debugger for linked Action programs without forcing
normal `.AVM` programs to carry permanent debug payload overhead.

The debugger target is:

- set breakpoints by source line
- run / break / continue
- step into / step over / step out
- stack trace by procedure name
- inspect globals, parameters, and locals by source name
- show the current source line and current module/procedure context

## Current Baseline

Today the repo has:

- `ACTC.PRG` emitting text `AVO1` objects
- `ACTC.PRG` now emitting the first debug-oriented `AVO1` records:
  - `f 0 src/<module>.act`
  - `q <export_index> 0 <line> <col>`
  - `l <export_index> <body_op_index> 0 <line> <col>`
  - `V g <type> <var_index> <file_id> <line> <col>`
  - `V p <type> <export_index> <var_index> <file_id> <line> <col>`
  - `V l <type> <export_index> <var_index> <file_id> <line> <col>`
- `ALINK.PRG` linking text `AVO1` objects into `AVM1`
- production `ALINK.PRG` now emitting the first text `DBG1` sidecar bootstrap:
  - `m <module_id> <module_name>`
  - `f <module_id> <file_id> <path>`
  - `q <module_id> <export_index> <entry_pc> <file_id> <line> <col> <proc_name>`
  - `l <module_id> <export_index> <pc> <file_id> <line> <col>`
  - `v g <type> <module_id> <var_index> <addr> <width> <file_id> <line> <col> <name>`
  - `v p <type> <module_id> <export_index> <var_index> <addr> <width> <file_id> <line> <col> <name>`
  - `v l <type> <module_id> <export_index> <var_index> <addr> <width> <file_id> <line> <col> <name>`
- `ACTDBG.PRG` bootstrap debugger slice that:
  - loads `BIN/<NAME>.AVM` plus `BIN/<NAME>.DBG`
  - resolves the first source file and first stop location
  - renders a source-centered full-screen debugger view
  - shows the current linked proc name in the title row
  - shows a compact `BT:` row with the current proc plus caller chain from the
    interpreter return stack and linked `q` proc-name metadata
  - supports `T` to swap the bottom three rows between variable summaries and
    detailed frame rows such as `0: SUB $0006` and `1: MAIN $0003`
  - supports arrow-key source browsing while stopped:
    - up/down move a separate source cursor
    - left/right apply horizontal source scroll
    - `,` / `.` jump across linked source files
    - `B` now toggles a breakpoint on that browsed cursor line, not only the
      live stop line
    - `L` swaps in the current breakpoint list view
  - consumes linked `v g` / `v p` / `v l` records and shows current-module
    globals, parameters, and locals in fixed summary rows
  - currently decodes `BYTE`, `CARD`, `INT`, and practical-range `REAL`
    values numerically from linked type tags
  - currently falls back to raw `$XXXXXXXX` bits only when a `REAL` value is
    outside the compact formatter's supported range
  - stages the linked `.AVM`, `.DBG`, and source file into REU and keeps only
    small header/window buffers resident while interpreting and rendering
  - breaks on entry
  - supports `F3` single-instruction step, `F4` step over, `F5` continue,
    and `F6` step out on the current interpreted path
  - supports `B` to toggle a breakpoint on the current source line
  - supports cursor-based source browsing with up/down/left/right while stopped
  - stops on those current-line breakpoints during `F5` continue and returns to
    source view when one hits
  - tracks current `pc` back to source lines while running that interpreted
    subset
  - keeps the clean program-output screen as a REU-backed image instead of a
    resident 1 KB shadow buffer
  - now moves the optional detail/list/jump UI slice plus stop-summary rebuild,
    variable-summary rendering, and source-line breakpoint toggle/lookup into
    `ACTDBG_OVL1.BIN`,
    staged into REU and executed at `$A000` on demand for:
    - `T` detail view
    - `L` breakpoint-list view
    - `M` next-proc jump
    - `N` next-line jump
    - `,` / `.` source-file jumps
    - stop-summary rebuild after location changes
    - live summary-row drawing in normal source view
  - now moves the debugger-owned execution engine plus AVM/bootstrap and
    PC-to-line lookup work into `ACTDBG_OVL2.BIN`, also staged into REU and
    executed at `$A000` on demand
  - toggles source/output with `F7`
  - forces source view with `RUN/STOP`
- current `ACTDBG` bootstrap footprint:
  - `ACTDBG.PRG`: `9141` bytes
  - `ACTDBG_OVL1.BIN`: `2874` bytes
  - `ACTDBG_OVL2.BIN`: `3160` bytes
  - resident span: `$0900-$2CB2`
  - resident `CODE`: `$23B3`
  - resident `ZPTEMP`: `$001F`
- `AVMRUN.PRG` running linked `AVM1`
- `ACTMON.PRG` as the first monitor-style Action front end
- no command-driven or conditional breakpoint system yet

## Core Decision

Debug data should be a sidecar artifact, not part of the normal runnable
program image.

That means:

- normal `BIN/<NAME>.AVM` stays lean
- debug data is written separately
- the debugger loads both the `.AVM` and the debug sidecar
- `AVMRUN.PRG` stays focused on normal execution

Planned debugger artifact:

- `BIN/<NAME>.DBG`

Planned debugger tool:

- `ACTDBG.PRG`

## Data Flow

Planned flow:

1. `ACTC` emits normal object code/data plus source debug records.
2. `ALINK` merges object debug records while it lays out final code/data.
3. `ALINK` writes:
   - `BIN/<NAME>.AVM`
   - `BIN/<NAME>.DBG`
4. `ACTDBG.PRG` loads both files, renders source context from `DBG1`, and then
   grows into a debug-aware runtime path.

## Compiler Responsibility

`ACTC` should emit debug data at the object level, before final addresses are
known.

The natural object-level anchors are:

- source file id
- source line and column
- module name
- procedure/export index
- body-op index inside a procedure
- variable slot metadata

The compiler should not try to guess final linked addresses.

### Planned `AVO1` Debug Records

During bootstrap, the easiest path is to extend the current text object format
with additional debug lines instead of inventing a second object container.

Planned record family:

- `f <file_id> <path>`
  - source file table
- `q <export_index> <file_id> <line> <col>`
  - procedure declaration site
- `l <export_index> <body_op_index> <file_id> <line> <col>`
  - statement/line mapping keyed to compiler body-op order
- `V g <type> <var_index> <file_id> <line> <col>`
  - global/module variable declaration site, keyed to the existing object var
    index so ALINK can recover width and final linked address without bloating
    the object format
- `V p <type> <export_index> <var_index> <file_id> <line> <col>`
  - procedure parameter declaration site, keyed to the owning export plus the
    existing object var index
- `V l <type> <export_index> <var_index> <file_id> <line> <col>`
  - procedure local declaration site, keyed to the owning export plus the
    existing object var index

Planned scope codes:

- `g` global/module var
- `p` proc parameter
- `l` proc local

This keeps the compiler aligned with how it already thinks about the program:

- exports
- body ops
- variable slots

Bootstrap status:

- landed:
  - `f 0 src/<module>.act`
  - `q` procedure declaration source sites
  - `l` body-op to source-line mappings
  - typed `V g` module/global declaration source sites
  - typed `V p` procedure parameter declaration source sites
  - typed `V l` procedure local declaration source sites
  - first `ALINK` text `DBG1` sidecar with linked procedure-entry `q` records
    including proc names, plus linked-PC `l` line mappings
  - typed linked global/parameter/local `DBG1` variable records:
    `v g <type> <module_id> <var_index> <addr> <width> <file_id> <line> <col> <name>`
    `v p <type> <module_id> <export_index> <var_index> <addr> <width> <file_id> <line> <col> <name>`
    `v l <type> <module_id> <export_index> <var_index> <addr> <width> <file_id> <line> <col> <name>`
  - `ACTDBG` consumption of linked `v g` / `v p` / `v l` records for live
    summary rows, with numeric `BYTE` / `CARD` / `INT` display and compact
    numeric `REAL` display plus raw-bit fallback for out-of-range values
- `ACTDBG` debugger-owned interpreted runtime:
  - stages the linked `.AVM`, `.DBG`, and source file into REU
  - breaks on entry
  - supports `F3` step / `F5` continue
  - supports `B` current-line breakpoint toggles
  - maps current `pc` back to source lines while running
- still pending:
- `ACTDBG` live-value and richer breakpoint work
  - widen the debugger-owned interpreted runtime toward the full current
    `AVMRUN` subset
  - richer procedure/frame/range records if the debugger needs them

## Linker Responsibility

`ALINK` is the tool that knows final addresses, so it is where source records
become executable debug records.

Planned linker work:

- read compiler debug lines from every included object
- carry them only for reachable code/data
- convert body-op-index mappings into final `AVM` program counters
- resolve final global variable addresses
- emit final per-procedure ranges
- emit sidecar `DBG` output

This is the main way source debugging expands the linker.

### Planned `DBG1` Sidecar Contents

First practical version:

- header:
  - magic `DBG1`
  - version
  - linked module name
- source file table
- procedure table:
  - name
  - module
  - entry pc
  - end pc
  - declaration source location
- line table:
  - pc -> file/line/column
- global variable table:
  - current bootstrap records:
    `v g <type> <module_id> <var_index> <addr> <width> <file_id> <line> <col> <name>`
    `v p <type> <module_id> <export_index> <var_index> <addr> <width> <file_id> <line> <col> <name>`
    `v l <type> <module_id> <export_index> <var_index> <addr> <width> <file_id> <line> <col> <name>`
  - linked address
  - width
  - declaration location
- proc param/local table:
  - proc id
  - linked var index in the bootstrap text form
  - width/type
  - name
  - declaration location

Bootstrap choice:

- start with text `DBG1` if inspection/debugging speed matters more than file
  size
- move to compact binary `DBG1` later if load cost becomes a real problem

The key requirement is not text vs binary. The key requirement is that the
debugger can load it into REU and query it cheaply.

## Runtime / Debugger Split

Normal execution and debug execution should be separate tools.

Planned split:

- `AVMRUN.PRG`
  - normal execution
  - no required debug sidecar
- `ACTDBG.PRG`
  - debug execution
  - loads `.AVM` plus `.DBG`
  - adds breakpoint/step/inspection behavior

That avoids burdening every runtime path with debugger machinery.

## Why `ACTDBG` Can Be Source-Level

`AVMRUN` is an interpreter. That is useful here.

The debugger does not need machine-code single-step support first. It can:

- stop before executing the next `AVM` instruction
- look up current `pc` in the line table
- compare call depth for step over/out
- map variable names to linked addresses or frame slots

That is much simpler than trying to retrofit source debugging onto native code.

## Planned Debug Features By Phase

### Phase 1

- `ACTC` emits file/proc/line/global-var debug records
- `ALINK` writes `BIN/<NAME>.DBG`
- `ACTDBG.PRG` supports:
  - launch under debugger
  - break on entry
  - continue
  - breakpoint by source line
  - current source line display
  - stack trace by procedure name
  - inspect global variables

### Phase 2

- parameter/local debug records become usable
- debugger supports:
  - step into
  - step over
  - step out
  - inspect params/locals in current frame
  - breakpoint by proc name

### Phase 3

- richer line fidelity for multi-statement lines
- watches
- conditional breakpoints
- better mixed map/debug output
- debugger/editor handoff to the current source line

## Planned `ACTMON` Integration

`ACTMON` should become the front-end entry point, not the debugger itself.

Planned commands:

- `ACTMON DEBUG <NAME>`
- `ACTMON TRACE <NAME>`

Those should dispatch to `ACTDBG.PRG`, the same way other project operations are
dispatched through one front end now.

## Interaction With The Future Editor

Source debugging gets much better once an editor exists.

Planned later integration:

- debugger opens the current module/line in the editor
- editor launches debugger on current module
- editor can place/remove breakpoints in source view

This is why debugger and editor planning must be consistent now, before the file
formats harden.

## Non-Goals For The First Debugger Slice

- no debug payload inside normal `.AVM`
- no watch-expression evaluator in phase 1
- no mixed machine-code/source debugger in phase 1
- no requirement that `AVMRUN.PRG` itself become the debugger

## Practical Next Implementation Steps

1. extend `ACTC` object emission with source file/proc/line/global-var debug
   records
2. extend `ALINK` to preserve and merge those records into `BIN/<NAME>.DBG`
3. add a narrow harness proof that linked debug sidecars match final procedure
   ranges and source lines
4. build the first `ACTDBG.PRG` slice around break-on-entry, continue, line
   lookup, and global inspection
