# ActionC64U Operator Guide

This guide covers the current VM-first runtime surface in the repo.

## What You Have

- `tools/avm_pack.py`: assembles `.avm.txt` source into `AVM1` files
- `build/vm.com`: CP/M-65 runner for `AVM1` payloads
- `src/runtime/reu_sim.c`: sparse simulated REU backend for `cpmemu`
- `src/runtime/reu_hw.c`: real C64 REU backend for VICE / hardware builds

The current practical workflow is:

1. assemble an AVM program on the host
2. run it under `vm.com`
3. use `cpmemu` for fast tests or `ACTIONC64U_REU_BACKEND=hw` builds for
   VICE / C64 validation

## Build `vm.com`

Default simulated backend:

```bash
./tools/build_vmrun.sh
```

Hardware REU backend:

```bash
ACTIONC64U_REU_BACKEND=hw ./tools/build_vmrun.sh
```

The build scripts automatically switch to `-Oz` for the hardware backend to
keep the tools inside the CP/M memory budget.

## Assemble an AVM Program

Examples:

```bash
python3 tools/avm_pack.py examples/reu_runtime.avm.txt --text --output examples/reurun.avm
python3 tools/avm_pack.py examples/vmecho.avm.txt --text --output examples/vmecho.avm
```

## Run Under `cpmemu`

Batch example:

```bash
python3 tools/cpmemu_runner.py \
  --cwd /mnt/c/test/action/actionc64u/examples \
  /mnt/c/test/action/actionc64u/build/vm.com \
  reurun.avm
```

Expected output:

```text
65
```

Interactive example:

```bash
python3 tools/cpmemu_runner.py \
  --stdin-text $'abc\r' \
  --cwd /mnt/c/test/action/actionc64u/examples \
  /mnt/c/test/action/actionc64u/build/vm.com \
  vmecho.avm
```

Expected output contains:

```text
type> stored:abc
```

## Current Example Programs

- `examples/hello.avm.txt`: minimal VM smoke payload
- `examples/reu_runtime.avm.txt`: runtime REU allocate/poke/peek/free flow
- `examples/vmecho.avm.txt`: console input stored in REU and replayed

## Testing

Focused VM runtime tests:

```bash
python3 -m unittest -q tests.test_vmrun_reu_runtime
```

Full suite:

```bash
python3 -m pytest -q
```

## What This Is Not Yet

- not a VM-based on-target ACTION! compiler
- not a VM-based editor
- not a debugger
- not a full original ACTION! development environment

Those remain later phases. The current runtime is the foundation for them.
