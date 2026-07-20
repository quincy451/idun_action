# ACTC Roadmap

The 6502-resident compiler conversion is complete for the documented Idun
language surface. Linux `actc` owns parsing, semantic checks, native 6502
lowering, object metadata, and source diagnostics.

Further work is feature expansion rather than process porting:

- add deliberately specified Action source forms as tests and examples require
- keep recursive frame size and C64 object/address limits explicit
- preserve deterministic OBJ1 output and source/debug records
- preserve the completed IEEE-754 REAL helpers and broaden REU helpers independently of the Linux compiler

The active gates are `tests.test_linux_workspace_tools` and
`tests.test_idun_prg_runtime`.
