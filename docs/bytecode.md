# ActionC64U `.avm` Bytecode Format

## Version 1 Header

All multibyte integers are little-endian.

| Offset | Size | Field |
| --- | ---: | --- |
| 0 | 4 | Magic = `AVM1` |
| 4 | 1 | Format version = `1` |
| 5 | 2 | Payload length |
| 7 | 2 | Entry offset |
| 9 | 1 | Flags (reserved, currently `0`) |
| 10 | N | Payload bytes |

Header size is fixed at 10 bytes.

## Rules

- `payload length` is the exact byte count of the Acheron instruction stream.
- `entry offset` is the byte offset within the payload where execution begins.
- `flags` must be zero for version 1 readers/writers.
- Readers must reject files with the wrong magic, unsupported version, or an
  entry offset beyond the payload length.

## Current Runtime Opcode Subset

All jump/string offsets are payload-relative absolute offsets.

| Opcode | Mnemonic | Operands | Effect |
| ---: | --- | --- | --- |
| `0x10` | `push8` | `u8` | Push zero-extended byte onto the VM stack |
| `0x11` | `push16` | `u16` | Push 16-bit value onto the VM stack |
| `0x12` | `store` | `u8 slot` | Pop into local slot |
| `0x13` | `load` | `u8 slot` | Push local slot |
| `0x14` | `add` | none | Pop two, push `lhs + rhs` |
| `0x15` | `sub` | none | Pop two, push `lhs - rhs` |
| `0x16` | `eq` | none | Pop two, push `1` if equal else `0` |
| `0x17` | `ne` | none | Pop two, push `1` if different else `0` |
| `0x18` | `jz` | `u16` | Pop condition, jump if zero |
| `0x19` | `jmp` | `u16` | Unconditional jump |
| `0x1a` | `dup` | none | Duplicate top of stack |
| `0x1b` | `drop` | none | Discard top of stack |
| `0x1c` | `lt` | none | Signed `<`, returns `0/1` |
| `0x1d` | `gt` | none | Signed `>`, returns `0/1` |
| `0x1e` | `band` | none | Pop two, push `lhs & rhs` |
| `0x1f` | `bor` | none | Pop two, push `lhs | rhs` |
| `0x20` | `bxor` | none | Pop two, push `lhs ^ rhs` |
| `0x21` | `shl1` | none | Pop one, push `(value << 1) & 0xffff` |
| `0x22` | `shr1` | none | Pop one, push logical `value >> 1` |
| `0x2d` | `native` | none | Terminate and return to native caller |
| `0x49` | `calln` | `u16 target` | Invoke a VM intrinsic pseudo-target |
| `0x61` | `setp16` | `u16` | Set the current string pointer |

## Stability

This format is intentionally small and stable for bootstrapping:

- one payload
- one entry point
- no relocation table yet
- no export table yet

Future extensions can add optional trailing sections after the payload, guarded
by new version values or non-zero feature flags.

## Current Example

Examples in the repo currently cover two useful shapes:

- `examples/hello.avm`: minimal `calln`/`native` smoke payload
- `examples/reu_runtime.avm.txt`: stack/branch/REU runtime payload assembled by
  `tools/avm_pack.py`
- `examples/vmecho.avm.txt`: interactive console + REU payload assembled by
  `tools/avm_pack.py`
