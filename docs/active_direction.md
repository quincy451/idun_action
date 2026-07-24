# Active Project Direction

This fork targets the Idun cartridge Linux environment.

The active product path is:

- Linux processes for build-time and workspace tools on the Idun Raspberry Pi
- direct linked Commodore 64 `.PRG` output as the maintained runtime artifact
- link-selected 6502 helper modules for services required by generated programs
- no UDOS dependency in the active toolchain or generated-program contract

`ALINK` remains a C64 program linker: it will run on Linux, but it emits C64
`.PRG` files and debug sidecars, not Linux executables.

## Active Code Paths

- `src/tools_linux/`
- `src/target_idun/` for the small UDOS-free C64 debug/profile agent
- `tools/build_linux_tools.sh`
- `tools/export_idun_workspace.py`
- `tests/test_linux_workspace_tools.py`
- `tests/test_idun_workspace_export.py`
- `src/runtime/modules/` for linkable 6502 runtime modules

The native ActionC64U repository owns the common contents of
`src/runtime/modules/`. This fork pins the same digests in
`resources/shared_6502_manifest.json`; `make sync-native` imports an intentional
native update and `make sync-native-check` proves both checkouts agree. The DBF
create and file-open-write adapters are the only OS-specific exclusions.

Historical UDOS sources are preserved but formally retired. The complete
retirement boundary and replacement inventory are documented in
`docs/retired_udos_tools.md` and `resources/retired_udos_tools.json`.

## Active Verification

Use Linux-only gates for the current fork work:

```sh
make all
make test-sanitize
make test-prg
make check
```

Do not use UDOS builds, UDOS VICE probes, or sibling `../udos` make targets as
proof for this fork's active Linux process tools.

## Development Rules

- Prefer `src/tools_linux` for converted tools.
- Prefer `std::string`, `std::vector`, and filesystem abstractions over fixed
  6502-style buffers.
- Do not add new dependencies on `udos_services.inc`, `UDOSDIR.TXT`, or UDOS
  resident labels in Linux tools.
- Do not build or test UDOS while working on the Linux process conversions.
- Keep generated `.PRG` output as Commodore 64 code.
- Move any service needed at C64 runtime into a selective 6502 library module
  linked by `ALINK`.

## Current State

Converted workspace tools:

- `actnew`
- `actadd`
- `actwork`
- `actsrc`
- `actfile`
- `actchk`
- `actdir`, `actcopy`, `actdel`, `actmkdir`, `actrmdir`, `actmove`,
  `actren`, `actwrite`, `actinfo`, `acttree`, `tree`, `xcopy`, `deltree`,
  `actspc`
- `actmon` Linux project/workflow monitor
- `actdbg` Linux `.PRG`/`.DBG` source/address and symbol inspector with
  SQLite-persisted prepared breakpoints and an Idun live console for registers,
  memory, run/halt, software breakpoints, events, and source lookup
- `actprof` Linux source-level PC-sampling profiler with imported and live
  collection modes and `.action/profile.sqlite3` persistence
- `actsprite` and `actbitmap` Linux resource editors with atomic ASP1/ABM1
  storage, scriptable operations, and interactive hires/multicolor TUIs
- `acthelp` external SQLite language, library, builtin, constant, and example
  reference; the validated catalog currently contains 260 topics
- `actedit` Linux source editor command with an SQLite-backed source and symbol
  index, linked semantic map, F5 definitions, F6 formatting, F7 references,
  an internal block clipboard, navigation history, and Ctrl-click definition
  lookup
- `act2save` / `actsave` compatibility names backed by the Linux linker path
- `actc` for native procedure/call object emission and
  `PrintE("...")` / constant `PrintIE(...)` direct output, including
  structured IF/ELSE and loop lowering, initialized/address-bound
  `BYTE`/`CARD` storage, variable `PrintI(...)` / `PrintIE(...)`, recursive word
  arithmetic, arbitrary unsigned word comparisons, BYTE/CARD/INT/REAL arrays,
  typed pointers and indirect parameters, length-prefixed BYTE strings,
  reentrant local-routine frames, and typed BYTE/CARD/INT/REAL user-function
  returns; full IEEE-754 binary32 behavior; `ASMBLOCK`; external graphics
  resources; and builtin argument staging for the complete `GFX1`, `INPUT1`,
  `SIDSPR1`, and `DBF1` callable families
- `alink` for `OBJ1` machine-code records, dependency closure,
  shared/project runtime libraries, object validation, and direct C64 `.PRG`
  output; every successful link atomically rebuilds
  `.action/code-map.sqlite3`
- the Idun export excludes legacy runtime objects whose payload is only their
  helper name; `DOC/runtime-status.txt` records these unavailable surfaces

Remaining product work:

1. Validate the `actsvc` transport, implemented instruction-step primitive,
   persistent breakpoint reinstallation, and PC sampling on attached Idun/C64
   hardware.
2. Validate standalone REU/DBF/KERNAL I/O, graphics, SID, sprite, joystick, and
   mouse behavior on physical C64 hardware. Legacy placeholders are not
   exported.
3. Keep shared Action source, OBJ1 records, link-selected 6502 runtime behavior,
   and direct-PRG results compatible with the UDOS-native product while using
   OS-appropriate implementations for editors, help, project tools, debugging,
   profiling, and packaging. The current comparison and native work order are
   recorded in `docs/udos_feature_parity.md`. The fixed register-entry ABI is
   now shared for native ASMBLOCK and core raw-code bodies, including all three
   integer literal radices and explicit signature limits. Native preprocessing
   now includes bounded directives, Idun-compatible checked signed 64-bit
   integer `CONST` expressions, and bodyless numeric or grouped local-symbol
   routine-address expressions with checked signed addends on either side. It
   also folds bounded `REAL CONST` expressions with exact decimal conversion
   and binary32 round-to-nearest, ties-to-even after every operation.
   Native named-REAL `FSign`, `FTrunc`, `FFloor`, `FCeil`, `FRound`, `FFrac`, `FMod`, `FHypot`, `FPow`, `FExp`, `FLn`, `FLog2`, `FLog10`, `FSin`, `FCos`, `FTan`, `FATan`, `FATan2`, `FASin`, `FMin`, and `FMax` calls plus its bounded
   storage-capturing `FClamp` ternary root now use synchronized, independently
   selected target helpers with complete portable call semantics. The root can
   permute initializer, argument, destination, and print slots but remains a
   fixed statement skeleton rather than general REAL lowering.
   Pass K's bounded finite two-parameter function also captures module,
   parameter-bind, comparison, and return storage roles. Canonical and permuted
   fixtures execute identically with native and Linux ACTC/ALINK.
   Pass A's bounded identity form now captures its named return independently
   and can return either REAL parameter; the reordered shared fixture executes
   identically in both products.
   Native pass K now also returns one selected binary operation over two REAL
   parameters through a hidden result cell. The shared FHypot fixture compiles
   and links in both products and produces binary32 5.0. Native pass L now
   consumes the recursive child-first postfix stream for bounded nested unary,
   binary, and `FClamp` trees. It also supports up to two nonrecursive
   two-REAL-parameter functions, each with bounded all-REAL static locals and
   DBG1 local records. `MAIN` may call either function, and either function may
   call the other while the graph remains acyclic. Native ACTC stack-preserves
   caller parameters, locals, and live temporaries across those edges. The
   shared backward call-chain and nested local-call-expression fixtures produce
   binary32 5.0; the nested user-call-argument and forward-call fixtures produce
   3.0 under both toolchains. Native pass M now lowers one nonnested
   `IF`/`ELSE` per supported REAL function through `rt_f_cmp` and relocatable
   internal code labels; the shared fixture executes both arms and prints `34`
   under both toolchains. Native pass N accepts a second conditional,
   sequentially or nested to depth two; shared fixtures print `43` and `143`
   under both toolchains. Native pass O accepts a third and fourth control or
   nesting to depth four; shared fixtures print `43` and `154`. Native pass P
   accepts immediate returns inside those bounded controls when a terminal
   fallback return is present; shared fixtures print `33` and `154`. Passes Q
   through T add bounded pre/post-test and plain loops, nearest-loop `EXIT`, and
   CARD-counter `FOR` loops with constant or named bounds. Pass U accepts folded
   binary32 literals and one- or two-REAL-parameter functions together with up
   to four pass-P conditional/early-return controls. The shared
   `DegToRad`/`RadToDeg` fixture compiles and links in both products, and the
   shared comma-local clamp fixture produces `-1`, `0`, and `1` in both
   generated 6502 programs. General or
   recursive call graphs, recursive/reentrant local frames, mixed controls,
   unrestricted user-call argument trees and nested call expressions, mixed
   types, arbitrary signatures, and recursive frames remain pending.
   Linux ACTC now lowers `FTrunc`, `FFloor`, `FCeil`, `FRound`, `FFrac`, `FMod`,
   `FHypot`, `FPow`, `FExp`, `FLn`, `FLog2`, `FLog10`, `FSin`, `FCos`, `FTan`, `FATan`, `FATan2`, `FASin`, `FMin`, and `FMax` to the same shared objects instead of embedding
   those MATH1 bodies. It retains all project routines and prunes unreachable MATH1/GFX1
   library bodies from their transitive project-rooted call graph while
   preserving bare routine-address and `OverlayCall` references. Linked
   external symbol expressions inside unchecked
   raw `[...]` bodies, general REAL/function behavior, full MATH1/GFX1,
   resources, and workflow parity remain explicit native work rather than Idun
   regressions. The OS-aware delivery ledger and acceptance gates are maintained
   in `docs/udos_feature_parity.md`.
