# ActionC64U Language Guide

The language target is the Idun/Linux ActionC64U toolchain.

Build flow:

- source files live under `SRC/`
- Linux `actc` compiles source to `OBJ/`
- Linux `alink` links objects and helpers to `BIN/<MODULE>.PRG`

Runtime features should be represented as language/library bindings that lower
to linker-visible helper imports. ALINK decides which helpers enter the final
PRG.

The first Linux variable-backed `PrintI(...)` and `PrintIE(...)` paths lower to
`RT_PRINT_I.OBJ`, a standalone 6502 helper that formats the signed 16-bit value
in `A`/`X` and writes through C64 KERNAL `CHROUT`. `PrintIE(...)` then emits a
carriage return through `CHROUT`.

Simple variable plus/minus expressions, such as `x + 5` and `x + y`, lower to
native 16-bit 6502 `ADC`/`SBC` sequences before storing or calling the print
helper. `BYTE` operands are zero-extended when mixed with `CARD` operands.

Runtime conditions compare arbitrary word expressions with `=`, `<>`, `#`,
`!=`, `<`, `<=`, `>`, and `>=`. Ordered `BYTE`/`CARD` comparisons are unsigned.
`IF` supports `ELSEIF` and `ELSE`; loops support bare `DO`/`OD`, post-tested
`UNTIL`, pre-tested `WHILE`, expression-step `FOR`, and `EXIT`. Control bodies use
generated local labels and absolute `JMP` relocations, so their size is not
limited to a 6502 relative branch's 127-byte reach.

`FOR` evaluates its initial value, final value, and step once on entry. Bounds
and steps may be dynamic expressions; the captured step must be nonzero and
may be negative for descending loops. Changing an input variable inside the
body does not change the active bound or step.

## Dynamic Word Arithmetic

ACTC preserves normal product-before-sum precedence for dynamic word
expressions using `+`, `-`, `*`, `/`, and parentheses. ACTC lowers product
expressions into ordinary OBJ1 `m` machine-code records with local data exports
and `r` relocations. ALINK follows the reachable imports and selects
`RT_I_MUL.OBJ`, `RT_I_DIV.OBJ`, and `RT_PRINT_I.OBJ` only when referenced; it
does not compile a separate integer instruction stream. Multiplication keeps
the low 16 product bits. Multiplication, division, and `MOD` follow Action's
signed 16-bit semantics, with division truncating toward zero and a remainder
carrying the dividend's sign. A zero divisor returns zero. The active Linux
`PrintI` helper formats signed 16-bit decimal output.

Unary `+` and `-` are accepted, and decimal, `$`-prefixed hexadecimal,
`0x`-prefixed hexadecimal, and `%`-prefixed binary integer literals share the
same expression parser. Constant subexpressions are folded without pulling an
otherwise-unused arithmetic helper into the final PRG.

`BYTE`, `CARD`, signed 16-bit `INT`, and four-byte `REAL` declarations may
appear at module scope or inside a procedure. Module-scope variables use one
shared storage record referenced by every procedure in the object. Source
unsupported target extensions are reported with a line number; they are not
silently dropped from the output.

Action declaration bindings retain their original distinction. `BYTE x=[5]`
or `CARD x=[$1234]` emits initialized linked storage. `BYTE border=$D020` binds
the identifier to that C64 address and emits direct absolute loads/stores,
without allocating a second storage byte. Initializer and address ranges are
validated during compilation.

## Arrays, Pointers, and Strings

`BYTE ARRAY`, `CARD ARRAY`, `INT ARRAY`, and `REAL ARRAY` declarations may be
global or procedure-local. A dimension allocates contiguous linked storage;
`[...]` initializes numeric elements, a quoted BYTE initializer creates an
Action string, and `=$address` binds the array pointer to existing C64 memory.
As in original Action, an initializer determines the allocated element count
even when it differs from the written dimension, so `(0)` can request an
inferred initialized size. Adjacent packed hexadecimal constants such as
`[$FFA2$A686]` are accepted in initializers and code blocks. Undimensioned
arrays are pointer cells that can receive another array address.
Subscripts are zero-based word expressions. Like historical Action, generated
array accesses do not perform target-side bounds checks. REAL elements occupy
four bytes and participate directly in REAL expressions, assignments, and
comparisons.

Action strings are BYTE arrays whose element zero is the length and whose
following bytes are the characters. The active length field permits 255
characters. `PrintE(array)` emits a direct length-driven C64 KERNAL output loop
and a carriage return; no resident string service is required. String literals
used as procedure arguments or word values are emitted into linked,
length-prefixed storage.

`BYTE POINTER`, `CARD POINTER`, `INT POINTER`, and `REAL POINTER` values are
16-bit C64 addresses. `@variable` obtains linked storage's address and
`pointer^` reads or writes the pointed-to value. REAL ARRAY and REAL POINTER
parameters pass that same address through the local-routine ABI. Pointer and
array metadata is dynamically sized on Linux; allocated target storage and an
individual OBJ1 object remain limited by the C64's 16-bit address space.

Local procedures accept grouped parameters such as
`PROC Copy(BYTE value,CARD count,BYTE ARRAY data,BYTE POINTER out)`. Packed
record values and record pointers are also valid parameters. Arguments
are evaluated before any callee parameter cell is changed, then copied by value
into linked parameter storage. Array and pointer parameters pass their 16-bit
address. A call on a direct or mutual recursion cycle saves the caller's live
linked frame, including local array contents and expression temporaries, and
restores it after return.

`MAIN` may remain parameterless or use the Idun process signature
`PROC MAIN(CARD argc,CARD ARRAY argv)`. At program entry ACTC copies the
16-bit `aceArgc` and `aceArgv` values from `$0F04-$0F07` into those ordinary
parameter cells. `argc` includes the executable name, so user arguments begin
at index 1. `argv(index)` is a pointer to a zero-terminated Idun string, not a
length-prefixed Action string. The live target client replaces the target
service's own arguments with a program-owned table before execution. Use
`actdbg module live -- argument ...` to install arguments at startup, or the
live command `args argument ...` before `run`.

User-defined functions use declarations such as
`CARD FUNC Square(CARD value)` and end with `ENDFUNC` or the next routine
declaration. Every function must contain at least one `RETURN(expression)`;
plain procedures may use only bare `RETURN`. BYTE, CARD, and INT results return
in `A`/`X` (BYTE zeroes `X`). REAL results are copied to a function-owned
four-byte cell and return that cell's address in `A`/`X`. Calls participate in
normal word and REAL expressions, including nested calls. Per-call frame
preservation and result staging make direct and mutual recursion valid. Frame
bytes use the C64 hardware stack, so practical recursion depth depends on local
storage size and the stack already in use by the surrounding program.

REAL expressions support decimal/exponent literals, `INF`/`INFINITY`, `NAN`,
`+`, `-`, `*`, `/`, comparisons, `REAL(integer)`, `INT(real)`, `FAbs`,
`FSqrt`, `FTrunc`, `FFloor`, `FCeil`, `PrintR`, and `PrintRE`. Integer operands in REAL expressions are
promoted through the signed or unsigned conversion helper selected from their
declaration. ACTC folds constant REAL trees with a binary32 rounding boundary
after every operation and imports only the standalone 6502 helpers needed by
dynamic expressions. The target implements the complete IEEE-754 binary32
value domain, gradual underflow, round-to-nearest ties-to-even core arithmetic,
and exact decimal formatting; `docs/real32.md` records the detailed semantics.

`REU BYTE ARRAY name(size)` allocates far storage through a link-selected
hardware REU module. Global REU arrays are allocated at `MAIN` entry; local REU
arrays are allocated when their declaration executes. `ReuPeek8`,
`ReuPeek16`, `ReuPoke8`, and `ReuPoke16` accept normal word expressions for
their handle, offset, and value arguments. Builtin function calls can
participate in arithmetic and conditions. The current source surface uses
16-bit sizes and offsets, while successive arrays are placed across the REU's
24-bit address space. Invalid handles and out-of-bounds reads return zero;
writes report failure internally and leave REU memory unchanged.

`OVERLAY name` / `ENDOVERLAY` defines a named program-owned code section.
`OverlayCall(name)` lowers to a relocated `JSR` to that section. ALINK places
the section in the same PRG, so it executes without a resident loader or UDOS.
This active form preserves source behavior but is resident: it does not yet
reduce the loaded PRG footprint through dynamic swapping.

The `DBF1` family supports create/open/close, record positioning and metadata,
raw or field-relative byte access, append, delete/undelete, pack, and save.
Filename arguments are `CARD` pointers to zero-terminated C64 strings. One DBF
image of at most 65535 bytes is staged at a time in an allocator-owned REU
block; direct C64 KERNAL adapters read and write device 8. The implementation
is UDOS-free and link-selected. Save scratches an existing sequential file,
waits for the command-channel result, and then writes a fresh copy; it does not
use the 1541's unsafe save-with-replace command. The generated 6502 path has
executed two consecutive saves in headless VICE against a D64 image; physical
Idun/C64/REU validation remains.

`examples/prime_real.act` uses `FSqrt(REAL(candidate))` to bound trial division
and produces all 30 primes from 2 through 120; a generated PRG regression runs
the example in VICE and checks that count. `examples/reu_dbf_sort.act` is a
stable in-place DBF sorter whose parameterized `MAIN` accepts a zero-terminated
filename and one through ten command-line keys in `START,LENGTH,A|D` form.
Start positions are one based. Every field is compared in argument order until
one differs. DBF1 keeps the complete image in REU, while the sorter uses a
separate 255-byte REU buffer to swap full records without consuming C64 main
memory. The current DBF adapter bounds the example to 255 records of at most
255 bytes each within its 65535-byte staged image.

The first argument-bearing hardware calls are `ScreenCell(x,y,ch)` and
`ColorCell(x,y,color)`. ACTC evaluates each argument into generated word
storage, loads the helper ABI registers `A`, `X`, and `Y`, and imports the
corresponding standalone `RT_GFX_*` object. These helpers write C64 screen or
color RAM directly and do not call a resident service.

`GFX1` retains the low-level VIC bank, background/border, screen/bitmap base,
copy/fill, and bitmap-mode calls. It adds tracked bank-2-safe screen, bitmap,
and sprite memory; clipped hires/multicolor pixels; lines, rectangles, squares,
circles, and triangles; bitmap-resource blitting/movement; and complete sprite
placement/movement helpers. The high-level source is in `lib/gfx1.act`; each
referenced low-level primitive still imports only its matching `RT_GFX_*` or
`RT_SPRITE_*` object.

Global graphics declarations keep packed pixels out of source:

```action
SPRITE Player=RESOURCE "player.spr"
MSPRITE Enemy=RESOURCE "enemy.spr"
BITMAP Marker=RESOURCE "marker.abm"
MBITMAP Tile=RESOURCE "tile.abm"
```

ACTC validates ASP1/ABM1 files found beside the source or under project `RES/`,
aligns sprite data to a VIC-II 64-byte boundary, and embeds the asset in the
linked program. ACTEDIT F8 launches the matching Linux pixel editor. The
recommended large-program layout is `GfxHires($8400,$A000)` with
`GfxUseSprites($8800)`; tracked calls restore the C64 processor port after
accessing RAM hidden beneath BASIC ROM. Full signatures and binary formats are
listed in `docs/new_gfx_func.txt`.

`INPUT1` BYTE functions are also lowered through explicit register signatures.
Their return byte arrives in `A`; ACTC zero-extends it in `X` before storing a
`CARD` or `BYTE` expression result. Joystick/mouse constants participate in
normal integer expressions, and ALINK discovers linked presence/mouse state
objects transitively from the selected helper imports.

The procedure and BYTE-function surface in `SIDSPR1` uses the same mechanism,
including argument reordering, CARD splitting across `X/Y`, and `SpritePos`'s
ninth X-coordinate bit in carry. SID and sprite constants are available to the
integer expression parser. Shadow state for write-only SID controls is linked
only when a selected helper imports it.

## Inline and Fixed-Address 6502 Routines

`PROC`/`FUNC name=*()` introduces an inline 6502 routine and
`PROC`/`FUNC name=$address()` binds an existing routine. Bracketed code blocks
emit byte constants, little-endian word constants, symbol addresses with
addends, and the current code address `*`; they intentionally do not validate
6502 opcodes. Machine-routine argument bytes are flattened left-to-right into
`A`, `X`, `Y`, then `$A3` upward. BYTE results return in `A`; CARD and INT
results return in `A`/`X`. REAL machine/external parameters and results are not
part of this ABI.

`ASMBLOCK [ ... ]` is the instruction-oriented alternative to a raw code
block. It assembles every legal NMOS 6502 opcode and addressing mode, validates
relative branch range, and supports forward/backward labels scoped to that
block. Operands may reference fixed C64 addresses, Action globals, locals,
normal procedure/function parameters, REAL storage, packed records, and
declared Action routines. `symbol+1` addresses a later byte; `#<symbol` and
`#>symbol` emit low- and high-byte relocations. `JSR procedure` and
`JMP localLabel` use normal linker relocation. Registers are manipulated with
ordinary 6502 instructions such as `LDA`, `TAX`, and `DEX`. The
`examples/asmblock_demo.act` sample exercises named storage, parameters,
registers, and a local branch label.
