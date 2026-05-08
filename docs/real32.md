# ActionC64U REAL32

## Format

`REAL32` follows the IEEE-754 binary32 bit layout:

- bit 31: sign
- bits 30..23: biased exponent
- bits 22..0: stored fraction

Precision is 24 bits for normalized values because the leading `1` is implicit.
The exponent bias is `127`.

## Special Cases

- zero uses exponent `0` and fraction `0`
- the current host reference compiler permits signed zero after underflow
- NaN and infinity are not source-level values; if an operation would overflow to
  a non-finite result, compilation fails with `REAL32 overflow`

## Rounding Model

The current compiler evaluates REAL expressions on the host, but rounds each
REAL literal, conversion, and arithmetic result back to binary32 by packing and
unpacking a native 32-bit float. That keeps the reference behavior aligned with
the intended 32-bit format even before a full runtime implementation exists.

## Literals

Supported forms:

- `1.0`
- `3.14`
- `2e-3`
- `-1.2E+5`

Unary minus is parsed separately, so negative literals are represented as a
positive REAL literal with a unary `-` operator applied to it.

## Operators

Supported REAL operators:

- arithmetic: `+`, `-`, `*`, `/`
- comparisons: `=`, `<>`, `<`, `<=`, `>`, `>=`

Mixed integer/REAL expressions promote the integer operand to REAL first.

## Conversions

- `REAL(x)`: converts an integer value to REAL32
- `INT(r)`: converts REAL32 to `INT` by truncating toward zero
  - proven cases include `3/2 -> 1`, `-3/2 -> -1`, `1/3 -> 0`,
    `-1/3 -> 0`, `(1/10)*10 -> 1` before truncation, and the positive
    boundary case `REAL(32767) -> 32767`, the negative boundary roundtrip
    `REAL(0-32768) -> INT -> REAL`, and out-of-range rejection for
    `REAL(32768)` and `REAL(0-32768)-REAL(1)`

Current proven runtime arithmetic/print cases also include non-dyadic values:

- `1/3 -> 0.3333333432674407958984375`
- `1/9 -> 0.111111111938953399658203125`
- `2/9 -> 0.22222222387790679931640625`
- `1/11 -> 0.0909090936183929443359375`
- `2/11 -> 0.181818187236785888671875`
- `1/13 -> 0.076923079788684844970703125`
- `2/13 -> 0.15384615957736968994140625`
- `1/17 -> 0.0588235296308994293212890625`
- `2/17 -> 0.117647059261798858642578125`
- `1/19 -> 0.052631579339504241943359375`
- `2/19 -> 0.10526315867900848388671875`
- `1/23 -> 0.0434782616794109344482421875`
- `2/23 -> 0.086956523358821868896484375`
- `2/3 -> 0.666666686534881591796875`
- `1/7 -> 0.14285714924335479736328125`
- `1/10 -> 0.100000001490116119384765625`
- `(1/10)+(1/5) -> 0.300000011920928955078125`
- `((1/10)+(1/5))+(1/5) -> 0.5`
- `(1/2)-(1/10) -> 0.4000000059604644775390625`
- `((1/10)+(1/10))-(1/5) -> 0`
- `((1/10)+(1/10)+(1/10))*10 -> 3`
- `(2/13)+(1/13) -> 0.2307692468166351318359375`
- `(2/17)+(1/17) -> 0.17647059261798858642578125`
- `(2/19)+(1/19) -> 0.15789473056793212890625`
- `(2/23)+(1/23) -> 0.1304347813129425048828125`
- `(1/7)*7 -> 1`
- `(1/9)*9 -> 1`
- `(1/11)*11 -> 1`
- `(1/13)*13 -> 1`
- `(1/17)*17 -> 1`
- `(1/19)*19 -> 1`
- `(1/23)*23 -> 1`
- `(1/5)*(1/5) -> 0.0400000028312206268310546875`
- `(1/10)/(1/5) -> 0.5`
- `(1/17)/(2/17) -> 0.5`
- `(1/19)/(2/19) -> 0.5`
- `(1/23)/(2/23) -> 0.5`
- `(6/5)/(3/10) -> 4`

Rules:

- integer-to-REAL conversion rounds to binary32 if needed
- REAL-to-INT conversion fails if the truncated result does not fit in
  `-32768..32767`
- runtime `INT(r)` overflow currently reports `REAL->INT RANGE`
- assigning REAL directly to `BYTE`, `CARD`, or `INT` is rejected unless an
  explicit `INT(...)` conversion is used first

## Comparison Rules

- integer/REAL mixed comparisons promote the integer side to REAL
- comparison results are still integer truth values: `0` or `1`
- only finite REAL values are supported in the bootstrap compiler

## Overflow And Underflow Policy

- overflow: compile error
- division by zero: compile error
- underflow: allowed to round to signed zero

## Runtime Symbols

The linker-level REAL runtime surface currently uses these stable symbol names:

- `rt.f_add`
- `rt.f_sub`
- `rt.f_mul`
- `rt.f_div`
- `rt.f_cmp`
- `rt.i_to_f`
- `rt.s_to_f`
- `rt.f_to_i`
- `rt.print_f`

## UDOS-Native Linking Rule

REAL support must stay out of the AVM interpreter opcode set. REAL arithmetic,
conversion, comparison, and printing are link-time runtime-library routines.

ACTC should emit only the runtime symbols required by reachable source code:

- a REAL declaration by itself allocates REAL32 storage and does not import
  arithmetic or print code
- `+` on REAL values imports only `rt.f_add`
- `-` on REAL values imports only `rt.f_sub`
- `*` on REAL values imports only `rt.f_mul`
- `/` on REAL values imports only `rt.f_div`
- REAL comparisons import only `rt.f_cmp`
- `REAL(x)` imports the matching integer bridge helper:
  `rt.i_to_f` for `BYTE`/`CARD` and `rt.s_to_f` for `INT`
- `INT(r)` imports only `rt.f_to_i`
- `PrintR` or `PrintRE` imports only `rt.print_f` plus the needed line/string
  output support

ALINK is then responsible for pulling only those runtime objects into the final
AVM image. Programs that do not use REAL must not pay for REAL code, and REAL
programs must not pay for unused REAL operators.

## Current UDOS-Native Slice

The current UDOS-native compiler/linker slice proves REAL declaration storage
metadata and the first operator-specific runtime import:

- `REAL X` emits a 4-byte variable slot in the AVO object
- ALINK preserves that 4-byte width in the linked AVM data layout
- `R=A`, where both variables are `REAL`, emits low/high word load/store ops
  and no REAL runtime import
- `R=A+B`, where all three variables are `REAL`, emits a live import of only
  `RT_F_ADD` / `rt_f_add`
- `R=A-B`, where all three variables are `REAL`, emits a live import of only
  `RT_F_SUB` / `rt_f_sub`
- `R=A*B`, where all three variables are `REAL`, emits a live import of only
  `RT_F_MUL` / `rt_f_mul`
- `R=A/B`, where all three variables are `REAL`, emits a live import of only
  `RT_F_DIV` / `rt_f_div`
- narrow integer-to-REAL conversion imports only the matching bridge helper
  (`RT_I_TO_F` / `rt_i_to_f` or `RT_S_TO_F` / `rt_s_to_f`)
- narrow REAL compare conditions import only `RT_F_CMP` / `rt_f_cmp`
- narrow `PrintR` / `PrintRE` lowering imports only `RT_PRINT_F` /
  `rt_print_f`
- no conversion, comparison, or print helper is imported for that source
  unless that operation is actually lowered later

The linker now has the required runtime-library lookup shape for per-operation
REAL helpers: pending externals search `OBJ/` first and then `LIB/`. The current
target-side text AVO spelling uses underscore aliases such as `rt_f_add`, which
map to the logical runtime symbols such as `rt.f_add`.

ALINK now queues helper objects from live `uN` body operations, not from
object-level `u <symbol>` metadata alone. That is required for REAL operator
dead-stripping: a helper mentioned only by a dead procedure must not enter the
final AVM image.

The repo now carries UDOS-target text runtime objects under
`src/runtime/udos_modules/`, and the workspace exporter overlays them into
`LIB/`. `rt_f_add.avo` is currently a partial helper: it returns the nonzero
operand when either side is exact `+0.0` and returns REAL32 zero for other
non-zero inputs except same-sign equal-power-of-two sums such as
`1.0 + 1.0 = 2.0`, `2.0 + 2.0 = 4.0`, `4.0 + 4.0 = 8.0`, and
`-2.0 + -2.0 = -4.0`, adjacent-exponent sums such as
`2.0 + 1.0 = 3.0`, `1.0 + 2.0 = 3.0`, and `-2.0 + -1.0 = -3.0`,
adjacent-exponent mixed-sign differences such as `2.0 + -1.0 = 1.0`,
`1.0 + -2.0 = -1.0`, `-2.0 + 1.0 = -1.0`, and
`-1.0 + 2.0 = 1.0`, gap-two sums such as `4.0 + 1.0 = 5.0`,
gap-two mixed-sign differences such as `4.0 + -1.0 = 3.0`,
`1.0 + -4.0 = -3.0`, `-4.0 + 1.0 = -3.0`, and
`-1.0 + 4.0 = 3.0`, plus exact `1.5 + 1.5 = 3.0`.
Equal-and-opposite cancellation is currently proven for `2.0 + -2.0`, but
broader mixed-sign addition remains incomplete. `rt_f_sub.avo` is also
partial: it handles `x - +0.0 = x`, `+0.0 - x` by flipping the sign bit,
equal signed power-of-two subtraction as zero, adjacent-exponent differences
such as `4.0 - 2.0 = 2.0`, `2.0 - 4.0 = -2.0`, and
`-4.0 - -2.0 = -2.0`, adjacent-exponent mixed-sign sums such as
`2.0 - -1.0 = 3.0`, `1.0 - -2.0 = 3.0`,
`-2.0 - 1.0 = -3.0`, and `-1.0 - 2.0 = -3.0`,
gap-two differences such as `4.0 - 1.0 = 3.0` and
`1.0 - 4.0 = -3.0`, gap-two mixed-sign sums such as
`4.0 - -1.0 = 5.0`, `1.0 - -4.0 = 5.0`,
`-4.0 - 1.0 = -5.0`, and `-1.0 - 4.0 = -5.0`, and exact
`2.0 - 1.0 = 1.0`.
`rt_f_mul.avo` is partial: it handles zero identity, `x * 1.0 = x`,
`1.0 * x = x`, signed power-of-two products such as
`2.0 * 2.0 = 4.0`, and low-word-zero values scaled by a power-of-two
operand, including `1.5 * 2.0 = 3.0` and `2.0 * 1.5 = 3.0`.
`rt_f_div.avo` is partial: it handles zero numerator, divide-by-zero as zero,
`x / 1.0 = x`, signed power-of-two quotients such as `4.0 / 2.0 = 2.0`,
and low-word-zero values divided by a power-of-two denominator, including
`3.0 / 2.0 = 1.5` and `1.5 / 2.0 = 0.75`.
These prove library lookup, stack
shape, dead-strip behavior, identity behavior, and first non-zero arithmetic
results without claiming complete IEEE-754 arithmetic yet.

## Current REAL Helper ABI

The current target-side REAL value ABI is intentionally simple:

- a `REAL32` stack value is two 16-bit cells
- cells are ordered low word first, then high word
- `RT_F_ADD`, `RT_F_SUB`, `RT_F_MUL`, and `RT_F_DIV` consume `lhs.low`,
  `lhs.high`, `rhs.low`, `rhs.high`
- REAL operator helpers push `result.low`, `result.high`
- ACTC emits `L` / `U` body ops to load the low and high words
- ALINK lowers `U` to the existing AVM `LOAD` opcode at variable offset `+2`
- ACTC emits `T` / `S` after the helper so the high word is stored first and
  then the low word is stored
- ALINK lowers `T` to the existing AVM `STORE` opcode at variable offset `+2`

The current UDOS-native compiler accepts only a narrow integer bridge in the
REAL paths:

- `REAL X=[0]`
- `REAL X`, `X=0`
- `REAL X`, `X=7`
- `REAL X`, `X=(1+2*3)`
- `REAL X`, `X=256`
- `REAL X`, `X=32767`
- `REAL X`, `X=(255+1)`
- `REAL X`, `X=0-256`
- `REAL X`, `X=REAL(255+1)`
- `REAL X`, `X=REAL(32767)`
- `REAL X`, `X=REAL(0-256)`
- `CARD A=[255]`, `REAL X`, `A=A+1`, `X=A`
- `CARD A=[255]`, `REAL X`, `A=A+1`, `X=REAL(A)`
- `BYTE A=[7]`, `REAL X`, `X=A`
- `BYTE A=[7]`, `REAL X`, `X=REAL(A)`
- `INT A=[0]`, `REAL X`, `A=0-7`, `X=A`
- `INT A=[0]`, `REAL X`, `A=0-7`, `X=REAL(A)`
- `REAL A`, `REAL B`, `REAL C`, then `IF A<B THEN`, `IF B=C THEN`,
  `IF C>=B THEN`, `IF A<>C THEN`, `IF B>A THEN`, and `IF A<=B THEN`

These body-assignment cases lower to two integer literal pushes plus the
existing high-word/low-word REAL store path and, for the current variable
bridges, import only the needed conversion helper:

- `BYTE`/`CARD` variable bridges import only `rt.i_to_f`
- signed `INT` variable bridges import only `rt.s_to_f`
- explicit `REAL(<integer var>)` bridges import only the same helper selected
  by the source var type

The current bridge surface is still intentionally narrow:
- module-scope non-zero REAL initializers are still rejected
- larger non-negative body assignments such as `X=256` and grouped `+`/`-`
  expressions such as `X=(255+1)` now lower through only `rt.i_to_f`,
  including the positive 16-bit boundary case `X=32767`
- direct signed body assignments such as `X=0-256` now lower through only
  `rt.s_to_f`
- explicit `REAL(<integer var>)` body assignment now lowers through only
  `rt.i_to_f` for `BYTE`/`CARD` vars and only `rt.s_to_f` for `INT` vars
- explicit `REAL(<narrow integer expression>)` body assignment now lowers
  through only `rt.i_to_f` for non-negative cases such as `REAL(255+1)` and
  `REAL(32767)`, and only `rt.s_to_f` for signed `0-<positive expr>` cases
  such as `REAL(0-256)`
- the first positive 16-bit `*` / `/` bridge cases now lower through only
  `rt.i_to_f`, for example direct `X=(128*2)` and explicit
  `X=REAL(128*2)` / `X=REAL(512/2)`
- the first signed grouped 16-bit `*` / `/` bridge cases now lower through
  only `rt.s_to_f`, for example direct `X=0-(128*2)` and explicit
  `X=REAL(0-(128*2))` / `X=REAL(0-(512/2))`
- `PrintR` / `PrintRE` now prints the current proven REAL32 slice, including
  integral values such as `7.0`, fractional dyadic values such as `1.5`,
  `0.75`, `0.125`, `0.03125`, `0.015625`, `0.00390625`, and
  `0.000030517578125`, signed dyadic values such as `-0.5`, first
  low-word-nonzero dyadic values such as `129/256 = 0.50390625`, first
  non-dyadic division cases such as
  `1.0 / 3.0 = 0.3333333432674407958984375` and
  `1.0 / 10.0 = 0.100000001490116119384765625`, and first
  end-to-end arithmetic print cases such as
  `1.5 + 1.5 = 3.0`, `4.0 + -1.0 = 3.0`, `1.0 + -4.0 = -3.0`,
  `-1.0 + 4.0 = 3.0`, `4.0 - 1.0 = 3.0`, `4.0 - -1.0 = 5.0`,
  `-1.0 - 4.0 = -5.0`, `1.5 * 2.0 = 3.0`, `-1.5 * 2.0 = -3.0`,
  `1.5 * -2.0 = -3.0`, `-1.5 * -2.0 = 3.0`,
  `1.5 * 1.5 = 2.25`, `0.75 * 0.75 = 0.5625`,
  `-3.0 / 2.0 = -1.5`, `3.0 / -2.0 = -1.5`,
  `-3.0 / -2.0 = 1.5`, `1.5 / 1.5 = 1.0`, `1.5 / 0.75 = 2.0`,
  `(1.0 / 3.0) * 3.0 = 1.0`, and `(1.0 / 10.0) * 10.0 = 1.0`
- wider `REAL(<literal-or-expression>)` still depends on broader typed
  expression lowering plus more helper proofs beyond the current proven
  grouped 16-bit `+`, `-`, `*`, and `/` bridge slice

This avoids false success where only part of a REAL32 slot would be read or
written.

Broader UDOS-native REAL32 literals, wider IEEE-754 `+`, `-`, `*`, `/`,
comparison, conversion, and broader general `PrintR` / `PrintRE` formatting
outside the current proven dyadic/runtime slice, which now extends cleanly
down through `1/32768` on the current 16-bit-source/runtime path, remain
future work. The host/reference compiler still
has broader REAL behavior than the UDOS-native ACTC path.
