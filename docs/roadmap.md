# Roadmap

Current roadmap:

1. Keep UDOS resident and Action tools building cleanly.
2. Widen ACTC source coverage and object emission.
3. Widen ALINK object closure resolution and direct PRG generation.
4. Convert optional runtime features into link-selected helper modules.
5. Keep direct PRG VICE gates green.

Retired roadmap items for CP/M-era runner flows are no longer maintained.

## 2026-07-09

- Added native `XCOPY.OVL` as a validated `UDOV` command module selected by the
  UDOS resident from the parsed `XCOPY` token.
- Added bounded recursive VICE tree copy through the fixed directory and file
  Tool ABI, including nested-path resolution and immediate release of transient
  file-cache slots after host persistence.
- Added release export/container checks and focused valid, invalid-module, and
  flat-image VICE gates; the valid gate copies eleven files over three levels.
- Added native `DELTREE.OVL` as command ID `22`, with bounded post-order VICE
  tree removal and preflight protection for the current directory and roots.
- Generalized Tool ABI directory removal to nested paths, persisted directory
  manifests safely across resident restore, and released transient host-delete
  cache slots so one invocation can exceed six files.
- Added release export/container checks plus valid, invalid-module, flat-image,
  and current-directory safety VICE gates; the valid gate removes eleven files
  and three directories.

## 2026-07-10

- Replaced the VICE tree backend's 255-byte `UDOSDIR.TXT` rewrite window with a
  line-streamed temporary catalog and deterministic copy-back path.
- Added first-catalog creation, unterminated-final-line handling, and exact
  oversized-catalog preservation across shell and Action Tool ABI mutations.
- Corrected VICE deferred file-not-found detection so newly created Action files
  retain live host state and subsequent rename/delete operations remove both
  physical files and catalog entries.
- Expanded focused `XCOPY.OVL`, `DELTREE.OVL`, `ACTMKDIR.PRG`, `ACTMOVE.PRG`,
  and `ACTRMDIR.PRG` gates to assert persisted manifests and no temporary
  catalog residue.

## 2026-07-10 Tool Overlay Boundary

- Kept all external-tool-callable resident services below the Action compiler's
  `$A000-$BFFF` pass-overlay window while retaining the larger streamed catalog
  implementation as REU-restored shell/post-return code.
- Normalized queued directory names during post-exit writeback and preserved
  directory-slot mappings across catalog persistence, keeping nested `XCOPY`
  manifests attached to their correct parents.

## 2026-07-10 Hardware/UCI Launch Staging

- Added a hardware/UCI tree-file staging route for direct PRGs and native
  `UDOV` command modules using `FILE_STAT`, `OPEN_FILE`, repeated `READ_DATA`
  transfers into the shared REU launch area, and `CLOSE_FILE`.
- Reused the linker-independent PRG load-address handling, `UDOV` validator,
  launch stub, and REU-backed resident restore used by the VICE path.
- Kept the hardware staging helpers above the `$A000` tool-callable boundary so
  external Action tools cannot overwrite resident services they call.
- The route is build- and VICE-compatibility-tested but remains unvalidated on
  real C64 Ultimate hardware. The corresponding recursive Tool ABI
  implementation is recorded below.

## 2026-07-10 Hardware/UCI Recursive Tool ABI

- Generalized nested tree-path resolution to select UCI `OPEN_DIR` / `READ_DIR`
  enumeration when the Ultimate transport is present and retain the VICE
  manifest path otherwise.
- Added UCI `CREATE_DIR`, file and empty-directory `DELETE_FILE`, same-drive
  `COPY_FILE`, and cross-drive read/write streaming behind the fixed recursive
  Tool ABI used by `TREE.OVL`, `XCOPY.OVL`, and `DELTREE.OVL`.
- Routed resident `MD` and `RD` through the same backend-generic directory
  operations.
- Made tool-time backend selection use UDOS's preserved transport snapshot so a
  large launched tool can overwrite low resident transport code and continue
  using the fixed Tool ABI; the 4,095-byte `ACTMON.PRG` gate covers this case.
- The implementation builds and preserves all focused VICE behavior, but it has
  not been validated on real C64 Ultimate hardware.

## 2026-07-10 ACTC Token Lookahead

- Added cached SourceReader lookahead for complete decimal, symbol, punctuation,
  and comparison tokens.
- Kept complete token caching in resident SourceReader while moving
  positive-word expression parsing into one shared body-overlay implementation
  reached through overlay-ABI v2 token callbacks. This keeps cold parser code
  outside resident ACTC without duplicating it between collect and preallocate
  passes.
- Added zero-lookahead page-boundary coverage for decimal and builtin-symbol
  tokens, operators, nested grouped expressions, and grouped signed values,
  and corrected sum/term state so normal arithmetic precedence remains intact.

## 2026-07-11 ACTC Small Decimal Tokens

- Replaced the resident byte-valued decimal factor's digit-by-digit scanner
  with complete SourceReader token consumption.
- Added a zero-lookahead proof with `255` crossing a 256-byte source-window
  boundary while preserving rejection of values outside the byte range.
- Consolidated duplicate byte-valued condition and decimal comparison parsing
  behind one complete-token tail covering `=`, `<`, `>`, `<=`, `>=`, and `<>`.
- Fixed nested declaration-initializer comparisons by preserving each outer
  left operand across recursive grouped right-hand expressions.
- Moved byte-valued arithmetic and grouping to complete-token dispatch and
  fixed recursive sum/term accumulator corruption for grouped operands.
- Moved resident byte-valued `AND`, `OR`, `NOT`, and boolean grouping to
  complete-token dispatch, including zero-lookahead keyword recognition across
  a page-aligned source-window boundary.
- Preserved boolean left operands on the machine stack across recursive right
  operands, fixing incorrect flat and nested `AND`/`OR` constant results.
- Moved resident runtime boolean grouping and all six integer comparison forms
  to complete-token dispatch, retaining zero-lookahead page-boundary coverage.
- Consolidated runtime comparison suffix lowering around one token classifier,
  recovering 26 resident bytes while preserving the existing direct-PRG op
  streams.
- Moved dynamic integer runtime `+`/`-` and grouped terms to complete-token
  dispatch, with variable-expression zero-lookahead proofs at a page boundary.
- Moved all six runtime REAL comparison forms to complete-token dispatch,
  preserving the existing `rt_f_cmp` lowering while recovering 76 resident
  bytes and adding zero-lookahead page-boundary proofs.
- Moved runtime call `(`, `,`, and `)` punctuation to a shared expected-token
  consume seam, retaining page-aligned zero-lookahead call proofs while keeping
  the parser independent of byte-oriented delimiter helpers.
- Moved shared conversion and unary-helper keyword opens to complete symbol plus
  `(` tokens, and moved resident runtime REAL conversion closes and the signed
  prefix to complete punctuation tokens. A resident-fallback proof places the
  keyword and delimiters independently at a zero-lookahead page boundary while
  preserving exact object emission and recovering 26 resident bytes.
- Moved the resident signed REAL conversion's single-zero sentinel to a strict
  decimal-token consume, including cross-page acceptance of `0-n` and rejection
  of `00-n`. Fixed source-cursor loss during conversion literal storage and
  preserved REAL comparison-control literals across RHS conversion arithmetic.
- Moved optional small-value `=`, `[`, and `]` punctuation in module,
  constant-expression, runtime-value, and resident integer-print paths to
  complete-token consumption, with a nine-case zero-lookahead boundary matrix.
- Made failed constant-expression probes transactional across REU page refills
  and aligned the legacy `PrintI`/`PrintIE` runtime fallback with the shared
  optional-wrapper syntax and complete-token close handling, including a
  production `ACTC_OVL6` boundary proof.
- Added dynamic integer `*` and `/` precedence lowering to ACTC, including
  complete-token page-boundary coverage and selective `rt_i_mul` / `rt_i_div`
  imports. ACTC now emits native 6502 `m` records with nested initialized-data
  exports and generic `r` relocations. ALINK links those records through the
  ordinary object-code path and includes only the referenced integer helpers
  plus `rt_print_i` when needed.
- Added exact-byte, malformed-body, missing-helper, stack-underflow, assignment
  store, divide-by-zero, and live VICE proofs. The linked programs are ordinary
  direct PRGs and do not use a runtime instruction runner.
- Removed ALINK's dedicated integer-body analyzer and code generator. The
  reduced linker now ends at `$8AE5`, leaving 3,354 bytes below the preserved
  UDOS Tool ABI boundary at `$9800`.
- Extended ACTC's native word emitter to straight-line assignments, loads, and
  load/store copies. Removed ALINK's matching word-body templates and converted
  the seeded positive cases to ordinary machine-code OBJ records, with the old
  compact bodies covered only as rejection inputs.
- Converted the remaining seeded empty-return and transitive-library fixtures
  to ordinary machine-code OBJ records with real relocations. Removed ALINK's
  empty-return, single-call, and fanout root-body templates, leaving the compact
  forms as explicit rejection probes.
- Extended ACTC's native integer emitter across string output and ordinary
  external calls. Converted the imported `printmath` root and its `W` library
  dependency to machine OBJ records, selected `rt_print_i` through normal
  closure, and removed ALINK's dedicated printmath strategy and template. The
  two old compact printmath bodies are retained only as rejection probes.
- Added compiler-owned native lowering for a simple integer equality `IF`.
  ACTC fuses the compact equality/branch pair into 6502 machine code and emits
  a named relocation to a synthetic `__if0` local export, so forward branch
  distance is not constrained by the 6502 relative-branch range.
- Removed ALINK's matching `if_eq` compact-body candidate and generated PRG
  template. The old body is now rejection-only.
- Split compiler-owned native integer object generation into `ACTC_OVL8.BIN`.
  The generic `ACTC_OVL5.BIN` now excludes the native generator, and explicit
  not-applicable dispatch preserves generic object output while leaving more
  than 2 KB free in each emission overlay for subsequent native control flow.
- Extended that native branch lowering to integer not-equal `IF`, removed
  ALINK's matching compact candidate/template, and retained the old body only
  as an explicit rejection case.
- Extended native branch lowering to unsigned integer less-than `IF`, removed
  ALINK's matching compact candidate/template, and retained the old body only
  as an explicit rejection case.
- Extended native branch lowering to unsigned integer greater-than `IF`,
  removed ALINK's matching compact candidate/template, and retained the old
  body only as an explicit rejection case.
- Fused the compiler's zero-inverted unsigned comparison forms into native
  greater-equal and less-equal branches, retired both matching ALINK templates,
  and retained their compact bodies as rejection cases.
- Extended the one-level native integer branch path through simple equality
  `IF/ELSE`, using `__if0` for the else entry and `__if1` for the join. Removed
  ALINK's matching candidate/template, added true/false live launch coverage,
  and retained the compact body as a rejection case. The broad direct-PRG
  matrix then contained 1258 cases.
- Extended native integer lowering to two nested `IF` levels, including an
  inner `ELSE`. ACTC emits fixed outer `__if0`/`__if1` and inner
  `__if2`/`__if3` relocation targets, while ordered comparison inversion is
  recalculated for each condition. Removed both nested ALINK templates, added
  an outer-false live case, and retained both compact bodies only as rejection
  probes. The broad direct-PRG matrix then contained 1261 cases.
- Migrated simple integer equality and less-than `DO ... UNTIL` loops to
  ACTC-owned native machine records with a `__do0` backward relocation.
  Removed both matching ALINK templates and retained their compact bodies as
  rejection probes. The broad direct-PRG matrix then contained 1263 cases.
- Generalized compiler-owned equality `DO ... UNTIL` lowering to two nested
  loops with `__do0`/`__do1` targets, removed ALINK's nested-loop template,
  and retained its compact body as a rejection probe. The broad direct-PRG
  matrix now contains 1269 cases.
- Added `ACTC_OVL9.BIN` for compiler-owned multi-procedure integer lowering.
  Eleven local-call/control-flow shapes now emit machine bodies, named
  procedure exports, local control targets, and ordinary relocations.
- Removed the corresponding ten remaining local-call signatures/templates from
  ALINK, converted the seeded runtime smoke fixture to relocatable machine OBJ
  records, and removed ALINK's final generic compact-body candidate table.

## 2026-07-14 Direct Tool Workflow

- Added ACTEDIT `Ctrl-O`, `Ctrl-B`, and `Ctrl-D` save-and-handoff commands for
  compile, build, and debug workflows.
- Added compact trailing `,` and `:` module workflow markers so all 24 supported
  module-name characters fit within UDOS's 31-byte command line.
- Added successful-output chaining from ACTC to ALINK and from ALINK to ACTDBG
  through the fixed UDOS Tool ABI; every stage remains an ordinary direct PRG.
- Added harness coverage for editor module derivation, exact successor commands,
  compile output, direct-PRG/debug-sidecar output, and no-chain plain ALINK use.

## 2026-07-14 ACTDBG Release Integration

- Made the UDOS release fail unless the full `ACTION.DNP` workspace contains
  `ACTDBG.PRG` and valid `DGOV` optional-UI and execution overlays.
- Kept the capacity-limited D64 as a boot/tool subset rather than removing
  maintained tools to duplicate the debugger payload.
- Added a mounted-workspace VICE workflow that follows `ACTC MAIN:` through
  direct ACTC, ALINK, and ACTDBG PRGs, exits ACTDBG, and verifies all compiler,
  linker, and debug-sidecar outputs.
- Cleared ACTDBG's full-screen canvas on normal interactive exit so the
  returning UDOS prompt is not mixed with stale debugger rows.

## 2026-07-14 Debugger-To-Editor Location Return

- Added strict `ACTEDIT <NAME-OR-PATH>:<LINE>` startup positioning with 16-bit
  decimal overflow, zero, and source-range checks.
- Added ACTDBG `E` handoff for the currently browsed linked source record. The
  debugger builds `ACTEDIT <SOURCE-PATH>:<LINE>` only when the complete command
  fits UDOS's 31-byte chain ABI and reports failure instead of truncating it.
- Corrected ACTEDIT path rendering for real UDOS screen-code command lines,
  where the letter `M` shares byte `$0D` with ASCII carriage return, and cleared
  the editor canvas on interactive exit.
- Extended the mounted-workspace VICE gate through direct ACTC, ALINK, ACTDBG,
  and ACTEDIT PRGs and back to the live project prompt.

## 2026-07-14 Compiler-Error Editor Return

- Added compile-only `ACTC <MODULE>;` and made compile, build, and debug modes
  queue `ACTEDIT <MODULE>:<LINE>` after source diagnostics while plain ACTC
  failures retain their nonzero shell return.
- Counted the failing line directly from the staged 24-bit REU source window,
  including offsets beyond the resident source cache, and rejected overlong
  editor commands instead of truncating the 31-byte chain ABI.
- Normalized screen-code module names to lowercase host paths in ACTEDIT so
  module entry works on case-sensitive VICE filesystems.
- Added an end-to-end VICE gate that drives ACTEDIT's compile key through ACTC
  failure, reopens line 3, returns to the project prompt, and verifies that no
  OBJ was emitted.

## 2026-07-14 ACTC Workflow Overlay

- Moved strict ALINK and source-positioned ACTEDIT successor-command assembly
  from resident ACTC into `ACTC_OVL0.BIN`, while preserving its zero-mode no-op
  ABI for direct pass-runner compatibility.
- Made the production ACTC build always emit pass 0 and added harness assertions
  that only requested compile/link/debug or error-return paths load it.
- Recovered enough resident space for the capacity guard: production ACTC BSS
  ends at `$4AF1`, below the UDOS resident floor at `$4AFE`.

## 2026-07-14 ACTEDIT Logical Line Index

- Added a persistent three-byte-per-line edited-document index in REU banks
  `$00-$02`, mapping each logical line directly to a derived piece and 16-bit
  offset while leaving undo/redo metadata in banks `$03-$04` untouched.
- Invalidated and rebuilt the index with piece metadata changes, then replaced
  linear piece-count scans during navigation and save with direct REU lookups.
- Added a 300-line split/save proof that crosses index write windows, verifies
  exact 301-line output, and observes both batched index writes and direct
  three-byte reads through the Tool ABI harness.

## 2026-07-14 ACTEDIT Direct Line-Patch Pieces

- Made clean source-line patches split or replace the indexed resident piece
  directly, persist the resulting source/patch/source spans, and rebuild only
  the edited-document logical index instead of reconstructing all descriptors.
- Retained the metadata-authoritative full-rebuild fallback for dirty caches and
  active structural transactions so reserved insert slots remain atomic across
  split, paste, undo, and save paths.
- Added a focused proof that patches and reloads a line in the middle of a source
  run with one initial descriptor rebuild and one direct piece mutation.

## 2026-07-14 ACTEDIT Direct Split Insert Pieces

- Reordered clean source-line split transactions so the shortened line first
  becomes a directly persisted PATCH piece, then captured that indexed boundary
  before insert metadata invalidates the cache.
- Added direct INSERT-piece persistence at the captured boundary, with the same
  metadata-authoritative capacity and I/O fallback used by direct line patches.
- Extended the 300-line split/save proof to require one initial descriptor
  rebuild, one direct patch, and one direct insert while preserving exact output.
- Recorded the resident-space boundary explicitly: `ACTEDIT.PRG` now ends at
  `$498A`, leaving `$174` bytes below the `$4AFE` UDOS floor.

## 2026-07-14 ACTEDIT Resident Mutation Sharing

- Shared clean-cache validation between direct patch and split-insert paths and
  replaced duplicate six-field piece-tail copies with one resident helper.
- Preserved direct mutation and fallback behavior while reducing `ACTEDIT.PRG`
  by `34` bytes; the resident image now ends at `$4968`, leaving `$196` bytes
  below the `$4AFE` UDOS floor.

## 2026-07-14 ACTEDIT Native Mutation Overlay

- Moved clean source-line patch and split-insert piece mutation into the native
  `ACTEDIT_OVL1.BIN` payload at `$A000`, retaining only bounded load, validation,
  dispatch, and fallback wrappers in `ACTEDIT.PRG`.
- Added an `AEOV` ABI header, one-load session lifecycle, and explicit load and
  failure counters; missing, oversized, or malformed payloads preserve edits by
  using the metadata-authoritative descriptor rebuild path.
- Reduced `ACTEDIT.PRG` from `16491` to `16041` bytes. Resident code now ends at
  `$47A6`, leaving `855` bytes below the `$4AFE` UDOS floor, while the mutation
  overlay occupies `853` bytes at `$A000-$A354`.
- Added complete `ACTION.DNP` release integration, focused valid and invalid
  overlay tests, and a VICE gate that edits, directly commits, saves, exits, and
  verifies the resulting source file.

## 2026-07-14 ACTEDIT Structural Mutation And Suffix Indexing

- Advanced the `AEOV` ABI to version 2 and added prepare/apply removal commands
  that validate logical-line identity before directly shrinking, splitting, or
  removing SOURCE, PATCH, and INSERT pieces.
- Routed joins and multiline cut/delete through that direct removal primitive,
  while malformed or missing overlays and stale caches retain the
  metadata-authoritative full descriptor rebuild.
- Prepared inserted-line splits before their text metadata changes, allowing
  source and inserted splits plus general multiline paste to remain on direct
  piece-table operations; text-only updates to an existing INSERT slot now
  preserve the unchanged piece/index cache.
- Replaced full logical-index rewrites after direct mutations with affected
  suffix writes. A 300-line split proof observes writes beginning at byte
  offsets `$01BF` and `$01C2` for lines 150 and 151.
- Kept `ACTEDIT.PRG` within the resident boundary at `16243` bytes
  (`$0900-$4870`, 653 bytes below `$4AFE`); the expanded overlay is `1758`
  bytes at `$A000-$A6DD`.
- Extended harness coverage across source-piece edges, PATCH and INSERT
  removal, inserted-line split, general paste, invalid-overlay fallback, and a
  live mounted-workspace VICE edit/remove/save workflow.

## 2026-07-16 Idun Linux Reentrant Routine Frames

- Completed the interrupted Linux `ACTC` routine ABI work by preserving each
  caller's live parameter, local scalar, local array, REAL, and generated
  expression-temporary bytes across local calls.
- Staged word and REAL function results while restoring the caller frame, with
  a distinct four-byte result cell for each dynamic REAL call expression.
- Added compile/link coverage for recursive word and REAL functions and a
  direct headless VICE execution gate proving a recursive local-array sum of
  `15` and adjacent recursive REAL calls totaling `10.5`.
- Generalized the VICE harness to load direct C64 PRGs without a UDOS disk,
  including binary-monitor memory writes and register discovery by name.

## 2026-07-16 Idun Linux Workflow And Fork Independence

- Added native `ACTEDIT` compile/build/debug modes and matching `ACTMON`
  project dispatch, all in-process with no shell or UDOS command chaining.
- Made the default test runner select the self-contained Idun suites rather
  than discovering archived CP/M/UDOS tests that require sibling repositories.
- Added one-command `make all`, Alpine/Debian setup guidance, a self-contained
  path probe, guarded workspace export replacement, and an authoritative
  historical-tool-to-Linux-command inventory.
- Added CRLF-correct source line accounting plus recursive copy/delete safety
  checks for the Linux compatibility commands.
- Limited frame saves to recursive call-graph cycles, covered direct and mutual
  recursion in a running PRG, and diagnosed recursive frames larger than the
  safe hardware-stack budget.
- Added a low-memory GCC profile and atomic binary replacement so the 512 MiB
  Pi Zero 2 target can compile the multicall C++ source without the previous
  near-500 MiB peak.

## 2026-07-16 Idun Semantic Editor, Debugger, And Profiler

- Added a validated 132-topic external SQLite help catalog, syntax-aware
  terminal highlighting, and contextual F1 help without consuming C64 memory.
- Made every successful `ALINK` atomically rebuild
  `.action/code-map.sqlite3` with linked modules, line addresses, definitions,
  calls/references, signatures, and a PRG fingerprint. Added ACTEDIT F12
  definition lookup, Shift-F12 reference selection, Alt-left/right history,
  and Ctrl-click definition navigation.
- Added the versioned/checksummed `IDBG` binary protocol, stream decoder,
  Linux simulator, and native Idun Unix-socket client. ACTDBG now has a live
  console for target upload, registers, memory, run/halt, prepared and
  transient breakpoints, source-mapped stop events, and PC samples.
- Added the UDOS-free `actsvc` Idun shell tool. It opens the type-8 socket at
  `$6D00`, relocates a self-contained 2,660-byte service to `$C000-$CA63`, then
  accepts PRG uploads without relying on the Idun kernel area that a `$1000`
  target can overwrite. It supplies IRQ halt/capture, eight one-shot software
  breakpoints, target exit/fault events, and a 100-PC sample buffer.
- Added Linux `actprof` with live and imported sample collection, ALINK-map
  attribution by process/function/statement, unmapped-address retention, time
  and percentage reports, and `.action/profile.sqlite3` run persistence.
- Formally retired every preserved `src/tools_udos/` directory through a
  machine-readable replacement manifest; active build, test, and export entry
  points no longer discover legacy UDOS tools.
- Passed 98 active Linux tests, the direct generated-PRG VICE execution gate,
  and export verification for 28 Linux commands, 132 help topics, and the
  bundled C64 target service. Attached Idun/C64 transport validation remains
  outstanding.

## 2026-07-17 Idun Target Hardware Boundary

- Corrected the target-service size recorded above: the public-socket loader
  added ten bytes, making the resident image 2,670 bytes at `$C000-$CA6D`
  (2,873 bytes including the `$6D00` loader).
- Made the Linux target client retry interrupted connect/accept polls, consume
  buffered socket data before acting on `POLLHUP`, and suppress `SIGPIPE` on a
  disconnected target write.
- Corrected and persisted the C64 Ultimate settings that conflicted with Idun:
  SwiftLink at `$DE00`, the command interface, and REU are disabled; C64U turbo
  registers, 8 MHz, badline timing, and D0BC detection are enabled.
- Proved the Pi monitor can flash `init.binary` and `idun64.binary`. End-to-end
  target validation is blocked below ActionC64U because cartridge reset reports
  `i2c write failed`, I2C bus 1 exposes no control device, and the C64 remains
  at BASIC. Added an operator preflight that separates this platform fault from
  an `actsvc` or IDBG failure.

## 2026-07-17 Idun Target Session Hardening

- Corrected the target-service size recorded above after adding address and
  video-standard checks: the resident image is 2,718 bytes at `$C000-$CA9D`
  (2,921 bytes including the `$6D00` loader), still within `$C000-$CAFF`.
- Made graceful Linux detach issue `RESET_SESSION` before closing the socket,
  restoring patched breakpoint bytes and halting an executing target on a
  best-effort basis.
- Rejected target uploads below `$0200` or beyond `$CFFF`, software breakpoints
  in stack/zero-page, service, ROM, or I/O ranges, and writes entering
  `$D000-$FFFF`; aligned the protocol simulator with the resident service.
- Made live ACTDBG require an explicit halt before commands that need target
  state, preventing an incoming command IRQ from silently invalidating Linux's
  running-state model.
- Made ACTPROF halt, drain, and resume the 100-PC sample buffer about once per
  second throughout a run, and report 20,000-microsecond PAL or
  16,667-microsecond NTSC frame intervals instead of retaining only the first
  buffer at a fixed NTSC approximation.

## 2026-07-17 Hardware-Free Completion Pass

- Closed the remaining historical Action compatibility gaps for relocatable
  declaration constants, dynamic captured `FOR STEP` expressions, initialized
  array-size inference, record parameters, adjacent packed code constants,
  local/global shadowing, routine address tables, and the A/X/Y/$A3 machine
  routine ABI. Retained explicit limits for machine/external REAL calls,
  compiler-memory `SET`, resident overlays, and the narrow REU/REAL extensions.
- Expanded the UDOS-free target resident to `$C000-$CFFF` and implemented safe
  instruction stepping plus persistent software-breakpoint reinstallation.
  The 3,936-byte resident image ends at `$CF5F`; the complete `$6D00` Idun tool
  is 4,139 bytes. Control-flow stepping covers branches, JSR/JMP (including the
  NMOS indirect-wrap behavior), RTS, and RTI while rejecting BRK and JAM/KIL.
- Added a deterministic fake Idun socket target that drives the real ACTDBG and
  ACTPROF Linux processes through PRG upload, registers/memory, prepared
  breakpoint synchronization, repeated persistent hits, step, sampling, and
  SQLite profile aggregation. Added a lib6502 harness that executes stepping
  helpers extracted from the actual assembled resident image.
- Proved ACTEDIT Ctrl-click navigation through a real pseudo-terminal, alongside
  F12 definitions, Shift-F12 references, syntax highlighting, and F1 help.
  Corrected the 144-topic external help catalog to match implemented loop,
  array, record, code-block, DBF, and machine-routine behavior.
- Added deterministic malformed target-packet and corrupt-help-database tests
  plus a repeatable ASan/UBSan build/test target. The normal suite passes
  114/114 tests, the sanitizer suite passes 110/110 hardware-free tests, and
  all 13 generated-PRG headless VICE cases pass, including REU and DBF/D64.
- Verified the 28-command Idun export, 144-topic SQLite database, environment,
  source paths, ordinary host build, and static Alpine/AArch64 cross-build.
  Fresh Pi execution remains pending because the reachable Pi accepted TCP 22
  but emitted no SSH banner during repeated 30-second connection attempts.

## 2026-07-17 Pi And Packaging Follow-Up

- Corrected the final resident size after adding live `$01` BASIC-ROM safety:
  3,970 bytes at `$C000-$CF81`, or 4,173 bytes including the `$6D00` loader.
  The assembled harness now validates all 256 opcode lengths, all eight branch
  conditions in both directions, page crossings, and visible-versus-banked
  `$A000-$BFFF` patch safety.
- Added explicit tool-build selection to the exporter/verifier and a complete
  `build/idun-action-aarch64/` release path. Added the missing top-level
  `ACTION.PROJ`, making the exported workspace directly compile and link every
  shipped example instead of failing with `NO PROJECT`.
- The final host gates pass 115/115 ordinary tests, 111/111 ASan/UBSan tests,
  and 13/13 generated-PRG VICE tests. Export verification covers 28 commands,
  the resident service, 144 help topics, and a compiled 116-byte `HELLO.PRG`.
- SSH recovered without a Pi reboot. Synchronized only to
  `/home/idun/idun_fork`, built natively with `clang++-20` and no swap, passed
  all 115 tests under Alpine/Python 3.14, verified the native export, compiled
  `HELLO.ACT`, and ran the protocol self-test. `/home/idun/action` was left
  untouched.

## 2026-07-17 Pi Resource Note

- Corrected the resource description above: the initial system check showed no
  active swap, while the final check showed the Pi's pre-existing 2 GiB
  `/swapfile` active with about 24 MiB used. No swap-management command was
  issued by this work. The native build itself completed in about 125 seconds.

## 2026-07-17 Global Tools And Flat Workspace Follow-Up

- Added a user-level installer for all 28 Linux commands and included it in
  each export. The Alpine account now resolves `actc`, `actedit`, and `alink`
  through `$HOME/.local/bin` on interactive login without a `TOOLS/` prefix.
- Added current-directory precedence: local `<module>.ACT` and `<module>.OBJ`
  files now win over an ancestor project, and ACTC/ALINK keep OBJ/PRG/DBG output
  beside them. With no local module, nearest-ancestor `ACTION.PROJ` discovery
  retains the structured SRC/OBJ/BIN workflow; `ACTION_PROJECT` selects a
  project explicitly from elsewhere.
- Added `PLAYGROUND/` to native and AArch64 exports with flat copies of every
  shipped example. Bare commands on the Pi compiled and linked HELLO and
  MATH1_DEMO there without creating nested OBJ or BIN directories.
- Made the ACTEDIT cursor a blinking block over an inverse-video cell. Clarified
  that `tui` forces the built-in editor past the Pi's `EDITOR=joe`; plain
  ACTEDIT continues to honor that standard setting.
- The expanded gates pass 118/118 locally and natively on Alpine, 114/114 under
  ASan/UBSan, and 13/13 under headless VICE. The current expanded native build
  took roughly four minutes on the Pi Zero 2 W; the existing swapfile showed
  about 29 MiB used, and no swap-management command was issued by this work.

## 2026-07-17 ACTEDIT External-Editor Removal

- Supersedes the plain-ACTEDIT behavior described immediately above: ACTEDIT no
  longer consults `$EDITOR` and can never launch Joe or another external
  editor. Plain `actedit <module>` uses ACTEDIT's own uncolored terminal mode;
  explicit `tui` uses the same editor with Action syntax highlighting.
- Verified before editing that all Alpine `HELLO.ACT` test copies were
  byte-identical to the canonical source, so the aborted Joe session did not
  save a damaged copy.
- Added F2 editor-command help in both presentations, with explanations of
  movement, editing, save/guarded quit, contextual help, code navigation,
  history, popup scrolling, and mouse bindings.
- Final verification passes 119/119 locally and on the native Alpine/aarch64
  build, 115/115 under ASan/UBSan, and 13/13 generated-PRG tests in VICE. Both
  native and static AArch64 exports pass artifact verification with 28 Linux
  commands and 144 help topics.

## 2026-07-17 ACTEDIT Reference Browsers And Expanded Examples

- Added F3 as a hierarchical SQLite-backed language reference: overview,
  feature categories, individual signatures, explanations, examples, and
  target notes. Added F4 as a library browser: library list, feature list, and
  detailed pages for each feature. Both work in plain and highlighted ACTEDIT.
- Added common terminal F3/F4 escape-sequence support and PTY coverage that
  drives the real keys through language, DBF1-library, feature, and example
  pages. F2's command reference now explains the new bindings.
- Made an example mandatory for every help-catalog topic and authored examples
  for all 144 core and library features. Catalog generation rejects an omitted
  example so future library additions cannot silently produce blank pages.
- Added `PRIME_REAL.ACT`, which bounds trial division with
  `FSqrt(REAL(candidate))`, prints primes from 2 through 120, and reports the
  expected count of 30. A generated-PRG VICE test executes that exact source.
- Added `REU_DBF_SORT.ACT`, a stable in-place sorter accepting two one-based
  `START,LENGTH,A|D` keys such as `10,20,A` and `40,10,D`. DBF1 stages the
  complete file in REU; a separate 255-byte REU buffer swaps records while key
  validation prevents zero-length and out-of-record ranges.
- Replaced DBF's 1541 save-with-replace command with a serialized
  scratch-then-write adapter. Its generated PRG regression performs two
  consecutive saves and verifies the resulting D64 directory entry.
- Final verification passes 121/121 ordinary tests locally and natively on the
  Alpine/aarch64 Pi, 116/116 hardware-free tests under ASan/UBSan, and 14/14
  generated-PRG tests in VICE. Native and static AArch64 exports both verify
  all 28 commands and 144 help topics; the installed Pi commands compile and
  link both new examples from the flat `PLAYGROUND/` directory.

## 2026-07-18 Idun Arguments, Ten-Key Sort, And ASMBLOCK

- Added the Idun entry ABI `PROC MAIN(CARD argc,CARD ARRAY argv)` while keeping
  `PROC MAIN()` compatible. Target uploads publish a bounded argv table, and
  ACTDBG supports both live `args` updates and startup arguments after `--`.
- Added two-pass `ASMBLOCK [ ... ]` assembly for every legal NMOS 6502 opcode
  and addressing mode. Blocks support scoped forward/backward labels, checked
  relative branches, relocated JSR/JMP and low/high address bytes, CPU
  registers, fixed memory, and Action globals, locals, ordinary parameters,
  REAL/record storage, and routine symbols. ALINK's object format now carries
  selected-byte relocations without breaking existing objects.
- Reworked `REU_DBF_SORT.ACT` to parse the new argv ABI and accept one through
  ten ordered `START,LENGTH,A|D` fields. Kept its stable DBF/REU sort and
  separate REU swap buffer, added complete argument/range validation, added an
  ASMBLOCK example, and normalized block indentation across all shipped sample
  programs.
- Expanded the external catalog to 145 validated topics and documented the
  new ABI, debugger argument controls, assembler, linker relocations, and
  examples. Local gates pass 127/127 ordinary tests, 122/122 ASan/UBSan tests,
  and 15/15 generated-PRG VICE tests. Native and static AArch64 exports each
  verify all 28 commands and 145 help topics.
- Synchronized only `/home/idun/idun_fork`, completed a native Alpine/aarch64
  `clang++-20` build, and passed all 127 tests on the Pi. Installed commands
  compiled and linked `REU_DBF_SORT` and `ASMBLOCK_DEMO`, generated the SQLite
  code map, and passed the target-protocol self-test. A stale dangling Emacs
  lock in the fork was removed; `/home/idun/action` remained untouched.

## 2026-07-18 ACTSPC And C64-Key Editor Operations

- Added Linux `actspc` for one Action source, multiple sources, shell-expanded
  lists, or quoted wildcards. It matches `.ACT` case-insensitively, deduplicates
  in deterministic order, validates and formats the complete set before any
  replacement, preserves file permissions, and atomically replaces only
  changed files. Its syntax-aware, idempotent layout preserves strings and
  comment text, handles routine/control/continuation indentation, and gives
  ASMBLOCK instructions and local labels a consistent layout.
- Moved ACTEDIT definition lookup from unavailable F12 to F5, assigned F6 to
  the exact ACTSPC engine for the current unsaved buffer, and moved reference
  selection to F7. Updated the status line, F2 command help, editor roadmap,
  operator guide, export instructions, and PTY tests for the real F5-F7 escape
  sequences.
- Added internal multiline block editing to both plain and highlighted ACTEDIT:
  Ctrl-B marks, cursor movement extends, Ctrl-A selects all, Ctrl-C copies,
  Ctrl-X cuts, Ctrl-V pastes, Escape clears, and left-button dragging selects.
  Typing, Backspace, and Delete replace/remove the active selection; Ctrl-click
  remains definition lookup. Selection is visible in inverse video and the
  clipboard lasts for the editor session.
- Added formatter, wildcard, atomic-write, permission, idempotence, example
  compile/link, editor-format, keyboard-clipboard, mouse-selection, installer,
  export, and code-navigation coverage. Corrected the two KERNAL-output VICE
  cases to wait for emulated BASIC readiness instead of assuming a one-second
  host delay; host and Pi compiler outputs were byte-identical, and the fix
  makes those cases portable to the slower AArch64 VICE 3.9 build.
- Final gates pass 131/131 ordinary tests locally and natively on Alpine,
  126/126 hardware-free tests under ASan/UBSan, and 15/15 generated-PRG tests
  under both local and Pi-native VICE. Native and static AArch64 exports verify
  all 29 commands and 145 help topics. The installed Pi `actspc`, `actc`, and
  `alink` workflow handles quoted uppercase-source wildcards and emits the
  expected 116-byte HELLO PRG, OBJ, DBG, and SQLite code map. Only
  `/home/idun/idun_fork` was synchronized; `/home/idun/action` retained its
  original timestamp.

## 2026-07-18 Full IEEE-754 Binary32 Runtime

- Replaced every Q8.8-backed REAL helper with independently link-selected
  6502 binary32 modules generated by `tools/generate_real_runtime.py`. Add,
  subtract, multiply, divide, comparison, absolute value, signed/unsigned
  conversion, REAL-to-INT truncation, and square root now cover signed finite
  values, gradual-underflow subnormals, signed zero, infinities, NaNs,
  overflow, and round-to-nearest ties-to-even behavior across the binary32
  range.
- Changed ACTC constant evaluation to round after every operation at binary32
  precision, permit IEEE overflow/divide-by-zero/domain results, canonicalize
  folded NaNs, recognize `INF`/`INFINITY` and `NAN`, and reject the runtime's
  unordered comparison sentinel for every ordered predicate. Removed an old
  unnecessary signed-conversion dependency from REAL multiplication closure.
- Replaced the limited REAL printer with a module-owned big-integer formatter.
  It prints every finite binary32 value as an exact decimal with trailing
  fractional zeroes removed, preserves signed zero, and emits `INF`, `-INF`,
  or `NAN`. The deliberate multi-subnormal worst-case VICE probe completes in
  23.2 seconds on the Pi Zero 2W and matches all 128-151 expected digits.
- Added generator consistency, binary32 constant-folding, special-literal,
  unordered-comparison, conversion-boundary, 116-vector raw target arithmetic,
  and whole-domain exact-print regressions. Updated F2/F3/F4 help, syntax
  highlighting, MATH1, samples, language documentation, matrix, README, and
  exported runtime status; the validated SQLite catalog now has 147 topics.
- Final gates pass 131/131 ordinary tests locally and natively on Alpine,
  126/126 hardware-free tests under ASan/UBSan, and 17/17 generated-PRG tests
  under both local and Pi-native VICE. Native and static AArch64 exports verify
  all 29 commands and 147 help topics. The Pi was force-built with
  `clang++-20`, re-exported, verified, and reinstalled entirely under
  `/home/idun/idun_fork`; `/home/idun/action` retained stat
  `287259:4096:1784278218` and index hash
  `06f76533d14b53220a26de585f84e2cebd380648aa6efa4d02324aea6b0bf54e`.

## 2026-07-18 MATH1, GFX1, And External Graphics Resources

- Completed portable MATH1 over the full IEEE-754 binary32 core: constants,
  rounding/remainder/min/max utilities, exponential/log/power/hypotenuse,
  circular and reciprocal trigonometry, inverse and quadrant-aware functions,
  versine/haversine, hyperbolic/inverse-hyperbolic functions, and degree/radian
  conversion. Corrected negative large-magnitude FATan reduction and exercised
  sixteen representative results in generated 6502 code.
- Expanded GFX1 with tracked VIC bank/screen/bitmap/sprite memory, clipped hires
  and multicolor pixel operations, cell colors, lines, rectangles, squares,
  circles, triangles, bitmap-resource stamp/draw/erase/move operations, and
  staged sprite place/move/show/hide operations. The recommended `$8400`
  screen, `$8800` sprite, `$A000` bitmap layout avoids the enlarged PRG and
  safely restores `$01` after accessing RAM hidden beneath BASIC ROM.
- Added Linux `actsprite` and `actbitmap` pixel editors with atomic ASP1/ABM1
  persistence, hires/multicolor TUIs, scrolling bitmap viewports, and
  scriptable create/set/clear/print/info operations. Added global
  `SPRITE`/`MSPRITE`/`BITMAP`/`MBITMAP name=RESOURCE "file"` compilation,
  case-insensitive project/SRC/RES resolution, strict mode/dimension/payload
  validation, 64-byte sprite alignment, and resource embedding without pixel
  data in Action source.
- Bound ACTEDIT F8 to the resource declaration under the cursor. It suspends
  and restores the source editor, resolves uppercase Linux export names, and
  creates missing hires or multicolor assets in `RES/`. Added all 76 GFX1 and
  51 MATH1 entries to the external F3/F4/ACTHELP catalog, plus
  `GFX_RESOURCE_DEMO.ACT`, sample ASP1/ABM1 assets, editor/compiler tests, and
  complete native-port notes in `docs/new_math_func.txt` and
  `docs/new_gfx_func.txt`.
- Final local gates pass 135/135 ordinary tests, 130/130 ASan/UBSan tests, and
  19/19 generated-PRG tests in VICE. Native and static AArch64 exports verify
  all 31 commands and 260 help topics. The Pi Zero 2W completed a native
  `clang++-20` build, all 135 ordinary tests, all 19 Pi-native VICE tests,
  export verification, installation, and flat-directory MATH1/GFX resource
  smoke builds.
- Synchronized source and build output under `/home/idun/idun_fork` and
  installed all commands under `/home/idun/.local/bin`. As explicitly
  requested, copied only `new_math_func.txt` and `new_gfx_func.txt` into
  `/home/idun/action`; the metadata index for every pre-existing protected file
  remains `06f76533d14b53220a26de585f84e2cebd380648aa6efa4d02324aea6b0bf54e`.
  Physical Idun-to-C64U display validation remains the only graphics gate not
  exercised in this milestone.

## 2026-07-18 Signed Alpine APK Repository

- Added a reproducible Docker-hosted Alpine 3.24/AArch64 packaging pipeline
  for `idun_action` and `idun_action_full`. The base package installs the
  static Linux multicall executable once, exposes all 31 command names through
  symlinks, and supplies the help database, C64 target service, Action source
  libraries, and link-selected 6502 objects. The exact-version full package
  adds examples, graphics resources, a complete workspace template, and the
  overwrite-safe `idun-action-new-workspace` helper.
- Added deterministic package-source staging, AArch64 ELF validation,
  APKBUILD rendering, 4096-bit RSA key initialization, package signing, signed
  apk-tools 2 `APKINDEX.tar.gz` and apk-tools 3 `Packages.adb` indexes, and an
  isolated repository verifier. The verifier trusts only the generated public
  key, installs `idun_action_full` into a clean AArch64 root, checks both
  package records and all command/data links, and exercises workspace creation
  and overwrite refusal.
- Kept the mode-0600 private key outside the web root at
  `.apk-keys/idun-action-apk.rsa`; its SHA-256 public-key fingerprint is
  `d2c29db420c9ca396827f026d82cd1a566781b555a8ddc57caf4afdfb72aa500`.
  Published artifacts and the mode-0644 public key are under
  `build/alpine-apk/repository/`. The final `0.1.0_pre20260718-r0` APKs are
  1,951,736 bytes (`idun_action`) and 72,427 bytes (`idun_action_full`).
- Installed Mint's lighttpd 1.4.74 and a hardened dedicated
  `idun-action-apk.service` configured for
  `http://192.168.0.26:8088/`. The distribution service, dedicated service,
  and lighttpd maintenance timer are all inactive and disabled, port 8088 has
  no listener, and the configuration passes `lighttpd -tt`; publication is
  deliberately deferred until an explicit service start.
- Added five focused key, staging, architecture, package-layout, web-hardening,
  and workspace-helper tests and included them in the active suite. The final
  ordinary gate passes 141/141 tests; both APK signatures, both repository
  signatures, clean-root package installation, all 31 commands, and the
  workspace helper pass the separate repository verification gate.

## 2026-07-18 Native Action Cross-Suite Validation

- Added five nonduplicate direct-PRG cases adapted from the native ActionC64U
  runtime matrix. They cover nested integer loops, inline `WHILE condition DO`,
  nested procedure/local control flow, ascending wraparound, and REAL
  comparison/arithmetic while preserving the original program bodies apart
  from fixed result and completion instrumentation.
- Fixed the Linux ACTC parser to accept the native inline `WHILE condition DO`
  spelling and guarded DBF runtime helper calls with saved/restored interrupt
  state while those helpers use KERNAL-owned zero-page scratch.
- Added the cross-suite to `make test-prg`. Local VICE 3.7 executes all new
  cases and skips only the known-unreliable long DBF monitor case; an isolated
  Pi Zero 2W build with VICE 3.9 passes all 141 ordinary tests, all 20 PRG
  tests, and three repeated focused DBF runs. The Pi's primary fork checkout
  was not modified by this validation.

## 2026-07-18 Idun Documentation And UDOS Parity Baseline

- Updated the Idun handoff and active-direction documents to the verified
  31-command, 260-topic, 141 ordinary-test, 131 sanitizer-test, and 20 PRG-test
  product state. Removed stale future-work claims for IEEE-754, MATH1, GFX1,
  graphics resources, resource editors, formatting, and signed APK packaging.
- Added `docs/udos_feature_parity.md` to compare capabilities rather than
  executable implementations. Linux sockets, SQLite, terminal processes,
  AArch64 builds, and APKs remain Idun-specific; UDOS resident services, REU
  overlays, and disk/DNP releases remain native-specific.
- Confirmed native parity for direct OBJ/PRG linking, ASMBLOCK's maintained
  shapes, IEEE-754 core helpers, INPUT1, DBF1, SIDSPR1, and source debugging.
  Recorded the remaining native compiler, complete MATH1, complete GFX1,
  resource compiler/editor, formatter/help, and physical-hardware work without
  changing the Idun runtime or its separately managed Pi checkout.

## 2026-07-18 Cross-Product Parity Documentation Validation

- Added a dated validation snapshot to `docs/udos_feature_parity.md` and
  corrected native release capacity to the measured four free D64 blocks.
  Shared Action/OBJ1/runtime requirements remain separate from Linux-only
  sockets, SQLite, terminal processes, AArch64 packaging, and APK delivery.
- Revalidated the active Idun Linux product after the documentation update.
  `make test` rebuilt the 31-command toolset and 260-topic help catalog, then
  passed all 141 compiler, linker, editor, resource, help, debugger, profiler,
  export, packaging, source-scan, and VICE-command tests.
- Recorded the corresponding native 741-test and focused direct-PRG VICE
  results without claiming that native MATH1, resource declarations, expanded
  GFX1, resource editors, or formatter/help workflow parity is complete.

## 2026-07-18 Shared Runtime And Native Prefix-Parity Refresh

- Recorded the native ActionC64U repository as authoritative for common
  link-selected 6502 runtime modules and added manifest-based synchronization.
  Only the direct-KERNAL DBF create/open-write adapters remain intentionally
  OS-specific.
- Synchronized the exact finite IEEE-754 binary32 decimal printer and its
  generator. The common target modules stay byte-identical even though Idun
  build tools run as Alpine Linux processes and native tools run under UDOS.
- Updated the cross-product matrix after the native compiler learned to accept
  semicolon documentation before `MODULE` across REU windows. Ordinary
  ASMBLOCK composition is also parity; native `symbol+constant` operands and
  fixed register-entry `=*(...)` routines remain explicit compiler/ABI work.
- The current baselines are 745 native ActionC64U tests, 133 UDOS tests with
  one intentional embedded-AUTOEXEC capacity skip, 145 Idun tests, and 20 Idun
  direct-PRG tests with one local VICE 3.7 long-DBF version skip. Attached Idun
  cartridge and physical C64U validation remain external release gates.

## 2026-07-18 OBJ1 Selector Interoperability

- Made the Linux ALINK parser accept native compact `l`/`h` byte-relocation
  selectors in addition to its emitted `lo`/`hi` forms. Optional signed decimal
  addends retain the existing post-placement 16-bit range validation.
- Added a Linux linker regression that consumes a native-style object using
  compact low/high selectors with positive and negative addends and checks the
  exact linked PRG bytes.
- Updated the shared OBJ1 documentation and parity matrix. Native VICE launch
  probes now consume Linux-style selectors, native source-generated addends
  execute correctly, and the complete native ALINK matrix passes 1,320/1,320.

## 2026-07-18 Native Fixed-Entry Parity And Inventory Refresh

- Updated the Idun handoff, README, active direction, and UDOS comparison after
  native ACTC implemented Idun's 16-byte fixed register-entry ABI for ASMBLOCK
  bodies. The focused native ACTC/ALINK/VICE proof verifies BYTE/CARD returns
  and mixed A/X/Y/`$A3` argument placement without changing Idun code.
- Expanded the comparison beyond the earlier narrow scalar slice. It now lists
  raw machine-code bodies, nondecimal call literals, arrays/pointers/records,
  typed recursive functions, general REAL source behavior, MATH1, GFX1,
  graphics resources/editors, formatting/help, and physical validation as
  distinct native tasks.
- Kept OS-specific boundaries explicit: Idun retains Linux processes, sockets,
  SQLite, AArch64/APK packaging, and its target-upload `argc`/`argv` ABI; native
  retains UDOS services, REU overlays, command-tail workflow, and disk/DNP
  releases. Shared Action/OBJ1/runtime behavior and linked PRG results remain
  the parity boundary.
- Recorded the current native inventories as 1,321 broad direct-PRG cases and
  165 source-backed object-emission cases. The prior complete 1,320-case run
  remains the baseline until the expanded matrices are rerun.

## 2026-07-18 Native Fixed-Entry Selector And Radix Refresh

- Updated the cross-product record after native ACTC began forcing every
  fixed-entry unit through its capable emitter and explicitly rejecting REAL,
  local-storage, and over-16-byte ABI signatures rather than falling back.
- Recorded native parity for decimal, hexadecimal, and binary ordinary call
  literals, including a zero-lookahead REU-window regression and a direct
  ACTC/ALINK/VICE result probe. No Idun compiler or target-runtime change was
  required.
- Kept Idun raw bracketed machine-code bodies as the next native syntax gap;
  general native REAL/types, full MATH1/GFX1, resources, editors, workflow, and
  physical-hardware validation remain separate work.
- Recorded complete rebuilt-native results for all 165 source-backed
  ACTC/ALINK/live-VICE shapes and all 1,321 broad direct-PRG ALINK shapes.
- Revalidated this fork with 146/146 ordinary tests, 132/132 ASan/UBSan tests,
  and 20 direct-PRG tests with one documented local VICE 3.7 DBF/REU version
  skip. The 31-command, 260-topic export, artifact verifier, shared-module
  digest check, and strict environment/path checks pass.

## 2026-07-18 Native Raw-Code Parity Refresh

- Updated the comparison after native ACTC added unchecked raw fixed-routine
  bodies with byte/word/character/sum constants plus storage, local-routine,
  and current-address OBJ1 relocations. The native focused direct-PRG VICE
  shape passes without any Idun compiler, linker, or runtime change.
- Recorded the new native inventories as 1,322 broad direct-PRG cases and 166
  source-backed cases. Named `DEFINE` values and external/fixed-address
  expressions remain native compiler work; Linux process services remain an
  intentional OS boundary rather than a UDOS porting requirement.
- Recorded the completed 166-case native source-backed ACTC/ALINK/live-VICE
  matrix and focused module-local routine relocation coverage. The 1,322-case
  broad native inventory remains a distinct release-validation gate.
- Revalidated all 754 native tests and all 146 Idun Linux product tests after
  the raw-code parity refresh; the shared 6502 digest check also passes.

## 2026-07-19 Native Numeric Absolute-Address Parity Refresh

- Updated this fork's parity matrix after native ACTC added bodyless numeric
  absolute-address procedure/function declarations and direct `JSR` lowering
  through its shared register ABI. No Idun compiler, linker, or target-runtime
  change was required.
- Recorded native pass J for compact fixed-only units and universal pass H for
  composition with ASMBLOCK, `=*(...)`, runtime-argument calls, and integer
  control. The focused native `$FFD2` compile, exact OBJ, ALINK closure, and
  live-VICE checks pass without selecting a library object.
- Recorded the later forward/backward local alias implementation and its named
  OBJ1 relocation/live-VICE proof. Native inventories are now 1,324 broad and
  168 source-backed shapes without a claim that the complete refreshed matrices
  passed. At that checkpoint, constant-first/general addend expressions and
  binary32 constant folding remained native compiler gaps; the following
  entries close both.
- Rechecked the shared target manifest. Common 6502 modules remain identical;
  Linux process/SQLite/socket/APK behavior and UDOS overlay/REU/DNP behavior
  remain intentional platform-specific implementations.

## 2026-07-19 Routine-Address Expression Parity

- Fixed Linux ACTC declaration parsing to identify the final top-level
  parameter group instead of treating a grouped address expression as the
  parameter list.
- Added matching Linux/native regressions for `WORKER+(2*3)`,
  `(1 LSH 2)+WORKER`, and grouped numeric `$FFD0+2` bindings. The linked forms
  emit ordinary named OBJ1 relocations with addends 6 and 4; aliases create no
  export, import, wrapper, or runtime dependency.
- Native pass I now canonicalizes the shared checked expression forms before
  bounded declaration scanning. Linux services and UDOS mechanics remain
  separate.

## 2026-07-19 Native REAL CONST Parity Refresh

- Recorded native ACTC's bounded binary32 folding for decimal/exponent and
  radix literals, prior REAL constants, arithmetic and grouping, `REAL`,
  `FABS`, `FSQRT`, `INF`/`INFINITY`, and `NAN`.
- Native conversion uses an exact 448-bit integer ratio and every operation
  rounds to binary32 with round-to-nearest, ties-to-even. Edge regressions cover
  subnormal underflow, maximum finite, overflow, signed zero, ties, infinity,
  NaN, precedence, and malformed expressions.
- Native overlay ABI v5 exposes a resident evaluator generated deterministically
  from the shared OBJ1 floating-point closure. Pass I occupies 7,680 bytes at
  `$A000-$BDFF` and retains its complete 512-byte reserve.
- A source-backed direct-PRG proof emits constant `7.5`, selects only
  `RT_PRINT_F.OBJ`, and passes in VICE. Native inventories are now 1,325 broad
  direct-PRG cases and 169 source-backed shapes; both complete matrices pass.

## 2026-07-19 Native Two-REAL-Parameter Parity Checkpoint

- Recorded the native pass-A `REAL FUNC F(REAL A,B)` checkpoint. Its bounded
  caller preserves left-to-right named REAL arguments, copies both binary32
  values into separate callee storage, and returns the first parameter by
  pointer without changing Idun's already-general source contract.
- Native ACTC emits ordinary OBJ1 machine exports and relocations, ALINK selects
  only `RT_I_TO_F.OBJ`, and the deterministic plus live-VICE probes verify both
  arguments, both parameter copies, and the result. Native inventories are now
  1,326 broad and 170 source-backed shapes.
- This does not close general native REAL or MATH1 parity. Expressions,
  control-flow function bodies, nested calls, and dependency-sized library
  modules remain first in the cross-product work order.
- No Idun compiler or target-runtime change was needed. The next shared-source
  parity dependency is general native REAL lowering sufficient for portable
  multi-function MATH1 modules.

## 2026-07-19 Native Finite REAL Function Parity Refresh

- Recorded native pass K for the exact two-REAL-parameter finite
  comparison/select form `IF B<A THEN RETURN(B) FI RETURN(A)`.
- Native OBJ1 uses ordinary machine exports, named relocations, and body import
  closure. The enclosing root selects `RT_I_TO_F.OBJ`, `RT_F_CMP.OBJ`, and
  transitive `RT_F_SPECIAL.OBJ`; unrelated REAL helpers remain pruned.
- The rebuilt UDOS release, deterministic ALINK probe, and live VICE launch
  verify caller values 2.0/1.0, callee copies 2.0/1.0, and result 1.0. Native
  inventories are now 1,327 broad and 171 source-backed shapes, and the complete
  171-case source-backed live matrix passes.
- Added the exact source to both `tests/parity` trees. Linux ACTC/ALINK compile
  and link it directly, and its PRG returns binary32 1.0 in VICE. Linux folds
  the constant conversions while native uses reachable `RT_I_TO_F.OBJ`, an
  allowed optimizer difference with equal result.
- No Idun implementation change was needed. This finite select does not claim
  Idun's general function bodies or MATH1 `FMin` NaN policy; those remain native
  parity work.

## 2026-07-20 Shared MATH1 Minimum/Maximum Selector Refresh

- Synchronized native-authoritative `RT_F_MIN.OBJ` and `RT_F_MAX.OBJ` into the
  Idun target module set. Each 77-byte module imports only `RT_F_CMP.OBJ`; the
  shared manifest and peer digest check require byte-identical code.
- Recorded complete MATH1 selector semantics: one NaN selects the other input,
  two NaNs select the right input, and equal ordered inputs preserve the left
  operand bits, including signed zero. The exact native host verifier passes
  2,304 edge/random pairs per selector.
- Native ACTC now lowers bounded `FMin(A,B)` and `FMax(A,B)` forms for named REAL
  operands in assignment, print, and condition positions. Focused live VICE and
  the 32-shape source-level MATH1 matrix plus eight full-range helper probes
  pass with reachable-only sibling pruning.
- Linux ACTC retains the general portable MATH1 implementation; it does not
  need to replace that source with compiler-specific selector lowering. Idun
  export and standalone-ALINK tests explicitly cover both synchronized modules.
- At this selector checkpoint, native inventories were 1,330 broad direct-PRG shapes, 171
  source-backed object-emission shapes, and 289 compiled-runtime relocation
  oracle cases. General native REAL expressions/calls/returns and the remaining
  dependency-sized MATH1 implementation remain the next cross-product work.

## 2026-07-20 Shared MATH1 Sign Refresh

- Synchronized native-authoritative `RT_F_SIGN.OBJ` into the Idun target module
  set. The dependency-free helper is 123 bytes and remains independently
  selected by generic ALINK closure.
- Matched portable MATH1 behavior exactly: every NaN becomes canonical quiet
  NaN, positive and negative zero retain their bits, and all other negative or
  positive finite/infinite values become `-1.0` or `1.0`.
- Native ACTC now lowers bounded named-REAL `FSign(A)` in assignment, print,
  and condition positions. Its focused direct PRG proves sibling pruning, and
  the exact host oracle passes 2,304 edge/random cases.
- Idun keeps compiling the general portable `FSign` function body. The shared
  module is available for direct OBJ consumers and is guarded by generator,
  manifest, export, and standalone-link checks.

## 2026-07-20 Shared MATH1 Clamp Refresh

- Synchronized native-authoritative `RT_F_CLAMP.OBJ` into the Idun target
  module set. The 199-byte helper imports comparison, maximum, and minimum only
  when directly reachable.
- Matched portable behavior: any NaN argument or inverted bounds produce
  canonical quiet NaN; otherwise clamp preserves the exact selected operand,
  including signed zero.
- Native pass K owns the constrained three-initializer assignment-and-print
  root without reducing pass A below its capacity reserve. Linux ACTC continues
  to compile the general portable `FClamp` body.
- Current native inventories are 1,331 broad direct-PRG shapes, 171
  source-backed object-emission shapes, and 290 compiled-runtime relocation
  oracle cases. The remaining cross-product work is general native REAL
  lowering, 35 public MATH1 routines, and the later type/resource/workflow
  items in `docs/udos_feature_parity.md`.

## 2026-07-20 Native MATH1 Clamp Storage Mapping

- Native pass K now captures all three initializer destinations, three clamp
  arguments, the result destination, and the printed value in its bounded
  four-REAL root instead of assuming fixed `A/B/C/X` storage order.
- Exact object checks and a source-backed direct VICE launch initialize slots
  1/3/2, clamp slots 3/2/1 into slot 0, print slot 0, and produce 5.0 while
  preserving generic reachable-only ALINK closure.
- At that checkpoint native inventories were 1,332 broad direct-PRG shapes, 171 non-runtime
  source-backed object-emission shapes, and 291 compiled-runtime relocation
  oracle cases. Native pass K is 4,359 bytes with 3,833 bytes free.
- Idun requires no implementation change because Linux ACTC already supports
  general portable `FClamp` calls. Shared runtime modules are unchanged; the
  next parity dependency remains general native REAL lowering.

## 2026-07-20 Native Finite REAL Function Storage Mapping

- Native pass K now captures the bounded finite function's initializer, call,
  result, reverse stack-bind, comparison, and return storage roles instead of
  assuming fixed module and parameter slots.
- Added `finite_real_min_permuted.act` to both parity trees. Linux ACTC/ALINK
  compiles and links both fixtures, and the Idun VICE subtest confirms each
  writes binary32 1.0 to `RESULT`; no compiler or runtime change was required.
- Native exact OBJ and live UDOS/VICE checks cover all five reordered REAL
  cells. At that checkpoint native inventories were 1,333 broad direct-PRG shapes, 172
  non-runtime source-backed shapes, and 291 compiled-runtime relocation-oracle
  cases. Pass K is 4,594 bytes with 3,598 bytes free.
- The bounded source skeleton remains intentional. General native REAL
  expressions, locals, arbitrary calls/returns, recursive frames, and portable
  MATH1 module compilation are still the next cross-product dependency.

## 2026-07-20 Native Two-REAL-Parameter Return Mapping

- Native pass A now keeps the bounded two-parameter function's named return
  selector independent from caller argument storage and preserves the first
  parameter selector outside relocation scratch.
- Added `two_real_second_return_permuted.act` to both parity trees. It declares
  `RESULT/RIGHT/LEFT`, binds parameters `B/A`, returns second parameter `A`, and
  writes binary32 2.0.
- Linux ACTC/ALINK compiles and links the fixture through its existing general
  implementation. The Idun direct-PRG subtest executes it in VICE alongside the
  two finite-MIN fixtures; no Idun compiler or shared runtime change was needed.
- Current native inventories are 1,334 broad direct-PRG shapes, 173 non-runtime
  source-backed shapes, and 291 compiled-runtime relocation-oracle cases. Pass A
  is 7,418 bytes with 774 bytes free under its 768-byte reserve.
- General native REAL expression returns, local frames, nested/recursive calls,
  and portable MATH1 module compilation remain the next dependency.

## 2026-07-20 Native MATH1 Include Constants

- Native `LIB/MATH1.ACT` now exposes all eight portable constants through an
  include-safe, zero-code header while retaining independently link-selected
  builtin calls for its current eight-routine surface.
- Added `math1_constants_include.act` to both parity trees. Native ACTC folds
  `MATH_PI` without an OBJ import; Linux ACTC/ALINK compiles and links the same
  source against Idun's complete portable library.
- The complete native suite passes 799 tests, including 210 overlay tests; the
  Idun active host suite passes 152 tests and its ASan/UBSan suite passes 137
  tests with the new shared fixture.
- The review also measured an Idun packaging gap: at that checkpoint its
  full-source MATH1 include emitted every function body into the selected root
  object. This is not an Alpine-versus-UDOS requirement. The later FTrunc slice
  removes one body; call-graph pruning or dependency-sized generated modules
  must restore referenced-only closure for the remainder before full parity.

## 2026-07-20 Shared MATH1 Truncation

- Added the generated 107-byte `RT_F_TRUNC.OBJ` to the shared 6502 manifest.
  It has no helper imports and truncates finite binary32 values toward zero
  while preserving NaN payloads, infinities, signed zero, and integral values.
- Native ACTC recognizes bounded assignment, direct-print, and condition forms.
  The focused direct PRG selects only conversion, truncation, and printing and
  raises the native inventories to 1,335 broad and 292 compiled-runtime cases.
- Linux ACTC now parses, constant-folds, and emits dynamic `FTrunc` expressions
  through the same helper. `lib/math1.act` declares the intrinsic instead of
  embedding its former portable function body.
- This is one dependency-sized packaging conversion, not completion of MATH1
  pruning. Idun still emits all remaining implementation bodies from a MATH1
  include, and native UDOS still lacks 34 public MATH1 routines plus general
  REAL source lowering.
