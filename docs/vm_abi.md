# VM ABI for Bootstrap ActionC64U Runtime

This ABI is still intentionally small, but `vm.com` is now a real stack
interpreter rather than a print-only placeholder.

## VM State

- one 16-bit data stack (`32` cells in the current runner)
- `16` 16-bit local slots
- one current string pointer set by `setp16`

All immediate addresses are payload-relative offsets inside the active `.avm`.

## Intrinsic Pseudo-Targets

`calln` uses reserved pseudo-addresses:

- `0xff00`: `Print`
- `0xff10`: `PrintE`
- `0xff20`: `Exit`
- `0xff30`: `PrintI`
- `0xff31`: `PrintIE`
- `0xff40`: `ReuAlloc`
- `0xff41`: `ReuFree`
- `0xff42`: `ReuPeek8`
- `0xff43`: `ReuPoke8`
- `0xff44`: `ReuPeek16`
- `0xff45`: `ReuPoke16`
- `0xff50`: `ConIn`
- `0xff51`: `ConOut`

These are not final machine addresses. `vm.com` recognizes them directly.

## Semantics

### `Print`

- input: current string pointer from `setp16`
- effect: print the string with no newline
- return: continue execution

### `PrintE`

- input: current string pointer from `setp16`
- effect: print the string followed by the standard CP/M newline sequence
- return: continue execution

### `Exit`

- input: none
- effect: terminate the current payload/program cleanly
- return: does not return to the caller

### `PrintI` / `PrintIE`

- input: pop one 16-bit value from the stack
- effect: print signed decimal, with `PrintIE` adding a newline
- return: continue execution

### REU Intrinsics

- `ReuAlloc`: pop `size`, push `handle`
- `ReuFree`: pop `handle`
- `ReuPeek8`: pop `offset`, `handle`; push zero-extended byte
- `ReuPoke8`: pop `value`, `offset`, `handle`
- `ReuPeek16`: pop `offset`, `handle`; push 16-bit value
- `ReuPoke16`: pop `value`, `offset`, `handle`

Current stack operands are 16-bit, so the first runtime REU path is aimed at
buffers and offsets within the low 64 KiB of a handle. The underlying backend
API remains 32-bit for future expansion.

### Console Intrinsics

- `ConIn`: push one input character from the CP/M console
- `ConOut`: pop one byte and write it to the CP/M console

## Bootstrap Compiler Pattern

`actc.com` still emits the older print-oriented pattern:

1. `setp16 <string_offset>`
2. `calln 0xff00` or `calln 0xff10`
3. `calln 0xff20`

Direct AVM assembly can now use the wider opcode/intrinsic subset.
