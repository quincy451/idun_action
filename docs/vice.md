# Direct PRG Verification With VICE

VICE is optional and does not require an attached C64. The Idun test harness
starts `x64sc` headlessly, writes a linked PRG directly into C64 memory through
the binary monitor, discovers the PC and stack registers by name, and starts at
the PRG load address.

Run the generated-code gate:

```sh
python3 -m unittest -v tests.test_idun_prg_runtime
```

The test compiles and links recursive word, local-array, mutual-recursion, and
REAL calls. It then checks result memory written by the running 6502 program.
The test skips cleanly when `x64sc` is not installed.

Run another linked PRG manually:

```sh
python3 tools/vice_harness.py --prg path/to/MAIN.PRG --timeout 2
```

An optional disk can be attached with `--disk-image`, but no UDOS or CP/M disk
is part of the active verification path.
