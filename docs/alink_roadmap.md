# ALINK Roadmap

The linker process conversion is complete for the active OBJ1 contract. Linux
`alink` owns deterministic closure selection, relocation, direct C64 PRG
construction, and DBG sidecar generation.

Further work is format/runtime expansion rather than process porting:

- add object records only with strict parser, bounds, and determinism tests
- keep optional runtime families reachable-import selected
- preserve the project/shared-library search order
- validate new hardware helpers through direct PRG or attached-hardware gates

The active gates are `tests.test_linux_workspace_tools`,
`tests.test_idun_workspace_export`, and `tests.test_idun_prg_runtime`.
