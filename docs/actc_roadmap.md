# `ACTC` Roadmap

Current as of `2026-04-16`.

This is the short planning document for the UDOS-native Action compiler, `ACTC.PRG`.
For the detailed proof ledger, see [actc_status.md](./actc_status.md).
For broader project coverage, see [action_matrix.md](./action_matrix.md).

## Current Position

Committed baseline:

- `ACTC.PRG` launches from a UDOS Action workspace.
- It loads the current project manifest and the tracked `SRC/<MODULE>.ACT` source file.
- It emits deterministic `AVO1` object output to `OBJ/<MODULE>.AVO`.
- The integrated `ACTC -> ALINK -> AVMRUN` path is proven on the committed Linux `VICE 3.7.1` line.

Current dirty-tree investigation:

- `ACTC` front-end and codegen still appear correct.
- The active regression is in the mounted-tree save/service path on the working tree.
- Current failure shape is: `ACTC` escapes to `READY.` before `OBJ/MAIN.AVO` lands on the host.
- So the compiler itself is mostly past parsing/lowering right now; the active blocker is tool-runtime persistence.

## Accomplished

## Tool And Runtime Integration

- Stable UDOS packaging on release media as `ACTC.PRG`.
- Stable `A:` release-tool launch path on the committed baseline.
- Real-target build fits and launches under the widened tool load window.
- Real-target one-shot proof exists through `ACTC -> ALINK -> AVMRUN`.

## Compiler Front-End

- Module selection from the command line.
- Project/manifest guardrails.
- Source loading from `SRC/`.
- Module-header validation.
- Current narrow parser for arithmetic, comparisons, branching, loops, local calls, and unresolved external calls.
- Current narrow integer variable surface for module-scope and proc-local `INT` declarations.

## Object Emission

- Deterministic `AVO1` text object generation.
- Export metadata emission.
- `body_ops` emission.
- Literal-pool emission for the current narrow surface.
- Current runtime-import emission.
- Object-path generation to `OBJ/<MODULE>.AVO`.

## Proven Widening Already Landed

- Nested `IF` / `ELSE`.
- `WHILE ... DO ... OD`.
- `DO ... UNTIL ... OD`.
- Mixed arithmetic/comparison conditions.
- Current multi-variable integer state slice.
- Current local/external integer arg/return slice.
- Current larger-object and larger-proc-size coverage proved through the harness.

## Remaining Work

## Immediate Blocker

- Make the current dirty-tree `ACTC` save path green again.
- Specifically: fix the `svc_file_save_sc0` / mounted-tree write path so `vice-action-actc` writes `OBJ/MAIN.AVO` reliably on the host.
- Keep the standalone `ACTC` proof green before leaning on the chained wrapper again.

## Near-Term Compiler Work

- Preserve the committed `ACTC -> ALINK -> AVMRUN` proof while the save-path regression is fixed.
- Widen diagnostics so save/load/parse failures are easier to localize without temporary probe code.
- Add more direct target-side proofs for the compiler save boundary, not just the integrated chain.

## Medium-Term Language Work

- Broaden expression lowering beyond the current proven narrow slice.
- Broaden statement coverage beyond the current branch/loop/call subset.
- Broaden stateful variable semantics beyond the current integer-only slice.
- Broaden procedure/function semantics beyond the current local/external integer path.

## Structural Work Still Outstanding

- Move proc-local integer storage from the current proc-scoped static-slot model toward a real frame/local model.
- Continue widening compatibility toward historical ACTION! source behavior.
- Improve compiler-oriented diagnostics and error reporting on the real target.

## Next Milestones

1. Restore `make -C ../udos vice-action-actc` on the current working tree.
2. Reconfirm `ACTC -> ALINK -> AVMRUN` after that fix.
3. Resume compiler-surface widening once runtime persistence is stable again.
