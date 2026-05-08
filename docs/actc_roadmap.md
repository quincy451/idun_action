# `ACTC` Roadmap

Current as of `2026-04-25`.

This is the short planning document for the UDOS-native Action compiler, `ACTC.PRG`.
For the detailed proof ledger, see [actc_status.md](./actc_status.md).
For broader project coverage, see [action_matrix.md](./action_matrix.md).

## Current Position

Committed baseline:

- `ACTC.PRG` launches from a UDOS Action workspace.
- It loads the current project manifest and the tracked `SRC/<MODULE>.ACT` source file.
- It emits deterministic `AVO1` object output to `OBJ/<MODULE>.OBJ`.
- `.AVO` is now the legacy compatibility name for project objects, not the
  primary output extension.
- The integrated `ACTC -> ALINK -> AVMRUN` path is proven on the committed Linux `VICE 3.7.1` line.

Current dirty-tree verification:

- `ACTC` front-end and codegen still appear correct.
- The previous mounted-tree save/service blocker has been cleared on the current
  UDOS line.
- `make -C ../udos vice-action-actc` is green again.
- The helper-free higher-level `ACTC -> ALINK -> MAIN.PRG` launch proof is
  green again on the current working tree.
- The named imported `printmath` higher-level proof is now green on the
  direct path through `make -C ../udos vice-action-actc-alink-launch-printmath`.
- The AVM-bearing `ACTC -> ALINK -> AVMRUN` chain remains the compat replay
  path for that shape rather than the generic green default.

## Accomplished

## Tool And Runtime Integration

- Stable UDOS packaging on release media as `ACTC.PRG`.
- Stable `A:` release-tool launch path on the committed baseline.
- Real-target build fits and launches under the widened tool load window.
- Real-target one-shot proof exists through `ACTC -> ALINK -> AVMRUN`.
- Real-target helper-free one-shot proof also exists through
  `ACTC -> ALINK -> MAIN.PRG`.

## Compiler Front-End

- Module selection from the command line.
- Project/manifest guardrails.
- Source loading from `SRC/`.
- Module-header validation.
- Current narrow parser for arithmetic, comparisons, branching, loops, local calls, and unresolved external calls.
- Current narrow integer variable surface for module-scope and proc-local
  `INT` declarations.
- Narrow `BYTE`/`CARD` declaration acceptance through the existing 16-bit
  variable slot path.
- Declaration-only module-scope `REAL` support now records a 4-byte storage
  width in AVO variable metadata.
- Exact-zero module-scope `REAL` initialization now lowers through the existing
  zero literal path:
  `REAL X=[0]`.
- Direct REAL copy assignment exists for `R=A` where both variables are
  module-scope `REAL`; ACTC emits low/high word load/store body ops and no
  runtime import.
- Exact-zero module-scope `REAL` assignment exists for `X=0`; ACTC emits
  `p`, `p`, `T`, and `S` body ops and no runtime import.
- First narrow non-zero integer-to-REAL body assignment lowering now exists
  for small non-negative integer expressions such as `X=7` and `X=(1+2*3)`;
  ACTC emits the low/high literal pair plus `T`/`S` and no REAL runtime
  import.
- First REAL operator lowering exists for `R=A+B`, `R=A-B`, `R=A*B`, and
  `R=A/B` where all operands are module-scope `REAL` variables. ACTC emits
  low/high word body ops and imports only `RT_F_ADD`, `RT_F_SUB`, `RT_F_MUL`,
  or `RT_F_DIV` for the operator used.
- Current safety guards still reject non-zero REAL initializers and
  wider integer-path REAL variable reads/writes outside the explicit exact-zero,
  narrow small-integer bridge, wide positive/signed bridge, explicit
  `REAL(<integer var>)` bridge, copy, and add/subtract/multiply/divide
  lowering paths.

## Object Emission

- Deterministic `AVO1` text object generation.
- Object-level source debug emission:
  - `f`
  - `q`
  - `l`
  - `V g`
  - `V p`
  - `V l`
- Export metadata emission.
- `body_ops` emission.
- Literal-pool emission for the current narrow surface.
- Current runtime-import emission.
- Object-path generation to `OBJ/<MODULE>.OBJ`.
- Production streamed object output through the resident write
  begin/chunk/close services.

## Proven Widening Already Landed

- Nested `IF` / `ELSE`.
- `WHILE ... DO ... OD`.
- `DO ... UNTIL ... OD`.
- Mixed arithmetic/comparison conditions.
- Current multi-variable integer state slice.
- Narrow module-scope `BYTE`/`CARD` and proc-local `BYTE` declaration slice.
- Module-scope `REAL` declaration storage-width slice.
- First module-scope `REAL` add/subtract/multiply/divide assignment slices:
  `REAL A`, `REAL B`, `REAL R`, `R=A+B`, `R=A-B`, `R=A*B`, and `R=A/B`.
- Current local/external integer arg/return slice.
- Current larger-object and larger-proc-size coverage proved through the harness.
- Production `ACTC.PRG` now uses the wider `$0900-$9FFF` tool window and builds
  with `ACTC_REU_SOURCE_CACHE=1`, `ACTC_REU_TABLES=1`,
  `ACTC_REU_BODY_OPS=1`, `ACTC_REU_STRING_LITERALS=1`,
  `ACTC_REU_VAR_NAMES=1`, `ACTC_REU_EXPORT_NAMES=1`,
  `ACTC_REU_INT_LITERALS=1`, `ACTC_REU_VAR_META=1`,
  `ACTC_REU_PROC_META=1`, `ACTC_REU_LAYOUT_META=1`,
  `ACTC_REU_STRING_OFFSETS=1`, `ACTC_USE_BODY_OVERLAY=1`, `STREAM_OUTPUT=1`,
  `CONTENT_BUFFER_SIZE=16`, `OUTPUT_CHUNK_SIZE=128`, `SOURCE_LIMIT=3328`,
  `SOURCE_LOOKAHEAD=255`, `BODY_OPS_STRIDE=255`, `INT_LITERAL_MAX=36`,
  `STRING_LITERAL_MAX=36`, `EXPORT_MAX=16`, `EXTERNAL_MAX=36`, and
  `LOOP_MAX=16`.
- Production `ACTC.PRG` has a tool-ABI-harness proof for staging and compiling
  a `49152` byte source module through the REU source-cache path, with
  `PROC MAIN()` discovered near offset `49120` in the third source window.
- Production `ACTC.PRG` now streams object output with the resident write
  begin/chunk/close ABI and has a proof for an `OBJ/MAIN.OBJ` larger than the
  legacy `640` byte object buffer.
- Large-source compilation is not solved by simply raising `SOURCE_LIMIT`.
  `docs/actc_source_streaming_plan.md` defines the required next architecture:
  chunked file-read ABI, one-time REU source staging, a refillable
  source-reader/tokenizer, two REU-backed parser passes, and REU-backed compiler
  lookup/storage tables.
- `ACTC_REU_SOURCE_CACHE=1` now proves the first service shape and scanner
  refill slice: source beyond the first `20480` bytes is staged into simulated
  REU through the resident-compatible service ABI, later windows are paged back
  into RAM with 255 bytes of bounded lookahead, and a `PROC MAIN` name that
  crosses the first window boundary or a `PrintE` string literal crossing that
  boundary compiles. Long inline spaces now commit 256-byte `Y` lookahead wraps
  back into the reader instead of silently wrapping inside the same window, and
  the first long `PrintIE(...)` expression proof preserves parser registers
  across that commit/read path. Boolean pre-scan wrap now routes to the boolean
  parser instead of rescanning from `Y=0` in the same window. Speculative
  expression pre-scans now mark and restore the active reader window, and failed
  keyword probes that cross into another REU source window now reload the
  original window before returning failure. Assignment parsing now preserves the
  `=` operator position across variable lookup and advances assignment
  punctuation through the same reader path, including the first `Y=$FF` operator
  proof. Procedure parameter parsing also has a first `Y=$FF` opening-`(` proof,
  and runtime/constant group speculation now restores the original REU source
  window before reinterpreting `(expr)` as a comparison left-hand side.
  The production parser still needs token-boundary-safe source reading before
  this is a general large-source solution.
- The unresolved external-name table has moved out of resident BSS and into REU.
  ACTC now keeps one 25-byte active external-name window in normal RAM and uses
  the additive `svc_reu_write_sc0` ABI to persist entries. This first REU-table
  step grew the production compiler development window from about `444` bytes
  to `$04B9` bytes below `$A000`.
- Procedure `body_ops` streams have also moved out of resident memory and into
  REU. ACTC now keeps one active `BODY_OPS_STRIDE` body window in normal RAM,
  flushes it when dirty, and reloads procedure bodies during layout/object
  emission.
- String literals, variable names, and export names have moved to REU-backed
  fixed-record tables.
- Integer literals, variable metadata, procedure parameter/local metadata,
  procedure layout metadata, and string offsets have moved to REU-backed
  fixed-record tables. Procedure declaration debug offsets now live in REU at
  `$00ED00`, and body-op debug offsets now live in REU at `$00EE00`, so
  `ACTC_OVL5.BIN` can emit `f`, `q`, and `l` object debug records without
  pulling those tables back into resident RAM. The overlay-only body parser now
  owns the wide positive sum/term path cleanly enough that production
  `ACTC.PRG` ships with `ACTC_KEEP_BODY_RESIDENT_FALLBACK=0`; the current
  production compiler span is `$0900-$4453`, leaving `1707` bytes below the
  current resident floor `$4AFE`.
- The first overlay support scaffold exists. `tools/build_actc_overlay_noop.sh`
  builds `build/udos_tools/ACTC_OVL0.BIN`, a raw `ACOV` overlay with ABI version
  `1`, pass id `0`, execution base `$A000`, and a no-op entry point.
- The first source-aware overlay exists. `tools/build_actc_overlay_source_header.sh`
  builds `build/udos_tools/ACTC_OVL1.BIN`, pass id `1`, which receives the
  source-window context plus a pointer to the requested module name,
  recognizes `MODULE <name>`, validates that name against the requested module,
  and writes the source mark for the start of the module name back into the
  context block.
- The first declaration-scanning overlay exists. `tools/build_actc_overlay_decl_counts.sh`
  builds `build/udos_tools/ACTC_OVL2.BIN`, pass id `2`, which receives the
  source-window context, counts module scalar declarations before the first
  `PROC`, counts procedure declarations, reports those counts through the
  context block, and writes resident `var_count_data`,
  `module_var_count_data`, and `export_count_data` through context pointers.
  It now also writes module variable names to the REU var-name table and initial
  metadata to the REU var-meta table, including module-scope decimal arithmetic
  and comparison/boolean initializer values, plus procedure export names to the
  REU export-name table.
  Procedure headers with parameter lists and procedure-local
  scalar declarations append parameter/local names and metadata to the REU-backed
  variable tables and write proc-meta param/local count/base records through
  resident store helpers. The overlay-local declaration cache now rejects
  duplicate names and malformed declaration tails before committing successful
  overlay status, and the declaration tail scanner rejects malformed
  initializers before later passes lower them.
- The first resident overlay scheduler proof exists. `actc_overlay_run_pass`
  accepts a pass id in `A`, looks it up in a descriptor table, stages
  `ACTC_OVL0.BIN`, `ACTC_OVL1.BIN`, or `ACTC_OVL2.BIN` into REU bank `$02`,
  copies it to `$A000`, banks out BASIC ROM by changing `$0001` from `$37` to
  `$36`, passes an ACTC context block in `X/Y`, calls the overlay, receives
  context status `0` plus return status `0`, and restores `$0001`.
- The first compile-path overlay chain exists. `tools/build_actc_udos.sh`
  accepts `ACTC_USE_SOURCE_HEADER_OVERLAY=1` and `ACTC_USE_DECL_OVERLAY=1`;
  with those flags enabled, ACTC runs `!ACTC_OVL1.BIN` for module-header
  validation, then `!ACTC_OVL2.BIN` for declaration scanning, and then uses the
  overlay-written REU metadata for later object emission. The `!` prefix is an
  executable-relative tool ABI rule, so the overlay is resolved beside the
  launched `ACTC.PRG`; it is intentionally not a search path. The declaration
  overlay now pages source windows by calling a resident `load next source
  window` callback from its ABI context, so declarations can be scanned after
  the first `20480` byte source window. That target-side executable-relative
  overlay load path is now covered by release/VICE proofs, so
  `tools/build_actc_udos.sh` now defaults both overlay flags to `1`.
- The production build now compiles out resident module-header parsing and
  resident declaration collection when that overlay path is enabled with the
  REU source cache. `ACTC_OVL1.BIN` and `ACTC_OVL2.BIN` are no longer optional
  for the normal build; `tools/build_actc_udos.sh` emits both automatically
  beside `ACTC.PRG`.
- The dedicated REU source-cache harness now also uses that slimmer declaration
  path by default. The declaration overlay wrap cases that had blocked it are
  fixed, including the proc-param `(` boundary and grouped constant initializer
  restore across a `Y` wrap.
- Exported UDOS workspaces and the UDOS release target now include
  `ACTC_OVL0.BIN` through `ACTC_OVL6.BIN` beside `ACTC.PRG`, which keeps the
  current overlay scheduler paths runnable outside the harness and carries the
  default proc-body overlay on release media as well.
- Payload layout and runtime-import detection have now moved out of the
  resident compiler image as well. `ACTC_OVL3.BIN` computes REU-backed proc
  layout and string offsets, and `ACTC_OVL4.BIN` sets import flags by calling
  the resident source-pattern finder through the overlay ABI.
- Streamed object emission has now moved out as well. `ACTC_OVL5.BIN` owns the
  `AVO1` list walks and decimal formatting while calling back into the resident
  compiler only for pointer setup, REU window loads, and byte emission to the
  already-open output stream.
- Proc-body lowering now runs through `ACTC_OVL6.BIN` in the default production
  build. The overlay is built, packaged, and covered by a compile-path proof.
- `ACTC_OVL6.BIN` now keeps its loop stack locally as well, so the default
  build no longer carries resident loop push/pop helpers or loop-stack BSS only
  for overlayed body lowering.
- `ACTC_OVL6.BIN` now also emits current-proc parameter bind ops directly after
  loading proc metadata through the overlay ABI, so the default build no longer
  carries the resident proc-param bind helper only to support overlayed body
  lowering.
- `ACTC_OVL6.BIN` now also lowers the current module-scope REAL assignment
  slice directly, so the default build no longer carries the resident REAL
  assignment helper or its scratch bytes only to support overlayed body
  lowering.
- `ACTC_OVL6.BIN` now also passes condition/print body-op markers in `A` to
  two generic resident callbacks, so the default build no longer carries the
  five one-op wrapper helpers for `IF`, `UNTIL`, `DO WHILE`, `PRINTI`, and
  `PRINTIE`.
- The long-term compiler shape should become a batch pass runner with REU-backed
  overlays. The resident `ACTC.PRG` should load pass code into REU once, copy one
  pass overlay into the same execution window, run it against REU-backed program
  data, then advance to the next overlay. See
  [actc_overlay_pass_plan.md](./actc_overlay_pass_plan.md).

## Remaining Work

## Immediate Stability Work

- Keep the restored `ACTC` save path green while other tool/runtime changes land.
- Preserve `vice-action-actc` and the chained `ACTC -> ALINK -> AVMRUN` proof as
  the first regression gates for compiler work.
- Remove temporary probe/debug noise once equivalent permanent diagnostics exist.

## Near-Term Compiler Work

- Widen diagnostics so save/load/parse failures are easier to localize without
  temporary probe code.
- Add more direct target-side proofs for the compiler save boundary, not just
  the integrated chain.
- Resume language-surface widening from a green real-target compiler baseline.
- Continue the source-streaming refactor from the resident REU stage/read ABI
  and harness proof into an ACTC source reader that can refill windows instead
  of assuming one contiguous source buffer.
- Keep ACTC object emission on the streamed output path and add larger object
  stress cases as language capacity grows.
- Continue moving linker lookup payloads into REU after the compiler source
  cache is stable; ALINK external/export queues should not all live in normal
  RAM.
- Next ACTC structural work should split the remaining body-related discovery
  work away from `ACTC_OVL6.BIN` so language growth can continue without
  refilling the resident compiler image.

## Medium-Term Language Work

- Broaden expression lowering beyond the current proven narrow slice.
- Broaden statement coverage beyond the current branch/loop/call subset.
- Broaden stateful variable semantics beyond the current integer-only slice.
- Continue REAL32 lowering without AVM opcode growth. `+`, `-`, `*`, and `/`
  now have the first variable-to-variable assignment slices, narrow
  `BYTE`/`CARD` to REAL assignment now imports only `rt.i_to_f`, and narrow
  signed `INT` to REAL assignment now imports only `rt.s_to_f`; explicit
  `REAL(<integer var>)` now lowers through those same bridge helpers; the
  first explicit constant-expression cases such as `REAL(255+1)` and
  `REAL(32767)` and `REAL(0-256)` now do as well; larger non-negative body
  assignments such as `X=256`, `X=32767`, and `X=(255+1)` now also lower
  through `rt.i_to_f`, and direct signed `0-<positive expr>` assignments now
  lower through `rt.s_to_f`; the first wide `*` / `/` bridge cases such as
  `X=(128*2)` and `X=REAL(512/2)` now lower through `rt.i_to_f`; direct and
  explicit signed grouped wide bridge cases such as `X=0-(128*2)`,
  `X=REAL(0-(128*2))`, and `X=REAL(0-(512/2))` now lower through `rt.s_to_f`;
  the first narrow REAL compare
  conditions now lower through `rt.f_cmp` for proven `<`, `=`, `>=`, `<>`,
  `>`, and `<=` body cases on module-scope REAL vars; the first
  narrow `PrintR` / `PrintRE` cases now lower through `rt.print_f` for proven
  REAL values such as `REAL X`, `X=REAL(7)`, `PrintRE(X)`,
  `A=REAL(3)`, `B=REAL(2)`, `X=A/B`, `PrintRE(X)`,
  `A=REAL(1)`, `B=REAL(8)`, `X=A/B`, `PrintRE(X)`,
  `A=REAL(1)`, `B=REAL(32)`, `X=A/B`, `PrintRE(X)`,
  `A=REAL(1)`, `B=REAL(64)`, `X=A/B`, `PrintRE(X)`,
  `A=REAL(1)`, `B=REAL(256)`, `X=A/B`, `PrintRE(X)`,
  `A=REAL(1)`, `B=REAL(32768)`, `X=A/B`, `PrintRE(X)`, signed
  `A=REAL(N)`, `B=REAL(2)`, `X=A/B`, `PrintRE(X)` with `N=0-1`, and
  low-word-nonzero dyadic values such as `A=REAL(129)`, `B=REAL(256)`,
  `X=A/B`, `PrintRE(X)`, plus first arithmetic print cases such as
  `A=REAL(3)`, `B=REAL(2)`, `X=A/B`, `A=A/B`, `X=X+A`, `PrintRE(X)`,
  `A=REAL(4)`, `B=REAL(N)`, `X=A+B`, `PrintRE(X)` with `N=0-1`,
  `A=REAL(1)`, `B=REAL(N)`, `X=A+B`, `PrintRE(X)` with `N=0-4`,
  `A=REAL(N)`, `B=REAL(4)`, `X=A+B`, `PrintRE(X)` with `N=0-1`,
  and `INT(REAL)` now has end-to-end proof beyond the first dyadic truncation
  slice: `3/2 -> 1`, `-3/2 -> -1`, `1/3 -> 0`, `-1/3 -> 0`,
  `(1/10)*10 -> 1`, `REAL(32767) -> 32767`,
  `REAL(0-32768) -> INT -> REAL` roundtrip, and runtime range rejection for
  `REAL(32768)` plus `REAL(0-32768)-REAL(1)`,
  `A=REAL(4)`, `B=REAL(1)`, `X=A-B`, `PrintRE(X)`,
  `A=REAL(4)`, `B=REAL(N)`, `X=A-B`, `PrintRE(X)` with `N=0-1`,
  `A=REAL(N)`, `B=REAL(4)`, `X=A-B`, `PrintRE(X)` with `N=0-1`, and
  `A=REAL(3)`, `B=REAL(2)`, `A=A/B`, `X=A*B`, `PrintRE(X)`,
  `A=REAL(3)`, `B=REAL(2)`, `X=A*B`, `PrintRE(X)` producing `2.25`,
  `A=REAL(3)`, `B=REAL(4)`, `X=A*B`, `PrintRE(X)` producing `0.5625`,
  `A=REAL(N)`, `B=REAL(2)`, `A=A/B`, `X=A*B`, `PrintRE(X)` with `N=0-3`,
  `A=REAL(3)`, `B=REAL(2)`, `A=A/B`, `N=0-2`, `B=REAL(N)`, `X=A*B`,
  `PrintRE(X)`, `A=REAL(N)`, `B=REAL(2)`, `A=A/B`, `N=0-2`, `B=REAL(N)`,
  `X=A*B`, `PrintRE(X)` with `N=0-3`, `A=REAL(N)`, `B=REAL(2)`, `X=A/B`,
  `PrintRE(X)` with `N=0-3`, `A=REAL(3)`, `N=0-2`, `B=REAL(N)`, `X=A/B`,
  `PrintRE(X)`, `A=REAL(3)`, `B=REAL(2)`, `X=A/B`, `PrintRE(X)` producing
  `1`, `A=REAL(3)`, `B=REAL(4)`, `X=A/B`, `PrintRE(X)` producing `2`,
  `A=REAL(1)`, `B=REAL(3)`, `X=A/B`, `PrintRE(X)` producing
  `0.3333333432674407958984375`,
  `A=REAL(1)`, `B=REAL(9)`, `X=A/B`, `PrintRE(X)` producing
  `0.111111111938953399658203125`,
  `A=REAL(2)`, `B=REAL(9)`, `X=A/B`, `PrintRE(X)` producing
  `0.22222222387790679931640625`,
  `A=REAL(1)`, `B=REAL(11)`, `X=A/B`, `PrintRE(X)` producing
  `0.0909090936183929443359375`,
  `A=REAL(2)`, `B=REAL(11)`, `X=A/B`, `PrintRE(X)` producing
  `0.181818187236785888671875`,
  `A=REAL(1)`, `B=REAL(13)`, `X=A/B`, `PrintRE(X)` producing
  `0.076923079788684844970703125`,
  `A=REAL(2)`, `B=REAL(13)`, `X=A/B`, `PrintRE(X)` producing
  `0.15384615957736968994140625`,
  `A=REAL(1)`, `B=REAL(17)`, `X=A/B`, `PrintRE(X)` producing
  `0.0588235296308994293212890625`,
  `A=REAL(2)`, `B=REAL(17)`, `X=A/B`, `PrintRE(X)` producing
  `0.117647059261798858642578125`,
  `A=REAL(1)`, `B=REAL(19)`, `X=A/B`, `PrintRE(X)` producing
  `0.052631579339504241943359375`,
  `A=REAL(2)`, `B=REAL(19)`, `X=A/B`, `PrintRE(X)` producing
  `0.10526315867900848388671875`,
  `A=REAL(1)`, `B=REAL(23)`, `X=A/B`, `PrintRE(X)` producing
  `0.0434782616794109344482421875`,
  `A=REAL(2)`, `B=REAL(23)`, `X=A/B`, `PrintRE(X)` producing
  `0.086956523358821868896484375`,
  `A=REAL(1)`, `B=REAL(10)`, `X=A/B`, `PrintRE(X)` producing
  `0.100000001490116119384765625`,
  `A=REAL(1)`, `B=REAL(10)`, `A=A/B`, `B=REAL(1)`, `X=REAL(5)`, `B=B/X`,
  `X=A+B`, `PrintRE(X)` producing `0.300000011920928955078125`,
  `A=REAL(1)`, `B=REAL(10)`, `A=A/B`, `B=REAL(1)`, `X=REAL(5)`, `B=B/X`,
  `C=REAL(1)`, `X=REAL(5)`, `C=C/X`, `X=A+B`, `X=X+C`, `PrintRE(X)`
  producing `0.5`,
  `A=REAL(1)`, `B=REAL(2)`, `A=A/B`, `B=REAL(1)`, `X=REAL(10)`, `B=B/X`,
  `X=A-B`, `PrintRE(X)` producing `0.4000000059604644775390625`,
  `A=REAL(1)`, `B=REAL(10)`, `A=A/B`, `B=REAL(1)`, `X=REAL(10)`, `B=B/X`,
  `C=REAL(1)`, `X=REAL(5)`, `C=C/X`, `X=A+B`, `X=X-C`, `PrintRE(X)`
  producing `0`,
  `A=REAL(1)`, `B=REAL(10)`, `A=A/B`, `B=REAL(1)`, `X=REAL(10)`, `B=B/X`,
  `C=REAL(1)`, `X=REAL(10)`, `C=C/X`, `X=A+B`, `X=X+C`, `B=REAL(10)`,
  `X=X*B`, `PrintRE(X)` producing `3`,
  `A=REAL(2)`, `B=REAL(17)`, `A=A/B`, `C=REAL(1)`, `B=REAL(17)`, `C=C/B`,
  `X=A+C`, `PrintRE(X)` producing `0.17647059261798858642578125`,
  `A=REAL(2)`, `B=REAL(19)`, `A=A/B`, `C=REAL(1)`, `B=REAL(19)`, `C=C/B`,
  `X=A+C`, `PrintRE(X)` producing `0.15789473056793212890625`,
  `A=REAL(2)`, `B=REAL(23)`, `A=A/B`, `C=REAL(1)`, `B=REAL(23)`, `C=C/B`,
  `X=A+C`, `PrintRE(X)` producing `0.1304347813129425048828125`,
  `A=REAL(2)`, `B=REAL(3)`, `X=A/B`, `PrintRE(X)` producing
  `0.666666686534881591796875`,
  `A=REAL(1)`, `B=REAL(7)`, `X=A/B`, `PrintRE(X)` producing
  `0.14285714924335479736328125`,
  `A=REAL(1)`, `B=REAL(7)`, `A=A/B`, `B=REAL(7)`, `X=A*B`, `PrintRE(X)`
  producing `1`,
  `A=REAL(1)`, `B=REAL(9)`, `A=A/B`, `B=REAL(9)`, `X=A*B`, `PrintRE(X)`
  producing `1`,
  `A=REAL(1)`, `B=REAL(11)`, `A=A/B`, `B=REAL(11)`, `X=A*B`, `PrintRE(X)`
  producing `1`,
  `A=REAL(1)`, `B=REAL(13)`, `A=A/B`, `B=REAL(13)`, `X=A*B`, `PrintRE(X)`
  producing `1`,
  `A=REAL(1)`, `B=REAL(17)`, `A=A/B`, `B=REAL(17)`, `X=A*B`, `PrintRE(X)`
  producing `1`,
  `A=REAL(1)`, `B=REAL(19)`, `A=A/B`, `B=REAL(19)`, `X=A*B`, `PrintRE(X)`
  producing `1`,
  `A=REAL(1)`, `B=REAL(23)`, `A=A/B`, `B=REAL(23)`, `X=A*B`, `PrintRE(X)`
  producing `1`,
  `A=REAL(1)`, `B=REAL(3)`, `A=A/B`, `B=REAL(3)`, `X=A*B`, `PrintRE(X)`
  producing `1`, and `A=REAL(1)`, `B=REAL(10)`, `A=A/B`, `B=REAL(10)`,
  `X=A*B`, `PrintRE(X)` producing `1`,
  `A=REAL(1)`, `B=REAL(5)`, `A=A/B`, `C=REAL(1)`, `B=REAL(5)`, `C=C/B`,
  `X=A*C`, `PrintRE(X)` producing `0.0400000028312206268310546875`, and
  `A=REAL(1)`, `B=REAL(10)`, `A=A/B`, `B=REAL(1)`, `X=REAL(5)`, `B=B/X`,
  `X=A/B`, `PrintRE(X)` producing `0.5`,
  `A=REAL(1)`, `B=REAL(17)`, `A=A/B`, `B=REAL(2)`, `X=REAL(17)`, `B=B/X`,
  `X=A/B`, `PrintRE(X)` producing `0.5`,
  `A=REAL(1)`, `B=REAL(19)`, `A=A/B`, `B=REAL(2)`, `X=REAL(19)`, `B=B/X`,
  `X=A/B`, `PrintRE(X)` producing `0.5`,
  `A=REAL(1)`, `B=REAL(23)`, `A=A/B`, `B=REAL(2)`, `X=REAL(23)`, `B=B/X`,
  `X=A/B`, `PrintRE(X)` producing `0.5`,
  `A=REAL(6)`, `B=REAL(5)`, `A=A/B`, `B=REAL(3)`, `X=REAL(10)`, `B=B/X`,
  `X=A/B`, `PrintRE(X)` producing `4`,
  `A=REAL(2)`, `B=REAL(13)`, `A=A/B`, `C=REAL(1)`, `B=REAL(13)`, `C=C/B`,
  `X=A+C`, `PrintRE(X)` producing `0.2307692468166351318359375`,
  and `A=REAL(N)`, `N=0-2`, `B=REAL(N)`, `X=A/B`,
  `PrintRE(X)` with the first `N=0-3`; wide
  `REAL(<literal-or-expression>)` beyond the current grouped 16-bit bridge
  slice, and broader general REAL print formatting still need broader typed
  lowering and helper proofs.
- Broaden procedure/function semantics beyond the current local/external integer path.

## Structural Work Still Outstanding

- Move proc-local integer storage from the current proc-scoped static-slot model toward a real frame/local model.
- Continue widening compatibility toward historical ACTION! source behavior.
- Improve compiler-oriented diagnostics and error reporting on the real target.

## Next Milestones

1. Keep `make -C ../udos vice-action-actc` green on the current working tree.
2. Keep `make -C ../udos vice-action-actc-alink-launch-printmath` green as the named higher-level proof, while keeping `vice-action-actc-alink-compat-printmath` available as the helper-bearing compat gate.
3. Widen REAL beyond the current `R=A` and `R=A+B` / `R=A-B` / `R=A*B` / `R=A/B` slices into
   literals, other expression shapes, conversions, comparisons, and printing with
   per-operation runtime imports.
