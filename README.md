# ActionC64U - Action! Commodore 64 Ultimate Edition

ActionC64U is a clean-room Action-style toolchain project for the Commodore 64.
This Linux/Idun product is published as
[`quincy451/idun_action`](https://github.com/quincy451/idun_action).

The active fork target is the Idun cartridge Linux environment. Development
tools run as normal Linux processes on the Raspberry Pi side of the cartridge.
Generated programs remain Commodore 64 `.PRG` files; `ALINK` still links C64
programs, not Linux executables.

UDOS is no longer part of the active runtime contract for this fork. Any service
that a generated Commodore program needs must be supplied by selective 6502
library modules linked into that program.

## Current Linux Tools

The converted tools live in `src/tools_linux/` and build into
`build/linux_tools/`:

- `actnew`: create an Action project tree
- `actadd`: add a tracked source module
- `actwork`: summarize project layout
- `actsrc`: list tracked source modules
- `actfile`: print a tracked source file without C64 buffer limits
- `actchk`: validate project directories and tracked source files
- `actdir`, `actcopy`, `actdel`, `actmkdir`, `actrmdir`, `actmove`,
  `actren`, `actwrite`, `actinfo`, `acttree`, `tree`, `xcopy`, `deltree`:
  Linux filesystem/utility commands
- `actmon`: Linux project/workflow monitor
- `actdbg`: Linux source debugger with sidecar lookup, persistent prepared
  breakpoints, and an Idun live console for registers, memory, run/halt,
  software breakpoints, stop events, and source locations
- `actprof`: imported or live PC-sampling profiler with process, function, and
  statement attribution stored in SQLite
- `actspc`: syntax-aware Action formatter for one file or any number of file
  specifications, including quoted wildcards such as `*.act`; formatting is
  atomic, idempotent, and uses four-space block indentation with canonical
  horizontal spacing
- `actsprite` / `actbitmap`: Linux pixel editors for hires and multicolor C64
  sprite/bitmap resource files. They provide interactive TUIs plus scriptable
  create, set, clear, print, and inspection commands
- `actedit`: Linux source editor command with line operations, an SQLite-backed
  project source/symbol index, and its own full-screen terminal editor. Plain
  invocation uses an uncolored display; explicit `tui` mode enables syntax
  highlighting. Both modes provide F1 contextual help, F2 editor-command help,
  an F3 complete language browser, an F4 library/feature/example browser, F5
  definition lookup, F6 source formatting, F7 references, F8 graphics-resource
  editing, history, and
  Ctrl-click navigation. Ctrl-B/C/X/V provide block mark/copy/cut/paste, Ctrl-A
  selects all, and mouse dragging selects text; external editors are never
  launched
- `acthelp`: exact, list, and full-text-style lookup over the external Action
  language/runtime SQLite catalog used by `actedit`
- `act2save` / `actsave`: compatibility command names that use the Linux linker
  path to write `.PRG` output
- `actc`: Linux compiler for the historical Action language surface used by
  the original manual and C64 libraries, including
  typed `BYTE`/`CARD`/`INT`/`REAL FUNC` declarations and returns,
  `PrintE("...")` string output, constant integer expressions,
  constant `PrintIE(...)` output, structured `IF` / `ELSEIF` / `ELSE` / `FI`,
  `DO` / `UNTIL` / `OD`, `WHILE`, `FOR`, and `EXIT` control flow,
  `BYTE`/`CHAR`/`CARD`/`INT`/`REAL` storage, records, arrays, pointers, address
  bindings, relocatable compiler constants, inline/fixed-address machine
  routines, assembler-backed `ASMBLOCK` sections, parameterized Idun
  `MAIN(CARD argc,CARD ARRAY argv)`, dynamic integer and REAL expressions,
  typed comparisons, and library calls. Calls on recursive cycles preserve
  live scalar, array, REAL, and expression-temporary frame bytes. REAL uses a
  full-domain IEEE-754 binary32 runtime with correctly rounded core arithmetic,
  square root, and exact decimal output. Documented target exceptions are no
  machine/external REAL ABI, historical compiler-memory `SET` directives having
  no effect, and resident rather than dynamically swapped overlays.
  Global `SPRITE`, `MSPRITE`, `BITMAP`, and `MBITMAP` `RESOURCE` declarations
  validate and embed external graphics assets while keeping packed pixels out
  of Action source.
- `alink`: Linux linker that resolves `OBJ1` machine-code records
  and their link-selected runtime closure, validates object/export/relocation
  bounds, then writes C64 `.PRG` plus `.DBG` and an atomic SQLite semantic map

The build also emits `actsvc`, a small UDOS-free Idun shell tool that relocates
to `$C000-$CFFF` and supplies the C64 hardware half shared by `actdbg` and
`actprof`.

The active UDOS-free library surface includes IEEE binary32 MATH1
transcendentals and GFX1 clipped pixels, shapes, bitmap resources, and staged
hardware sprites in addition to INPUT1 and SIDSPR1. Low-level modules use
KERNAL or C64 hardware directly and are selected only when referenced.

Cross-product parity is tracked in
[`docs/udos_feature_parity.md`](docs/udos_feature_parity.md). Shared Action
syntax, OBJ1 records, target library APIs, and generated-PRG results should
match. Linux filesystems, SQLite, sockets, terminal processes, AArch64 builds,
and APKs remain Idun implementations; UDOS services, REU overlays, and disk
images remain native implementations. The native compiler now implements the
shared 16-byte fixed register-entry ABI for ASMBLOCK and core raw-code bodies,
including decimal, hexadecimal, and binary call literals, raw character/signed/
sum constants, address relocations, and explicit signature rejection. Bounded
preprocessing and Idun-compatible checked signed 64-bit integer `CONST`
expressions before or after `MODULE` are also present. Numeric bodyless
absolute-address routine declarations and fixed register-entry machine bodies
now emit through native passes J/H; forward/backward local routine aliases accept checked signed 16-bit
constant expressions on either side of the symbol and emit normal named OBJ1
relocations. Native `REAL CONST` now folds decimal/radix literals, dependent
constants, arithmetic, `REAL`, `FABS`, `FSQRT`, infinity, and NaN with binary32
nearest-even semantics and no target arithmetic imports. Native pass K also
proves one finite two-REAL-parameter comparison/select function through OBJ1,
generic ALINK closure, and live VICE. Its bounded caller and callee storage
roles now follow captured names, and both canonical and permuted shared fixtures
compile, link, and execute in this fork. Native pass A also returns either named
parameter in its bounded two-REAL-parameter identity form; a shared reordered
second-return fixture writes 2.0 through both products. Native pass K now also
returns one selected binary expression over two REAL parameters through a
hidden non-aliasing result cell. The shared `RETURN(FHypot(A,B))` fixture
compiles and links in both products; native ALINK selects only its reachable
closure and the direct PRG writes binary32 5.0 in VICE. This remains a bounded
checkpoint rather than general native REAL lowering. Native pass L additionally
accepts two bounded REAL functions and one declaration-order edge; the shared
`MAIN -> CHAIN -> LENGTH` fixture returns binary32 5.0 under both toolchains,
and the later function may use `LENGTH(A,B)` directly inside `FMax`. Native
forward/cyclic edges are rejected. Native ACTC now lowers
`FSign`, `FTrunc`, `FFloor`, `FCeil`, `FRound`, `FFrac`, `FMod`, `FHypot`, `FMin`, and `FMax` for named REAL operands and a bounded,
storage-capturing `FClamp`
ternary root through synchronized, independently selected target modules with
complete MATH1
NaN/signed-zero/bound-order semantics. General native REAL expressions/functions, the rest of
MATH1, GFX1, resources, formatting, and help remain listed there explicitly.
The native MATH1 include now supplies all eight constants without target code.
Idun now lowers `FTrunc`, `FFloor`, `FCeil`, `FRound`, `FFrac`, `FMod`, and
`FHypot` to the same independently selected target objects. Linux ACTC retains
and validates every project routine, then prunes full-source MATH1/GFX1 library
routines to the transitive graph those project routines reference. Bare routine
addresses, `OverlayCall` targets, globals, and declaration-time address
expressions also keep their referenced library routines alive. Unused library
siblings no longer enter the application object.

Build them with:

```sh
bash tools/build_linux_tools.sh
```

Install the exported Linux commands for the current user so `actc`, `actedit`,
`actspc`, and `alink` work without a `./TOOLS/` prefix:

```sh
make install-user
hash -r
```

The installer uses `$HOME/.local/bin` and does not require root. Commands first
look for `<module>.ACT` in the invocation directory. In that flat mode, ACTC
writes `<module>.OBJ` there and ALINK writes `<module>.PRG` plus `<module>.DBG`
there. If no local module exists, the nearest `ACTION.PROJ` supplies the
traditional `SRC/`, `OBJ/`, and `BIN/` layout. `ACTION_PROJECT=/path/to/project`
can select a project while invoking the commands elsewhere.

Format one source or a wildcard set in place with:

```sh
actspc hello.act
actspc '*.act'
actspc 'SRC/*.act' 'LIB/*.act'
```

The quotes are optional when the shell expands the wildcard. Keeping them lets
ACTSPC perform deterministic matching itself, including uppercase `.ACT`
extensions. It validates every filespec before replacing any file, preserves
file permissions and strings/comment text, and reports each changed or already
canonical source.

Or build, test, and export the complete Idun workspace in one command:

```sh
make all
```

On a Pi Zero 2 W with Alpine's `clang20` package installed, the build script
automatically uses `clang++-20`; it does not create or manage swap. The verified
Pi had its existing 2 GiB swapfile active by the final system check. On a larger
Docker host, `make build-aarch64` additionally produces a static Alpine/aarch64
binary. `make verify-aarch64` packages and verifies the complete Pi-ready
workspace under `build/idun-action-aarch64/`.

The Mint host can turn that verified static export into a signed Alpine 3.24
AArch64 repository containing `idun_action` and `idun_action_full`:

```sh
make apk
```

Packages, signed indexes, and the client public key are written under
`build/alpine-apk/repository/`; the private signing key remains outside the web
root under `.apk-keys/`. See [docs/alpine_packages.md](docs/alpine_packages.md)
for package contents, key handling, Idun installation, and the stopped/disabled
Mint lighttpd service.

The build requires a C++17 compiler, `pkg-config`, the SQLite 3 development
package, and ACME for `actsvc`. SQLite is used only by Linux tools; it is never
linked into generated C64 programs. The authored help metadata in `resources/action_help.json` is
validated against compiler builtins and `lib/*.act`, then emitted as
`action-help.sqlite3` beside development tools and under the exported `DOC/`
directory.

## Linux-Only Verification

Run the maintained Linux product suite:

```sh
make test
```

The Makefile's `ACTIVE_TESTS` list is the authoritative hardware-free gate.
Do not substitute an unrestricted `python3 -m unittest discover`: this fork
preserves native UDOS test modules for provenance and compatibility work, but
those modules build the other product's 6502 overlays and are not Idun Linux
tests.

For a narrower compiler or export iteration, run:

```sh
python3 -m unittest -v tests.test_linux_workspace_tools
python3 -m unittest -v tests.test_idun_workspace_export
```

These tests do not build UDOS, do not run UDOS, and do not use VICE.

When `x64sc` is available, run the direct generated-PRG gate as well:

```sh
python3 -m unittest -v tests.test_idun_prg_runtime
```

This headless VICE test needs no attached C64. It executes recursive word,
local-array, and REAL call frames in the emitted C64 program.

## Export An Idun Workspace

Build a Linux-side Action workspace for the Idun cartridge:

```sh
python3 tools/export_idun_workspace.py
```

Default output:

- `build/idun-action/`

The export contains Linux tools under `TOOLS/`, Action source under `SRC/`,
object output under `OBJ/`, generated Commodore programs under `BIN/`, and
linkable 6502 modules under `LIB/`. `PLAYGROUND/` contains flat copies of every
example for current-directory compilation, and `install-user.sh` exposes the
Linux commands through the user PATH. `DOC/action-help.sqlite3` supplies external
editor and command-line help without consuming C64 memory. The export includes
only the currently executable compiler examples, source interfaces, and
runtime objects. Legacy ASCII-payload stubs are omitted and listed in
`DOC/runtime-status.txt`.

The expanded examples include `PRIME_REAL.ACT`, which uses REAL conversion and
square root to find primes, `REU_DBF_SORT.ACT`, a stable one-to-ten-key DBF
sorter, and `ASMBLOCK_DEMO.ACT`, which mixes Action storage with scoped 6502
assembly. The sorter accepts command-line `START,LENGTH,A|D` specifications
such as `10,20,A` and `40,10,D`; DBF1 stages the file in REU and the sample uses
an additional 255-byte REU record-swap buffer.

## Post-Port Feature Work

The Linux process conversion inventory is complete. Historical 6502/UDOS
sources remain in Git for provenance, are formally retired, and are not built.
Remaining Idun work includes one required library-packaging correction plus
optional runtime expansion and physical validation:

- prune unreachable routines from full-source library includes, or generate
  dependency-sized library objects, so `INCLUDE "MATH1"` does not embed all
  remaining unused function bodies in the application object; `FTrunc`,
  `FFloor`, `FCeil`, `FRound`, `FFrac`, `FMod`, and `FHypot` are the first seven routines moved to
  independently selected shared OBJs
- add new REAL library functions only when a separate post-MATH1 API is specified
- extend the direct REU surface beyond 16-bit-sized arrays and 8/16-bit
  peek/poke
- add optional dynamic load/unload placement for resident program-owned
  overlay sections
- validate the VICE-proven standalone DBF/REU/KERNAL runtime on physical C64
  and REU hardware
- validate the new `actsvc` socket transport, IRQ halt path, breakpoints, and
  sampling on attached Idun/C64 hardware
- validate the implemented instruction-step and persistent-breakpoint
  reinstallation path on physical Idun/C64 hardware

Historical UDOS documents and scripts should not drive new feature work for this
fork.

## Documentation Map

The authoritative/current versus historical/native split is indexed in
[docs/README.md](docs/README.md). Key current docs:

- [docs/udos_feature_parity.md](docs/udos_feature_parity.md)
- [docs/idun_linux_process_split.md](docs/idun_linux_process_split.md)
- [docs/linux_tool_port_status.md](docs/linux_tool_port_status.md)
- [docs/idun_fork_handoff.md](docs/idun_fork_handoff.md)
- [docs/active_direction.md](docs/active_direction.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/linker.md](docs/linker.md)
- [docs/source_debugger_roadmap.md](docs/source_debugger_roadmap.md)
- [docs/idun_target_service.md](docs/idun_target_service.md)
- [docs/retired_udos_tools.md](docs/retired_udos_tools.md)
- [docs/setup_linux.md](docs/setup_linux.md)
- [docs/alpine_packages.md](docs/alpine_packages.md)
- [docs/new_math_func.txt](docs/new_math_func.txt)
- [docs/new_gfx_func.txt](docs/new_gfx_func.txt)
