# ACTC REU Overlay Pass Plan

Current as of `2026-04-23`.

## Goal

Turn `ACTC.PRG` from one large resident compiler image into a small batch driver
that runs compiler passes from reusable overlay memory.

The driver should keep only permanent services, source/table window helpers, and
the pass scheduler resident. Each compiler pass should be loaded into REU once,
copied into the same C64 execution window when needed, run, and then replaced by
the next pass.

## Proposed Shape

- `ACTC.PRG` remains the user-facing command.
- On startup, `ACTC.PRG` stages source and pass overlays into REU.
- One fixed C64 overlay execution window is reserved for pass code.
- The driver copies pass code from REU into that window with `svc_reu_read_sc0`.
- Each pass reads and writes REU-backed program data through stable helper ABI
  routines.
- Passes advance the representation instead of all passes sharing one resident
  code body.

## Data Model

- Source text: staged in REU and paged through source-reader windows.
- Symbols and names: REU-backed string tables with small resident windows.
- Procedure bodies: REU-backed `body_ops` windows.
- Literals and metadata: now REU-backed fixed-record tables for the current
  ACTC cold metadata set.
- Final object output: streamed through write begin/chunk/close services.

## Current Overlay Artifacts

The first artifacts are intentionally small and raw:

- `src/tools_udos/actc/actc_overlay_abi.inc` defines overlay ABI version `1`.
- `src/tools_udos/actc/actc_overlay_noop.asm` builds a no-op pass.
- `tools/build_actc_overlay_noop.sh` emits `build/udos_tools/ACTC_OVL0.BIN`.
- `src/tools_udos/actc/actc_overlay_source_header.asm` builds the first
  source-aware pass.
- `tools/build_actc_overlay_source_header.sh` emits
  `build/udos_tools/ACTC_OVL1.BIN`.
- `src/tools_udos/actc/actc_overlay_decl_counts.asm` builds the first
  declaration-scanning pass.
- `tools/build_actc_overlay_decl_counts.sh` emits
  `build/udos_tools/ACTC_OVL2.BIN`.
- The workspace exporter and UDOS release Makefile include `ACTC_OVL0.BIN`,
  `ACTC_OVL1.BIN`, and `ACTC_OVL2.BIN` next to `ACTC.PRG`, so pass files are
  present when the scheduler runs from an exported or release image.
- `tests/test_actc_overlay.py` proves the `ACOV` header, ABI version, pass id,
  `$A000` execution base, encoded byte length, no-op return sequence, and the
  source-header/declaration-count passes receiving the resident source-window
  context. The declaration-count pass also proves writing resident count state
  through explicit context pointers and writing module variable names/metadata,
  procedure export names, and procedure parameter/local names/metadata through
  the resident REU table helpers. It also emits module-scope decimal arithmetic
  and comparison/boolean initializer values in var metadata. It keeps an
  overlay-local declaration
  cache plus declaration initializer validation so duplicate names, malformed
  declaration tails, and invalid initializer tails return failed overlay status
  instead of partial success.
- `actc_overlay_run_pass` in `ACTC.PRG` accepts a pass id in `A`, finds a pass
  descriptor, stages that file into REU bank `$02`, copies it to `$A000`, passes
  a context block to the overlay in `X/Y`, banks out BASIC ROM for the call,
  executes it, and restores the previous memory configuration.
- `ACTC.PRG` now has a five-stage compile-path overlay handoff. When built with
  `ACTC_USE_SOURCE_HEADER_OVERLAY=1` and `ACTC_USE_DECL_OVERLAY=1`, it calls
  `ACTC_OVL1.BIN` for module-header validation and then `ACTC_OVL2.BIN` for
  declaration scanning. The current production path also stages `ACTC_OVL6.BIN`
  for proc-body lowering, `ACTC_OVL4.BIN` for runtime-import detection,
  `ACTC_OVL3.BIN` for payload layout, and `ACTC_OVL5.BIN` for streamed object
  emission; on
  success, later compiler phases consume the overlay-written REU metadata.
  Overlay staging uses the executable-relative tool ABI path prefix, so
  `!ACTC_OVL1.BIN` through `!ACTC_OVL6.BIN` resolve beside the launched
  `ACTC.PRG`.
- `tools/build_actc_overlay_body_collect.sh` now also builds
  `build/udos_tools/ACTC_OVL6.BIN`, pass id `6`, which is the current
  proc-body lowering overlay. It is packaged beside `ACTC.PRG` and enabled in
  the default production build.
- In the normal production build that path is now mandatory rather than
  best-effort: resident module-header parsing and resident declaration
  collection are compiled out, the build emits `ACTC_OVL1.BIN` and
  `ACTC_OVL2.BIN` automatically, and both overlays must be present beside
  `ACTC.PRG`.
- The overlay context includes a resident `load next source window` callback.
  `ACTC_OVL2.BIN` uses it to page source windows after the current committed
  window is consumed, while keeping a 24-bit source mark and a per-window
  remaining counter. This proves declaration scans can continue after the first
  `20480` byte source window. The target-side executable-relative overlay load
  path is now covered by release/VICE proofs, so the default build enables
  `ACTC_USE_DECL_OVERLAY=1`.
- The focused REU source-cache harness now also runs with declaration overlay
  collection by default. The wrap-edge cases that had blocked it are fixed in
  `ACTC_OVL2.BIN`.

The overlay execution window is `$A000-$BFFF`, which means the ACTC resident
driver must clear LORAM in `$0001` before calling overlay code and restore the
previous memory configuration after the pass returns. This keeps the existing
`$0900-$9FFF` tool window available while opening an 8 KiB pass-code window
under BASIC ROM.

## Initial Pass Split

1. `actc_p0_load`: validate project/module and stage source.
2. `actc_p1_decls`: collect module variables, procedure exports, params, and locals.
3. `actc_p2_body`: lower procedure bodies into REU-backed `body_ops`. Current
   production state: implemented in `ACTC_OVL6.BIN`.
4. `actc_p3_imports`: detect runtime imports and unresolved externals. Current
   production state: runtime-import detection is in `ACTC_OVL4.BIN`; unresolved
   external discovery still happens during resident body lowering.
5. `actc_p4_layout`: compute proc sizes, offsets, and literal offsets. Current
   production state: implemented in `ACTC_OVL3.BIN`.
6. `actc_p5_emit`: stream `AVO1` object output. Current production state:
   implemented in `ACTC_OVL5.BIN`.

## Why This Matters

The current REU table work increases the immediate development window, but a
full-feature compiler still should not require every parser and lowering routine
to be resident at the same time. Overlay passes let compiler features grow by
adding pass-specific code modules instead of consuming one fixed `$0900-$9FFF`
tool image.

## Next Engineering Steps

1. Keep the remaining ACTC metadata slab REU-backed and covered by capacity
   tests.
2. Split unresolved-external discovery and other follow-on body helpers away
   from `ACTC_OVL6.BIN` so later language growth does not refill the resident
   tool image.
3. Keep release packaging for every overlay binary next to `ACTC.PRG`.
4. Keep `ACTC -> ALINK -> AVMRUN` as the regression gate while each pass moves.
