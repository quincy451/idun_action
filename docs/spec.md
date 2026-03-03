# Language and System Spec (Very Early Draft)

## Language Direction

- Action-like syntax and ergonomics.
- Structured programming first.
- Clean-room implementation.

## Numeric Types

- Integer primitives (details TBD).
- `REAL32`: 1 sign, 8 exponent, 24 mantissa.

## Memory Model

- Conventional near memory plus REU-backed far data.
- Overlay loading support for larger programs.

## Backend

- AcheronVM target with project-specific extensions where justified.
