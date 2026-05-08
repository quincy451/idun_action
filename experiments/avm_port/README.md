# AVM Port Feasibility Probe

This directory holds direct-AVM experiments intended to answer one question:

- if some compiler/linker logic moves from resident 6502 into AVM payload code,
  does the logic itself get materially smaller?

This is not a product change. Existing tool code and build contracts stay intact.

## Benchmark Set

The current direct-AVM probes cover three workload shapes:

1. parser/state machine
2. emitter/serializer
3. closure/walk with dedupe

That is a better test than arguing from one parser alone.

## Probe A: `ALINK` `body_ops` Parser

Current 6502 slice:
- source: [alink.asm:1773](/mnt/c/test/action/actionc64u/src/tools_udos/alink/alink.asm:1773)
- helper: [alink.asm:1103](/mnt/c/test/action/actionc64u/src/tools_udos/alink/alink.asm:1103)
- sizes from [alink.current.labels](/mnt/c/test/action/actionc64u/build/udos_tools/alink.current.labels):
  - parser: `244` bytes
  - store helper: `44` bytes
  - comparable total: `288` bytes

Direct AVM probe:
- source: [alink_bodyops_extract.avm.txt](/mnt/c/test/action/actionc64u/experiments/avm_port/alink_bodyops_extract.avm.txt)
- artifact: [ALINK_BODYOPS_EXTRACT.AVM](/mnt/c/test/action/actionc64u/build/udos_tools/ALINK_BODYOPS_EXTRACT.AVM)
- packed file: `385` bytes
- payload: `375` bytes
- embedded filenames: `18` bytes
- approximate AVM logic: `357` bytes

Result:
- AVM is `69` bytes larger than the comparable 6502 slice

## Probe B: `ACTC` External-List Emitter Shape

Current 6502 slice:
- source: [actc_overlay_emit_object.asm:539](/mnt/c/test/action/actionc64u/src/tools_udos/actc/actc_overlay_emit_object.asm:539)
- size from [actc_overlay_emit_object.labels](/mnt/c/test/action/actionc64u/build/udos_tools/actc_overlay_emit_object.labels):
  - `emit_external_list`: `50` bytes

Direct AVM probe:
- source: [actc_emit_external_list_reu.avm.txt](/mnt/c/test/action/actionc64u/experiments/avm_port/actc_emit_external_list_reu.avm.txt)
- artifact: [ACTC_EMIT_EXTERNAL_LIST_REU.AVM](/mnt/c/test/action/actionc64u/build/udos_tools/ACTC_EMIT_EXTERNAL_LIST_REU.AVM)
- packed file: `129` bytes
- payload: `119` bytes
- embedded filename string: `11` bytes
- approximate AVM logic: `108` bytes

Important boundary:
- this AVM probe assumes a pre-populated REU name table and measures emitter logic only
- it does not include data-table construction overhead

Result:
- AVM is `58` bytes larger than the 6502 emitter slice

## Probe C: `ALINK` External Queue / Walk Shape

Current 6502 slice:
- source walk: [alink.asm:7106](/mnt/c/test/action/actionc64u/src/tools_udos/alink/alink.asm:7106)
- source enqueue: [alink.asm:7177](/mnt/c/test/action/actionc64u/src/tools_udos/alink/alink.asm:7177)
- sizes from [alink.current.labels](/mnt/c/test/action/actionc64u/build/udos_tools/alink.current.labels):
  - walk: `124` bytes
  - enqueue/dedupe: `59` bytes
  - combined comparison point: `183` bytes

Direct AVM probe:
- source: [alink_queue_external_digits.avm.txt](/mnt/c/test/action/actionc64u/experiments/avm_port/alink_queue_external_digits.avm.txt)
- artifact: [ALINK_QUEUE_EXTERNAL_DIGITS.AVM](/mnt/c/test/action/actionc64u/build/udos_tools/ALINK_QUEUE_EXTERNAL_DIGITS.AVM)
- packed file: `518` bytes
- payload: `508` bytes
- embedded filenames: `21` bytes
- approximate AVM logic: `487` bytes

Important boundary:
- this is a simplified but representative walk
- it scans `body_ops`-style text, skips one-operand body ops, recognizes `u` followed by one digit, and dedupes seen externals by index rather than by copied symbol-name string
- so this is still slightly simpler than the current 6502 implementation

Result:
- AVM is `304` bytes larger than the comparable 6502 walk+dedupe slice
- even against the scan-only `124`-byte 6502 routine, AVM is much larger

## Summary Table

| Probe | 6502 bytes | AVM logic bytes | Delta |
|---|---:|---:|---:|
| `ALINK` `body_ops` parser + store | 288 | 357 | +69 |
| `ACTC` external-list emitter | 50 | 108 | +58 |
| `ALINK` external queue/walk + dedupe | 183 | 487 | +304 |

## What The Current Evidence Says

On the current VM spec, direct AVM is not showing a size advantage for these compiler/linker-shaped slices.

The likely reasons are structural:
- AVM has no general payload-byte dereference primitive, so data-driven logic becomes file-stream or REU-state-machine code
- bytewise parsing and classification are dense on 6502 and verbose in current AVM opcodes
- small branches, comparisons, and local-state updates expand quickly in stack bytecode

## Current Recommendation

The fork idea "rewrite most of the compiler/linker in AVM to save memory" is currently discredited by these probes.

That does not mean AVM has no place. It means:
- AVM is not presently a good candidate for shrinking parser/emitter/linker-core logic
- if kept, it should be for execution portability or narrow runtime/helper surfaces, not because it is assumed to compress tool logic

## Best Next Check If We Want To Be Extra Sure

One more `ACTC` emit-oriented slice with a wider payload than `emit_external_list` would be the strongest final confirmation.
If that also loses, there is no serious size case left for a compiler/linker AVM fork on the current spec.
