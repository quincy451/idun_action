# ACTDBG Native Source Debugger

Current as of `2026-07-16`.

## Active Idun/Linux Fork

The active `actdbg` is a C++ Linux process in `src/tools_linux`. Linux `actc`
emits source-file and machine-code-offset records, and Linux `alink` resolves
them into absolute `DBG1` source-line records while also emitting linked symbol
addresses. The current commands are:

- `actdbg <module>`: inspect PRG metadata and the complete debug sidecar
- `actdbg <module> symbols [filter]`: list linked symbols
- `actdbg <module> source <address>`: resolve an address to its closest source
  location
- `actdbg <module> line <line>`: resolve a root-module source line to an address
- `actdbg <module> break <line>`, `breaks`, and `clear <id>`: persist prepared
  breakpoints in `.action/debug.sqlite3`

The sidecar workflow and Linux UI are active. `actdbg <module> live` uses the
shared UDOS-free `actsvc` resident agent for target upload, register/memory
inspection, run/halt, persistent breakpoints, instruction step, stop events,
and PC samples. Real Linux client/server behavior is covered by a fake Idun
socket target; stepping and breakpoint re-arming helpers from the actual
assembled 6510 image execute under lib6502. Physical Idun/C64 transport and IRQ
timing validation remain. SQLite stays Linux-only and is not a C64 dependency.

The historical dependency audit and the transport-neutral resident-agent
design are in `docs/idun_target_service.md`. The old debugger's BRK/register
capture and direct `$DF01-$DF0A` REU snapshot core are candidates for
extraction. Its UDOS command-line, chaining, file staging, console, and
service-mediated REU shell are not. The target agent owns only machine control;
Linux owns files, symbols, source maps, UI, and databases.

Linux `actprof` uses the same protocol for bounded periodic PC sampling and
stores process/function/statement attribution in SQLite. Imported samples and
live fake-target collection are tested; instrumented counters remain optional
future work.

## Historical UDOS Debugger

The design below is retained as historical context. Its `ACTDBG.PRG`, REU
snapshots, overlays, UDOS build, and VICE workflow are not the active Idun fork
implementation or verification path.

`ACTDBG` debugs the normal native 6502 `.PRG` written by `ALINK`. It does not
run a private instruction set and it is not a runtime required by released
programs.

## Artifacts

The exported Action workspace includes:

- `ACTDBG.PRG`: resident debugger and source UI
- `ACTDBG_OVL1.BIN`: optional navigation, breakpoint, and value UI
- `ACTDBG_OVL2.BIN`: native execution and source-location controller
- `BIN/<module>.PRG`: ordinary linked C64 program
- `BIN/<module>.DBG`: linker-produced source/debug sidecar

Build the debugger with:

```sh
./tools/build_actdbg_udos.sh
```

The build script also builds both overlays under `build/udos_tools/`.

## Workflow

```text
ACTC.PRG MAIN
ALINK.PRG MAIN
ACTDBG.PRG MAIN
```

`ACTDBG.PRG BIN/MAIN.PRG` is also accepted. Running `BIN/MAIN.PRG` directly is
still the normal non-debug path and requires no debugger program or sidecar.

## Debug Records

ACTC emits source anchors in ordinary text `OBJ1` files:

- `f`: source file
- `q`: procedure declaration
- `L`: exact native machine-code offset to source location
- `V`: typed variable declaration metadata

ALINK resolves included records after final dependency closure and writes text
`DBG1` records:

- `e <address>`: linked entry address
- `m <module-id> <name>`: linked module
- `f <module-id> <file-id> <path>`: source file
- `q <module-id> <export-id> <address> <file-id> <line> <col> <name>`:
  procedure entry
- `l <module-id> <export-id> <address> <file-id> <line> <col>`: exact native
  line address
- `v ...`: typed global, parameter, or local with an absolute linked address

The sidecar is separate so release PRGs contain no debugger payload. ALINK
derives root addresses from the selected export context, so maps remain valid
for project/local/library dependency closure rather than only a single-module
proof.

## Native Execution

The execution overlay alternates debugger and target low memory through REU
snapshots while remaining in the `$A000-$BFFF` overlay window. It:

- loads the ordinary two-byte-load-address PRG
- patches temporary BRK stops into native 6502 code
- traps through the C64 BRK vector
- captures A, X, Y, P, SP, target RAM, and the output screen
- restores debugger memory before returning to the source UI
- restores patched target bytes before every stop
- tracks native JSR/RTS call depth for backtraces and step-out

The target snapshot supplies variable values after execution. Before first
execution, values are read from the staged linked PRG image.

## Controls

- `F3`: step into one native instruction
- `F4`: step over a native call
- `F5`: continue
- `F6`: step out of the current native call
- `F7`: toggle source/output view
- `RUN/STOP`: return to source view
- `B`: toggle a breakpoint at the browsed source line
- `C`: clear all breakpoints
- `L`: toggle breakpoint-list view
- `T`: toggle variable/backtrace detail
- cursor keys: browse source and scroll horizontally
- `M`: next linked procedure
- `N`: next linked source line
- `,` / `.`: previous/next linked source file
- `E`: leave ACTDBG and open the currently browsed linked source file/line in
  ACTEDIT
- `Q`: leave ACTDBG

Continue re-arms a breakpoint at the current PC by stepping over the restored
instruction once before reinstalling all user breakpoints.

## Current Coverage

The complete native-object path supports:

- break on entry and source-line breakpoints
- step into, over, and out
- continue to breakpoint or normal uDOS exit
- source/procedure lookup at absolute linked addresses
- native call-chain summaries
- typed global/parameter/local value summaries from linked addresses
- project-local and library module records in the selected link closure
- direct source-location return to ACTEDIT without a runner or debugger payload
  in the linked program

Some older ALINK specialized synthesis strategies still consume abstract body
records instead of ACTC native `L` records. Their sidecars contain a valid
entry, module, source-file, and procedure record, but cannot claim exact line
or variable addresses for code ALINK rewrote. As ACTC native object emission
replaces those strategies, the existing `L`/`V` path supplies full maps without
changing ACTDBG.

## Verification

The focused deterministic suite is:

```sh
python3 -m unittest -v tests.test_actdbg
```

It covers normal PRG loading, long sidecars, native stepping, breakpoint
re-arming, call-stack behavior, variable reads, active linked-file editor
handoff, 31-byte chain-limit rejection, and a fresh `ACTC -> ALINK -> ACTDBG`
linked-program run. The mounted-workspace VICE gate follows the full
`ACTC -> ALINK -> ACTDBG -> ACTEDIT -> UDOS` sequence. The ALINK direct-PRG
probe also rejects missing/invalid sidecars and dropped native `L`/`V` mappings.
