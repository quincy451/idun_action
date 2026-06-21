# REU Backend ABI

ActionC64U keeps the REU-facing API stable across simulated and hardware
backends so the compiler and UDOS-native tools can switch implementations
without changing source-level semantics.

## Build Selection

Maintained UDOS-native build scripts select the backend with:

```text
ACTIONC64U_REU_BACKEND=sim
ACTIONC64U_REU_BACKEND=hw
```

Current defaults:

- `sim` for host-side harness tests that need deterministic sparse REU behavior
- `hw` for UDOS-native VICE / real C64 validation builds

The build scripts currently default to `-Oz` when `ACTIONC64U_REU_BACKEND=hw`
so the on-target tools keep fitting below the UDOS resident/tool memory floor.

## Stable C API

Declared in `src/runtime/reu_backend.h`:

- `reu_backend_reset()`
- `reu_backend_name()`
- `reu_alloc(size, &handle)`
- `reu_free(handle)`
- `reu_copy(dest_handle, dest_offset, src_handle, src_offset, length)`
- `reu_peek8(handle, offset, &value)`
- `reu_peek16(handle, offset, &value)`
- `reu_poke8(handle, offset, value)`
- `reu_poke16(handle, offset, value)`

## Simulated Backend

`src/runtime/reu_sim.c` is sparse and deterministic:

- allocations are handle-based
- unwritten bytes read back as zero
- only touched offsets consume local memory
- bounds checks are enforced on every access

This is the backend used by host-side tool ABI tests when hardware REU behavior
is not required.

## Hardware Backend

`src/runtime/reu_hw.c` now performs real C64 REU register transfers:

- REU registers at `$df00-$df0a`
- trigger at `$ff00`
- I/O visible while programming registers
- all-RAM memory configuration during the transfer trigger

Current implementation limits:

- `4` live handles
- monotonic bump allocation with simple tail-pop reclaim
- `reu_copy()` is currently implemented as repeated `peek8` / `poke8`
  operations to keep code size under control

This backend is now maintained through the UDOS-native toolchain builds, and the
repo test suite exercises those build paths.
