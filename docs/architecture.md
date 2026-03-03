# Architecture (Early Draft)

ActionC64U is currently planned as a staged toolchain:

1. Frontend parser + semantic passes for an Action-like language.
2. IR lowering to AcheronVM-compatible bytecode.
3. Runtime and system bindings for CP/M-65 execution model.
4. Packaging/link stage with dead-strip and overlay planning.

Initial architecture focus is on host-first determinism and testability.
