# `actc.com`

`actc.com` is the first on-target ActionC64U compiler for CP/M-65.

## Prompt 13 Scope

The current shipped subset is intentionally tiny:

- optional `MODULE <name>` header
- `PROC main()`
- `Print("literal")`
- `PrintE("literal")`
- `RETURN`

The compiler emits a runnable `.avm` file directly. There is no on-target
`.avo` linker yet.

## File Behavior

- input: first filename argument, default `main.act`
- output: `<stem>.avm`
- filenames should stay lowercase 8.3 when running under `cpmemu`

`actc.com` reads the source through CP/M BDOS sequential file calls and writes a
monolithic `AVM1` file that `vm.com` can execute.

## `vm.com`

The CP/M runner currently validates the `AVM1` header and interprets the small
opcode subset used by the bootstrap compiler:

- `setp16`
- `calln 0xff00` (`Print`)
- `calln 0xff10` (`PrintE`)
- `calln 0xff20` (`Exit`)

## Limitations

- only one procedure: `main`
- only string literal printing
- no variables, integer expressions, or control flow yet
- output files are written in 128-byte CP/M records; `vm.com` relies on the
  `AVM1` payload length instead of host file length

## Planned Expansion

Next steps are:

- integer locals and compile-time expression evaluation
- `IF ... FI`
- parity tests against the host reference compiler
- eventually moving more of the host object/link pipeline on target
