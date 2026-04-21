# ActionC64U AVM Language Guide

This guide describes the current text format accepted by `tools/avm_pack.py`.

## File Structure

An AVM text file can contain:

- `entry <label-or-offset>`
- labels: `name:`
- instructions
- data directives

Comments start with `#` or `;`.

Example:

```text
entry start

start:
  setp16 msg
  calln print
  calln exit

msg:
  stringz "hello"
```

## Directives

- `entry <label|number>`: set the entry offset
- `byte 1, 2, 3` or `db 1, 2, 3`: emit raw bytes
- `stringz "text"` or `asciz "text"`: emit a NUL-terminated ASCII string

## Stack Model

- stack cells are 16-bit
- locals are 16-bit slots
- `store` pops
- `load` pushes
- arithmetic wraps to 16 bits
- `lt` and `gt` use signed 16-bit comparison

## Instructions

- `push8 <n>`
- `push16 <n|label>`
- `store <slot>`
- `load <slot>`
- `add`
- `sub`
- `eq`
- `ne`
- `lt`
- `gt`
- `band`
- `bor`
- `bxor`
- `shl1`
- `shr1`
- `dup`
- `drop`
- `jz <label>`
- `jmp <label>`
- `setp16 <label|offset>`
- `calln <target>`
- `native`

## Built-In `calln` Targets

String and process control:

- `print`
- `printe`
- `exit`
- `printi`
- `printie`

REU:

- `reu_alloc`
- `reu_free`
- `reu_peek8`
- `reu_poke8`
- `reu_peek16`
- `reu_poke16`

Console:

- `conin`
- `conout`

Numeric forms:

- decimal: `42`
- hex with `$`: `$2a`
- C-style numeric forms accepted by Python `int(..., 0)` such as `0x2a`

## Calling Conventions

### `print` / `printe`

1. `setp16 some_label`
2. `calln print` or `calln printe`

### `printi` / `printie`

1. push a 16-bit value
2. `calln printi` or `calln printie`

### `reu_alloc`

1. push size
2. `calln reu_alloc`
3. result handle is pushed back

### `reu_poke8`

Push arguments in this order:

1. handle
2. offset
3. value
4. `calln reu_poke8`

### `reu_peek8`

Push arguments in this order:

1. handle
2. offset
3. `calln reu_peek8`
4. value is pushed back

### `conin`

- `calln conin`
- pushed result is the input byte

### `conout`

1. push character value
2. `calln conout`

## Current Limits

The current runner is intentionally small:

- AVM file buffer: `4096` bytes in `vm.com`
- VM stack: `32` cells
- locals: `16` slots
- REU runtime operands: currently 16-bit stack values

## Good Reference Programs

- `examples/reu_runtime.avm.txt`
- `examples/vmecho.avm.txt`
