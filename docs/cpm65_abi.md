# CP/M-65 ABI Notes (Bootstrap)

These notes are inferred from the adjacent `../cpm65-u64` sources, especially:

- `cpmfs/hello.asm`
- `apps/cpuinfo.asm`
- `src/arch/nano6502/utils/colorfg.S`
- `apps/cpm65.inc`

## Minimal Console Output Pattern

For the CP/M-65 `BDOS` string-write call:

- `A` = low byte of the string pointer
- `X` = high byte of the string pointer
- `Y` = BDOS function number `9`
- string data is NUL-terminated

In the native CP/M-65 assembler, the `BDOS` entry is reached via `start - 3`:

```asm
start:
    lda #<message
    ldx #>message
    ldy #9
    jsr start - 3
    rts
```

In the llvm-mos-flavored assembly used elsewhere in `cpm65-u64`, the same call
appears as `jsr BDOS` with `Y` loaded from `BDOS_WRITE_STRING`.

## Return to CP/M

For a tiny `.com` program, `rts` returns control to the CP/M command processor.
That is the exit path used by the adjacent `cpmfs/hello.asm` sample.

## Practical Implications for ActionC64U

- Use NUL-terminated strings for the first smoke tests.
- Keep filenames all-lowercase 8.3 when running under `cpmemu`.
- Treat the native `asm.com` flow as the preferred long-term bootstrap path.
- For now, host-side llvm-mos builds are an acceptable fallback when `cpmemu`
  and `asm.com` are not both available.
