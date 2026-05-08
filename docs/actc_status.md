# `ACTC` Status

Current as of `2026-04-25`.

This file is a focused ledger for the UDOS-native `ACTC.PRG` tool.
It is narrower and easier to update than the broad [action_matrix.md](/mnt/c/test/action/actionc64u/docs/action_matrix.md).

## Proven On The Committed Baseline

- [x] Launches from a UDOS Action workspace as `ACTC.PRG <module>`
- [x] Requires a loaded project and a tracked manifest entry
- [x] Reads `SRC/<NAME>.ACT` for the requested module
- [x] Validates the source `MODULE` header against the requested module name
- [x] Emits deterministic `AVO1` object text into `OBJ/<NAME>.OBJ`
- [x] Treats `.OBJ` as the primary project-object name while preserving legacy
  `.AVO` compatibility for downstream tools
- [x] Emits object-level source debug records:
  - `f 0 src/<module>.act`
  - `q <export_index> 0 <line> <col>`
  - `l <export_index> <body_op_index> 0 <line> <col>`
  - `V g <type> <var_index> <file_id> <line> <col>`
  - `V p <type> <export_index> <var_index> <file_id> <line> <col>`
  - `V l <type> <export_index> <var_index> <file_id> <line> <col>`
- [x] Emits compiler-owned export names plus offset/size metadata
- [x] Emits `body_ops`
- [x] Emits a minimal payload skeleton plus `payload_bytes`
- [x] Emits current inferred runtime-import lines
- [x] Supports the current narrow decimal print-expression subset for object emission
- [x] Integrated narrow proof exists through `ACTC -> ALINK -> AVMRUN`
- [x] Current shipped UDOS build links again under the real target after widening the tool load window from `$2000` to `$4000`

Current real-target build note:

- `./tools/build_actc_udos.sh` is green again
- `make -C ../udos vice-action-actc` is green again on the current working tree
- `make -C ../udos vice-action-actc-alink-launch` is green again as the
  helper-free higher-level default launch path on the current working tree
- `make -C ../udos vice-action-actc-alink-launch-printmath` is green again
  as the named imported `printmath` direct-launch proof on the current working
  tree
- `make -C ../udos vice-action-actc-alink-compat-printmath` remains the
  helper-bearing compat replay target for the same shape
- current shipped `ACTC` map footprint is:
  - `CODE`: `$3838`
  - `BSS`: `$0318`
  - total runtime span from `$0900` through `$444F`
  - free bytes below the current resident floor `$4AFE`: `1707`
- current shipped `ACTC` file footprint is:
  - `ACTC.PRG`: `14394` bytes
  - `ACTC_REU.PRG`: `31485` bytes
  - `ACTC_OVL0.BIN`: `48` bytes
  - `ACTC_OVL1.BIN`: `357` bytes
  - `ACTC_OVL2.BIN`: `4663` bytes
  - `ACTC_OVL3.BIN`: `605` bytes
  - `ACTC_OVL4.BIN`: `235` bytes
  - `ACTC_OVL5.BIN`: `1930` bytes
  - `ACTC_OVL6.BIN`: `5056` bytes
  - total current overlay payload: `12894` bytes
- current shipped `ACTC` link window is `$0900-$9FFF`
- current shipped `ACTC` build now uses:
  - `ACTC_REU_SOURCE_CACHE=1`
  - `ACTC_REU_TABLES=1`
  - `ACTC_REU_BODY_OPS=1`
  - `ACTC_REU_STRING_LITERALS=1`
  - `ACTC_REU_VAR_NAMES=1`
  - `ACTC_REU_EXPORT_NAMES=1`
  - `ACTC_REU_INT_LITERALS=1`
  - `ACTC_KEEP_BODY_RESIDENT_FALLBACK=0`
  - `ACTC_REU_VAR_META=1`
  - `ACTC_REU_PROC_META=1`
  - `ACTC_REU_VAR_DEBUG=1`
  - `ACTC_REU_LAYOUT_META=1`
  - `ACTC_REU_STRING_OFFSETS=1`
  - `ACTC_USE_BODY_OVERLAY=1`
  - `STREAM_OUTPUT=1`
  - `CONTENT_BUFFER_SIZE=16`
  - `OUTPUT_CHUNK_SIZE=128`
  - `SOURCE_LIMIT=3328`
  - `SOURCE_LOOKAHEAD=255`
  - `BODY_OPS_STRIDE=255`
  - `INT_LITERAL_MAX=36`
  - `STRING_LITERAL_MAX=36`
  - `EXPORT_MAX=16`
  - `EXTERNAL_MAX=36`
  - `LOOP_MAX=16`
- current shipped REAL-to-INT proof surface includes:
  - `A=REAL(3)`, `B=REAL(2)`, `A=A/B`, `X=INT(A)` -> `1`
  - `N=0-3`, `A=REAL(N)`, `B=REAL(2)`, `A=A/B`, `X=INT(A)` -> `-1`
  - `A=REAL(1)`, `B=REAL(3)`, `A=A/B`, `X=INT(A)` -> `0`
  - `N=0-1`, `A=REAL(N)`, `B=REAL(3)`, `A=A/B`, `X=INT(A)` -> `0`
  - `A=REAL(1)`, `B=REAL(10)`, `A=A/B`, `B=REAL(10)`, `A=A*B`,
    `X=INT(A)` -> `1`
  - `A=REAL(32767)`, `X=INT(A)` -> `32767`
  - `A=REAL(0-32768)`, `X=INT(A)`, `B=REAL(X)`, `A=B` -> `1`
  - `A=REAL(32768)`, `X=INT(A)` -> runtime `REAL->INT RANGE`
  - `A=REAL(0-32768)`, `B=REAL(1)`, `A=A-B`, `X=INT(A)` -> runtime
    `REAL->INT RANGE`
- current shipped `ACTC` stores the unresolved external-name table in REU
  through `svc_reu_read_sc0` / `svc_reu_write_sc0`; only the 25-byte active
  external-name window remains resident
- current shipped `ACTC` stores procedure `body_ops` streams in REU at
  `$00D000`, keeping only one `BODY_OPS_STRIDE` active body window resident and
  flushing dirty procedure bodies through `svc_reu_write_sc0`
- current shipped `ACTC` also stores string literals at `$00E000`, variable
  names at `$00E400`, and export names at `$00E600`, each behind one small
  resident active window
- current shipped `ACTC` also stores integer literals at `$00E800`, variable
  metadata at `$00E900`, procedure parameter/local metadata at `$00EA00`,
  procedure layout metadata at `$00EB00`, and string offsets at `$00EC00`,
  each behind a small resident active window or fixed-record staging slot
- current shipped `ACTC` also stores procedure declaration debug offsets at
  `$00ED00`, body-op debug offsets at `$00EE00`, and variable declaration
  debug offsets at `$00EF00`, so object emission can format `q`, `l`,
  typed `V g`, `V p`, and `V l` source debug records without keeping those
  tables resident
- `tests/test_actc_capacity.py` proves production `ACTC.PRG` stages and
  compiles a `49152` byte source module through the REU source-cache path under
  the tool ABI harness, with `PROC MAIN()` discovered near offset `49120` in the
  third REU-backed source window, and also proves the production REU table
  writes/reads for `body_ops`, string literals, export names, layout metadata,
  and string offsets
- `tests/test_actc_capacity.py` also proves production `ACTC.PRG` streams an
  `OBJ/MAIN.OBJ` larger than the legacy `640` byte object buffer through
  `svc_file_write_begin_sc0`, `svc_file_write_chunk_sc0`, and
  `svc_file_write_close_sc0`, while exercising REU-backed variable names,
  variable metadata, procedure metadata, and integer literals
- `tests/test_actc_capacity.py`, `tests/test_actc_overlay.py`, and
  `tests/test_actc_reu_source_cache.py` now also prove the emitted `f`, `q`,
  `l`, typed `V g`, `V p`, and `V l` object debug records and the REU writes
  that back the procedure/body/variable source mapping tables
- current end-to-end REAL print/runtime proof surface also includes signed
  arithmetic cases:
  - `-1.5 * 2.0 = -3.0`
  - `1.5 * -2.0 = -3.0`
  - `-1.5 * -2.0 = 3.0`
  - `-3.0 / 2.0 = -1.5`
  - `3.0 / -2.0 = -1.5`
  - `-3.0 / -2.0 = 1.5`
  - `1.5 * 1.5 = 2.25`
  - `0.75 * 0.75 = 0.5625`
  - `1.5 / 1.5 = 1.0`
  - `1.5 / 0.75 = 2.0`
  - `1.0 / 3.0 = 0.3333333432674407958984375`
  - `1.0 / 9.0 = 0.111111111938953399658203125`
  - `2.0 / 9.0 = 0.22222222387790679931640625`
  - `1.0 / 11.0 = 0.0909090936183929443359375`
  - `2.0 / 11.0 = 0.181818187236785888671875`
  - `1.0 / 13.0 = 0.076923079788684844970703125`
  - `2.0 / 13.0 = 0.15384615957736968994140625`
  - `1.0 / 17.0 = 0.0588235296308994293212890625`
  - `2.0 / 17.0 = 0.117647059261798858642578125`
  - `1.0 / 19.0 = 0.052631579339504241943359375`
  - `2.0 / 19.0 = 0.10526315867900848388671875`
  - `1.0 / 23.0 = 0.0434782616794109344482421875`
  - `2.0 / 23.0 = 0.086956523358821868896484375`
  - `2.0 / 3.0 = 0.666666686534881591796875`
  - `1.0 / 7.0 = 0.14285714924335479736328125`
  - `1.0 / 10.0 = 0.100000001490116119384765625`
  - `(1.0 / 10.0) + (1.0 / 5.0) = 0.300000011920928955078125`
  - `((1.0 / 10.0) + (1.0 / 5.0)) + (1.0 / 5.0) = 0.5`
  - `(1.0 / 2.0) - (1.0 / 10.0) = 0.4000000059604644775390625`
  - `((1.0 / 10.0) + (1.0 / 10.0)) - (1.0 / 5.0) = 0.0`
  - `((1.0 / 10.0) + (1.0 / 10.0) + (1.0 / 10.0)) * 10.0 = 3.0`
  - `(2.0 / 13.0) + (1.0 / 13.0) = 0.2307692468166351318359375`
  - `(2.0 / 17.0) + (1.0 / 17.0) = 0.17647059261798858642578125`
  - `(2.0 / 19.0) + (1.0 / 19.0) = 0.15789473056793212890625`
  - `(2.0 / 23.0) + (1.0 / 23.0) = 0.1304347813129425048828125`
  - `(1.0 / 7.0) * 7.0 = 1.0`
  - `(1.0 / 9.0) * 9.0 = 1.0`
  - `(1.0 / 11.0) * 11.0 = 1.0`
  - `(1.0 / 13.0) * 13.0 = 1.0`
  - `(1.0 / 17.0) * 17.0 = 1.0`
  - `(1.0 / 19.0) * 19.0 = 1.0`
  - `(1.0 / 23.0) * 23.0 = 1.0`
  - `(1.0 / 5.0) * (1.0 / 5.0) = 0.0400000028312206268310546875`
  - `(1.0 / 10.0) / (1.0 / 5.0) = 0.5`
  - `(1.0 / 17.0) / (2.0 / 17.0) = 0.5`
  - `(1.0 / 19.0) / (2.0 / 19.0) = 0.5`
  - `(1.0 / 23.0) / (2.0 / 23.0) = 0.5`
  - `(6.0 / 5.0) / (3.0 / 10.0) = 4.0`
  - `(1.0 / 3.0) * 3.0 = 1.0`
  - `(1.0 / 10.0) * 10.0 = 1.0`
- `tests/test_actc_overlay.py` proves the first ACTC pass-overlay artifact:
  `tools/build_actc_overlay_noop.sh` builds raw `ACTC_OVL0.BIN` with `ACOV`
  magic, overlay ABI version `1`, pass id `0`, execution base `$A000`, and a
  no-op entry that returns status `0`
- `tests/test_actc_overlay.py` also proves the first useful ACTC pass overlay:
  `tools/build_actc_overlay_source_header.sh` builds `ACTC_OVL1.BIN`, pass id
  `1`, which receives the source-window context plus a pointer to the requested
  module name, validates the `MODULE <name>` header against that requested
  name, reports the consumed source offset through the context source mark
  fields, and returns a diagnostic pointer when the module header is invalid
- `tests/test_actc_overlay.py` also proves a declaration-count overlay:
  `tools/build_actc_overlay_decl_counts.sh` builds `ACTC_OVL2.BIN`, pass id
  `2`, which receives the source-window context, scans top-level declarations
  in the current source window, reports module scalar declaration and procedure
  declaration counts, writes those counts back into resident `ACTC` count
  fields through context pointers, writes module variable names into the
  REU-backed var-name table, writes initial var metadata, including
  module-scope decimal arithmetic and comparison/boolean initializer values,
  into the REU-backed
  var-meta table, writes procedure export names into the REU-backed export-name
  table, parses procedure parameter lists and procedure-local scalar
  declarations, appends parameter/local names and metadata to the REU-backed
  variable tables, writes procedure param/local count/base metadata into the
  REU-backed proc-meta table, rejects duplicate module vars, duplicate procedure
  exports, duplicate params, param/module collisions, local/param collisions,
  duplicate locals, malformed declaration names/tails, empty or unterminated
  initializer tails, trailing initializer operators, and REAL initializers, and
  leaves the final source offset in the source mark fields
- `tests/test_actc_overlay.py` also proves the first resident ACTC overlay
  scheduler: `actc_overlay_run_pass` accepts a pass id in `A`, finds the pass
  descriptor, stages `ACTC_OVL0.BIN`, `ACTC_OVL1.BIN`, or `ACTC_OVL2.BIN` into
  REU bank `$02`, copies it into
  `$A000`, clears LORAM so `$0001` changes from `$37` to `$36` for the call,
  passes an ACTC context block to the overlay in `X/Y`, executes the overlay,
  receives context status `0` plus return status `0`, and restores `$0001` to
  `$37`
- `tests/test_actc_overlay.py` also proves the first real compile-path overlay
  chain: building `ACTC.PRG` with `ACTC_USE_SOURCE_HEADER_OVERLAY=1` and
  `ACTC_USE_DECL_OVERLAY=1` runs `ACTC_OVL1.BIN` for module-header validation,
  then `ACTC_OVL2.BIN` for declaration scanning, and the overlay-generated var
  metadata is used by the later object emitter. Overlay staging uses the
  executable-relative tool ABI path prefix: `!ACTC_OVL1.BIN` and
  `!ACTC_OVL2.BIN` resolve beside the launched `ACTC.PRG`.
- `tests/test_actc_overlay.py` now also proves the later production overlay
  passes: `ACTC_OVL3.BIN`, pass id `3`, computes REU-backed proc layout and
  string offsets; `ACTC_OVL4.BIN`, pass id `4`, detects runtime import flags by
  calling the resident source-pattern finder through the overlay ABI;
  `ACTC_OVL5.BIN`, pass id `5`, streams `AVO1` object emission by using resident
  pointer-setter, REU-window-loader, and append-byte callbacks; and
  `ACTC_OVL6.BIN`, pass id `6`, now owns the default proc-body lowering path.
  The full compile path now stages `ACTC_OVL1.BIN`, `ACTC_OVL2.BIN`,
  `ACTC_OVL6.BIN`, `ACTC_OVL4.BIN`, `ACTC_OVL3.BIN`, and `ACTC_OVL5.BIN`
  during a normal compile.
- `ACTC_OVL6.BIN` now also owns its loop stack locally. The default build no
  longer keeps the resident loop push/pop helpers or the resident loop-stack
  BSS just to support overlayed proc-body lowering.
- `ACTC_OVL6.BIN` now also emits current-proc parameter bind ops directly after
  loading proc metadata through the overlay ABI. The default build no longer
  keeps the resident proc-param bind helper only to support overlayed body
  lowering.
- `ACTC_OVL6.BIN` now also lowers the current module-scope REAL assignment
  slice directly. The default build no longer keeps the resident REAL
  assignment helper or its resident scratch bytes only to support overlayed
  proc-body lowering.
- `ACTC_OVL6.BIN` now also owns the direct grouped/widened REAL integer bridge
  assignment path, so the default build no longer keeps the resident
  direct-REAL-assignment helper block only to support overlayed body lowering.
- `ACTC_OVL6.BIN` now also passes the condition/print body op marker in `A`
  to two generic resident callbacks. The default build no longer keeps the five
  resident body wrapper helpers for `IF`, `UNTIL`, `DO WHILE`, `PRINTI`, and
  `PRINTIE` just to support the overlay path.
- `ACTC_OVL2.BIN` now has source-window paging support through the overlay ABI.
  The resident compiler passes a `load next source window` callback in the
  context block, and the overlay maintains a 24-bit source mark plus a current
  window remaining counter so declarations after the first `20480` byte source
  window can be scanned. The executable-relative overlay load path is now
  covered by release/VICE proofs, so the normal `tools/build_actc_udos.sh`
  build defaults `ACTC_USE_DECL_OVERLAY` to `1`.
- The normal production build now treats the source-header and declaration
  overlays as required: when `ACTC_USE_SOURCE_HEADER_OVERLAY=1` and
  `ACTC_USE_DECL_OVERLAY=1` with the REU source cache enabled, resident module
  header parsing and declaration collection are compiled out,
  `tools/build_actc_udos.sh` builds `ACTC_OVL1.BIN` and `ACTC_OVL2.BIN`
  automatically, and both overlays must be present beside `ACTC.PRG`.
- `tests/test_actc_overlay.py` also proves unknown pass ids fail before any
  file/REU operations, leaving context status as failed
- `tools/export_udos_workspace.py` and `../udos/Makefile` now package
  `ACTC_OVL0.BIN` through `ACTC_OVL6.BIN` beside `ACTC.PRG`, so exported
  workspaces and release disks carry every overlay file currently built for the
  ACTC scheduler and body-overlay bring-up work
- `tests/test_actc_reu_source_cache.py` proves the same source-cache ABI stages
  source beyond `20480` bytes into simulated REU, pages later windows back into
  `source_buffer`, and emits `OBJ/MAIN.OBJ` when the `PROC MAIN` name crosses
  the first compile-window boundary or a `PrintE` string literal crosses that
  boundary, and when long inline spaces before a `PrintIE` literal cross that
  boundary
- `tests/test_actc_reu_source_cache.py` also proves a long `PrintIE(...)`
  expression with a symbol token crossing the boundary can commit an 8-bit `Y`
  lookahead wrap, preserve parser registers across the REU read service, and
  continue parsing from the next window
- `tests/test_actc_reu_source_cache.py` also proves the boolean pre-scan no
  longer silently wraps inside the same window: a `PrintIE(1 ... AND 1)` line
  with `AND` beyond an 8-bit `Y` wrap is routed to the boolean parser and
  compiled across the REU boundary
- `tests/test_actc_reu_source_cache.py` also proves failed boolean keyword
  probes restore the original REU source window before falling back to normal
  expression parsing, so a long-space `PrintIE(...)` expression can continue on
  a variable symbol after the probe crosses the first window boundary
- `tests/test_actc_reu_source_cache.py` also proves assignment parsing can
  preserve the `=` operator position after variable lookup and advance past an
  operator sitting at an 8-bit `Y` wrap before parsing the right-hand side
- `tests/test_actc_reu_source_cache.py` also proves procedure parameter parsing
  can advance past an opening `(` sitting at an 8-bit `Y` wrap and continue
  reading parameters from the next REU-backed reader position
- `tests/test_actc_reu_source_cache.py` also proves runtime and constant
  parenthesized comparison left-hand-side speculation can cross an 8-bit `Y`
  wrap, restore the original REU source window, and reinterpret `(expr)` as the
  left side of `=`
- `tests/test_actc_reu_source_cache.py` now stays green with the declaration
  overlay enabled in the focused REU source-cache harness. The former wrap-edge
  failures are covered: procedure parameter parsing now tolerates the `(` after
  a long cross-window space run, and the simple initializer evaluator now
  preserves grouped constant comparisons across a `Y` wrap.

Current lowering note:

- [x] proc-local `INT` declarations currently lower to proc-scoped static slots plus declaration-site runtime init stores; this is not a stack-frame model yet
- [x] current harness-proven variable slot ceiling is `16`, aligned with the current VM local-slot count
- [x] module-scope `REAL` declarations now emit 4-byte storage-width metadata
- [x] exact-zero module-scope `REAL` initialization now lowers through the
  integer zero literal path:
  `REAL X=[0]`
- [x] direct REAL copy assignment now supports `R=A` for module-scope
  `REAL` variables, emitting low/high word load/store ops with no runtime import
- [x] exact-zero module-scope `REAL` assignment now lowers without a runtime
  helper:
  `REAL X`, `X=0`
- [x] first narrow non-zero integer-to-REAL body assignment bridge now lowers
  small non-negative integer expressions such as `X=7` and `X=(1+2*3)` to two
  integer literals plus `T`/`S`, with no REAL runtime import
- [x] wider non-negative integer-to-REAL body assignment now lowers larger
  literals and grouped `+`/`-` expressions such as `X=256` and `X=(255+1)`
  through only `RT_I_TO_F` / `rt_i_to_f`
- [x] narrow signed direct integer-to-REAL body assignment now lowers
  `0-<positive word expr>` such as `X=0-256` through only `RT_S_TO_F` /
  `rt_s_to_f`
- [x] narrow `BYTE`/`CARD` variable-to-REAL body assignment now lowers through
  only `RT_I_TO_F` / `rt_i_to_f`, for example
  `CARD A=[255]`, `A=A+1`, `REAL X`, `X=A`
- [x] narrow signed `INT` variable-to-REAL body assignment now lowers through
  only `RT_S_TO_F` / `rt_s_to_f`, for example
  `INT A=[0]`, `A=0-7`, `REAL X`, `X=A`
- [x] narrow explicit `REAL(<integer var>)` body conversion now lowers through
  the same helper selected by source var type, for example
  `CARD A=[255]`, `A=A+1`, `REAL X`, `X=REAL(A)` and
  `INT A=[0]`, `A=0-7`, `REAL X`, `X=REAL(A)`
- [x] narrow explicit `REAL(<integer expression>)` body conversion now lowers
  through the same bridge helpers for the first proven constant-expression
  cases, for example `REAL X`, `X=REAL(255+1)` and
  `REAL X`, `X=REAL(32767)`, and `REAL X`, `X=REAL(0-256)`; the first wide
  `*` / `/` bridge cases now lower too, for example `REAL X`, `X=REAL(512/2)`
- [x] narrow REAL condition lowering now imports only `RT_F_CMP` /
  `rt_f_cmp` for the current proven module-scope compare cases:
  `REAL A`, `REAL B`, `REAL C`, then `IF A<B THEN`, `IF B=C THEN`,
  `IF C>=B THEN`, `IF A<>C THEN`, `IF B>A THEN`, and `IF A<=B THEN`
- [x] narrow `PrintR` / `PrintRE` body lowering now imports only
  `RT_PRINT_F` / `rt_print_f` for the current proven REAL print cases,
  including integral, fractional, signed, and first low-word-nonzero dyadic
  values such as
  `REAL X`, `X=REAL(7)`, `PrintRE(X)`,
  `REAL A`, `REAL B`, `REAL X`, `A=REAL(3)`, `B=REAL(2)`, `X=A/B`,
  `PrintRE(X)`, `X=X/B`, `PrintRE(X)`, `REAL A`, `REAL B`, `REAL X`,
  `A=REAL(1)`, `B=REAL(8)`, `X=A/B`, `PrintRE(X)`, `INT N=[0]`, `N=0-1`,
  `REAL A`, `REAL B`, `REAL X`, `A=REAL(N)`, `B=REAL(2)`, `X=A/B`,
  `PrintRE(X)`, `REAL A`, `REAL B`, `REAL X`, `A=REAL(1)`,
  `B=REAL(32)`, `X=A/B`, `PrintRE(X)`, `REAL A`, `REAL B`, `REAL X`,
  `A=REAL(1)`, `B=REAL(64)`, `X=A/B`, `PrintRE(X)`, `REAL A`,
  `REAL B`, `REAL X`, `A=REAL(1)`, `B=REAL(256)`, `X=A/B`,
  `PrintRE(X)`, `REAL A`, `REAL B`, `REAL X`, `A=REAL(1)`,
  `B=REAL(32768)`, `X=A/B`, `PrintRE(X)`, `REAL A`, `REAL B`,
  `REAL X`, `A=REAL(129)`, `B=REAL(256)`, `X=A/B`,
  `PrintRE(X)`, and first arithmetic print cases such as
  `REAL A`, `REAL B`, `REAL X`, `A=REAL(3)`, `B=REAL(2)`, `X=A/B`,
  `A=A/B`, `X=X+A`, `PrintRE(X)`, `INT N=[0]`, `N=0-1`, `REAL A`,
  `REAL B`, `REAL X`, `A=REAL(4)`, `B=REAL(N)`, `X=A+B`,
  `PrintRE(X)`, `INT N=[0]`, `N=0-4`, `REAL A`, `REAL B`,
  `REAL X`, `A=REAL(1)`, `B=REAL(N)`, `X=A+B`, `PrintRE(X)`,
  `INT N=[0]`, `N=0-1`, `REAL A`, `REAL B`, `REAL X`,
  `A=REAL(N)`, `B=REAL(4)`, `X=A+B`, `PrintRE(X)`, `REAL A`,
  `REAL B`, `REAL X`, `A=REAL(4)`, `B=REAL(1)`, `X=A-B`,
  `PrintRE(X)`, `INT N=[0]`, `N=0-1`, `REAL A`, `REAL B`,
  `REAL X`, `A=REAL(4)`, `B=REAL(N)`, `X=A-B`, `PrintRE(X)`,
  `INT N=[0]`, `N=0-1`, `REAL A`, `REAL B`, `REAL X`,
  `A=REAL(N)`, `B=REAL(4)`, `X=A-B`, `PrintRE(X)`, and
  `REAL A`, `REAL B`, `REAL X`, `A=REAL(3)`, `B=REAL(2)`,
  `A=A/B`, `X=A*B`, `PrintRE(X)`, `INT N=[0]`, `N=0-3`, `REAL A`,
  `REAL B`, `REAL X`, `A=REAL(N)`, `B=REAL(2)`, `A=A/B`, `X=A*B`,
  `PrintRE(X)`, `REAL A`, `REAL B`, `REAL X`, `A=REAL(3)`, `B=REAL(2)`,
  `A=A/B`, `N=0-2`, `B=REAL(N)`, `X=A*B`, `PrintRE(X)`,
  `INT N=[0]`, `N=0-3`, `REAL A`, `REAL B`, `REAL X`, `A=REAL(N)`,
  `B=REAL(2)`, `A=A/B`, `N=0-2`, `B=REAL(N)`, `X=A*B`, `PrintRE(X)`,
  `INT N=[0]`, `N=0-3`, `REAL A`, `REAL B`, `REAL X`, `A=REAL(N)`,
  `B=REAL(2)`, `X=A/B`, `PrintRE(X)`, `REAL A`, `REAL B`, `REAL X`,
  `A=REAL(3)`, `N=0-2`, `B=REAL(N)`, `X=A/B`, `PrintRE(X)`, and
  `INT N=[0]`, `N=0-3`, `REAL A`, `REAL B`, `REAL X`, `A=REAL(N)`,
  `N=0-2`, `B=REAL(N)`, `X=A/B`, `PrintRE(X)`
- [x] the positive 16-bit bridge parser now carries the first proven `*` / `/`
  precedence cases for REAL lowering, for example `REAL X`, `X=(128*2)`, and
  `REAL X`, `X=REAL(512/2)`
- [x] the first REAL expression-lowering slices support `R=A+B`, `R=A-B`,
  `R=A*B`, and `R=A/B` for module-scope `REAL` variables, emitting low/high
  word body ops plus only the matching `RT_F_ADD`, `RT_F_SUB`, `RT_F_MUL`, or
  `RT_F_DIV` runtime import
- [x] `REAL` variables are guarded from the current 16-bit integer expression
  path; non-zero initializers, integer-path reads, integer-path writes, and
  unsupported REAL operators are rejected until their typed lowering lands
- [x] wide `REAL` integer bridge support is still intentionally bounded:
  the current proven surface now covers direct and explicit grouped 16-bit
  `+`, `-`, `*`, and `/` bridge cases such as `X=(128*2)`,
  `X=0-(128*2)`, `X=REAL(128*2)`, `X=REAL(32767)`, and
  `X=REAL(0-(512/2))`; the positive 16-bit boundary direct-assignment case
  `X=32767` is also proven; broader `REAL(<literal-or-expression>)` lowering
  beyond that slice still depends on wider typed lowering

## Proven Narrow Source Surface

- [x] `MODULE <name>`
- [x] top-level `PROC` discovery for current object emission flow
- [x] `PrintI(...)`
- [x] `PrintIE(...)`
- [x] inline-space tolerant decimal arithmetic for the current narrow path
- [x] `+`
- [x] `-`
- [x] `*`
- [x] `/`
- [x] parenthesized grouping in the current narrow expression path
- [x] simple comparisons:
  `=`, `<>`, `<`, `<=`, `>`, `>=`
- [x] `IF ... THEN ... FI`
- [x] `IF ... THEN ... ELSE ... FI`
- [x] nested `IF ... THEN ... FI`
- [x] nested `IF ... THEN ... ELSE ... FI`
- [x] explicit `RETURN`
- [x] `DO ... UNTIL ... OD`
- [x] local and unresolved-external calls inside `DO ... UNTIL ... OD`
- [x] `IF ... THEN ... ELSE ... FI` inside `DO ... UNTIL ... OD`
- [x] local branch calls inside `DO ... UNTIL ... OD`
- [x] unresolved-external branch calls inside `DO ... UNTIL ... OD`
- [x] nested `DO ... UNTIL ... OD`
- [x] local and unresolved-external calls inside nested `DO ... UNTIL ... OD`
- [x] `DO ... UNTIL ... OD` containing nested `WHILE ... DO ... OD`
- [x] `WHILE ... DO ... OD` containing nested `DO ... UNTIL ... OD`
- [x] mixed local/external and branch content across `DO`/`WHILE` mixed nesting
- [x] first REAL add/subtract/multiply/divide assignment lowering:
  `REAL A`, `REAL B`, `REAL R`, `R=A+B`, `R=A-B`, `R=A*B`, and `R=A/B`

## Current Widening Work

- [ ] broader runtime-emitted integer expression chains beyond the already-proven narrow path
- [ ] larger statement/control-flow surface beyond the current `IF`/`ELSE`/`WHILE ... DO ... OD`/`DO ... UNTIL ... OD`/nested-loop/branch-combined path
- [ ] broader stateful variable surface beyond the current multi-var module-scope
  `INT`, narrow `BYTE`/`CARD`, and declaration-only 4-byte `REAL` slices
- [ ] broader procedure/function surface beyond the current local/external integer arg/return slice
- [ ] full historical ACTION! source compatibility

## Harness-Proven Current Widening Line

- [x] additive integer print chains:
  `PrintI(50 + 7 - 3)`
- [x] additive integer print-expression chains in `PrintIE(...)`:
  `PrintIE(60 - 3 + 2)`
- [x] mixed-precedence integer print chains:
  `PrintI(2 + 3 * 4)`
- [x] parenthesized integer print-expression chains:
  `PrintIE((20 - 5) / 3)`
- [x] arithmetic/comparison mixes in print-expression chains:
  `PrintIE((2 + 3) * 4 = 20)` and `PrintIE((2 + 3 * 4) > 10)`
- [x] direct comparison operator print-expression chains:
  `PrintIE(2 <> 3)`, `PrintIE(2 < 3)`, `PrintIE(3 <= 3)`, `PrintIE(4 >= 3)`
- [x] string-literal pool indices widened through `Z` on the harness line with dead-stripped locals:
  `PROC F() PrintE("0") ... PrintE("Y") RETURN` and `PROC MAIN() PrintE("Z") RETURN`
- [x] integer-literal pool indices widened through `Z` on the harness line with dead-stripped locals:
  `PROC F() PrintIE(0..30) RETURN`, `PROC G() PrintIE(31..34) RETURN`, `PROC MAIN() PrintIE(35) RETURN`
- [x] dense local-call proc bodies widened beyond the old `96`-char harness ceiling:
  `PROC MAIN() T() ... T() PrintIE(X) RETURN` with `74` local calls in one body
- [x] compiler-emitted export offsets now print past `255` on the harness line:
  `PROC T() RETURN`, `PROC F() T() ...`, `PROC G() T() ...`, `PROC MAIN() PrintE("OK") RETURN`, proving `x main 261 7` in one `AVO1`
- [x] compiler-emitted proc sizes now print past `255` on the harness line:
  `PROC BIG() PrintI(X) ... RETURN`, `PROC MAIN() PrintE("OK") RETURN`, proving `x big 0 259`
- [x] high string-index control flow under `IF/ELSE`:
  `IF 1 = 0 THEN ... ELSE PrintE("I") ... PrintE("P") FI`
- [x] high string-index loop bodies:
  `DO PrintE("A") ... PrintE("P") UNTIL 1 = 1 OD`
- [x] high string-index loop bodies combined with `IF/ELSE`:
  `DO IF 1 = 0 THEN PrintE("A") ... ELSE PrintE("I") ... PrintE("P") FI UNTIL 1 = 1 OD`
- [x] high int-index control flow under `IF/ELSE`:
  `IF 1 = 0 THEN PrintIE(0..7) ELSE PrintIE(8..15) FI`
- [x] high int-index loop bodies combined with `IF/ELSE`:
  `DO IF 1 = 0 THEN PrintIE(0..7) ELSE PrintIE(8..15) FI UNTIL 1 = 1 OD`
- [x] high string indices mixed with unresolved externals under branch control:
  `IF 1 = 1 THEN W() PrintE("A") ... PrintE("L") ELSE PrintE("BAD") FI`
- [x] high string indices mixed with transitive externals under branch control:
  `IF 1 = 1 THEN W() PrintE("A") ... PrintE("L") ELSE PrintE("BAD") FI` with `W -> Z`
- [x] high string indices mixed with shared transitive externals under branch control:
  `IF 1 = 1 THEN W() Q() PrintE("A") ... PrintE("L") ELSE PrintE("BAD") FI` with `W -> Z` and `Q -> Z`
- [x] high string indices beyond the old 16-literal root ceiling under shared transitive branch control:
  `IF 1 = 1 THEN W() Q() PrintE("A") ... PrintE("P") ELSE PrintE("BAD") FI` with `W -> Z` and `Q -> Z`
- [x] high string indices mixed with shared transitive externals inside loop control:
  `DO W() Q() PrintE("A") ... PrintE("J") UNTIL 1 = 1 OD` with `W -> Z` and `Q -> Z`
- [x] high string indices mixed with nested branch + shared transitive externals:
  `IF 1 = 1 THEN IF 2 + 3 * 4 > 10 THEN W() Q() PrintE("A") ... PrintE("H") ELSE ... FI ELSE ... FI`
- [x] high string indices mixed with nested-loop external control:
  `DO WHILE 1 = 0 DO PrintE("BAD") OD W() PrintE("A") ... PrintE("J") UNTIL 1 = 1 OD`
- [x] full high int indices inside nested loop + `IF/ELSE` control:
  `DO WHILE 1 = 0 DO OD IF 1 = 0 THEN PrintIE(0..7) ELSE PrintIE(8..15) FI UNTIL 1 = 1 OD`
- [x] full high string indices inside nested loop + `IF/ELSE` control:
  `DO WHILE 1 = 0 DO OD IF 1 = 0 THEN PrintE("A") ... PrintE("H") ELSE PrintE("I") ... PrintE("P") FI UNTIL 1 = 1 OD`
- [x] arithmetic/comparison conditions inside `IF ... THEN ... ELSE ... FI`:
  `IF 2 + 3 * 4 > 10 THEN ... ELSE ... FI`
- [x] module-scope integer variable declaration plus direct read/assignment:
  `INT X=[0]`, `PrintIE(X)`, `X=X+1`, `PrintIE(X)`
- [x] module-scope integer variable state carried through loop control:
  `DO PrintIE(X) X=X+1 UNTIL X=2 OD`
- [x] module-scope integer variables driving branch control:
  `IF X=1 THEN ... ELSE ... FI`
- [x] module-scope integer variables driving `WHILE ... DO ... OD`:
  `WHILE X<2 DO ... OD`
- [x] module-scope integer variables driving local/external calls under control flow:
  `IF X=1 THEN HELLO() ...`, `IF X=2 THEN W() FI`, `WHILE X<1 DO W() ... OD`
- [x] multiple module-scope integer variables in one module:
  `INT X=[0]`, `INT Y=[2]`, `PrintIE(X)`, `PrintIE(Y)`, `X=Y+1`
- [x] narrow module-scope `BYTE`/`CARD` declarations lower through the existing
  16-bit variable slot path:
  `BYTE X=[0]`, `CARD Y=[2]`, `PrintIE(X)`, `PrintIE(Y)`, `X=Y+1`
- [x] module-scope `REAL` declarations emit a 4-byte variable slot without
  importing unused REAL runtime operators:
  `REAL X`, `PrintIE(7)`
- [x] exact-zero module-scope `REAL` initialization lowers through the existing
  zero literal path without importing a REAL helper:
  `REAL X=[0]`
- [x] module-scope `REAL` copy assignment imports no runtime helper:
  `R=A` emits `L`, `U`, `T`, and `S` body ops only
- [x] exact-zero module-scope `REAL` assignment imports no runtime helper:
  `X=0` emits `p`, `p`, `T`, and `S` body ops only
- [x] module-scope `REAL` add/subtract/multiply/divide assignment imports only the
  operator used:
  `R=A+B` imports `RT_F_ADD`; `R=A-B` imports `RT_F_SUB`; `R=A*B` imports
  `RT_F_MUL`; `R=A/B` imports `RT_F_DIV`
- [x] unsafe current-stage REAL use is rejected:
  non-zero REAL initializers, `PrintIE(X)`, and non-zero integer-path writes
  where `X` is REAL
- [x] variable-to-variable arithmetic assignment:
  `X=X+Y`
- [x] multiple module-scope integer variables driving `WHILE ... DO ... OD`:
  `WHILE X<Y DO ... OD`
- [x] multiple module-scope integer variables driving local/external calls under branch control:
  `IF X<Y THEN HELLO() W() FI`
- [x] multiple module-scope integer variables driving shared-transitive external closure under branch control:
  `IF X<Y THEN W() Q() FI` with `W -> Z` and `Q -> Z`
- [x] multiple module-scope integer variables driving shared-transitive external closure under `WHILE` control:
  `WHILE X<Y DO W() Q() X=X+1 OD` with `W -> Z` and `Q -> Z`
- [x] direct comparison operator conditions inside `IF ... THEN ... FI`:
  `IF 2 <> 3 THEN ... FI`, `IF 2 < 3 THEN ... FI`, `IF 3 <= 3 THEN ... FI`, `IF 4 >= 3 THEN ... FI`
- [x] direct comparison operator conditions inside loop forms:
  `DO ... UNTIL 3 <= 3 OD` and `WHILE 2 >= 3 DO ... OD`
- [x] direct comparison operator conditions driving local branch calls:
  `IF 2 < 3 THEN HELLO() FI` and `IF 2 >= 3 THEN ... ELSE ... FI`
- [x] multiple local procedures in one module:
  `PROC HELLO() ...` and `PROC MAIN() ...`
- [x] local user procedure calls:
  `HELLO()`
- [x] explicit integer return values from zero-arg local procedures:
  `PROC TWO() RETURN 2`
- [x] expression-position local procedure calls with returned values:
  `PrintIE(TWO())`, `PrintIE(TWO()+THREE())`
- [x] expression-position unresolved-external calls with returned values:
  `PrintIE(W())`, `PrintIE(W()+1)`
- [x] returned values used in assignment and control flow:
  `X=NEXT()` and `IF W()=7 THEN ... FI`
- [x] local procedure parameters and expression-valued call arguments:
  `PROC INC(N) RETURN N+1`, `PrintIE(INC(2+3))`
- [x] multiple local procedure parameters:
  `PROC ADD(X,Y) RETURN X+Y`, `PrintIE(ADD(2,3))`
- [x] unresolved-external procedure parameters:
  `PrintIE(W(5))` with `PROC W(N) RETURN N+2`
- [x] multiple unresolved-external procedure parameters:
  `PrintIE(W(2,3))` with `PROC W(X,Y) RETURN X+Y`
- [x] nested call results reused as later call arguments:
  `PrintIE(W(INC(2+3)))`
- [x] composed boolean conditions with `AND`, `OR`, and `NOT`:
  `IF (X<Y AND W()=7) OR Z()=1 THEN ... FI` and `IF NOT(Z()=1) THEN ... FI`
- [x] local/external arg-bearing calls inside branch and loop control:
  `IF 1 = 1 THEN PrintIE(INC(2+3)) ELSE ... FI` and `WHILE X < 2 DO PrintIE(W(X+5)) X=X+1 OD`
- [x] composed boolean predicates driven by arg-bearing local/external calls:
  `IF (X<Y AND W(5)=7) OR Z(1)=1 THEN ... FI` and `IF (INC(X)=2 AND W(Y+5)=9) OR NOT(Z(1)=1) THEN ... FI`
- [x] boolean/comparison expressions used as value expressions in assignment, return, and call-arg position:
  `X=(X<Y AND W(5)=7) OR Z(1)=1`, `RETURN N<3`, and `PrintIE(INC((X<Y AND W(5)=7) OR Z(1)=1))`
- [x] compound boolean/comparison expressions used in print-value position:
  `PrintIE((X<Y AND W(5)=7) OR Z(1)=1)`, `PrintIE((INC(X)=2 AND W(Y+5)=9) OR NOT(Z(1)=1))`, and `PrintI((X<Y AND W(5)=7) OR Z(1)=1)`
- [x] parenthesized boolean/comparison value expressions reused as arithmetic factors:
  `RETURN (N<3)+1`, `X=((X<Y AND W(5)=7) OR Z(1)=1)+1`, `PrintIE(INC(((X<Y AND W(5)=7) OR Z(1)=1)+1))`, and `PrintIE(((X<Y AND W(5)=7) OR Z(1)=1)+1)`
- [x] module-scope integer initializers from composed boolean/comparison literal expressions:
  `INT X=[(1<2 AND 2<3) OR NOT(0=1)]`
- [x] module-scope integer initializers from parenthesized boolean/comparison literal expressions reused as arithmetic factors:
  `INT X=[((1<2 AND 2<3) OR NOT(0=1))+1]`
- [x] proc-local integer declarations with declaration-site runtime initialization:
  `PROC TICK() INT X=[0] ...`
- [x] narrow proc-local `BYTE` declarations use the existing declaration-site
  runtime initialization path:
  `PROC TICK() BYTE X=[0] ...`
- [x] proc-local integer initializers rerun on each call:
  `TICK()` then `TICK()` prints `0`, `1`, `0`, `1`
- [x] proc-local integer initializers can read proc parameters and drive loop control:
  `PROC COUNT(N) INT X=[N] DO ... UNTIL X=2 OD`
- [x] module-scope integer storage/read/write reaches the current slot-`F` ceiling:
  `INT A=[0] ... INT P=[15]`, `PrintIE(K)`, `PrintIE(P)`, `P=P+1`
- [x] proc-local integer storage/read/write reaches the current slot-`F` ceiling with params plus locals:
  `PROC SHOW(Z) INT A ... INT O`, `O=Z+2`, `PrintIE(O)`
- [x] harness local procedure export tables reach the current slot-`A` ceiling with live calls beyond `7`:
  `PROC MAIN() P7() P8() P9() RETURN` with `PROC P0() ... PROC P9()`, proving `c8`, `c9`, and `cA` body-op emission
- [x] harness unresolved-external symbol tables reach the current digit-bearing `10`-entry fanout:
  `PROC MAIN() W0() ... W9() RETURN`, proving `u w0` through `u w9` emission in one root object
- [x] harness loop nesting reaches `9` deep across both loop forms:
  nested `DO ... UNTIL ... OD` printing `DEEP` and nested `WHILE 0=1 DO ... OD` falling through to `DONE`
- [x] identifiers can include digits after the first character across vars, proc names, params, and locals:
  `INT V0=[1]`, `PROC ADD1(N1)`, `INT X2=[N1+1]`, `ADD1(5)`
- [x] digit-bearing module/proc names compile through command-line module selection and module-header validation:
  `ACTC.PRG W1` on `MODULE W1`, `PROC W1()`
- [x] local user procedure calls inside `IF ... THEN ... ELSE ... FI`:
  `IF 1 = 1 THEN HELLO() ELSE BYE() FI`
- [x] arithmetic/comparison-driven local procedure calls inside `IF ... THEN ... ELSE ... FI`:
  `IF 2 + 3 * 4 > 10 THEN HELLO() ELSE BYE() FI`
- [x] nested local procedure calls inside control flow:
  `IF 1 = 1 THEN IF 2 + 3 * 4 > 10 THEN HELLO() ELSE BYE() FI ELSE OUTER() FI`
- [x] unresolved external calls inside arithmetic/comparison-driven `IF ... THEN ... ELSE ... FI`:
  `IF 2 + 3 * 4 > 10 THEN W() ELSE ... FI`
- [x] nested unresolved external calls inside control flow:
  `IF 1 = 1 THEN IF 2 + 3 * 4 > 10 THEN W() ELSE ... FI ELSE OUTER() FI`
- [x] transitive unresolved-external emission across multiple modules:
  `MAIN -> W -> Z`
- [x] transitive unresolved-external calls inside arithmetic/comparison-driven control flow:
  `IF 2 + 3 * 4 > 10 THEN W() ...` with `W -> Z`
- [x] multiple sibling unresolved-external calls from one procedure:
  `W()` and `Z()`
- [x] child-module sibling unresolved-external calls:
  `W()` with `Z()` and `Q()`
- [x] local procedure calls mixed with transitive unresolved externals inside branch control flow:
  `IF ... THEN LOCAL() W() ...` with `W -> Z`
- [x] repeated root unresolved-external reuse from multiple call sites:
  `W()`, `Z()`, `W()`
- [x] shared transitive unresolved-external reuse:
  `W -> Z` and `Q -> Z`
- [x] sibling unresolved-external calls inside arithmetic/comparison-driven control flow:
  `IF ... THEN W() Z() ...`
- [x] shared transitive unresolved-external calls inside arithmetic/comparison-driven control flow:
  `IF ... THEN W() Q() ...` with `W -> Z` and `Q -> Z`
- [x] single-branch control flow:
  `IF 1 = 0 THEN ... FI` and `IF 1 = 1 THEN ... FI`
- [x] `ELSE` control flow:
  `IF 1 = 0 THEN ... ELSE ... FI`
- [x] nested control flow:
  `IF 1 = 1 THEN IF 1 = 0 THEN ... FI ... FI`
- [x] nested `ELSE` control flow:
  `IF 1 = 1 THEN IF 1 = 0 THEN ... ELSE ... FI ELSE ... FI`
- [x] explicit early return inside current control-flow forms:
  `IF ... THEN RETURN FI`, `IF ... ELSE RETURN FI`, `DO ... RETURN UNTIL ... OD`, `WHILE ... RETURN OD`
- [x] explicit early return after local/external calls:
  `IF HELLO() RETURN FI`, `IF W() RETURN FI`, `WHILE HELLO() W() RETURN OD`
- [x] explicit early return with transitive external closure inside nested control flow:
  `IF ... THEN IF ... THEN W() RETURN FI ... FI` with `W -> Z`
- [x] explicit early return inside mixed nested loop/branch control flow:
  `DO IF ... THEN W() ELSE HELLO() FI RETURN UNTIL ... OD`
- [x] explicit early return inside nested loop forms with transitive externals:
  `WHILE ... DO DO W() RETURN UNTIL ... OD OD` with `W -> Z`
- [x] multi-arg local/external calls inside early-return control flow:
  `IF 1 = 1 THEN PrintIE(W(X,Y)) RETURN FI` and `DO IF X<Y THEN PrintIE(ADD(X,Y)) PrintIE(W(X+1,Y+1)) RETURN FI UNTIL 1 = 1 OD`
- [x] multi-arg transitive external calls inside nested mixed-loop early return:
  `WHILE X<3 DO DO IF W(X,Y)=3 THEN PrintIE(Q(X+3,Y+4)) RETURN FI UNTIL 1 = 1 OD X=X+1 OD` with `Q -> Z`
- [x] `DO ... UNTIL ... OD` loop control flow:
  `DO ... UNTIL 1 = 1 OD`
- [x] local and unresolved-external calls inside `DO ... UNTIL ... OD`:
  `DO HELLO() W() UNTIL 1 = 1 OD`
- [x] branch control flow inside `DO ... UNTIL ... OD`:
  `DO IF 2 + 3 * 4 > 10 THEN ... ELSE ... FI UNTIL 1 = 1 OD`
- [x] local branch calls inside `DO ... UNTIL ... OD`:
  `DO IF 2 + 3 * 4 > 10 THEN HELLO() ELSE BYE() FI UNTIL 1 = 1 OD`
- [x] unresolved-external branch calls inside `DO ... UNTIL ... OD`:
  `DO IF 2 + 3 * 4 > 10 THEN W() ELSE ... FI UNTIL 1 = 1 OD`
- [x] nested `DO ... UNTIL ... OD`:
  `DO ... DO ... UNTIL 1 = 1 OD UNTIL 1 = 1 OD`
- [x] local and unresolved-external calls inside nested `DO ... UNTIL ... OD`:
  `DO HELLO() DO W() UNTIL 1 = 1 OD UNTIL 1 = 1 OD`
- [x] nested `IF ... THEN ... ELSE ... FI` inside nested `DO ... UNTIL ... OD`:
  `DO IF ... THEN ... FI DO IF ... THEN ... ELSE ... FI UNTIL ... OD UNTIL ... OD`
- [x] mixed local/external branch calls inside nested `DO ... UNTIL ... OD`:
  `DO IF ... THEN W() ELSE ... FI DO IF ... THEN HELLO() ELSE ... FI UNTIL ... OD UNTIL ... OD`
- [x] top-tested `WHILE ... DO ... OD` with false entry condition:
  `WHILE 1 = 0 DO ... OD`
- [x] local and unresolved-external calls inside top-tested `WHILE ... DO ... OD`
- [x] `IF ... THEN ... ELSE ... FI` inside top-tested `WHILE ... DO ... OD`
- [x] local branch calls inside top-tested `WHILE ... DO ... OD`
- [x] unresolved-external branch calls inside top-tested `WHILE ... DO ... OD`
- [x] nested top-tested `WHILE ... DO ... OD`
- [x] local and unresolved-external calls inside nested top-tested `WHILE ... DO ... OD`
- [x] mixed local/external branch content inside nested top-tested `WHILE ... DO ... OD`
- [x] shared transitive unresolved-external reuse inside top-tested `WHILE ... DO ... OD`
- [x] compiler body-op stride widened to support the current nested-loop surface:
  `BODY_OPS_STRIDE = 48`
- [x] compiler integer literal pool widened for the current nested-loop + nested-branch surface:
  `INT_LITERAL_MAX = 10`
- [x] harness `ACTC` source-load limit widened beyond one page for dense source scenarios:
  `SOURCE_LIMIT = 511`
- [x] harness `ACTC` per-proc body-op storage widened beyond the old `96`-char ceiling for dense local-call bodies:
  `BODY_OPS_STRIDE = 160`
- [x] harness `ACTC` integer-literal pool widened through base-36 slot `Z` for dense local dead-strip proofs:
  `INT_LITERAL_MAX = 36`
- [x] harness `ACTC` string-literal pool widened through base-36 slot `Z` for dense module graphs:
  `STRING_LITERAL_MAX = 36`
- [x] harness `ACTC` local export/proc table widened beyond the old `8`-proc ceiling for dense modules:
  `EXPORT_MAX = 16`
- [x] harness `ACTC` unresolved-external table widened beyond the old `8`-symbol ceiling for wide root fanout:
  `EXTERNAL_MAX = 16`
- [x] harness `ACTC` loop-kind stack widened beyond the old `8`-deep nesting ceiling:
  `LOOP_MAX = 16`
- [x] production `ACTC` source staging widened beyond one page:
  `ACTC_REU_SOURCE_CACHE = 1`, `SOURCE_LIMIT = 20480`, and
  `SOURCE_LOOKAHEAD = 255`, with a `49152` byte source compile proof that finds
  `PROC MAIN()` near offset `49120` through the REU source-cache path
- [x] production `ACTC` now uses the same widened literal/export/loop family as
  the harness line, with `BODY_OPS_STRIDE = 255`, `INT_LITERAL_MAX = 36`,
  `STRING_LITERAL_MAX = 36`, `EXPORT_MAX = 16`, `EXTERNAL_MAX = 36`, and
  `LOOP_MAX = 16`
- [ ] token-safe large-source parsing:
  current ACTC stages source into REU and refills `source_buffer` as raw scans
  advance, with 255 bytes of bounded lookahead for direct `(scan_ptr),y` reads,
  commits 256-byte inline-space skips and long expression scans back into the
  reader, marks/restores the active source window around speculative expression
  pre-scans, routes boolean pre-scan wrap cases into the boolean parser, restores
  failed keyword probes that crossed into another REU source window, preserves
  assignment operator positions across variable lookup, advances assignment
  punctuation and procedure parameter punctuation through the reader, restores
  runtime and constant group speculation before reinterpretation as a comparison
  left-hand side, and now streams object output; it still needs
  token-boundary-safe source reading before DNP-sized sources are realistic
- [x] REU source-cache service-shape proof:
  `ACTC_REU_SOURCE_CACHE=1` stages source bytes beyond the first `20480` window
  into simulated REU at `$010000` through resident-compatible REU service
  entries and pages later windows back into `source_buffer`
- [x] first scanner-refill proof:
  ACTC compiles sources where the `PROC MAIN` name or a `PrintE` string literal
  crosses the first `SOURCE_LIMIT` window boundary
- [x] first reader commit proof:
  ACTC compiles a source where long inline spaces before a `PrintIE` literal
  force 8-bit `Y` lookahead to wrap across the first source window boundary
- [x] first expression reader commit proof:
  ACTC compiles a source where a long `PrintIE(...)` expression crosses the
  first source window boundary and a long variable symbol itself spans the
  commit point
- [x] first boolean pre-scan wrap proof:
  ACTC compiles a source where `AND` appears after a 320-space run crossing the
  first source window boundary, proving pre-scan wrap routes to boolean parsing
  instead of silently rescanning from the start of the same window
- [x] first failed-keyword restore proof:
  ACTC compiles a source where a boolean keyword probe skips spaces across the
  first source window boundary, fails on a variable symbol, reloads the original
  REU source window, and lets normal value parsing continue from the original
  expression position
- [x] first assignment punctuation wrap proof:
  ACTC compiles a source where an assignment `=` sits at an 8-bit `Y` wrap after
  long inline spaces, preserving the operator position across variable lookup
  and parsing the right-hand side from the next reader position
- [x] first procedure parameter punctuation wrap proof:
  ACTC compiles a source where `PROC MAIN` has 251 inline spaces before `(`, so
  the opening parameter-list delimiter sits at `Y=$FF` and parameters continue
  from the next REU-backed reader position
- [x] first group-speculation restore proofs:
  ACTC compiles runtime `PrintIE((1 ... )=1)` and constant `INT X=[(1 ... )=1]`
  cases where closing the parenthesized left-hand side crosses an 8-bit `Y` wrap,
  then reloads the original REU source window before reparsing the group as the
  left side of a comparison
- [ ] production large-source parser:
  direct `(scan_ptr),y` lookahead remains; ACTC still needs a source-reader
  refactor so long identifiers, strings, expressions, and line endings can
  safely cross bounded-lookahead windows
- [x] current widened control-flow object emission:
  `b p0p1qhe0vp2p3qhe1ve2r`
- [x] current widened `ELSE` object emission:
  `b p0p1qhe0we1ve2r`
- [x] current widened nested-control-flow object emission:
  `b p0p1qhp2p3qhe0ve1ve2r`
- [x] current widened nested-`ELSE` object emission:
  `b p0p1qhp2p3qhe0we1vwe2ve3r`
- [x] current widened `DO ... UNTIL ... OD` object emission:
  `b de0p0p1qtoe1r`
- [x] current widened call/external loop object emission:
  `b dc0u0p0p1qtoe1r`
- [x] current widened loop + branch object emission:
  `b dp0p1ap2ghe0we1vp3p4qtoe2r`
- [x] current widened loop + branch-call object emission:
  `b dp0p1ap2ghc0wc1vp3p4qtoe2r`
- [x] current widened loop + branch-external object emission:
  `b dp0p1ap2ghu0we0vp3p4qtoe1r`
- [x] current widened nested-loop object emission:
  `b de0de1p0p1qtop2p3qtoe2r`
- [x] current widened nested loop + call/external object emission:
  `b dc0du0p0p1qtop2p3qtoe1r`
- [x] current widened nested loop + nested-branch object emission:
  `b dp0p1ap2ghe0vdp3p4qhe1we2vp5p6qtop7p8qtoe3r`
- [x] current widened nested loop + mixed branch local/external object emission:
  `b dp0p1ap2ghu0we1vdp3p4qhc0we2vp5p6qtop7p8qtoe3r`
- [x] current widened `WHILE ... DO ... OD` object emission:
  `b dp0p1qfe0xe1r`
- [x] current widened `WHILE` + call/external object emission:
  `b dp0p1qfc0u0xe1r`
- [x] current widened `WHILE` + branch object emission:
  `b dp0p1qfp2p3ap4ghe0we1vxe2r`
- [x] current widened `WHILE` + branch-call object emission:
  `b dp0p1qfp2p3ap4ghc0wc1vxe2r`
- [x] current widened `WHILE` + branch-external object emission:
  `b dp0p1qfp2p3ap4ghu0we0vxe1r`
- [x] current widened nested `WHILE` object emission:
  `b dp0p1qfe0dp2p3qfe1xxe2r`
- [x] current widened nested `WHILE` + call/external object emission:
  `b dp0p1qfc0dp2p3qfu0xxe1r`
- [x] current widened nested `WHILE` + mixed branch local/external object emission:
  `b dp0p1qfp2p3ap4ghu0we1vdp5p6qfp7p8qhc0we2vxxe3r`
- [x] current widened `WHILE` + shared-transitive object emission:
  `b dp0p1qfu0u1xe0r`
- [x] current widened `DO` + nested `WHILE` object emission:
  `b de0dp0p1qfe1xp2p3qtoe2r`
- [x] current widened `WHILE` + nested `DO` object emission:
  `b dp0p1qfe0de1p2p3qtoxe2r`
- [x] current widened `DO` + nested `WHILE` + call/external object emission:
  `b dc0dp0p1qfu0xp2p3qtoe1r`
- [x] current widened `WHILE` + nested `DO` + call/external object emission:
  `b dp0p1qfc0du0p2p3qtoxe1r`
- [x] current widened mixed `DO`/`WHILE` + branch local/external object emission:
  `b dp0p1ap2ghu0we1vdp3p4qfp5p6qhc0we2vxp7p8qtoe3r`
- [x] current widened `WHILE` + nested `DO` + shared-transitive object emission:
  `b dp0p1qfu0du1p2p3qtoxe0r`
- [x] current widened additive object emission:
  `b e0u0p0p1ap2myp3p4mp5azr`
- [x] current widened precedence object emission:
  `b p0p1ayi2r`
- [x] current widened arithmetic/comparison object emission:
  `b p0p1azi2p3p4qzp5p6gzu0r`
- [x] current widened direct-comparison object emission:
  `b p0p1nzp2p3lzp4p5gp6qzp7p8lp9qzpApBgpCqzpDpElpFqzr`
- [x] current widened string-index object emission:
  `b e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFr`
- [x] current widened int-index object emission:
  `b i0i1i2i3i4i5i6i7i8i9iAiBiCiDiEiFiGiHiIiJr`
- [x] current widened high string-index `IF/ELSE` object emission:
  `b p0p1qhe0e1e2e3e4e5e6e7we8e9eAeBeCeDeEeFvr`
- [x] current widened high string-index `DO ... UNTIL ... OD` object emission:
  `b de0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFp0p1qtor`
- [x] current widened high int-index `IF/ELSE` object emission:
  `b p0p1qhi2i3i4i5i6i7i8i9wiAiBiCiDiEiFiGiHvr`
- [x] current widened high string-index branch-external object emission:
  `b p0p1qhu0e0e1e2e3e4e5e6e7e8e9eAeBweCvr`
- [x] current widened direct-comparison `IF` object emission:
  `b p0p1nhe0vp2p3lhe1vp4p5gp6qhe2vp7p8lp9qhe3vpApBgpCqhe4vpDpElpFqhe5vr`
- [x] current widened direct-comparison loop object emission:
  `b de0p0p1gp2qtodp3p4lp5qfe1xe2r`
- [x] current widened direct-comparison branch-call object emission:
  `b p0p1lhc0vp2p3lp4qhe1we2vr`
- [x] current widened arithmetic/comparison `IF/ELSE` object emission:
  `b p0p1ap2ghe0we1ve2r`
- [x] current widened branch-call object emission:
  `b p0p1qhc0wc1ve2r`
- [x] current widened arithmetic/comparison branch-call object emission:
  `b p0p1ap2ghc0wc1ve2r`
- [x] current widened nested branch-call object emission:
  `b p0p1qhp2p3ap4ghc0wc1vwc2ve3r`
- [x] current widened branch-external object emission:
  `b p0p1ap2ghu0we0ve1r`
- [x] current widened nested branch-external object emission:
  `b p0p1qhp2p3ap4ghu0we1vwc0ve2r`
- [x] current widened transitive-external root object emission:
  `b e0u0e1r`
- [x] current widened transitive-branch-external root object emission:
  `b p0p1ap2ghe0u0we1ve2r`
- [x] current widened sibling-external root object emission:
  `b e0u0u1e1r`
- [x] current widened child-sibling-external object emission:
  `b e0u0u1r`
- [x] current widened branch-local + transitive-external object emission:
  `b p0p1ap2ghc0u0we1ve2r`
- [x] current widened repeated-root-external object emission:
  `b e0u0u1u0e1r`
- [x] current widened branch-sibling-external object emission:
  `b p0p1ap2ghu0u1we0ve1r`
- [x] harness proof exists through:
  `ACTC -> ALINK -> AVMRUN`
- [x] current harness runtime output for that widened slice:
  `HELLO`, `TOOL7`, `5459`
- [x] current harness runtime output for the precedence slice:
  `145`
- [x] current harness runtime output for the arithmetic/comparison slice:
  `14`, `5`, `1`, `1`, `TOOL7`
- [x] current harness runtime output for the arithmetic/comparison `IF/ELSE` slice:
  `YES`, `DONE`
- [x] current harness runtime output for the branch-call slice:
  `HELLO`, `DONE`
- [x] current harness runtime output for the arithmetic/comparison branch-call slice:
  `HELLO`, `DONE`
- [x] current harness runtime output for the nested branch-call slice:
  `HELLO`, `DONE`
- [x] current harness runtime output for the branch-external slice:
  `TOOL7`, `DONE`
- [x] current harness runtime output for the nested branch-external slice:
  `TOOL7`, `DONE`
- [x] current harness runtime output for the transitive-external slice:
  `START`, `MID`, `END`, `DONE`
- [x] current harness runtime output for the transitive-branch-external slice:
  `START`, `MID`, `END`, `DONE`
- [x] current harness runtime output for the `DO` + nested `WHILE` slice:
  `OUTER`, `DONE`
- [x] current harness runtime output for the `WHILE` + nested `DO` slice:
  `DONE`
- [x] current harness runtime output for the `DO` + nested `WHILE` + call/external slice:
  `HELLO`, `DONE`
- [x] current harness runtime output for the `WHILE` + nested `DO` + call/external slice:
  `DONE`
- [x] current harness runtime output for the mixed `DO`/`WHILE` + branch local/external slice:
  `TOOL7`, `DONE`
- [x] current harness runtime output for the `WHILE` + nested `DO` + shared-transitive slice:
  `DONE`
- [x] current harness runtime output for the sibling-external slice:
  `START`, `MID1`, `MID2`, `DONE`
- [x] current harness runtime output for the child-sibling-external slice:
  `START`, `MID`, `END1`, `END2`, `DONE`
- [x] current harness runtime output for the branch-local + transitive-external slice:
  `LOCAL`, `MID`, `END`, `DONE`
- [x] current harness runtime output for the repeated-root-external slice:
  `START`, `MID1`, `MID2`, `MID1`, `DONE`
- [x] current harness runtime output for the shared-transitive-external slice:
  `START`, `MID1`, `END`, `MID2`, `END`, `DONE`
- [x] current harness runtime output for the branch-sibling-external slice:
  `MID1`, `MID2`, `DONE`
- [x] current harness runtime output for the branch-shared-transitive slice:
  `MID1`, `END`, `MID2`, `END`, `DONE`
- [x] current harness runtime output for the local-procedure slice:
  `ONE`, `TWO`
- [x] current harness runtime output for the `IF` slice:
  `YES`, `DONE`
- [x] current harness runtime output for the `ELSE` slice:
  `GOOD`, `DONE`
- [x] current harness runtime output for the nested-`IF` slice:
  `INNERDONE`, `OUTERDONE`
- [x] current harness runtime output for the nested-`ELSE` slice:
  `GOOD1`, `DONE`
- [x] current harness runtime output for the `DO ... UNTIL ... OD` slice:
  `BODY`, `DONE`
- [x] current harness runtime output for the call/external loop slice:
  `HELLO`, `TOOL7`, `DONE`
- [x] current harness runtime output for the loop + branch slice:
  `YES`, `DONE`
- [x] current harness runtime output for the loop + branch-call slice:
  `HELLO`, `DONE`
- [x] current harness runtime output for the loop + branch-external slice:
  `TOOL7`, `DONE`
- [x] current harness runtime output for the nested-loop slice:
  `OUTER`, `INNER`, `DONE`
- [x] current harness runtime output for the nested loop + call/external slice:
  `HELLO`, `TOOL7`, `DONE`
- [x] current harness runtime output for the nested loop + nested-branch slice:
  `OUTER`, `INNER`, `DONE`
- [x] current harness runtime output for the nested loop + mixed branch local/external slice:
  `TOOL7`, `HELLO`, `DONE`
- [x] current harness runtime output for the `WHILE ... DO ... OD` slice:
  `DONE`
- [x] current harness runtime output for the `WHILE` + call/external slice:
  `DONE`
- [x] current harness runtime output for the `WHILE` + branch slice:
  `DONE`
- [x] current harness runtime output for the `WHILE` + branch-call slice:
  `DONE`
- [x] current harness runtime output for the `WHILE` + branch-external slice:
  `DONE`
- [x] current harness runtime output for the nested `WHILE` slice:
  `DONE`
- [x] current harness runtime output for the nested `WHILE` + call/external slice:
  `DONE`
- [x] current harness runtime output for the nested `WHILE` + mixed branch local/external slice:
  `DONE`
- [x] current harness runtime output for the `WHILE` + shared-transitive slice:
  `DONE`
- [x] current harness runtime output for the dense shared-transitive branch + early-return slice:
  `MID1`, `END`, `MID2`, `END`, `A` through `P`
- [x] current harness runtime output for the dense mixed nested-loop + shared-transitive slice:
  `MID2`, `END`, `A` through `P`
- [x] current harness runtime output for the dense early-return nested mixed-loop + shared-transitive slice:
  `MID1`, `END`, `MID2`, `END`, `A` through `P`
- [x] current harness runtime output for the dense branch-gated early-return nested mixed-loop + shared-transitive slice:
  `MID1`, `END`, `MID2`, `END`, `A` through `P`

## Current Biggest Risks

- Resident/VICE tool-service ABI sensitivity.
  The previous resident-facing load/save blocker is cleared on the current
  working tree, but this remains the first area to watch when widening compiler
  output.
- Probe stability.
  VICE automation is good enough to prove narrow slices, but it still costs time whenever a dirty line perturbs boot, mount, or prompt timing.
- Dirty-line versus committed-line drift.
  The current narrow compiler/linker/runtime path is green again. The active
  work is widening it without reintroducing the older ABI sensitivity.

## What Is Not Claimed Here

- full ACTION! compiler coverage
- full runtime lowering for arbitrary expressions/statements
- stable proof for every currently dirty widening experiment
