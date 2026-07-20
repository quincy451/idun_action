# ACTC

Linux `actc` is the active compiler front end for the Idun fork.

Current contract:

- input: `SRC/<MODULE>.ACT`
- output: `OBJ/<MODULE>.OBJ`
- object format: text object records consumed by Linux `alink`
- runtime policy: emit object-level calls/imports only; final runtime selection
  belongs to Linux `alink`

The compiler uses dynamically sized C++ strings, vectors, maps, and syntax
trees; it does not retain C64 editor/compiler buffer limits. Module-level and
procedure-local `BYTE`/`CARD`/`INT`/`REAL` storage, recursive word and REAL
arithmetic, simple procedures/calls, printing, signed or unsigned word
comparisons, initialized/address-bound declarations, and structured IF/loop
forms emit native 6502 code and relocations. REAL operations and conversions
emit only the referenced standalone `RT_F_*`, `RT_I_TO_F`, `RT_S_TO_F`, and
`RT_F_TO_I` imports. C++ vectors back expression and control stacks; long
bodies use absolute local-label relocations instead of range-limited relative
branches. Unsupported source forms are diagnosed with source line numbers
instead of being omitted from a successful object.

`BYTE`, `CARD`, `INT`, and `REAL ARRAY` declarations use vector-backed compiler
metadata and emit contiguous target storage plus a relocated 16-bit array
pointer. Fixed dimensions, constant-value initializers, BYTE string
initializers, pointer-only declarations, and address-bound arrays are active.
Indexing is zero-based and lowers to indirect 6502 loads/stores. Ordinary typed
`POINTER` declarations support pointer values, `@variable`, and `pointer^`
loads/stores. REAL indices scale by four and indirect REAL reads/writes copy the
complete four-byte target representation.

Local `PROC` and `BYTE`/`CARD`/`INT`/`REAL FUNC` declarations accept grouped
scalar, array, pointer, and scalar REAL parameters. Call arguments are fully
evaluated into generated temporary storage before the callee's parameter cells
are updated and a local `JSR` is emitted. `RETURN(expression)` exits a function
with its typed value; word results use `A`/`X`, while REAL results use a
function-owned four-byte cell whose address is returned in `A`/`X`. Function
calls are expression nodes and can be nested in word or REAL arithmetic.
Storage cells remain statically linked. When a call lies on a direct or mutual
recursion cycle, it saves the caller's live parameter, local scalar, local
array, REAL, and expression-temporary bytes on the 6502 stack before arguments
are evaluated. It restores that frame after the callee returns and stages word
or REAL results across the restore. Recursion is therefore supported within
the available C64 hardware stack depth; larger local arrays consume
proportionally more stack per recursive call.

`MAIN` accepts either no parameters or the Idun process ABI
`PROC MAIN(CARD argc,CARD ARRAY argv)`. Its entry sequence snapshots the
16-bit argument count and argument-vector pointer from `$0F04-$0F07` before
global REU allocation or user statements. The count includes `argv(0)` and
the table entries point to zero-terminated strings.

`ASMBLOCK [ ... ]` runs a two-pass NMOS 6502 assembler inside a routine. It
supports the complete legal opcode/addressing matrix, block-local labels and
checked relative branches, Action scoped symbols, routine symbols, symbol
addends, and low/high-byte relocations. Raw `[constant ...]` code blocks remain
available when exact byte control is preferred.

`REU BYTE ARRAY` declarations emit runtime allocation at `MAIN` entry or the
local declaration point. REU peek functions are ordinary expression nodes, so
they can appear inside arithmetic and conditions. Poke procedures use the same
vector-backed argument staging as other builtins, with their value word passed
through the documented zero-page ABI.

Named `OVERLAY` bodies reuse the same vector-backed operation representation as
procedures. `OverlayCall` validates its target against the source overlay set
and emits a local JSR relocation. No placeholder overlay helper import is
emitted.

The complete `DBF1` callable surface lowers through explicit register and
zero-page signatures. DBF calls import only their selected 6502 modules; the
linker follows those imports into allocator-owned REU staging and standalone
C64 KERNAL file adapters. Compiler and linker operation do not require UDOS.

`actc` does not emit a standalone runtime artifact and does not depend on a
separate launch program. The direct C64 runtime product is created by `alink`.
