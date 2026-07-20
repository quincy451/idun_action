# ActionC64U Idun Matrix

| Area | Current status | Active proof |
| --- | --- | --- |
| Build and workspace tools | Linux C++ processes | `bash tools/build_linux_tools.sh` and `tests.test_linux_workspace_tools` |
| `actc` | Emits `OBJ1` machine code and relocations for the historical Action language surface, with documented target-specific exceptions | compiler matrix plus direct-PRG execution cases |
| `alink` | Resolves object/helper closure and emits C64 `.PRG` plus `.DBG` | `tests.test_linux_workspace_tools` linker cases |
| Dynamic integer runtime | Native `+`/`-`; selected standalone 6502 multiply, divide, and print helpers | dynamic-expression and helper-selection tests |
| Structured control | IF/ELSEIF/ELSE, DO/UNTIL, WHILE, FOR, and EXIT use vector-backed stacks and absolute labels | long-body, nesting, and loop tests |
| Scalar declarations | `BYTE`/`CARD`/signed `INT`/`REAL` storage, linked initialization, and direct C64 address bindings | declaration binding and signed bridge tests |
| Arrays, pointers, strings | BYTE/CARD/INT/REAL linked arrays, typed dereference/address-of including four-byte REAL values, length-prefixed BYTE strings, and frame-preserved local routine parameters | combined compile/link ABI, direct-PRG recursion, and target-size diagnostic tests |
| Idun program arguments | Parameterless MAIN or `MAIN(CARD argc,CARD ARRAY argv)` with a target-owned zero-terminated argument table | compiler ABI, fake target transport, and direct-PRG VICE execution tests |
| User functions | BYTE/CARD/INT/REAL functions, typed returns, early return, nested expression calls, and direct/mutual recursion use caller-frame preservation and staged results | compile/link diagnostics plus `tests.test_idun_prg_runtime` execution |
| Embedded 6502 assembly | `ASMBLOCK` assembles legal NMOS instructions/addressing modes, scoped Action symbols, low/high relocations, and local branch/jump labels | object diagnostics, linked sample, and direct-PRG VICE execution tests |
| REAL32 | Full-domain IEEE-754 binary32 arithmetic, comparison, conversion, absolute value, correctly rounded square root, and exact decimal printing use standalone link-selected 6502 helpers | generator consistency, compiler folding, raw edge/random VICE vectors, exact-output tests, and shipped examples |
| REU | `REU BYTE ARRAY` plus 8/16-bit peek/poke lower to direct `$DF00` hardware modules with linked bounds/allocation state | REU generator, source/closure, and size-diagnostic tests |
| Overlays | Named bodies are resident program-owned PRG sections; `OverlayCall` is a local relocation with no runtime host | shipped overlay and unknown-target tests |
| DBF | Complete `DBF1` call lowering with link-selected REU staging and C64 KERNAL file adapters; generated execution is VICE/D64-proven, with physical hardware validation pending | DBF generator, full-family closure, shipped-example, export, and direct-PRG tests |
| C64 hardware libraries | Complete `GFX1`, `INPUT1`, and `SIDSPR1` callable families use direct hardware/KERNAL modules | full-family compile/link tests |
| Runtime library layout | Project `LIB` plus shared Idun workspace `LIB` | shared-library dependency test |
| Idun export | Linux executables and active source/runtime files only; no UDOS artifacts or ASCII-payload stubs | `tests.test_idun_workspace_export` |
| Source formatting | ACTSPC atomically formats files/wildcards; ACTEDIT F6 formats its in-memory buffer with the same syntax-aware engine | formatter, compiler, export, idempotence, and PTY tests |
| Source editor/index | Linux editing, syntax highlighting, internal mark/copy/cut/paste, F1-F4 SQLite help, F5/F7 semantic navigation, history, and Ctrl-click lookup | help/catalog, code-map, and PTY interaction tests |
| Source debugger | Linked source lookup, SQLite-persisted breakpoints, live upload/control, instruction step, persistent breakpoint re-arm, sampling, and shared resident agent | protocol simulator, fake Idun transport E2E, and assembled 6510-agent harness; physical transport pending |
| Source profiler | Live/imported PC sampling with process/function/statement attribution and SQLite reports | deterministic fake Idun E2E and imported aggregation tests; physical sampling pending |

The active verification command is:

```sh
python3 -m unittest -v tests.test_linux_workspace_tools tests.test_idun_workspace_export
python3 -m unittest -v tests.test_action_help tests.test_code_map tests.test_profiler_target
python3 -m unittest -v tests.test_idun_prg_runtime  # skips when x64sc is absent
```

Historical UDOS source and test paths are not active proof for this fork. Final
programs remain C64 `.PRG` files, and any runtime behavior they need must be
provided by link-selected 6502 modules.
