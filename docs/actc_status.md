# ACTC Status

Linux `actc` is the active Idun compiler process. It reads
`SRC/<MODULE>.ACT`, emits native 6502 machine/data records and relocations in
`OBJ/<MODULE>.OBJ`, and has no CP/M-65 or UDOS dependency.

Current verified surface:

- BYTE, CARD, signed INT, and REAL scalars, arrays, pointers, and functions
- constant and dynamic word/REAL expressions
- IF/ELSEIF/ELSE, DO/UNTIL, WHILE, FOR, and EXIT
- local procedures plus direct and mutual recursion with frame preservation
- strings, integer/REAL printing, address-bound C64 storage, REU declarations,
  resident program-owned overlays, and the documented hardware/runtime builtins
- source-line records for Linux `alink` and `actdbg`

The compiler diagnoses unsupported forms instead of silently emitting a partial
object. Recursive frame preservation is emitted only on call-graph cycles; a
single preserved frame is capped at 224 bytes to leave C64 stack headroom.

Active proof:

```sh
python3 -m unittest -v tests.test_linux_workspace_tools
python3 -m unittest -v tests.test_idun_prg_runtime
```

The second command executes generated recursive word, local-array, mutual, and
REAL code in headless VICE when `x64sc` is available.
