# `ALINK` Status

Current as of `2026-04-24`.

This file is a focused ledger for the UDOS-native `ALINK.PRG` tool.
It tracks the real linker slice separately from the broader [action_matrix.md](/mnt/c/test/action/actionc64u/docs/action_matrix.md).

## Proven On The Committed Baseline

- [x] Launches from a UDOS Action workspace as `ALINK.PRG <module>`
- [x] Loads deterministic `AVO1` object stubs from `OBJ/`
- [x] Prefers `.OBJ` project/library objects and falls back to legacy `.AVO`
  compatibility paths
- [x] Parses export metadata
- [x] Parses `body_ops`
- [x] Parses unresolved external symbol lines
- [x] Parses integer literal pools
- [x] Parses string literal pools
- [x] Uses compiler-emitted export sizes to recover procedure boundaries
- [x] Builds a live-set from the requested module entry
- [x] Resolves the current narrow external-object closure by loading child objects
- [x] Resolves pending dependent objects from `LIB/` when no project object exists
  in `OBJ/`
- [x] Queues external dependencies from live `uN` body operations instead of
  every object-level `u <symbol>` line
- [x] Carries child-object int/string pools into the linked image
- [x] Emits direct native `PRG` output to `BIN/<NAME>.PRG` on the default live gate
- [x] Retains binary `AVM1` emission to `BIN/<NAME>.AVM` on the AVM-specific compat gate
- [x] Emits the first text `DBG1` sidecar to `BIN/<NAME>.DBG`
- [x] Narrow exact-byte proof exists for the emitted image
- [x] Narrow integrated proof exists through `ALINK -> AVMRUN`
- [ ] Live helper-bearing higher-level proof through `ACTC -> ALINK -> AVMRUNC`
- [x] Current shipped UDOS build links again under the real target after widening the tool load window from `$2000` to `$4000`
- [x] Current workspace exporter is green again with `--build-udos-tools`

Current real-target build note:

- `./tools/build_alink_udos.sh` is green again
- `make -C ../udos vice-action-alink` is green again on the current working
  tree as the default direct-native PRG gate
- `make -C ../udos vice-action-alink-compat` is green again as the
  AVM-specific linker/runner proof on the current working tree
- `make -C ../udos vice-action-actc-alink-launch-printmath` is green again
  as the named imported `printmath` direct-launch proof on the current working
  tree, reaching `hello`, `tool7`, and `5459` before returning to the UDOS
  prompt. The separate helper-bearing
  `make -C ../udos vice-action-actc-alink-compat-printmath` path remains the
  compat replay target for the same source shape.
  returning to the UDOS prompt
- `make -C ../udos vice-action-actc-alink-launch` is green again as the
  helper-free higher-level default launch path on the current working tree
- current shipped `ALINK` map footprint is:
  - `CODE`: `$28BD`
  - `BSS`: `$0793`
  - total runtime span from `$0900` through `$394F`
- current shipped `ALINK` file footprint is:
  - `ALINK.PRG`: `10431` bytes
- current shipped `ALINK` link window is `$0900-$9FFF`
- current shipped `ALINK` build now uses:
  - `ACTC_REU_SOURCE_CACHE=1` through the shared project-source loader
  - `STREAM_OUTPUT=1`
  - `ALINK_DEBUG_SIDECAR=1`
  - `SOURCE_LIMIT=512` resident source window
  - `SOURCE_LOOKAHEAD=255` read-ahead margin for cross-window line scans
  - `BODY_OPS_STRIDE=255`
  - `OUTPUT_CHUNK_SIZE=128`
  - `EXPORT_MAX=16`
  - `EXTERNAL_MAX=36`
  - `PENDING_SYMBOL_MAX=36`
  - `CONTENT_BUFFER_SIZE=16` for the legacy non-stream path only
  - streamed output payload guard: `$C000` bytes (`49152`) before the
    12-byte AVM header
- the previous real-target `LOAD FAIL`/save-return blocker is cleared for the
  current narrow object/link/runtime slice
- `external_names`, `pending_names`, `export_names`, `var_names`,
  `string_literals`, `saved_string_literals`, `body_ops_data`, loaded AVO
  source windows, per-pending layout records, and export/proc layout tables are
  now REU-backed in production `ALINK`; the export/proc layout record now also
  carries the root/current export target offsets, so the resident linker no
  longer keeps separate root/current export target arrays. Root/current var
  target mirrors are now also REU-backed, so resident RAM no longer keeps those
  arrays either. Resident RAM keeps only the active `25`-byte name windows, one
  `24`-byte string window, one `255`-byte body-op window, one `8`-byte
  export/proc layout window, and a `768`-byte source/read-ahead window
- compared to the pre-REU-table linker baseline, resident `BSS` is down by
  `10080` bytes and the total runtime span is down by `8839` bytes, even though
  code grew by `1241` bytes to pay for the REU helpers
- compared to the immediately previous shipped linker build, the root/current
  var target mirror REU move shrinks `ALINK.PRG` by `136` bytes and code by
  `136` bytes, but grows resident `BSS` by `155` bytes and grows total runtime
  span by `19` bytes; that makes it a functional REU move, but not yet a clean
  resident-memory win
- UDOS tool ABI version 2 adds chunked file output services used by production
  `ALINK.PRG`: begin write, write chunk, and close write
- production `ALINK.PRG` now emits a first text `DBG1` sidecar. The current
  bootstrap records are:
  - `m <module_id> <module_name>`
  - `f <module_id> <file_id> <path>`
  - `q <module_id> <export_index> <entry_pc> <file_id> <line> <col> <proc_name>`
  - `l <module_id> <export_index> <pc> <file_id> <line> <col>`
  - `v g <type> <module_id> <var_index> <addr> <width> <file_id> <line> <col> <name>`
  - `v p <type> <module_id> <export_index> <var_index> <addr> <width> <file_id> <line> <col> <name>`
  - `v l <type> <module_id> <export_index> <var_index> <addr> <width> <file_id> <line> <col> <name>`
- `tests/test_alink_capacity.py` now proves that production `ALINK.PRG`
  preserves compiler-emitted `f/q/l/V g/V p/V l` records into `BIN/MAIN.DBG`
  while still emitting the expected large streamed `BIN/MAIN.AVM`
- the host `tool_abi_harness` now dedupes identical REU read/write traces so
  large REU-backed compiler/linker runs still retain the final streamed
  `wopn`/`wrte`/`wcls` records in test output
- `AVMRUN.PRG` no longer keeps the binary AVM file image in its BSS. Binary
  AVM loads now use the fixed runtime window at `$2E00` with a current limit of
  `$C000` bytes (`49152`), and `tests/test_avmrun_capacity.py` proves a
  high-entry `49152` byte AVM through the tool ABI harness. AVMRUN uses
  `$0001 = $36` during file load, then switches to `$34` for patch/execute so
  RAM through `$EBFF` is visible as well, and finally restores the
  original memory configuration before returning to UDOS.
- This clears the immediate runtime choke point for the earlier `15311` byte
  production `ALINK` capacity proof. Production `ALINK` can now emit a `48079`
  byte streamed AVM under the harness, but AVMRUN is still not at the final
  `48K` runtime target:
  true near-`48K` runtime execution needs either a REU/banked payload executor or
  a loader/interpreter split that does not require the whole AVM to coexist with
  AVMRUN code in plain low RAM.

## Proven Linker Behaviors

- [x] dead-strip on the current narrow local/export graph
- [x] child object loading for the already-proven narrow object shape
- [x] final binary target path `BIN/<NAME>.AVM`
- [x] direct binary output instead of text or planning-report output
- [x] dependent-object lookup falls back from `OBJ/<symbol>.OBJ` to
  `LIB/<symbol>.OBJ`, keeping runtime helpers outside compiler output until
  imported
- [x] dead-stripped procedures no longer pull their external helper objects into
  the linked image
- [x] REAL upper-word body ops are lowered without adding VM opcodes: `U<n>`
  emits `LOAD var+2`, and `T<n>` emits `STORE var+2` for 4-byte variables
- [x] production `ALINK.PRG` no longer uses one contiguous final-image buffer:
  it streams `BIN/<NAME>.AVM` through 128-byte UDOS write chunks
- [x] production `ALINK.PRG` now has a near-`48K` streamed-image proof beyond
  the old `575` byte ceiling and the interim `3072` byte buffer ceiling: seeded
  AVO objects link to a `48079` byte `BIN/MAIN.AVM` under the tool ABI harness
- [x] `AVMRUN.PRG` now has a binary AVM load/run proof beyond the old `2048`
  byte runtime file buffer: a `49152` byte AVM loads at `$2E00`, patches near
  the top of the widened window, and exits cleanly
  under the tool ABI harness

## Current Widening Work

- [x] prove production `ALINK` streamed output past `16K` and close to the
  intended `48K` target
- [x] remove AVMRUN's immediate plain-low-RAM payload ceiling so the runtime can
  execute the current `49152` byte binary AVM window
- [ ] continue widening source/object table limits now that final-image output
  no longer requires a contiguous linker-owned buffer
- [x] move the first large linker lookup payloads to REU-backed storage:
  `body_ops_data` (`4080` bytes), `external_names` (`900` bytes), and
  `pending_names` (`900` bytes) no longer sit resident in normal C64 RAM
- [x] move loaded object source windows into REU-backed staging instead of a
  resident `4097`-byte source buffer
- [x] move current and saved string literal pools into REU-backed staging
- [x] move per-pending layout mirrors into REU-backed staging
- [x] move export/proc offset tables into REU-backed staging
- [x] move root/current export target mirrors into the REU-backed export layout
  record
- [x] move root/current var target mirrors into REU-backed staging
- [ ] continue that REU move for the remaining heavy linker payloads:
  map/debug records should not all consume normal C64 RAM
- [ ] next measured resident-pressure targets for that REU move are now the
  remaining always-live metadata tables: final map/debug data and the small
  integer literal tables that still sit resident
- [x] start the source-debug sidecar line described in
  [source_debugger_roadmap.md](/mnt/c/test/action/actionc64u/docs/source_debugger_roadmap.md):
  preserve compiler-emitted file/proc/body-line debug records and write the
  first linked `BIN/<NAME>.DBG` output
- [ ] grow that source-debug sidecar with any richer procedure/frame records
  the debugger will need beyond the current linked global/parameter/local
  variable metadata
- [ ] broader object graph / external-resolution surface
- [ ] more robust child-object load diagnostics for future wider object graphs
- [ ] more robust final save/return diagnostics for future larger outputs
- [ ] larger body-op surface than the current arithmetic/procedure/branch/`WHILE`/nested-loop-combined slice
- [ ] broader variable/data surface beyond the current multi-var module-scope
  integer storage/read/write/control, narrow `BYTE`/`CARD`, and declaration-only
  4-byte `REAL` storage slice
- [ ] broader procedure/function surface beyond the current local/external integer arg/return slice
- [ ] full historical dead-strip/link behavior

## Harness-Proven Current Widening Line

- [x] loads widened `ACTC` output for:
  `PrintI(50 + 7 - 3)` and `PrintIE(60 - 3 + 2)`
- [x] also loads mixed-precedence / parenthesized `ACTC` output for:
  `PrintI(2 + 3 * 4)` and `PrintIE((20 - 5) / 3)`
- [x] also loads arithmetic/comparison mixed `ACTC` output for:
  `PrintIE((2 + 3) * 4 = 20)` and `PrintIE((2 + 3 * 4) > 10)`
- [x] also loads module-scope integer storage/read/write `ACTC` output for:
  `INT X=[0]`, `PrintIE(X)`, `X=X+1`, `PrintIE(X)`
- [x] also loads module-scope integer storage/read/write under loop control:
  `DO PrintIE(X) X=X+1 UNTIL X=2 OD`
- [x] also loads module-scope integer storage/read/write under branch control:
  `IF X=1 THEN ... ELSE ... FI`
- [x] also loads module-scope integer storage/read/write under `WHILE` control:
  `WHILE X<2 DO ... OD`
- [x] also loads module-scope integer storage/read/write driving local/external calls:
  `IF X=1 THEN HELLO() ...`, `IF X=2 THEN W() FI`, `WHILE X<1 DO W() ... OD`
- [x] also loads multiple module-scope integer vars in one module:
  `INT X=[0]`, `INT Y=[2]`, `PrintIE(X)`, `PrintIE(Y)`, `X=Y+1`
- [x] also loads narrow compiler output from module-scope `BYTE`/`CARD`
  declarations through the existing 16-bit variable slot path:
  `BYTE X=[0]`, `CARD Y=[2]`, `PrintIE(X)`, `PrintIE(Y)`, `X=Y+1`
- [x] also preserves optional variable-width metadata from compiler output,
  currently proving a 4-byte module-scope `REAL` slot without pulling REAL
  operator code:
  `REAL X`, `PrintIE(7)`
- [x] also links direct REAL copy assignment without importing helper code:
  `REAL A`, `REAL R`, `R=A`, `PrintE("DONE")`, proving `U<n>`/`T<n>`
  high-word lowering can support REAL storage movement without runtime bloat
- [x] also loads a runtime-style library object only from `LIB/` when imported:
  `MAIN -> rt_f_add`, proving the lookup shape needed for per-operation REAL
  helper inclusion without making REAL an AVM opcode
- [x] also ignores a runtime-style library import listed only by a dead proc:
  `DEAD -> rt_f_add`, `MAIN -> DONE`, proving helper metadata alone does not
  force inclusion
- [x] also links the first REAL add/subtract/multiply/divide assignment runtime
  shapes:
  `REAL A`, `REAL B`, `REAL R`, `R=A+B`, `R=A-B`, `R=A*B`, and `R=A/B`,
  proving live `RT_F_ADD`, `RT_F_SUB`, `RT_F_MUL`, or `RT_F_DIV` lookup from
  `LIB/`, upper-word variable load/store lowering, and no monolithic REAL VM
  opcode requirement
- [x] repo-exported UDOS `LIB/RT_F_ADD.AVO` now exists as a target text-object
- [x] harness-sized `ALINK.PRG` now also uses streamed output, so REAL compare
  cases that pull `RT_I_TO_F` and `RT_F_CMP` from `LIB/` no longer trip the old
  resident payload ceiling; the current harness proof links and runs
  `A<B`, `B=C`, `C>=B`, and `A<>C` through `ALINK -> AVMRUN`
  helper with exact `+0.0` identity behavior for either operand, same-sign
  equal-power-of-two sums such as `1.0 + 1.0 = 2.0`, `2.0 + 2.0 = 4.0`,
  `4.0 + 4.0 = 8.0`, and `-2.0 + -2.0 = -4.0`, plus exact
  `1.5 + 1.5 = 3.0`, adjacent-exponent same-sign sums such as
  `2.0 + 1.0 = 3.0`, adjacent-exponent mixed-sign differences such as
  `2.0 + -1.0 = 1.0`, plus gap-two sums such as `4.0 + 1.0 = 5.0`
  and gap-two mixed-sign differences such as `4.0 + -1.0 = 3.0` and
  `1.0 + -4.0 = -3.0`; full
  IEEE-754 addition inside that helper remains future work
- [x] repo-exported UDOS `LIB/RT_F_SUB.AVO` now exists as a target text-object
  helper with exact `x - +0.0`, sign-flipped `+0.0 - x`, equal signed
  power-of-two subtraction as zero, adjacent-exponent differences such as
  `4.0 - 2.0 = 2.0`, adjacent-exponent mixed-sign sums such as
  `2.0 - -1.0 = 3.0`, gap-two differences such as
  `4.0 - 1.0 = 3.0`, and gap-two mixed-sign sums such as
  `4.0 - -1.0 = 5.0` and `-4.0 - 1.0 = -5.0`, and exact
  `2.0 - 1.0 = 1.0`; full IEEE-754
  subtraction inside that helper
  remains future work
- [x] repo-exported UDOS `LIB/RT_F_MUL.AVO` now exists as a target text-object
  helper with zero identity, one identity, and low-word-zero values scaled by
  exact power-of-two operands, including `2.0 * 2.0 = 4.0`,
  `4.0 * 2.0 = 8.0`, `-2.0 * 2.0 = -4.0`, and
  `1.5 * 2.0 = 3.0`; full IEEE-754 multiplication inside that helper
  remains future work
- [x] repo-exported UDOS `LIB/RT_F_DIV.AVO` now exists as a target text-object
  helper with zero numerator, divide-by-zero as zero, `x / 1.0 = x`, and
  low-word-zero values divided by exact power-of-two denominators, including
  `4.0 / 2.0 = 2.0`, `8.0 / 2.0 = 4.0`, `2.0 / 4.0 = 0.5`,
  `2.0 / -4.0 = -0.5`, and `3.0 / 2.0 = 1.5`; full IEEE-754 division
  inside that helper remains future work
- [x] also loads variable-to-variable arithmetic assignment:
  `X=X+Y`
- [x] also loads multiple module-scope integer vars under `WHILE` control:
  `WHILE X<Y DO ... OD`
- [x] also loads multiple module-scope integer vars driving local/external calls:
  `IF X<Y THEN HELLO() W() FI`
- [x] also loads multiple module-scope integer vars driving shared-transitive external closure under branch control:
  `IF X<Y THEN W() Q() FI` with `W -> Z` and `Q -> Z`
- [x] also loads multiple module-scope integer vars driving shared-transitive external closure under `WHILE` control:
  `WHILE X<Y DO W() Q() X=X+1 OD` with `W -> Z` and `Q -> Z`
- [x] also loads zero-arg local procedures that return integer values:
  `PROC TWO() RETURN 2`
- [x] also loads expression-position local procedure calls with returned values:
  `PrintIE(TWO())`, `PrintIE(TWO()+THREE())`
- [x] also loads expression-position unresolved-external calls with returned values:
  `PrintIE(W())`, `PrintIE(W()+1)`
- [x] also loads returned values used in assignment and control flow:
  `X=NEXT()` and `IF W()=7 THEN ... FI`
- [x] also loads local procedure parameters and expression-valued call arguments:
  `PROC INC(N) RETURN N+1`, `PrintIE(INC(2+3))`
- [x] also loads multiple local procedure parameters:
  `PROC ADD(X,Y) RETURN X+Y`, `PrintIE(ADD(2,3))`
- [x] also loads unresolved-external procedure parameters:
  `PrintIE(W(5))` with `PROC W(N) RETURN N+2`
- [x] also loads multiple unresolved-external procedure parameters:
  `PrintIE(W(2,3))` with `PROC W(X,Y) RETURN X+Y`
- [x] also loads nested call results reused as later call arguments:
  `PrintIE(W(INC(2+3)))`
- [x] also loads composed boolean conditions with `AND`, `OR`, and `NOT`:
  `IF (X<Y AND W()=7) OR Z()=1 THEN ... FI` and `IF NOT(Z()=1) THEN ... FI`
- [x] also loads arg-bearing local/external calls under branch and loop control:
  `IF 1 = 1 THEN PrintIE(INC(2+3)) ELSE ... FI` and `WHILE X < 2 DO PrintIE(W(X+5)) X=X+1 OD`
- [x] also loads composed boolean predicates driven by arg-bearing local/external calls:
  `IF (X<Y AND W(5)=7) OR Z(1)=1 THEN ... FI` and `IF (INC(X)=2 AND W(Y+5)=9) OR NOT(Z(1)=1) THEN ... FI`
- [x] also loads boolean/comparison value expressions outside control-flow conditions:
  `X=(X<Y AND W(5)=7) OR Z(1)=1`, `RETURN N<3`, and `PrintIE(INC((X<Y AND W(5)=7) OR Z(1)=1))`
- [x] also loads compound boolean/comparison print-value expressions:
  `PrintIE((X<Y AND W(5)=7) OR Z(1)=1)`, `PrintIE((INC(X)=2 AND W(Y+5)=9) OR NOT(Z(1)=1))`, and `PrintI((X<Y AND W(5)=7) OR Z(1)=1)`
- [x] also loads parenthesized boolean/comparison value expressions reused as arithmetic factors:
  `RETURN (N<3)+1`, `X=((X<Y AND W(5)=7) OR Z(1)=1)+1`, `PrintIE(INC(((X<Y AND W(5)=7) OR Z(1)=1)+1))`, and `PrintIE(((X<Y AND W(5)=7) OR Z(1)=1)+1)`
- [x] also loads module-scope integer initializers from composed boolean/comparison literal expressions:
  `INT X=[(1<2 AND 2<3) OR NOT(0=1)]`
- [x] also loads module-scope integer initializers from parenthesized boolean/comparison literal expressions reused as arithmetic factors:
  `INT X=[((1<2 AND 2<3) OR NOT(0=1))+1]`
- [x] also loads proc-local integer slots emitted by widened `ACTC` output:
  `PROC TICK() INT X=[0] ...`
- [x] also loads narrow proc-local `BYTE` declarations emitted by widened
  `ACTC` through the existing declaration-site initialization path:
  `PROC TICK() BYTE X=[0] ...`
- [x] also loads proc-local integer declaration-site reinitialization across repeated calls:
  `TICK()` then `TICK()` prints `0`, `1`, `0`, `1`
- [x] also loads proc-local integer initializers driven by proc parameters under loop control:
  `PROC COUNT(N) INT X=[N] DO ... UNTIL X=2 OD`
- [x] also loads module-scope integer storage/read/write at the current slot-`F` ceiling:
  `INT A=[0] ... INT P=[15]`, `PrintIE(K)`, `PrintIE(P)`, `P=P+1`
- [x] also loads proc-local integer storage/read/write at the current slot-`F` ceiling with params plus locals:
  `PROC SHOW(Z) INT A ... INT O`, `O=Z+2`, `PrintIE(O)`
- [x] also loads harness local procedure export tables beyond the old `8`-proc ceiling:
  `PROC MAIN() P7() P8() P9() RETURN` with `PROC P0() ... PROC P9()`, proving linker parse/live-set/emit of `c8`, `c9`, and `cA`
- [x] also resolves a harness root with more than eight child objects and more than seven pending queue entries:
  `MAIN -> W0 .. W9`, proving parse/queue/link/emit across `10` child modules in one image
- [x] also links harness loop nesting deeper than eight across both loop walkers:
  `9` nested `DO ... UNTIL ... OD` and `9` nested `WHILE ... DO ... OD`
- [x] also loads digit-bearing symbol names in compiler-emitted object metadata:
  `v v0 1`, `v n1 0`, `v x2 0`, and `x add1 ...`
- [x] also resolves digit-bearing external module/proc names:
  `MAIN -> W1`
- [x] harness linker object loading now accepts compiler-emitted `AVO1` project objects beyond the old `255`-byte ceiling:
  `large_object_proc_local_inits` proves a `291`-byte `MAIN.OBJ`
- [x] also loads dense local-call compiler output beyond the old `96`-char harness body ceiling:
  `PROC MAIN() T() ... T() PrintIE(X) RETURN` with `74` local calls, proving a `152`-char root body line
- [x] harness linker payload buffer now emits binaries beyond the old `256`-byte image ceiling:
  `payload265_local_calls` proves a `265`-byte `BIN/MAIN.AVM`
- [x] harness linker payload path now emits payloads beyond the old `255`-byte payload ceiling:
  `payload269_local_calls` proves a `257`-byte payload in a `269`-byte `BIN/MAIN.AVM`
- [x] harness linker now parses and scans compiler-emitted source code spans past `255` bytes:
  `code268_dead_local_calls` proves an object with `x main 261 7` and total source code span `268`, while dead-strip still links a `24`-byte `BIN/MAIN.AVM`
- [x] harness linker now parses compiler-emitted proc sizes past `255` bytes:
  `proc259_dead_printi_var` proves an object with `x big 0 259`, while dead-strip still links a `26`-byte `BIN/MAIN.AVM`
- [x] also loads direct comparison-operator `ACTC` output for:
  `PrintIE(2 <> 3)`, `PrintIE(2 < 3)`, `PrintIE(3 <= 3)`, `PrintIE(4 >= 3)`
- [x] also loads high string-index `ACTC` output through `Z` with dead-stripped locals:
  `PROC F() PrintE("0") ... PrintE("Y") RETURN` and `PROC MAIN() PrintE("Z") RETURN`
- [x] also loads high integer-index `ACTC` output through `Z` with dead-stripped locals:
  `PROC F() PrintIE(0..30) RETURN`, `PROC G() PrintIE(31..34) RETURN`, `PROC MAIN() PrintIE(35) RETURN`
- [x] also loads high string-index `IF/ELSE` control-flow `ACTC` output:
  `IF 1 = 0 THEN ... ELSE PrintE("I") ... PrintE("P") FI`
- [x] also loads high string-index `DO ... UNTIL ... OD` control-flow `ACTC` output:
  `DO PrintE("A") ... PrintE("P") UNTIL 1 = 1 OD`
- [x] also loads high string-index `DO ... UNTIL ... OD` + `IF/ELSE` control-flow `ACTC` output:
  `DO IF 1 = 0 THEN PrintE("A") ... ELSE PrintE("I") ... PrintE("P") FI UNTIL 1 = 1 OD`
- [x] also loads high integer-index `IF/ELSE` control-flow `ACTC` output:
  `IF 1 = 0 THEN PrintIE(0..7) ELSE PrintIE(8..15) FI`
- [x] also loads high integer-index `DO ... UNTIL ... OD` + `IF/ELSE` control-flow `ACTC` output:
  `DO IF 1 = 0 THEN PrintIE(0..7) ELSE PrintIE(8..15) FI UNTIL 1 = 1 OD`
- [x] also loads high string-index branch-local unresolved-external output:
  `IF 1 = 1 THEN W() PrintE("A") ... PrintE("L") ELSE PrintE("BAD") FI`
- [x] also loads high string-index transitive branch-local unresolved-external output:
  `IF 1 = 1 THEN W() PrintE("A") ... PrintE("L") ELSE PrintE("BAD") FI` with `W -> Z`
- [x] also loads high string-index shared-transitive branch-local unresolved-external output:
  `IF 1 = 1 THEN W() Q() PrintE("A") ... PrintE("L") ELSE PrintE("BAD") FI` with `W -> Z` and `Q -> Z`
- [x] also loads high string-index shared-transitive branch-local unresolved-external output beyond the old 16-literal root ceiling:
  `IF 1 = 1 THEN W() Q() PrintE("A") ... PrintE("P") ELSE PrintE("BAD") FI` with `W -> Z` and `Q -> Z`
- [x] also loads high string-index shared-transitive loop output:
  `DO W() Q() PrintE("A") ... PrintE("J") UNTIL 1 = 1 OD` with `W -> Z` and `Q -> Z`
- [x] also loads high string-index nested shared-transitive branch output:
  `IF 1 = 1 THEN IF 2 + 3 * 4 > 10 THEN W() Q() PrintE("A") ... PrintE("H") ELSE ... FI ELSE ... FI`
- [x] also loads high string-index nested-loop unresolved-external output:
  `DO WHILE 1 = 0 DO PrintE("BAD") OD W() PrintE("A") ... PrintE("J") UNTIL 1 = 1 OD`
- [x] also loads full high int-index nested-loop `IF/ELSE` output:
  `DO WHILE 1 = 0 DO OD IF 1 = 0 THEN PrintIE(0..7) ELSE PrintIE(8..15) FI UNTIL 1 = 1 OD`
- [x] also loads full high string-index nested-loop `IF/ELSE` output:
  `DO WHILE 1 = 0 DO OD IF 1 = 0 THEN PrintE("A") ... PrintE("H") ELSE PrintE("I") ... PrintE("P") FI UNTIL 1 = 1 OD`
- [x] also loads arithmetic/comparison `IF/ELSE` `ACTC` output for:
  `IF 2 + 3 * 4 > 10 THEN ... ELSE ... FI`
- [x] also loads direct comparison-operator branch and loop `ACTC` output for:
  `IF 2 <> 3 THEN ... FI`, `DO ... UNTIL 3 <= 3 OD`, `WHILE 2 >= 3 DO ... OD`
- [x] also loads direct comparison-operator branch-local procedure-call `ACTC` output for:
  `IF 2 < 3 THEN HELLO() FI` and `IF 2 >= 3 THEN ... ELSE ... FI`
- [x] also loads multi-procedure local-call `ACTC` output for:
  `PROC HELLO() ...` and `HELLO()`
- [x] also loads branch-local procedure-call `ACTC` output for:
  `IF 1 = 1 THEN HELLO() ELSE BYE() FI`
- [x] also loads arithmetic/comparison branch-local procedure-call `ACTC` output for:
  `IF 2 + 3 * 4 > 10 THEN HELLO() ELSE BYE() FI`
- [x] also loads nested branch-local procedure-call `ACTC` output for:
  `IF 1 = 1 THEN IF 2 + 3 * 4 > 10 THEN HELLO() ELSE BYE() FI ELSE OUTER() FI`
- [x] also loads branch-local unresolved-external `ACTC` output for:
  `IF 2 + 3 * 4 > 10 THEN W() ELSE ... FI`
- [x] also loads nested branch-local unresolved-external `ACTC` output for:
  `IF 1 = 1 THEN IF 2 + 3 * 4 > 10 THEN W() ELSE ... FI ELSE OUTER() FI`
- [x] also loads transitive unresolved-external `ACTC` output across modules:
  `MAIN -> W -> Z`
- [x] also loads transitive unresolved-external control-flow `ACTC` output:
  `IF 2 + 3 * 4 > 10 THEN W() ...` with `W -> Z`
- [x] also loads sibling unresolved-external `ACTC` output from one procedure:
  `W()` and `Z()`
- [x] also loads child-module sibling unresolved-external `ACTC` output:
  `W()` with `Z()` and `Q()`
- [x] also loads branch-local call + transitive unresolved-external `ACTC` output:
  `IF ... THEN LOCAL() W() ...` with `W -> Z`
- [x] also loads repeated root unresolved-external reuse:
  `W()`, `Z()`, `W()`
- [x] also loads shared transitive unresolved-external reuse:
  `W -> Z` and `Q -> Z`
- [x] also loads sibling unresolved-external calls inside arithmetic/comparison-driven control flow:
  `IF ... THEN W() Z() ...`
- [x] also loads shared transitive unresolved-external calls inside arithmetic/comparison-driven control flow:
  `IF ... THEN W() Q() ...` with `W -> Z` and `Q -> Z`
- [x] also loads single-branch `IF` control-flow `ACTC` output for:
  `IF 1 = 0 THEN ... FI` and `IF 1 = 1 THEN ... FI`
- [x] also loads `ELSE` control-flow `ACTC` output for:
  `IF 1 = 0 THEN ... ELSE ... FI`
- [x] also loads nested `IF` control-flow `ACTC` output for:
  `IF 1 = 1 THEN IF 1 = 0 THEN ... FI ... FI`
- [x] also loads nested `ELSE` control-flow `ACTC` output for:
  `IF 1 = 1 THEN IF 1 = 0 THEN ... ELSE ... FI ELSE ... FI`
- [x] also loads explicit early-return control-flow `ACTC` output for:
  `IF ... THEN RETURN FI`, `IF ... ELSE RETURN FI`, `DO ... RETURN UNTIL ... OD`, `WHILE ... RETURN OD`
- [x] also loads explicit early-return control flow after local/external calls:
  `IF HELLO() RETURN FI`, `IF W() RETURN FI`, `WHILE HELLO() W() RETURN OD`
- [x] also loads explicit early-return control flow with transitive externals under nested branches:
  `IF ... THEN IF ... THEN W() RETURN FI ... FI` with `W -> Z`
- [x] also loads explicit early-return mixed branch/local-external loop control:
  `DO IF ... THEN W() ELSE HELLO() FI RETURN UNTIL ... OD`
- [x] also loads multi-arg local/external calls under early-return control:
  `IF 1 = 1 THEN PrintIE(W(X,Y)) RETURN FI` and `DO IF X<Y THEN PrintIE(ADD(X,Y)) PrintIE(W(X+1,Y+1)) RETURN FI UNTIL 1 = 1 OD`
- [x] also loads nested mixed-loop early return with multi-arg transitive externals:
  `WHILE X<3 DO DO IF W(X,Y)=3 THEN PrintIE(Q(X+3,Y+4)) RETURN FI UNTIL 1 = 1 OD X=X+1 OD` with `Q -> Z`
- [x] also loads explicit early-return nested-loop control with transitive externals:
  `WHILE ... DO DO W() RETURN UNTIL ... OD OD` with `W -> Z`
- [x] also loads `DO ... UNTIL ... OD` loop `ACTC` output for:
  `DO ... UNTIL 1 = 1 OD`
- [x] also loads local-call plus unresolved-external loop `ACTC` output for:
  `DO HELLO() W() UNTIL 1 = 1 OD`
- [x] also loads branch control flow inside `DO ... UNTIL ... OD`:
  `DO IF 2 + 3 * 4 > 10 THEN ... ELSE ... FI UNTIL 1 = 1 OD`
- [x] also loads branch-local procedure calls inside `DO ... UNTIL ... OD`:
  `DO IF 2 + 3 * 4 > 10 THEN HELLO() ELSE BYE() FI UNTIL 1 = 1 OD`
- [x] also loads branch-local unresolved externals inside `DO ... UNTIL ... OD`:
  `DO IF 2 + 3 * 4 > 10 THEN W() ELSE ... FI UNTIL 1 = 1 OD`
- [x] also loads nested `DO ... UNTIL ... OD` `ACTC` output for:
  `DO ... DO ... UNTIL 1 = 1 OD UNTIL 1 = 1 OD`
- [x] also loads local-call plus unresolved-external nested-loop `ACTC` output for:
  `DO HELLO() DO W() UNTIL 1 = 1 OD UNTIL 1 = 1 OD`
- [x] also loads nested branch control flow inside nested `DO ... UNTIL ... OD`:
  `DO IF ... THEN ... FI DO IF ... THEN ... ELSE ... FI UNTIL ... OD UNTIL ... OD`
- [x] also loads mixed local/external branch calls inside nested `DO ... UNTIL ... OD`:
  `DO IF ... THEN W() ELSE ... FI DO IF ... THEN HELLO() ELSE ... FI UNTIL ... OD UNTIL ... OD`
- [x] also loads top-tested `WHILE ... DO ... OD` `ACTC` output for:
  `WHILE 1 = 0 DO ... OD`
- [x] also loads local/external calls inside top-tested `WHILE ... DO ... OD`
- [x] also loads `IF ... THEN ... ELSE ... FI` inside top-tested `WHILE ... DO ... OD`
- [x] also loads local branch calls inside top-tested `WHILE ... DO ... OD`
- [x] also loads unresolved-external branch calls inside top-tested `WHILE ... DO ... OD`
- [x] also loads nested top-tested `WHILE ... DO ... OD`
- [x] also loads local/external calls inside nested top-tested `WHILE ... DO ... OD`
- [x] also loads mixed local/external branch content inside nested top-tested `WHILE ... DO ... OD`
- [x] also loads shared transitive unresolved-external reuse inside top-tested `WHILE ... DO ... OD`
- [x] also loads `DO ... UNTIL ... OD` containing nested `WHILE ... DO ... OD`
- [x] also loads `WHILE ... DO ... OD` containing nested `DO ... UNTIL ... OD`
- [x] also loads mixed local/external and branch content across `DO`/`WHILE` mixed nesting
- [x] also loads shared transitive unresolved-external reuse across `WHILE` containing nested `DO ... UNTIL ... OD`
- [x] resolves the current widened child-object closure including `OBJ/W.OBJ`
- [x] resolves the current widened transitive child-object closure including `OBJ/W.OBJ` and `OBJ/Z.OBJ`
- [x] resolves sibling child objects from the root:
  `OBJ/W.OBJ` and `OBJ/Z.OBJ`
- [x] resolves sibling child objects from a child module:
  `OBJ/Z.OBJ` and `OBJ/Q.OBJ`
- [x] reuses the same root child object across repeated call sites
- [x] reuses the same transitive child object across multiple parents
- [x] emits a widened `BIN/MAIN.AVM` of `76` bytes on that slice
- [x] emits a precedence-slice `BIN/MAIN.AVM` of `31` bytes
- [x] emits an arithmetic/comparison slice `BIN/MAIN.AVM` of `72` bytes
- [x] emits a direct-comparison print slice `BIN/MAIN.AVM` of `91` bytes
- [x] emits a high string-index slice `BIN/MAIN.AVM` of `143` bytes
- [x] emits a high integer-index slice `BIN/MAIN.AVM` of `135` bytes
- [x] emits a high string-index `IF/ELSE` slice `BIN/MAIN.AVM` of `156` bytes
- [x] emits a high string-index `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `153` bytes
- [x] emits a high string-index `DO ... UNTIL ... OD` + `IF/ELSE` slice `BIN/MAIN.AVM` of `166` bytes
- [x] emits a high integer-index `IF/ELSE` slice `BIN/MAIN.AVM` of `124` bytes
- [x] emits a high integer-index `DO ... UNTIL ... OD` + `IF/ELSE` slice `BIN/MAIN.AVM` of `134` bytes
- [x] emits a high string-index branch-external slice `BIN/MAIN.AVM` of `155` bytes
- [x] emits a high string-index transitive branch-external slice `BIN/MAIN.AVM` of `162` bytes
- [x] emits a high string-index shared-transitive branch-external slice `BIN/MAIN.AVM` of `181` bytes
- [x] emits a 17-root-string shared-transitive branch-external slice `BIN/MAIN.AVM` of `213` bytes
- [x] emits a high string-index shared-transitive `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `152` bytes
- [x] emits a high string-index nested shared-transitive branch slice `BIN/MAIN.AVM` of `178` bytes
- [x] emits a high string-index nested-loop external slice `BIN/MAIN.AVM` of `144` bytes
- [x] emits a full high int-index nested-loop `IF/ELSE` slice `BIN/MAIN.AVM` of `147` bytes
- [x] emits a full high string-index nested-loop `IF/ELSE` slice `BIN/MAIN.AVM` of `179` bytes
- [x] emits a direct-comparison branch slice `BIN/MAIN.AVM` of `149` bytes
- [x] emits a direct-comparison loop slice `BIN/MAIN.AVM` of `76` bytes
- [x] emits a direct-comparison branch-call slice `BIN/MAIN.AVM` of `77` bytes
- [x] emits an arithmetic/comparison `IF/ELSE` slice `BIN/MAIN.AVM` of `62` bytes
- [x] emits a branch-call `BIN/MAIN.AVM` of `69` bytes
- [x] emits an arithmetic/comparison branch-call `BIN/MAIN.AVM` of `73` bytes
- [x] emits a nested branch-call `BIN/MAIN.AVM` of `102` bytes
- [x] emits a branch-external `BIN/MAIN.AVM` of `74` bytes
- [x] emits a nested branch-external `BIN/MAIN.AVM` of `104` bytes
- [x] emits a transitive-external `BIN/MAIN.AVM` of `66` bytes
- [x] emits a transitive-branch-external `BIN/MAIN.AVM` of `93` bytes
- [x] emits a sibling-external `BIN/MAIN.AVM` of `68` bytes
- [x] emits a child-sibling-external `BIN/MAIN.AVM` of `82` bytes
- [x] emits a branch-local + transitive-external `BIN/MAIN.AVM` of `97` bytes
- [x] emits a repeated-root-external `BIN/MAIN.AVM` of `71` bytes
- [x] emits a shared-transitive-external `BIN/MAIN.AVM` of `85` bytes
- [x] emits a branch-sibling-external `BIN/MAIN.AVM` of `83` bytes
- [x] emits a branch-shared-transitive `BIN/MAIN.AVM` of `100` bytes
- [x] emits a dense local-call body slice `BIN/MAIN.AVM` of `256` bytes
- [x] emits a widened payload-buffer slice `BIN/MAIN.AVM` of `265` bytes
- [x] emits a widened over-`255` payload slice `BIN/MAIN.AVM` of `269` bytes
- [x] emits an `IF` slice `BIN/MAIN.AVM` of `65` bytes
- [x] emits an `ELSE` slice `BIN/MAIN.AVM` of `60` bytes
- [x] emits a nested-`IF` slice `BIN/MAIN.AVM` of `77` bytes
- [x] emits a nested-`ELSE` slice `BIN/MAIN.AVM` of `86` bytes
- [x] emits an early-return `IF` slice `BIN/MAIN.AVM` of `62` bytes
- [x] emits an early-return `ELSE` slice `BIN/MAIN.AVM` of `64` bytes
- [x] emits an early-return `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `62` bytes
- [x] emits an early-return `WHILE ... DO ... OD` slice `BIN/MAIN.AVM` of `65` bytes
- [x] emits a nested early-return `IF` slice `BIN/MAIN.AVM` of `105` bytes
- [x] emits an early-return local-call `IF` slice `BIN/MAIN.AVM` of `66` bytes
- [x] emits an early-return external `IF` slice `BIN/MAIN.AVM` of `66` bytes
- [x] emits an early-return external `ELSE` slice `BIN/MAIN.AVM` of `68` bytes
- [x] emits an early-return external `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `66` bytes
- [x] emits an early-return `WHILE` local/external slice `BIN/MAIN.AVM` of `85` bytes
- [x] emits a nested early-return transitive-external `IF` slice `BIN/MAIN.AVM` of `121` bytes
- [x] emits an early-return mixed branch/local-external `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `99` bytes
- [x] emits an early-return nested `DO ... UNTIL ... OD` external slice `BIN/MAIN.AVM` of `76` bytes
- [x] emits an early-return transitive-external `WHILE` slice `BIN/MAIN.AVM` of `81` bytes
- [x] emits an early-return nested `WHILE`/`DO` transitive-external slice `BIN/MAIN.AVM` of `91` bytes
- [x] emits a `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `47` bytes
- [x] emits a call/external `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `73` bytes
- [x] emits a branch `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `73` bytes
- [x] emits a branch-call `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `83` bytes
- [x] emits a branch-external `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `84` bytes
- [x] emits a nested `DO ... UNTIL ... OD` slice `BIN/MAIN.AVM` of `70` bytes
- [x] emits a nested loop + call/external slice `BIN/MAIN.AVM` of `83` bytes
- [x] emits a nested loop + nested-branch slice `BIN/MAIN.AVM` of `107` bytes
- [x] emits a nested loop + mixed branch local/external slice `BIN/MAIN.AVM` of `135` bytes
- [x] emits a `WHILE ... DO ... OD` slice `BIN/MAIN.AVM` of `49` bytes
- [x] emits a `WHILE` + call/external slice `BIN/MAIN.AVM` of `76` bytes
- [x] emits a `WHILE` + branch slice `BIN/MAIN.AVM` of `78` bytes
- [x] emits a `WHILE` + branch-call slice `BIN/MAIN.AVM` of `86` bytes
- [x] emits a `WHILE` + branch-external slice `BIN/MAIN.AVM` of `87` bytes
- [x] emits a nested `WHILE` slice `BIN/MAIN.AVM` of `76` bytes
- [x] emits a nested `WHILE` + call/external slice `BIN/MAIN.AVM` of `89` bytes
- [x] emits a nested `WHILE` + mixed branch local/external slice `BIN/MAIN.AVM` of `141` bytes
- [x] emits a `WHILE` + shared-transitive slice `BIN/MAIN.AVM` of `86` bytes
- [x] emits a `DO` + nested `WHILE` slice `BIN/MAIN.AVM` of `73` bytes
- [x] emits a `WHILE` + nested `DO` slice `BIN/MAIN.AVM` of `73` bytes
- [x] emits a `DO` + nested `WHILE` + call/external slice `BIN/MAIN.AVM` of `86` bytes
- [x] emits a `WHILE` + nested `DO` + call/external slice `BIN/MAIN.AVM` of `86` bytes
- [x] emits a mixed `DO`/`WHILE` + branch local/external slice `BIN/MAIN.AVM` of `138` bytes
- [x] emits a `WHILE` + nested `DO` + shared-transitive slice `BIN/MAIN.AVM` of `96` bytes
- [x] helper-bearing harness proof exists through:
  `ACTC -> ALINK -> AVMRUNC`
- [x] current harness runtime output for that widened slice:
  `HELLO`, `TOOL7`, `5459`
- [x] current harness runtime output for the precedence slice:
  `145`
- [x] current harness runtime output for the arithmetic/comparison slice:
  `14`, `5`, `1`, `1`, `TOOL7`
- [x] current harness runtime output for the direct-comparison slice:
  `1`, `1`, `1`, `1`, `0`, `0`
- [x] current harness runtime output for the high string-index slice:
  `A` through `P`
- [x] current harness runtime output for the high integer-index slice:
  `0` through `19`
- [x] current harness runtime output for the high string-index `IF/ELSE` slice:
  `I` through `P`
- [x] current harness runtime output for the high string-index `DO ... UNTIL ... OD` slice:
  `A` through `P`
- [x] current harness runtime output for the high integer-index `IF/ELSE` slice:
  `8` through `15`
- [x] current harness runtime output for the high string-index branch-external slice:
  `TOOL7` then `A` through `L`
- [x] current harness runtime output for the direct-comparison branch slice:
  `NE`, `LT`, `LE`, `GE`
- [x] current harness runtime output for the direct-comparison loop slice:
  `DO`, `DONE`
- [x] current harness runtime output for the direct-comparison branch-call slice:
  `HELLO`, `OK`
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
- [x] current harness runtime output for the early-return `IF` slice:
  `START`, `EARLY`
- [x] current harness runtime output for the early-return `ELSE` slice:
  `EARLY`
- [x] current harness runtime output for the early-return `DO ... UNTIL ... OD` slice:
  `START`, `EARLY`
- [x] current harness runtime output for the early-return `WHILE ... DO ... OD` slice:
  `START`, `EARLY`
- [x] current harness runtime output for the nested early-return `IF` slice:
  `START`, `EARLY`
- [x] current harness runtime output for the early-return local-call `IF` slice:
  `START`, `HELLO`
- [x] current harness runtime output for the early-return external `IF` slice:
  `START`, `TOOL7`
- [x] current harness runtime output for the early-return external `ELSE` slice:
  `TOOL7`
- [x] current harness runtime output for the early-return external `DO ... UNTIL ... OD` slice:
  `START`, `TOOL7`
- [x] current harness runtime output for the early-return `WHILE` local/external slice:
  `START`, `HELLO`, `TOOL7`
- [x] current harness runtime output for the nested early-return transitive-external `IF` slice:
  `START`, `MID`, `END`
- [x] current harness runtime output for the early-return mixed branch/local-external `DO ... UNTIL ... OD` slice:
  `START`, `TOOL7`
- [x] current harness runtime output for the early-return nested `DO ... UNTIL ... OD` external slice:
  `START`, `TOOL7`
- [x] current harness runtime output for the early-return transitive-external `WHILE` slice:
  `START`, `MID`, `END`
- [x] current harness runtime output for the early-return nested `WHILE`/`DO` transitive-external slice:
  `START`, `MID`, `END`
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
- [x] current harness runtime output for the dense shared-transitive branch + early-return slice:
  `MID1`, `END`, `MID2`, `END`, `A` through `P`
- [x] emits a dense shared-transitive branch + early-return slice `BIN/MAIN.AVM` of `227` bytes
- [x] current harness runtime output for the dense mixed nested-loop + shared-transitive slice:
  `MID2`, `END`, `A` through `P`
- [x] emits a dense mixed nested-loop + shared-transitive slice `BIN/MAIN.AVM` of `223` bytes
- [x] current harness runtime output for the dense early-return nested mixed-loop + shared-transitive slice:
  `MID1`, `END`, `MID2`, `END`, `A` through `P`
- [x] emits a dense early-return nested mixed-loop + shared-transitive slice `BIN/MAIN.AVM` of `226` bytes
- [x] current harness runtime output for the dense branch-gated early-return nested mixed-loop + shared-transitive slice:
  `MID1`, `END`, `MID2`, `END`, `A` through `P`
- [x] emits a dense branch-gated early-return nested mixed-loop + shared-transitive slice `BIN/MAIN.AVM` of `251` bytes

## Current Biggest Risks

- Call-depth / return-context sensitivity around tool ABI file loads and saves.
  The current narrow VICE-facing path is green again, but this remains the
  first risk area when widening child-object loading or final output size.
- Proof friction from VICE automation.
  This is real, but secondary. It slows narrowing because some dirty lines perturb shell launch, mount timing, or prompt detection before the actual linker boundary is reached.
- Lack of a small, stable comparator for every dirty line.
  When the control path itself gets perturbed, it becomes harder to make honest claims about whether the next failure is in `ALINK` or in the shared tool/service context.

## How Current Debugging Relates To The Linker

The current debugging is directly about core linker function, not side work.

`ALINK` only becomes meaningfully functional when it can:

1. load the root object
2. load child objects for unresolved externals
3. build the final live image
4. save `BIN/<NAME>.AVM`
5. hand that image to `AVMRUN`

The active failures are in steps `2` and `4` on the widened dirty line, so the current work is still central linker work.

## What Is Not Claimed Here

- full ACTION! linker coverage
- full historical module/runtime graph support
- stability for every currently dirty widening experiment
