# REU Target ABI

The active REU ABI is between ACTC-generated 6502 code and standalone linked
runtime modules. It has no UDOS entry points.

## Public Helpers

`RT_REU_ALLOC`:

- input: array size low in `A` and high in `X`
- output: BYTE handle in `A`; `$FF` means allocation/probe failure

`RT_REU_PEEK8`:

- input: handle in `A`, offset low in `X`, offset high in `Y`
- output: byte in `A`

`RT_REU_PEEK16`:

- input: handle in `A`, offset low in `X`, offset high in `Y`
- output: word low in `A` and high in `X`

`RT_REU_POKE8` and `RT_REU_POKE16`:

- input: handle in `A`, offset low in `X`, offset high in `Y`
- value low/high: zero page `$0E/$0F`
- output: `A=1` on success and `A=0` on invalid handle/range

ACTC treats poke calls as procedures, so their status result is currently
discarded.

## Internal Helpers

`RT_REU_RESOLVE` receives a transfer count in `$0A/$0B`. It validates the
handle and exclusive end offset, then writes the resolved 24-bit address to
`$04-$06` and returns carry set. Carry clear reports failure.

`RT_REU_TRANSFER` receives:

- C64 address in `$02/$03`
- REU address in `$04-$06`
- transfer count in `$0A/$0B`
- command in `A` (`$EC` C64-to-REU or `$ED` REU-to-C64)

It saves and restores the C64 memory configuration at `$01`, makes I/O visible
while programming `$DF00-$DF0A`, switches to all RAM for the `$FF00` trigger,
and restores the original configuration afterward.

## Object Closure

REU helpers use ordinary OBJ1 imports and relocations. `RT_REU_STATE` is an
anchor import that loads the shared state object before references to its
exported tables are resolved. Programs without a REU declaration or call do
not include any REU module.

`tools/generate_reu_runtime.py` is the reproducible source for the active REU
OBJ1 files. Its `--check` mode verifies that checked-in runtime objects match
the generator without building or testing UDOS.
