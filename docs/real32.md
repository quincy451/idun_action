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

- `rt.f_add`
- `rt.f_sub`
- `rt.f_mul`
- `rt.f_div`
- `rt.f_cmp`
- `rt.i_to_f`
- `rt.s_to_f`
- `rt.f_to_i`
- `rt.print_f`

## Direct PRG Linking Rule

REAL support is link-time runtime-library code. ACTC should emit only the helper
imports required by reachable source code, and ALINK should include only those
helpers in the final PRG.

Examples:

- a REAL declaration by itself allocates four bytes and imports no arithmetic
  helper
- `+` on REAL values imports `rt.f_add`
- `-` on REAL values imports `rt.f_sub`
- `*` on REAL values imports `rt.f_mul`
- `/` on REAL values imports `rt.f_div`
- REAL comparisons import `rt.f_cmp`
- `REAL(x)` imports the matching integer bridge helper
- `INT(r)` imports `rt.f_to_i`
- `PrintR` / `PrintRE` imports `rt.print_f` plus required text output support

Programs that do not use REAL must not pay for REAL helper code. Programs that
use only one REAL operation must not pay for unrelated REAL operators.

## Current Status

The current runtime helper set is partial and proof-oriented. It establishes
object metadata, helper lookup, stack shape, dead-strip behavior, identity cases,
and selected non-zero arithmetic cases without claiming complete IEEE-754
coverage yet.

The active implementation goal is direct linked PRG output with ALINK-owned
helper selection.
