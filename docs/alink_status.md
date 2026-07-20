# ALINK Status

Linux `alink` is the active Idun linker process. It resolves the reachable
`OBJ1` project/library closure and emits:

- `BIN/<MODULE>.PRG`: direct native C64 code and data
- `BIN/<MODULE>.DBG`: linked source, line, module, and symbol records

The linker searches project `OBJ/`, project `LIB/`, and the shared Idun
workspace `LIB/`. It validates object headers, body/import declarations,
export and relocation ranges, duplicate symbols, the root `MAIN` entry, and
the final 16-bit C64 address span. Runtime helper families enter the PRG only
when reachable imports select them.

Legacy name-only placeholder objects are rejected and excluded from exports.
The linker itself is a Linux executable; its output remains 6502 code.

Active proof:

```sh
python3 -m unittest -v tests.test_linux_workspace_tools
python3 -m unittest -v tests.test_idun_workspace_export
python3 -m unittest -v tests.test_idun_prg_runtime
```
