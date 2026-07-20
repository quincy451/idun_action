# ActionC64U REU Model

## Active Source Surface

The Linux ACTC compiler accepts REU byte arrays and direct 8/16-bit accesses:

```text
REU BYTE ARRAY big(50000)
ReuPoke8(big, 0, 65)
ReuPoke16(big, 2, 1234)
ReuPeek8(big, 0)
ReuPeek16(big, 2)
```

A declaration creates a BYTE handle. Global arrays are allocated at `MAIN`
entry, and local arrays are allocated when execution reaches the declaration.
Allocation failure leaves the handle at `$FF`.

Peek calls are expression nodes. They can be assigned, printed, combined with
word arithmetic, or used in conditions. Poke calls are procedures. Arguments
are evaluated into compiler-generated word slots before the helper ABI is
loaded, so nested expressions do not depend on evaluation registers remaining
live.

## Linked Hardware Runtime

ALINK includes only the modules reached from source imports:

- `RT_REU_ALLOC` probes the REU and assigns a handle and 24-bit base address
- `RT_REU_STATE` holds handle-indexed allocation metadata
- `RT_REU_RESOLVE` validates a handle/range and computes a 24-bit REU address
- `RT_REU_TRANSFER` programs `$DF00-$DF0A` and triggers the transfer at `$FF00`
- `RT_REU_PEEK8` and `RT_REU_PEEK16` transfer from REU to C64 memory
- `RT_REU_POKE8` and `RT_REU_POKE16` transfer from C64 memory to REU

These are program-owned 6502 modules in the generated PRG. They do not call a
UDOS resident service.

The allocator uses the BYTE handle domain directly: `0..254` are usable and
`$FF` means failure. Allocation metadata is indexed by handle rather than
limited to the four-entry table in the historical C backend. Allocation is
monotonic across the REU's 24-bit address space.

## Current Limits

- source-visible array sizes are `1..65535` bytes
- source-visible offsets are 16-bit word expressions
- allocation is monotonic; source-level free is not active
- copy and 32-bit peek/poke helpers remain quarantined placeholders
- invalid handles and out-of-bounds reads return zero
- failed writes return internally without changing REU memory

The size/offset limit follows the currently active 16-bit Action scalar
expression surface. Extending it requires a wider source scalar and call ABI,
not a fixed Linux compiler buffer.

The cartridge is not currently connected to a C64, and VICE exits before the
monitor script in this environment. Compiler, linker, object-closure, and
generated-register-sequence tests are active; physical REU execution remains a
hardware integration checkpoint.
