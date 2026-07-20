# Idun Workspace Release

The Idun product is a native Linux workspace, not a CP/M or UDOS disk image.

Build and verify it with:

```sh
make all
```

The generated `build/idun-action/` tree contains:

- `TOOLS/`: native Linux executables for every converted command
- `SRC/`: executable examples
- `OBJ/`: compiler output directory
- `BIN/`: linked C64 PRG and debug-sidecar output directory
- `LIB/`: Action interfaces and link-selected native 6502 runtime objects
- `DOC/`: operator and runtime-availability notes

The export marker `.actionc64u-idun-export` prevents the exporter from
recursively replacing an unrelated external directory. Legacy placeholder
runtime objects and UDOS artifacts are not included.

The default exported executables are native to the build host. A larger Docker
host can produce and verify a static Alpine/AArch64 deployment bundle without
using the Pi or C64:

```sh
make verify-aarch64
```

That bundle is written to `build/idun-action-aarch64/`. A native build on the
Idun Pi remains supported when its SSH service is available.

Build the signed Alpine/AArch64 package repository from that verified export
with `make apk`. It emits `idun_action`, `idun_action_full`, both apk-tools 2
and apk-tools 3 signed repository indexes, and the public trust key under
`build/alpine-apk/repository/`. Packaging and Mint-hosted repository setup are
documented in `docs/alpine_packages.md`.
