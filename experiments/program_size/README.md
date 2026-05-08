# AVM Vs Native 6502 Program Size Probes

This directory measures **user-program shape**, not compiler/linker implementation size.

The question under test is:

- does AVM save space for shipped user programs?
- if it does, is that only because it leans on shared runtime services?
- when AVM does not get that shared-service advantage, is it still competitive enough to keep?

## Method

There are now two measurement tracks.

### 1. Raw Representation Probes

Each benchmark is hand-written twice:

- direct AVM from the AVM spec using `avm_pack.py --text`
- direct 6502 using `ca65`/`ld65`

This tells us what the raw code representation looks like.

Important boundary:

- some of these AVM probes intentionally lean on shared runtime services like print and file I/O
- those rows are valid for “platform with shared runtime” questions
- they are **not** sufficient by themselves for the stronger “remove AVM entirely?” question

### 2. Fair No-Shared-Runtime Compiled Probe

One additional benchmark is now measured through the real toolchain:

- Action source -> `ACTC_HARNESS.PRG` -> `.AVO`
- `ALINK.PRG` -> `MAIN.AVM`
- `AVMRUNC.PRG` under `tool_abi_harness`

The paired native 6502 version is hand-written to do the same work.

This benchmark is deliberately chosen to avoid the “AVM looks smaller only because it called common code” problem:

- no print
- no file I/O
- no helper-family trailer imports
- no runtime module linkage
- only local state update and local control flow

## Speed Metric

Speed is measured as exact emulator **step count** from `tool_abi_harness`, not wall-clock time.

That means we do **not** need an artificial outer timing loop just to make the difference measurable. The harness already gives a stable execution-count metric.

## Current Runner Size

- `AVMRUN.PRG`: `8616` bytes

## Raw Representation Results

| benchmark | description | shared runtime leverage | native raw | native prg | avm payload | avm packed | delta payload vs prg | delta packed vs prg | break-even vs `AVMRUN.PRG` |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `hello` | literal string print | `print` | `25` | `27` | `15` | `25` | `-12` | `-2` | `4308` programs |
| `sum100_only` | pure loop/arithmetic: sum `1..100`, no output | `none` | `44` | `46` | `40` | `50` | `-6` | `+4` | none |
| `sum100` | sum `1..100` plus decimal integer print | `print` | `152` | `154` | `44` | `54` | `-110` | `-100` | `87` programs |
| `filecopy` | open source file, copy bytes to output file, close | `fileio` | `114` | `116` | `77` | `87` | `-39` | `-29` | `298` programs |
| `count_digits` | open input file, count ASCII digit bytes, print total | `fileio+print` | `196` | `198` | `86` | `96` | `-112` | `-102` | `85` programs |

Interpretation:

- AVM payload is smaller in all five raw probes.
- Packed `.AVM` size is smaller in four of five probes.
- The one packed loss is the pure arithmetic/control-flow case: `sum100_only`.
- AVM wins the most when the program leans on shared runtime services.

That supports keeping AVM as a **shared-runtime code-size layer**.

It does **not** prove AVM is a general size win for arbitrary compiled code.

## Fair No-Shared-Runtime Compiled Result

Benchmark files:

- Action source: [local_call74.act](/mnt/c/test/action/actionc64u/experiments/program_size/local_call74.act)
- Native 6502 source: [asm_local_call74.asm](/mnt/c/test/action/actionc64u/experiments/program_size/asm_local_call74.asm)

Workload:

- one local routine increments `INT X`
- `MAIN` calls it `74` times
- program returns
- no output
- no file services

Results:

| benchmark | shared runtime leverage | native raw | native prg | compiled avo | linked avm | delta avo vs prg | delta avm vs prg | native steps | avm steps | avm/native step ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `local_call74` | `none` | `236` | `238` | `212` | `250` | `-26` | `+12` | `300` | `38463` | `128.21x` |

Important nuance:

- the compiled object text (`.AVO`) is smaller than the native `.prg`
- the final shipped linked AVM image is **larger** than the native `.prg`
- runtime speed is much worse for AVM on this no-shared-runtime workload

So for this fair compiled case:

- AVM did **not** save shipped program bytes
- AVM was about `128x` slower by harness step count

## Large-Scale No-Shared-Runtime Size Probe

To answer the “maybe AVM only starts helping at 30k or 40k of code” question, there is now a second experiment family:

- direct native 6502
- direct executable AVM
- no print
- no file I/O
- no helper-family trailer imports
- no shared runtime services beyond the VM itself

Workload shape:

- one trivial local subroutine that immediately returns
- main body is just a very long chain of local calls

This is intentionally simple. It isolates representation size instead of smuggling in shared-service wins.

### Results

| benchmark | native raw | native prg | direct avm | delta avm vs prg | native steps | avm steps to harness boundary | avm note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `bigcall_nodata_30k` | `30002` | `30004` | `30014` | `+10` | `20001` | `782241` | `HARNESS NO ACHERON` |
| `bigcall_nodata_40k` | `39986` | `39988` | `39998` | `+10` | `26657` | `1041903` | `HARNESS NO ACHERON` |

Interpretation:

- even at roughly `30 KB` and `40 KB`, AVM still does **not** become smaller on this fair no-shared-runtime workload
- the final AVM artifact stays slightly larger than native
- the expected “larger codebase compression crossover” did **not** appear here

Important boundary:

- the AVM side reaches the Acheron fast-path boundary, so `tool_abi_harness` stops with `HARNESS NO ACHERON`
- that means the AVM step count here is **not** full end-to-end runtime
- it is a lower bound on runner work **before** payload execution under the current harness

That lower bound is already large:

- `782241` steps before payload execution for the `30 KB` case
- `1041903` steps before payload execution for the `40 KB` case

So even before the actual user payload runs, the AVM side has already spent far more steps than the native side needs to finish the whole benchmark.

## What This Says Now

The current evidence supports a narrower position than “AVM everywhere” or “remove AVM entirely”.

### Supported

- keep AVM when the platform wants shared runtime services and many programs share one runner
- AVM can still reduce per-program artifact size when the program heavily uses print/file/runtime facilities

### Not Supported

- port compiler/linker internals to AVM just to save memory
- assume AVM is a size win for pure local compiled code
- assume AVM becomes a size win automatically just because the code sample gets large
- assume AVM is worth the speed hit when it is not buying real code-size compression

## Current Practical Read

If the workload is mostly:

- print
- file I/O
- other shared runtime services

then AVM still has a size case.

If the workload is mostly:

- local arithmetic
- local control flow
- local procedure calls

then the current evidence points the other way:

- native 6502 is smaller or similar
- native 6502 is much faster

## Reproduce

Run:

```bash
python3 /mnt/c/test/action/actionc64u/experiments/program_size/measure_sizes.py
```

That prints:

- the raw representation table
- the fair no-shared-runtime compiled benchmark table
