# Idun C64 target service

## Decision

The Idun fork will use a small, resident C64 target service shared by the
Linux `actdbg` debugger and Linux `actprof` profiler. The service is a
hardware-control agent, not a C64 user interface or filesystem tool. Project
files, `.DBG` maps, source text, help, breakpoints, traces, and profiles stay on
Linux, where SQLite is available.

This design is implemented by `src/target_idun/action_target_service.asm`,
`action_target_protocol.*`, and `action_target_client.*`. Hardware validation
is still pending when an attached C64 is unavailable.

## Historical dependency audit

The old 6502 tools cannot be copied into the Idun build unchanged.

| Component | Historical dependency | Idun disposition |
| --- | --- | --- |
| ACTEDIT startup and exit | `svc_program_get_cmdline_*`, `svc_program_chain_sc0`, and `svc_program_exit` | Replaced by the Linux process and normal arguments/exit status |
| ACTEDIT source load/save | `svc_file_stage_reu_sc0`, `svc_file_load_sc0`, and the `svc_file_write_*` stream | Replaced by Linux filesystem I/O |
| ACTEDIT text, line index, undo, redo, and piece metadata | All REU transfers use `svc_reu_read_sc0` or `svc_reu_write_sc0`; banks 0 through 7 have fixed editor roles | Retired with the C64 editor; Linux `actedit` owns host memory and files |
| ACTDBG startup, UI handoff, and exit | `svc_program_get_cmdline_*`, `svc_program_chain_sc0`, console services, and `svc_program_exit` | Replaced by Linux `actdbg` |
| ACTDBG PRG, DBG, source, and overlay staging | `svc_file_stage_reu_sc0` plus service-mediated REU reads/writes | Replaced by Linux file parsing and target-protocol memory writes |
| ACTDBG execution core | BRK interception, CPU-state capture, stepping state, and target restoration | Extract and adapt for the resident target service |
| ACTDBG native snapshots | `actdbg_native_exec.inc` directly programs `$DF01` through `$DF0A` and triggers at `$FF00` | Reusable without UDOS; expose as an optional REU capability |

The important boundary is therefore not “6502 versus Linux.” ACTDBG contains a
useful hardware-native core surrounded by a UDOS shell. The shell must be
replaced. ACTEDIT, by contrast, uses UDOS as its filesystem, process launcher,
and REU abstraction throughout, so the Linux editor is the maintainable Idun
replacement.

The active generated C64 runtime already demonstrates the required pattern:
REU and DBF support use direct REU registers and C64 KERNAL adapters rather
than UDOS. The target service must follow the same rule.

## Ownership boundary

The C64 service owns only state that must exist next to the running 6510:

- target memory reads and writes;
- CPU register capture and restoration;
- run, halt, and single-step control;
- software-breakpoint patch bytes and stop events;
- optional direct-REU snapshots;
- optional low-overhead program-counter samples or counters reserved for
  future profiling.

Linux owns everything else:

- PRG loading and `.DBG` parsing;
- address-to-module, procedure, and source-line mapping;
- breakpoint definitions and persistence;
- source display and editor integration;
- debug session history;
- profile aggregation, reports, and SQLite storage.

No target-service request contains a host path. No target code opens a project
file, reads SQLite, chains another program, or calls a UDOS service.

## Transport and protocol

The record protocol runs over Idun's type-8 local Unix-socket device. The Linux
client creates `$XDG_RUNTIME_DIR/<pid>` and launches `actsvc` through `idunsh`;
the C64 opens `[:<pid>` and uses the raw `$DE00`/`$DE01` byte interface. Framing
remains independent of that adapter and is covered by a Linux simulator.

The service first opens the socket as an Idun tool at `$6D00`, copies its
self-contained resident image to `$C000-$CFFF`, and enters a raw-I/O command
loop. The Linux client then uploads the linked PRG in bounded memory writes.
This order matters because a target loaded at `$1000` may overwrite Idun's
kernel jump table at `$1303`.

After upload, the Linux client replaces the service process's own arguments
with the target program's Action ABI. It writes a bounded pointer table and
zero-terminated ASCII strings in `$0800-$0EFF`, then publishes 16-bit argc and
the `$0800` argv pointer at Idun's standard `$0F04-$0F07` process locations.
`argv(0)` is the Action module name. ACTDBG's `args` command or
`live -- argument ...` startup form supplies subsequent entries.

Every request and response has a fixed header containing a magic value,
protocol major/minor version, message type, sequence number, payload length,
and flags. Multi-byte values are little-endian. A checksum covers the header
and payload because a corrupted memory-write or breakpoint request is worse
than a rejected request. Responses echo the request sequence and contain an
explicit status code. Stop notifications are asynchronous event records.

The initial command surface is:

| Command | Purpose |
| --- | --- |
| `HELLO` | Negotiate protocol version, maximum payload, transport limits, and capability bits |
| `TARGET_INFO` | Report current run state/PC and the resident agent address range |
| `READ_MEMORY` / `WRITE_MEMORY` | Transfer bounded C64 address ranges |
| `READ_REGISTERS` / `WRITE_REGISTERS` | Transfer A, X, Y, SP, status, PC, and target run state |
| `HALT` / `RUN` | Stop or resume the target at a defined state boundary |
| `STEP` | Execute exactly one supported 6510 instruction, including stepping over and re-arming a breakpoint |
| `BREAK_SET` / `BREAK_CLEAR` / `BREAK_LIST` | Manage target software breakpoints and preserved instruction bytes |
| `REU_READ` / `REU_WRITE` | Optional direct-hardware REU transfers when negotiated |
| `SAMPLE_CONFIG` / `SAMPLE_READ` | Configure and drain bounded periodic PC samples for ACTPROF |
| `PING` / `RESET_SESSION` | Liveness and recovery without restarting the Linux process |

The service emits `STOPPED`, `BREAKPOINT_HIT`, `TARGET_EXIT`, and
`TARGET_FAULT` events. Events carry a stopped PC and, for a breakpoint hit, the
target breakpoint identifier. Linux obtains the complete register record with
`READ_REGISTERS` after the stop.

Capability negotiation is mandatory. Base debugging must not require an REU.
Useful capability bits include instruction stepping, writable software
breakpoints, direct REU access, cycle counters, periodic PC sampling, and
instrumented counters. `actdbg` must fail a requested operation clearly when
the service did not advertise it.

## Breakpoints and stepping

The implemented BRK path is resident-agent safe in these respects:

- reserve and report the service RAM range, while saving/restoring its `$02-$09`
  working zero-page bytes around target execution;
- preserve the original byte for every software breakpoint;
- reject low-memory, visible BASIC ROM, I/O/KERNAL, or agent patches; allow
  `$A000-$BFFF` only when the live `$01` map has banked BASIC out;
- restore the original byte on a hit and report the source location;
- preserve the captured CPU status and stack state in the register record;
- make detach restore all patched bytes before relinquishing control.

Breakpoint IDs persist after a hit. The resident service restores the original
instruction, computes a one-instruction successor, temporarily patches that
successor, executes the original, restores the temporary patch, and re-arms
the user breakpoint. `RUN` performs that step-over automatically when resuming
from a breakpoint; `STEP` exposes it directly. JSR, absolute and NMOS-indirect
JMP, RTS, RTI, conditional branches, and ordinary one/two/three-byte opcodes
are handled. BRK and all NMOS JAM/KIL opcodes are rejected instead of risking
an agent lockup. Landing on another user breakpoint remains a normal
breakpoint event.

The resident IRQ path uses the C64 KERNAL dispatcher and Idun's `$DE00/$DE01`
port. A debugged program must therefore keep KERNAL and I/O mapped while it is
running. Banking BASIC out with the normal `$36` configuration is supported;
banking out KERNAL or I/O is not an active target-service mode.

## ACTPROF use

`actprof` connects through the same handshake and session transport and does
not use debugger stop/continue loops for normal collection. Two collection
modes are defined:

1. Periodic PC sampling, with the service buffering address/count pairs and
   Linux draining them in roughly one-second halt/read/resume batches. This
   has low memory cost but perturbs IRQ timing. The service reports 20,000
   microseconds on PAL machines and 16,667 microseconds on NTSC machines from
   the C64 KERNAL video-standard flag.
2. Imported address/count samples for deterministic testing or external
   collectors. Compiler/linker-inserted counters remain a future extension.

Linux maps sampled or counted addresses through `.DBG`, aggregates by module,
procedure, source file, and line, and stores run metadata and results in
SQLite. Reports must retain unmapped addresses instead of silently discarding
them. Comparisons between runs are valid only when PRG and DBG fingerprints,
collection mode, and interval match.

The active `.action/profile.sqlite3` schema has `profile_runs` and
`profile_samples` keyed by run and ALINK build fingerprint. Function and
statement metadata is copied from `.action/code-map.sqlite3`; it never occupies
C64 memory.

## Implementation status

Implemented: UDOS-free service ABI, binary framing/checksums, protocol
simulator, target upload, bounded memory/register access, IRQ run/halt,
instruction stepping, eight persistent software-breakpoint slots,
stop/exit/fault events, 100-entry PC sample batches, ACTDBG source integration,
ACTPROF full-duration SQLite aggregation, unsafe PRG/patch rejection, and
best-effort session reset that restores breakpoint bytes before a graceful
socket detach. A fake Idun socket target drives both Linux tools end-to-end,
and a lib6502 harness executes helper routines extracted from the actual
assembled resident image.

The assembled resident image is 3,970 bytes at `$C000-$CF81`; the complete
tool, including its `$6D00` socket loader, is 4,173 bytes. `$C000-$CFFF`
is reserved and enforced by both target and host overlap checks.

The 2026-07-17 attached-hardware attempt reached the platform boundary but not
the IDBG handshake. The Ultimate's conflicting SwiftLink `$DE00`, command
interface, REU, and turbo settings were corrected and persisted. The Pi then
successfully flashed `init.binary` and selected `idun64.binary`, but cartridge
reset failed with `i2c write failed`; I2C bus 1 exposed no control device, the
C64 stayed at BASIC, and even the stock `idunsh -o drives` preflight timed out.
That is a cartridge-control hardware/power/connection blocker rather than an
`actsvc` protocol failure.

Remaining after that platform connection is restored: attached IDBG transport,
IRQ timing, persistent-breakpoint/step, and profiler-sampling validation, plus
optional direct-REU acceleration.
