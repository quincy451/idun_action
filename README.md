# ActionC64U - Action! Commodore 64 Ultimate Edition

ActionC64U is an early-stage, clean-room project to build an Action-like language toolchain for the Commodore 64 Ultimate ecosystem.

The language direction keeps the Action! vibe (compact, practical, Algol-60-ish syntax and workflows) while avoiding direct code reuse.

## Targets and Core Components

- Target OS/runtime environment: **CP/M-65**, sourced locally from `../cpm65-u64`
- VM backend: **AcheronVM**, sourced locally from `../acheronvm`
- Backend policy: project-specific backend extensions are allowed where needed

## Planned Feature Deltas

- `REAL32` type support: `1 sign bit, 8 exponent bits, 24 mantissa bits`
- REU-aware memory model for Commodore 64 Ultimate:
  - 16MB far-data support
  - overlay loading model
- Dead-strip linker behavior to reduce final program footprint

## Build and Test Strategy

1. Start with host-based, headless tests.
2. Use `cpm65-u64/bin/cpmemu` for early execution and rapid iteration.
3. Validate true C64 behavior under **VICE**, since CP/M-65 C64-port verification needs full machine emulation.

## Workflow

Development follows a prompt chain (`prompt-1.txt` through `prompt-n.txt`) with deterministic, testable increments.

## Status

Bootstrap only. This repository currently contains structure, docs seeds, and smoke tests.
