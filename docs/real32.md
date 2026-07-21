# ActionC64U IEEE-754 REAL32

## Representation and Value Domain

`REAL` uses the IEEE-754 binary32 interchange format in four little-endian
bytes:

- bit 31 is the sign
- bits 30..23 are the biased exponent
- bits 22..0 are the stored fraction
- normal values have 24 bits of precision because the leading `1` is implicit

The runtime supports the complete binary32 value domain: positive and negative
finite values, positive and negative zero, gradual-underflow subnormals,
positive and negative infinity, and NaN. It has no former Q8.8 magnitude,
sign, or fractional-precision restriction.

The limits that remain are the intrinsic binary32 limits:

- maximum finite magnitude: approximately `3.4028234663852886E38`
- minimum positive normal: approximately `1.1754943508222875E-38`
- minimum positive subnormal: approximately `1.401298464324817E-45`
- precision: 24 binary significant bits, normally about 7 decimal digits

## Source Semantics

Source forms include decimal and exponent literals, `INF`/`INFINITY`, `NAN`,
`+`, `-`, `*`, `/`, comparisons, `REAL(integer)`, `INT(real)`, `FAbs`,
`FSqrt`, `FSign`, `FTrunc`, `FFloor`, `FCeil`, `FRound`, `FFrac`, `FMod`, `FMin`, `FMax`, `FClamp`, `PrintR`, and `PrintRE`.

Rules:

- every constant-folded and target-side arithmetic operation rounds to binary32
  using round-to-nearest, ties-to-even
- mixed integer/REAL expressions convert the integer operand to REAL first
- finite overflow produces signed infinity
- finite underflow is gradual and can produce a subnormal or signed zero
- nonzero division by signed zero produces signed infinity
- `0.0/0.0`, `INF-INF`, `0.0*INF`, and square root of a negative nonzero value
  produce NaN
- `FSqrt(-0.0)` preserves negative zero
- `FSign` returns canonical NaN for NaN, preserves either signed zero, and
  returns `-1.0` or `1.0` for every other negative or positive value
- `FTrunc` truncates finite values toward zero, preserves signed zero,
  infinities, NaN payloads, and values that are already integral
- `FFloor` rounds finite nonintegers toward negative infinity and preserves
  signed zero, infinities, NaN payloads, and integral values
- `FCeil` rounds finite nonintegers toward positive infinity and preserves
  signed zero, infinities, NaN payloads, and integral values
- `FRound` rounds finite nonintegers to the nearest integer with halfway cases
  away from zero and preserves signed zero, infinities, NaN payloads, and
  integral values
- `FFrac` returns `value-FTrunc(value)`; finite nonzero fractional parts keep
  their sign, while exceptional values follow ordinary REAL subtraction
- `FMod(value,divisor)` returns `value-FTrunc(value/divisor)*divisor`; NaN,
  zero divisor, and infinite dividend return canonical quiet NaN, while a
  finite dividend with an infinite divisor is returned bit-for-bit
- `FClamp(value,lower,upper)` returns canonical quiet NaN if any argument is
  NaN or if `lower>upper`; otherwise it returns
  `FMin(FMax(value,lower),upper)` with selected operand bits preserved
- ordered comparisons with NaN are false; `NAN<>value` is true, including
  `NAN<>NAN`
- positive and negative zero compare equal
- `INT(real)` truncates toward zero and returns zero for NaN, infinity, or a
  truncated result outside `-32768..32767`; this is the range of the destination
  `INT` type, not a restriction on REAL
- `PrintR` and `PrintRE` emit the exact finite decimal value with trailing
  fractional zeroes removed; special values print as `INF`, `-INF`, or `NAN`

Arithmetic helpers canonicalize a NaN result as quiet NaN `0x7FC00000`.
`FAbs` and source unary negation operate on the sign bit and therefore preserve
an existing NaN payload. The language contract has one deterministic rounding
rule; alternate rounding-mode controls and floating-point exception status
flags are not part of the Action source API.

## Runtime Symbols

ALINK resolves the following standalone helper symbols:

- `rt_f_add`
- `rt_f_sub`
- `rt_f_mul`
- `rt_f_div`
- `rt_f_cmp`
- `rt_f_sign`
- `rt_f_trunc`
- `rt_f_floor`
- `rt_f_ceil`
- `rt_f_round`
- `rt_f_frac`
- `rt_f_mod`
- `rt_f_min`
- `rt_f_max`
- `rt_f_clamp`
- `rt_f_abs`
- `rt_f_sqrt`
- `rt_i_to_f`
- `rt_s_to_f`
- `rt_f_to_i`
- `rt_print_f`

Each helper remains independently link-selected. A program using only `FAbs`,
for example, does not absorb add, divide, minimum/maximum, square-root, or
decimal-formatting code.

## Target Helper ABI

Binary arithmetic and comparison read operand pointers from zero page `$02/$03`
and `$04/$05`. Arithmetic writes through the destination pointer in `$06/$07`.
Unary REAL helpers read `$02/$03` and write through `$06/$07`.

Specific return conventions are:

- `rt_f_cmp` returns `-1`, `0`, or `1` in `A`/`X`, and returns `2` for unordered
  NaN comparisons
- `rt_f_sign` writes canonical quiet NaN for NaN input, copies signed zero
  exactly, and writes signed one for every other finite or infinite input; it
  has no imported helper dependency
- `rt_f_trunc` clears only fractional significand bits, preserves NaN payloads,
  infinities, signed zero, and integral values, and has no imported helper
  dependency
- `rt_f_floor` rounds finite nonintegers toward negative infinity, preserves
  NaN payloads, infinities, signed zero, and integral values, and imports only
  `rt_f_trunc`
- `rt_f_ceil` rounds finite nonintegers toward positive infinity, preserves
  NaN payloads, infinities, signed zero, and integral values, and imports
  `rt_f_floor` plus its transitive `rt_f_trunc` dependency
- `rt_f_round` rounds finite nonintegers nearest with halfway cases away from
  zero, preserves NaN payloads, infinities, signed zero, and integral values,
  and imports only `rt_f_trunc`
- `rt_f_frac` computes `value-FTrunc(value)`, supports aliased source and
  destination pointers, and imports `rt_f_trunc` plus `rt_f_sub`
- `rt_f_mod` reads value and divisor through `$02/$03` and `$04/$05`, writes
  through `$06/$07`, supports destination aliasing either operand, and imports
  `rt_f_div`, `rt_f_trunc`, `rt_f_mul`, and `rt_f_sub` to implement
  `value-FTrunc(value/divisor)*divisor`
- `rt_f_min` and `rt_f_max` write through `$06/$07`, ignore one NaN, select the
  right operand when both inputs are NaN, and preserve the left operand's exact
  bits when ordered values compare equal; both import `rt_f_cmp`
- `rt_f_clamp` reads value, lower, and upper through `$02/$03`, `$04/$05`, and
  `$08/$09`, writes through `$06/$07`, and imports comparison, maximum, and
  minimum. Any NaN or inverted bounds produce canonical quiet NaN; valid
  bounds preserve the exact selected value, including signed zero
- `rt_i_to_f` accepts an unsigned 16-bit value in `A` low and `X` high and
  writes through `$02/$03`
- `rt_s_to_f` accepts a signed 16-bit value in `A` low and `X` high and writes
  through `$02/$03`
- `rt_f_to_i` reads through `$02/$03` and returns the signed 16-bit result in
  `A` low and `X` high
- `rt_print_f` reads through `$02/$03` and writes characters through C64 KERNAL
  `CHROUT`

The arithmetic helpers synchronously use zero page `$20..$5A` as private
scratch. Generated Action code keeps no live value there across a helper call.
The exact printer additionally owns a private 54-byte integer workspace and a
128-byte reversed digit buffer inside its link-selected module.

## Rounding Implementation

Finite arithmetic unpacks each operand to a signed exponent and normalized
24-bit significand. Add/subtract align with guard, round, and sticky bits;
multiply uses the complete 48-bit significand product; divide emits 27 quotient
bits plus remainder sticky state; and square root performs a 54-bit restoring
integer square root. A shared pack path performs ties-to-even rounding, gradual
underflow, and overflow-to-infinity.

Linux ACTC folds constants with a binary32 rounding boundary after every source
operation, so a constant expression and the same dynamic expression have the
same value semantics. For example,
`(16777216.0+1.0)-16777216.0` folds to `0.0`, not `1.0`.

## Direct PRG Linking Rule

REAL support is runtime-library code selected by imports emitted from reachable
source:

- a REAL declaration by itself imports no arithmetic helper
- arithmetic imports only the matching operator helper
- comparisons import `rt_f_cmp`
- `REAL(x)` imports the matching signed or unsigned integer bridge
- `INT(r)` imports `rt_f_to_i`
- `FAbs(r)`, `FSqrt(r)`, direct `FSign(r)`, and `FTrunc(r)` runtime imports use
  only their respective unary helpers; portable MATH1 bodies may instead
  compile into ordinary reachable code where they remain source-defined
- `FFloor(r)` imports `rt_f_floor` plus its transitive `rt_f_trunc` dependency
- `FCeil(r)` imports `rt_f_ceil` plus transitive `rt_f_floor` and `rt_f_trunc`
- `FRound(r)` imports `rt_f_round` plus transitive `rt_f_trunc`
- `FFrac(r)` imports `rt_f_frac` plus its truncation and subtraction closure
- `FMod(a,b)` imports `rt_f_mod` plus its division, truncation,
  multiplication, subtraction, and special-value closure
- `FMin(a,b)` and `FMax(a,b)` import only the selected helper plus its comparison
  closure
- direct `FClamp(value,lower,upper)` imports `rt_f_clamp` plus its
  comparison/minimum/maximum closure; portable MATH1 may compile the same
  semantics into ordinary reachable code
- `PrintR` and `PrintRE` import `rt_print_f`

Programs that do not use REAL pay no REAL runtime code cost. Trigonometric and
other transcendental functions are supplied by the portable MATH1 library and
remain separate from the implemented binary32 core operations.

## Verification

`tools/generate_math_runtime.py --check --output src/runtime/modules` verifies
the generated compact OBJ1 core. `tools/generate_real_runtime.py --check`
remains a compatibility entry point and delegates to that generator plus the
shared 6502 manifest check. The shared manifest verifies that all checked-in OBJ1
modules match their reviewed generator. Headless VICE tests execute raw binary32
edge vectors and deterministic random vectors for arithmetic, sign, truncation, remainder,
minimum/maximum/clamp, square root, comparison, conversion, signed zero, subnormal,
infinity, NaN, and ties-to-even behavior. A separate target test compares exact
printed decimals at both finite extremes and across normal, subnormal,
signed-zero, and special values.
