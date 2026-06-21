# ActionC64U REAL32

## Format

`REAL32` follows IEEE-754 binary32 layout:

- bit 31: sign
- bits 30..23: biased exponent
- bits 22..0: stored fraction

Precision is 24 bits for normalized values because the leading `1` is implicit.
The exponent bias is `127`.

## Source Semantics

Supported forms include decimal literals, exponent notation, arithmetic
operators, comparisons, `REAL(x)`, and `INT(r)`.

Rules:

- mixed integer/REAL expressions promote the integer operand to REAL first
- REAL comparisons produce integer truth values: `0` or `1`
- REAL-to-INT conversion truncates toward zero
- REAL-to-INT conversion fails if the truncated result is outside
  `-32768..32767`
- source-level infinity and NaN are not supported values

## Runtime Symbols

The linker-level REAL runtime surface uses stable helper symbols:

- `rt_f_add`
- `rt_f_sub`
- `rt_f_mul`
- `rt_f_div`
- `rt_f_cmp`
- `rt_f_abs`
- `rt_f_sqrt`
- `rt_i_to_f`
- `rt_s_to_f`
- `rt_f_to_i`
- `rt_print_f`

## Target Helper ABI

The first implemented target-side helper ABI is intentionally narrow:

- `rt_i_to_f` accepts an unsigned 16-bit integer in `A` low and `X` high,
  and writes the converted REAL32 value through the destination pointer in zero
  page `$02/$03`
- `rt_s_to_f` accepts a signed 16-bit integer in `A` low and `X` high, and
  writes the exact REAL32 value through the destination pointer in zero page
  `$02/$03`
- `rt_f_to_i` reads a REAL32 value through the source pointer in zero page
  `$02/$03`, returns the signed 16-bit truncated result in `A` low and `X`
  high, and returns zero for unsupported or out-of-range inputs
- `rt_f_add` reads source REAL32 pointers from `$02/$03` and `$04/$05`, writes
  the result through destination pointer `$06/$07`, and currently supports
  non-negative inputs and sums below `128.0`; operands are converted through a
  Q8.8 fixed-point accumulator before being converted back to REAL32
- `rt_f_sub` reads source REAL32 pointers from `$02/$03` and `$04/$05`, writes
  the result through destination pointer `$06/$07`, and currently supports
  non-negative inputs where the result is greater than or equal to zero and
  below `128.0`; operands are converted through a Q8.8 fixed-point accumulator
  before being converted back to REAL32, and underflow writes zero
- `rt_f_mul` reads source REAL32 pointers from `$02/$03` and `$04/$05`, writes
  the result through destination pointer `$06/$07`, and currently supports
  non-negative inputs where the Q8.8 product is below `128.0`; operands are
  multiplied in fixed-point precision before being converted back to REAL32,
  and overflow writes zero
- `rt_f_div` reads source REAL32 pointers from `$02/$03` and `$04/$05`, writes
  the result through destination pointer `$06/$07`, and currently supports
  non-negative inputs with Q8.8 quotients below `128.0`; operands and the
  quotient are computed in Q8.8 precision before being converted back to REAL32,
  and divide-by-zero or wider results write zero
- `rt_f_cmp` reads source REAL32 pointers from `$02/$03` and `$04/$05`, returns
  signed byte comparison in `A`/`X`: `-1` for less, `0` for equal, and `1` for
  greater, and currently supports non-negative inputs below `128.0` converted
  through Q8.8 fixed-point precision
- `rt_f_abs` reads a REAL32 value through zero page `$02/$03`, copies it to the
  destination pointer in `$06/$07`, and clears the sign bit in the copied value
- `rt_f_sqrt` reads a REAL32 value through zero page `$02/$03`, writes through
  destination pointer `$06/$07`, and currently returns floor square roots for
  non-negative unsigned 16-bit REAL integer inputs; unsupported inputs write zero
- `rt_print_f` reads a REAL32 pointer from `$02/$03`, prints non-negative
  values below `128.0` through C64 `CHROUT`, converts through Q8.8 fixed-point
  precision, and emits up to two fractional decimal digits with trailing zeroes
  trimmed
- REAL32 values are stored little-endian in memory, so `7.0` is
  `00 00 E0 40`
- unsupported wider inputs currently write `0.0`

ALINK now lowers the covered direct-PRG REAL body operations to helper calls.
Later slices should broaden that lowering beyond the current proof cases.

## Direct PRG Linking Rule

REAL support is link-time runtime-library code. ACTC should emit only the helper
imports required by reachable source code, and ALINK should include only those
helpers in the final PRG.

Examples:

- a REAL declaration by itself allocates four bytes and imports no arithmetic
  helper
- `+` on REAL values imports `rt_f_add`
- `-` on REAL values imports `rt_f_sub`
- `*` on REAL values imports `rt_f_mul`
- `/` on REAL values imports `rt_f_div`
- REAL comparisons import `rt_f_cmp`
- `REAL(x)` imports the matching integer bridge helper
- `INT(r)` imports `rt_f_to_i`
- `FAbs(r)` imports `rt_f_abs`
- `FSqrt(r)` imports `rt_f_sqrt`
- `PrintR` / `PrintRE` imports `rt_print_f` plus required text output support

Programs that do not use REAL must not pay for REAL helper code. Programs that
use only one REAL operation must not pay for unrelated REAL operators.

## Action-Facing Reference

`LIB/MATH1.ACT` is the shipped Action-facing reference for the currently
implemented REAL32 helper surface. It documents the core source forms that ACTC
already recognizes directly: `REAL(x)`, `INT(x)`, REAL arithmetic/comparison
operators, `FAbs`, `FSqrt`, and `PrintR` / `PrintRE`.

`SRC/MATH1_DEMO.ACT` validates the exported-library path by compiling a small
REAL absolute-value program through ACTC, linking it with ALINK, and running
the linked `.PRG` directly. `FSqrt` is available for non-negative unsigned 16-bit
integer inputs; broader math functions such as trig remain deferred
until matching link-selected `RT_*.OBJ` modules and their call ABI are
implemented.

## Current Status

The current runtime helper set is partial and proof-oriented. It establishes
object metadata, helper lookup, stack shape, dead-strip behavior, identity cases,
and selected non-zero arithmetic cases without claiming complete IEEE-754
coverage yet.

The active implementation goal is direct linked PRG output with ALINK-owned
helper selection.
