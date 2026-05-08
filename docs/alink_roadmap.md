# `ALINK` Roadmap

Current as of `2026-04-23`.

This is the short planning document for the UDOS-native Action linker, `ALINK.PRG`.
For the detailed proof ledger, see [alink_status.md](./alink_status.md).
For object-format context, see [linker.md](./linker.md).

## Current Position

Committed baseline:

- `ALINK.PRG` launches from a UDOS Action workspace.
- It loads deterministic `AVO1` objects from `OBJ/`.
- It now prefers `.OBJ` and falls back to legacy `.AVO` when needed.
- It emits deterministic direct `PRG` output to `BIN/<MODULE>.PRG` on the
  default live gate, while retaining `BIN/<MODULE>.AVM` on the AVM-specific
  compat gate.
- `ALINK -> MAIN.PRG` is proven on the default gate.
- `ALINK -> AVMRUN` is proven on the AVM-specific compat gate.
- `ACTC -> ALINK -> AVMRUN` is also proven on the committed Linux `VICE 3.7.1` line.

Current working-tree verification:

- The previous upstream `ACTC` save regression has been cleared on the current
  UDOS line.
- Standalone `ALINK` is green again on the current working tree.
- `ALINK -> AVMRUN` is green again as the AVM-specific linker/runner proof on
  the current working tree.
- `ACTC -> ALINK -> MAIN.PRG` is green again as the helper-free higher-level
  default on the current working tree.
- `ACTC -> ALINK -> MAIN.PRG` is now also green for the named imported
  `printmath` replay through `make -C ../udos vice-action-actc-alink-launch-printmath`.
- `ACTC -> ALINK -> AVMRUN` remains the helper-bearing compat replay path for
  the same shape rather than the primary higher-level proof.
- Linker work can move back from rescue verification to object/link-surface
  widening.

## Accomplished

## Tool And Runtime Integration

- Stable UDOS packaging on release media as `ALINK.PRG`.
- Stable `A:` release-tool launch path on the committed baseline.
- `AVMRUN.PRG` is packaged on release media, which keeps chained linker/runtime proofs off the weaker host-tree PRG launch path.
- Seeded `ALINK` and chained `ALINK -> AVMRUN` probes are stabilized on the committed baseline.

## Linker Core

- `AVO1` object loading from `OBJ/`.
- Parsing of export metadata.
- Parsing of `body_ops`.
- Parsing of unresolved external symbol lines.
- Parsing of integer and string literal pools.
- Use of compiler-emitted procedure sizes to recover procedure boundaries.
- Live-set construction from the requested module entry.
- Deterministic child-object loading across the current narrow dependency closure.

## Output Generation

- Deterministic `AVM1` binary emission to `BIN/<MODULE>.AVM`.
- First text `DBG1` sidecar emission to `BIN/<MODULE>.DBG`.
- Narrow exact-byte proof for emitted output.
- Proven handoff to `AVMRUN` on the real target.
- Proven chained handoff from compiler output on the committed baseline.

## Proven Widening Already Landed

- Larger object files beyond the old `255`-byte ceiling.
- Larger payloads beyond the old `255`-byte payload ceiling.
- Production `ALINK.PRG` now streams final output through the UDOS tool ABI
  instead of requiring one contiguous final-image buffer.
- The current production build has a harness proof for a `48079` byte
  `BIN/MAIN.AVM`, beyond both the old `575` byte ceiling and the interim
  `3072` byte buffer ceiling.
- `AVMRUN.PRG` now loads binary AVM images outside its BSS at `$3000`, with a
  current proven runtime file limit of `49152` bytes. This removes the old
  `2048` byte runtime load ceiling for binary `AVM1` images.
- AVMRUN uses `$0001 = $36` during file load and then switches to `$34` during
  payload patch/execute, which exposes RAM through `$EFFF` in the current
  widened window and restores the previous setting on exit.
- Production `ALINK.PRG` now accepts larger AVO inputs through a REU-backed
  source cache with a `512`-byte resident source window plus `255` bytes of
  lookahead, while keeping `BODY_OPS_STRIDE=255`, `EXPORT_MAX=16`,
  `EXTERNAL_MAX=36`, and `PENDING_SYMBOL_MAX=36`.
- Production `ALINK.PRG` now keeps `external_names`, `pending_names`,
  `export_names`, `var_names`, `string_literals`, `saved_string_literals`,
  `body_ops_data`, per-pending layout records, and export/proc layout tables in
  REU-backed tables.
- Production `ALINK.PRG` now also keeps the root/current export target mirrors
  inside that REU-backed export layout record, so the resident linker no longer
  carries separate root/current export target arrays.
- Production `ALINK.PRG` now also keeps root/current var target mirrors in
  REU-backed storage instead of resident arrays.
- Production `ALINK.PRG` now also stages loaded AVO source into REU instead of
  holding a resident `4097`-byte source buffer.
- Production `ALINK.PRG` now also emits the first debug sidecar bootstrap:
  text `DBG1` with per-module `m`, source-file `f`, procedure-entry `q`, and
  body-op source `l` records carried from linked objects, with `q` and `l`
  now keyed to final linked procedure entry PCs / line PCs. The first global
  debug record is also landed:
  `v g <type> <module_id> <var_index> <addr> <width> <file_id> <line> <col> <name>`.
  The same sidecar now also carries linked parameter/local debug records:
  `v p <type> <module_id> <export_index> <var_index> <addr> <width> <file_id> <line> <col> <name>`
  and
  `v l <type> <module_id> <export_index> <var_index> <addr> <width> <file_id> <line> <col> <name>`.
- Current shipped linker footprint is now `CODE=$28BD`, `BSS=$0793`, and
  runtime span `$0900-$394F`.
- Larger procedure sizes past `255` bytes.
- Deeper child-object closure than the old small-graph limit.
- Current loop/control-flow/body-op slice emitted by the widened compiler.
- Narrow `BYTE`/`CARD` compiler declaration output through the existing
  16-bit variable slot path.
- Optional variable-width metadata for compiler-emitted data, currently proving
  4-byte module-scope `REAL` storage.
- Pending externals now fall back from `OBJ/<symbol>.OBJ` to
  `LIB/<symbol>.OBJ`, proving the lookup shape needed for operator-specific
  runtime modules such as REAL helpers.
- Pending externals are queued from live `uN` body operations rather than every
  object-level `u <symbol>` line, so dead-stripped procedures do not pull their
  helper objects into the final image.
- First REAL add/subtract/multiply/divide assignment runtime shapes link from
  `LIB/` and use `U<n>` / `T<n>` body ops for high-word `LOAD` / `STORE`
  without adding AVM opcodes.

## Remaining Work

## Immediate Stability Work

- Keep standalone `ALINK` green while compiler and runtime changes continue.
- Keep `ALINK -> AVMRUN` and `ACTC -> ALINK -> AVMRUN` as the first chained
  regression gates.
- Continue reducing probe-specific noise so linker failures are easier to
  separate from boot/mount noise.

## Medium-Term Linker Work

- Broaden supported object-graph shapes and external-resolution patterns.
- Broaden body-op coverage as `ACTC` widens.
- Broaden data/variable support beyond the current integer-centered slice.
- Grow `ALINK` into the source-debug metadata merger described in
  [source_debugger_roadmap.md](./source_debugger_roadmap.md): object-level
  file/proc/line/var debug records need to become final `BIN/<NAME>.DBG`
  sidecars keyed to linked addresses. The first bootstrap sidecar now carries
  file/proc/line records plus linked global/parameter/local variable records,
  but it still needs any richer range/frame data the debugger will consume.
- Converge UDOS text-object runtime symbol spelling with the logical dotted
  runtime names, or keep a documented alias map if target constraints require
  underscore names.
- Continue consuming ACTC-emitted REAL runtime imports as operator-specific link
  inputs rather than AVM opcode growth or one monolithic REAL blob.
- Broaden procedure/function semantics as compiler output becomes richer.

## Structural Work Still Outstanding

- Production `ALINK` streamed output is now proven at `48079` bytes. Keep this
  proof green while other linker semantics widen.
- Replace AVMRUN's current low-RAM binary AVM window with a REU/banked executor
  or loader/interpreter split so runtime execution can also reach near `48K`.
- Continue widening source/object table limits now that ALINK's final output
  path is no longer constrained by a single linker-owned image buffer.
- Continue the ALINK REU move beyond the already-landed body-op,
  pending/external-symbol, export/var-name, string-pool, source-window,
  per-pending-layout, export/proc-layout, root/current export-target, and
  root/current var-target cuts. The next obvious resident-pressure targets are
  the still-live metadata tables: final map/debug data and the small integer
  literal tables.
- Keep the current bootstrap sidecar as text `DBG1` until the debugger can
  consume it, then decide whether the next format should stay text or move to a
  compact binary `DBG1`. Keep the sidecar model itself: normal `.AVM` images
  should not permanently carry source debug payload.
- Keep the UDOS external-tool file ABI version 2 stream-write services stable:
  begin write, write chunk, and close write.
- Move beyond the current narrow dead-strip model toward fuller historical behavior.
- Improve map/debug output so linker decisions are easier to inspect on target.
- Keep object format, linker expectations, and compiler emission aligned as the compiler widens.

## Dependency Note

- The linker still depends on stable compiler object emission.
- That dependency is currently green again, so the next meaningful linker work
  can widen object-graph and body-op coverage instead of chasing the prior
  save-path blocker.

## Next Milestones

1. Keep `make -C ../udos vice-action-alink` green.
2. Keep `make -C ../udos vice-action-alink-compat` and `vice-action-actc-alink-launch-printmath` green as legacy compat/direct named proofs, while keeping `vice-action-actc-alink-compat-printmath` available as the helper-bearing compat replay target.
3. Keep the `48079` byte production ALINK streamed-output proof green.
4. Keep AVMRUN's current `49152` byte execution path green and decide later
   whether runtime growth past that window should use REU or another banked
   executor design.
5. Replace the current partial `RT_F_ADD`, `RT_F_SUB`, `RT_F_MUL`, and
   `RT_F_DIV` aliases with real floating-point `LIB/` code, then add the
   remaining REAL operator aliases and proofs one at a time.
