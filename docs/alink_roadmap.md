# `ALINK` Roadmap

Current as of `2026-04-16`.

This is the short planning document for the UDOS-native Action linker, `ALINK.PRG`.
For the detailed proof ledger, see [alink_status.md](./alink_status.md).
For object-format context, see [linker.md](./linker.md).

## Current Position

Committed baseline:

- `ALINK.PRG` launches from a UDOS Action workspace.
- It loads deterministic `AVO1` objects from `OBJ/`.
- It emits deterministic `AVM1` binaries to `BIN/<MODULE>.AVM`.
- `ALINK -> AVMRUN` is proven.
- `ACTC -> ALINK -> AVMRUN` is also proven on the committed Linux `VICE 3.7.1` line.

Current working-tree reality:

- The main active blocker is upstream of the linker: the current dirty-tree `ACTC` save regression.
- There is no stronger standalone `ALINK` regression than that on the last committed baseline.
- So linker work is currently less about rescue and more about preserving the proven baseline while compiler/runtime fixes land.

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
- Narrow exact-byte proof for emitted output.
- Proven handoff to `AVMRUN` on the real target.
- Proven chained handoff from compiler output on the committed baseline.

## Proven Widening Already Landed

- Larger object files beyond the old `255`-byte ceiling.
- Larger payloads beyond the old `255`-byte payload ceiling.
- Larger procedure sizes past `255` bytes.
- Deeper child-object closure than the old small-graph limit.
- Current loop/control-flow/body-op slice emitted by the widened compiler.

## Remaining Work

## Immediate Practical Work

- Keep standalone `ALINK` green while the compiler save-path regression is repaired.
- Reconfirm the chained `ACTC -> ALINK -> AVMRUN` proof after the current `ACTC` fix lands.
- Continue reducing probe-specific noise so linker failures are easier to separate from boot/mount noise.

## Medium-Term Linker Work

- Broaden supported object-graph shapes and external-resolution patterns.
- Broaden body-op coverage as `ACTC` widens.
- Broaden data/variable support beyond the current integer-centered slice.
- Broaden procedure/function semantics as compiler output becomes richer.

## Structural Work Still Outstanding

- Move beyond the current narrow dead-strip model toward fuller historical behavior.
- Improve map/debug output so linker decisions are easier to inspect on target.
- Keep object format, linker expectations, and compiler emission aligned as the compiler widens.

## Dependency Note

- The next meaningful linker milestone depends on a stable compiler object-save path.
- In practice, that means the highest-value next step for the overall toolchain is still restoring clean dirty-tree `ACTC` object emission.

## Next Milestones

1. Restore the current dirty-tree `ACTC` object-save path.
2. Reconfirm `make -C ../udos vice-action-alink` and `vice-action-alink-avmrun` on top of that fix.
3. Resume linker-surface widening once the upstream compiler/runtime boundary is stable again.
