# Prompt Chain Archive

The original `prompt-1.txt` through `prompt-18.txt` sequence is historical
bootstrap material and is not an active workflow.

The self-contained Idun/Linux fork uses:

```sh
make all
```

That command builds the native Linux tools, runs the active Idun tests, and
exports `build/idun-action/`. No sibling CP/M-65 or UDOS checkout is needed.

The maintained product path is:

```text
Linux actc -> OBJ/<MODULE>.OBJ -> Linux alink -> BIN/<MODULE>.PRG
```

The output PRG and selected `RT_*.OBJ` helpers are native 6502 code. See
[linux_tool_port_status.md](linux_tool_port_status.md) for the complete process
conversion inventory.
