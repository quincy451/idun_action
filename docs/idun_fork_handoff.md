# Idun Fork Handoff

Status as of 2026-07-21: the active ActionC64U fork is a self-contained Linux
toolchain for the Idun cartridge. Linux processes manage projects, edit and
index source, provide external SQLite language help, compile Action source,
link selected 6502 runtime modules, inspect debug sidecars, and emit native
Commodore 64 `.PRG` files.

The active build, test, export, and VICE paths have no CP/M-65 or UDOS runtime
dependency. Historical sources remain in Git only as provenance and are not
part of the active command inventory.

This checkout is the Linux/Idun product repository at
`https://github.com/quincy451/idun_action`, not a working branch of the native
GitHub remote. Its `origin` points to `idun_action`; the native ActionC64U
repository is retained as the `native` remote. Shared target 6502 modules are
synchronized from the native checkout with `make sync-native`; Linux tools,
target transport, packaging, and the two OS-specific DBF adapters remain owned
here.

## Reproducible Builds

Native host build, test, and workspace export:

```sh
make all
```

Static Alpine/aarch64 build on a larger Docker host:

```sh
make build-aarch64
```

The cross-build output is:

```text
build/linux_tools-aarch64/action-workspace-tools
```

Package and verify the complete deployable AArch64 workspace with
`make verify-aarch64`; it writes `build/idun-action-aarch64/`.

On a Pi with less than 512 MiB RAM, the native build automatically selects an
installed versioned Clang executable. The current Pi Zero 2 W build completes
the expanded source in roughly four minutes. A final system check showed the
Pi's existing 2 GiB `/swapfile` active with about 29 MiB used; this work did
not create it.
GCC remains an intentionally slow fallback. Compiler temporaries stay off the
RAM-backed `/tmp`, and executable replacement is atomic.

## Verified Results

- 153 active Linux/tool/target tests pass on the local x86-64 host. The prior
  150-test baseline also passes natively on the Alpine/aarch64 Idun Pi; rerun
  the new shared finite-REAL fixture there at the next source deployment.
- 138 hardware-free tests also pass under AddressSanitizer and
  UndefinedBehaviorSanitizer.
- 21 direct-PRG tests pass in local VICE with the documented VICE 3.7 long-DBF
  skip. The prior 20-test set passes on the Idun Pi; deploy and run the new
  finite-REAL fixture there with the next source refresh.
- Every one of the 31 exported command names dispatches through the native
  multicall executable.
- A forced native compile from synchronized source completed on the Pi in
  roughly four minutes with `clang++-20`. The current static
  Alpine/AArch64 cross-build also completes locally.
- The current static Alpine/AArch64 workspace verifies all 31 commands and 260
  help topics. The signed repository rebuild installs both `idun_action` and
  `idun_action_full` in a clean Alpine container and passes its workspace
  helper smoke test.
- `actedit` always uses its built-in full-screen editor on a terminal and never
  launches `$EDITOR`. Plain invocation is uncolored for C64-display
  compatibility; explicit `tui` mode adds Action syntax colors. Both have an
  inverse-video blinking-block cursor, atomic save, guarded quit, F1 contextual
  help, an F2 keyboard/mouse command screen, an F3 language browser, and an F4
  library/feature/example browser. F5 opens a definition, F6 formats the
  unsaved buffer, and F7 selects a reference. Its internal block editor supports
  keyboard/mouse selection, copy, cut, and paste. PTY integration tests exercise
  both presentations, cursor control, and actual F1-F7 escape sequences.
- `actspc` atomically and idempotently applies the same syntax-aware indentation
  and spacing engine to one source or a deterministic wildcard set. It validates
  all files before replacement, preserves permissions and string/comment text,
  and matches uppercase `.ACT` files from quoted `*.act` specifications.
- The export's installer exposes all 31 Linux commands through
  `$HOME/.local/bin`. Current-directory `.ACT`/`.OBJ` files take precedence and
  keep `.OBJ`/`.PRG`/`.DBG` outputs beside the source; otherwise the nearest
  `ACTION.PROJ` supplies the structured `SRC/OBJ/BIN` layout. The exported
  `PLAYGROUND/` provides every shipped example in flat form.
- `PRIME_REAL.ACT` finds primes with REAL square-root bounds and is executed in
  VICE; `REU_DBF_SORT.ACT` is a stable one-to-ten-key command-line DBF sorter
  using DBF1's staged REU image plus an REU record-swap buffer;
  `ASMBLOCK_DEMO.ACT` demonstrates scoped 6502 assembly and labels.
- Idun programs may declare `PROC MAIN(CARD argc,CARD ARRAY argv)` to receive
  the executable name and zero-terminated command-line strings. ACTDBG's live
  `args` command and startup `--` separator publish the same ABI before upload.
- `ASMBLOCK [ ... ]` accepts legal NMOS 6502 instructions, block-local labels,
  branches and jumps, CPU registers, fixed memory, and relocatable references
  to Action globals, locals, routine parameters, and declared routines.
- The native UDOS compiler now shares Idun's fixed register-entry ABI through
  native pass J for
  ASMBLOCK and core raw-code `=*(...)` routines: up to 16 flattened BYTE/CARD/INT bytes use
  A, X, Y, then `$A3+`, with BYTE returns in A and word returns in A/X. The
  focused native ACTC/ALINK/VICE case passes all eight result bytes, including
  hexadecimal and binary call arguments. Native selection and rejection tests
  prevent unsupported signatures from falling back to an older emitter. Raw
  character/signed/sum constants and storage/local-routine/current-address
  relocations have focused native OBJ and live VICE coverage. Native UDOS ACTC
  now also has bounded token-aware `DEFINE`, compatibility `SET`, recursive
  project `SRC`/`LIB` `INCLUDE`, and storage-free typed BYTE/CHAR/CARD/INT
  constants using Idun-compatible checked signed 64-bit expressions before or
  after `MODULE`. Directive-free native sources keep their original streamed
  REU layout and long-line behavior. Bodyless numeric absolute-address
  procedure/function declarations now emit direct JSR calls through native
  passes J/H and have exact OBJ, ALINK-closure, and live-VICE coverage. Forward
  and backward local routine aliases now accept checked signed 16-bit constant
  expressions on either side of the symbol and emit ordinary named OBJ1
  relocations. The Linux parser and native pass I have matching grouped-address
  regressions. Native `REAL CONST` now folds decimal and exponent forms,
  radix-prefixed integers, prior constants, arithmetic and grouping, `REAL`,
  `FABS`, `FSQRT`, infinity, and NaN at binary32 precision. Exact decimal
  conversion and every operation use round-to-nearest, ties-to-even. A native
  direct-PRG proof emits `7.5`, selects only the print helper, and passes in
  VICE. The broader native type/REAL/library backlog remains tracked in
  `docs/udos_feature_parity.md`.
  Native preprocessing is isolated in base-36 pass `I`; pass 1 remains the
  streamed module-header validator. Pass I retains its full 512-byte reserve by
  invoking the resident evaluator through overlay ABI v5.
- `REAL` now uses full-domain IEEE-754 binary32 helpers for signed arithmetic,
  gradual underflow, infinities, NaNs, ordered comparison, integer conversion,
  correctly rounded square root, exact sign/minimum/maximum/clamp selection, and exact
  decimal output. ACTC recognizes `INF`/`INFINITY` and `NAN` and folds every
  operation at binary32 precision. The synchronized `RT_F_MIN.OBJ` and
  `RT_F_MAX.OBJ` helpers preserve MATH1's one-NaN, two-NaN, equal-value, and
  signed-zero selection policy for native direct-link consumers. The
  dependency-free `RT_F_SIGN.OBJ` canonicalizes NaN, preserves signed zero, and
  returns signed one without selecting sibling math helpers.
  `RT_F_CLAMP.OBJ` validates all three operands and bound order, then selects
  only comparison, minimum, and maximum through ordinary ALINK closure.
- MATH1 supplies the completed portable utility, exponential/logarithmic,
  trigonometric, inverse, hyperbolic, and conversion families. GFX1 supplies
  tracked VIC setup, pixels, shapes, bitmap-resource operations, and staged
  sprite-resource operations. `actsprite`, `actbitmap`, and ACTEDIT F8 manage
  ASP1/ABM1 resources without placing pixel arrays in Action source.
- The shipped MATH1 interface has 43 public routines and 8 constants, matching
  its 51 help features. GFX1 has 67 public source routines and 16 constants;
  its 76 help features contain 60 of those routines, while seven low-level
  sprite aliases are documented in SIDSPR1 instead of duplicated in GFX1 help.
- The external `action-help.sqlite3` contains 260 validated topics. Build-time
  checks require coverage for every compiler builtin/constant, every shipped
  library declaration, and every active language keyword/type.
- Every successful ALINK run atomically rebuilds a semantic SQLite code map.
  ACTEDIT uses it for F5 definitions, F7 references, navigation
  history, and Ctrl-click lookup.
- Linux ACTDBG has a live Idun console, and Linux ACTPROF supports imported and
  live PC sampling with process/function/statement attribution in SQLite.
- The export includes the UDOS-free `actsvc` C64 support tool. Its 3,970-byte
  resident image occupies `$C000-$CF81`, inside the reserved `$C000-$CFFF`
  service range.
- The fake Idun socket target drives real ACTDBG and ACTPROF processes through
  upload, register/memory access, persistent breakpoints, step, sampling, and
  SQLite aggregation. A lib6502 harness also executes stepping helpers from the
  actual assembled resident image.
- Live target sessions restore all patched breakpoint bytes on graceful
  detach, reject unsafe PRG and breakpoint ranges, and report PAL/NTSC sample
  timing. ACTPROF periodically drains the bounded target buffer throughout a
  long run instead of retaining only its first batch.
- AddressSanitizer and UndefinedBehaviorSanitizer pass locally.
- The prior 20-test direct-PRG gate passes on AArch64 VICE 3.9, including five
  nonduplicate native ActionC64U control-flow programs plus REU and DBF/D64
  I/O. The current local gate has 21 cases; VICE 3.7.1 version-skips only the
  long REU-plus-disk monitor case. All other KERNAL-output cases wait for
  emulated BASIC readiness rather than relying on host-speed timing.
- Direct and mutual recursive word, local-array, and REAL frames execute with
  the expected C64 memory results.
- The exported workspace is itself an Action project and compiles/links
  `HELLO.ACT` on the Pi into a 116-byte C64 PRG.
- Native Pi and local artifacts are rebuilt atomically; use
  `tools/verify_idun_artifacts.py` to validate the current build instead of
  relying on a stale recorded digest.

## Current Boundaries

The process-conversion inventory, target agent, Linux debugger, profiler,
instruction stepping, and persistent-breakpoint reinstallation are
implemented. Full IEEE-754, MATH1, GFX1, ASMBLOCK, graphics resources, resource
editors, formatting, external help, direct-PRG execution, and signed Alpine
packaging are implemented. Linux ACTC now retains every project routine and
prunes full-source library routines to their transitive project-rooted call
graph; routine-address, `OverlayCall`, global, and declaration-time references
conservatively preserve their targets.
Attached-hardware validation and normal release integration remain.
Cross-product UDOS parity is tracked separately in
`docs/udos_feature_parity.md`.

Cross-product parity is judged by portable Action source, normalized OBJ1
meaning, reachable-only common-module selection, and direct-PRG results. It does
not require native UDOS to copy Linux processes, SQLite, sockets, or APKs, and
it does not require Idun to copy UDOS services, compiler overlays, REU
workspace management, or DNP packaging.

The native MATH1 header now exposes all eight constants as zero-code compile-
time values and keeps each implemented call in an independently selected OBJ1
module. The shared `math1_constants_include.act` fixture compiles and links in
both products. Idun now lowers `FTrunc`, `FFloor`, `FCeil`, `FRound`, `FFrac`,
`FMod`, and `FHypot` to shared independently selected objects. Its remaining
full-source implementation is now size-selective: Linux ACTC emits only the
transitive library-routine closure referenced by retained project routines and
module-level addresses, excluding unreferenced siblings.

The 2026-07-19 native checkpoints add a bounded two-REAL-parameter function ABI
and one finite comparison/select body without changing Idun syntax or the
common runtime. Native ACTC preserves left-to-right argument order, copies both
binary32 values by value, compares them through `RT_F_CMP.OBJ`, and returns the
selected parameter by pointer in a direct PRG. The root closure selects only
integer conversion, comparison, and comparison's special-value dependency.
Exact OBJ, ALINK, and live VICE checks pass, raising the native inventories to
1,327 broad and 171 source-backed shapes; the complete 171-case source-backed
live matrix also passes. Idun already supports the general form. The exact
source is now shared as a parity fixture: Idun folds its two
constant conversions while native executes the reachable `RT_I_TO_F.OBJ`, and
both select comparison and produce the same result. Arbitrary native REAL
expressions and control flow, nested calls, full MATH1 source, and the remaining
type/resource/workflow items remain cross-product work tracked in
`docs/udos_feature_parity.md`.

The 2026-07-20 shared selector refresh adds byte-identical 77-byte
`RT_F_MIN.OBJ` and `RT_F_MAX.OBJ` modules to both checkouts. Native ACTC now
recognizes their bounded source forms, while Linux ACTC continues to compile
the general portable MATH1 bodies. Exact 2,304-pair host checks, focused native
VICE launches, the 32-shape native MATH1 source matrix, and its eight full-range
helper probes pass. The broad native link inventory is 1,331 shapes and its
compiled-runtime object/relocation oracle covers 290 cases. The shared manifest
and Idun export/standalone-link tests guard this snapshot. The current Idun
host suite passes 153 tests, the sanitizer suite passes 138, and the 21-test
direct-PRG gate passes with only the documented VICE 3.7 DBF/REU skip. Both
host and static Alpine/AArch64 exports verify 31 commands and 260 help topics.
This refresh is hardware-independent and has not yet been redeployed to the Pi;
attached cartridge/C64 acceptance remains a release gate.

The subsequent native `FSign` slice adds the shared 123-byte
`RT_F_SIGN.OBJ`, native named-REAL assignment/print/condition lowering, 2,304
exact edge/random oracle cases, and a direct-PRG sibling-pruning launch. Idun's
general portable MATH1 source remains unchanged; the synchronized module is
available to direct OBJ consumers and guarded by the manifest and standalone
link tests.

The following native `FClamp` slice adds the shared 199-byte
`RT_F_CLAMP.OBJ`, a bounded native assignment/print root, an exact
three-input oracle, and a focused direct-PRG closure launch. Any NaN or inverted
bounds produce canonical quiet NaN; valid bounds preserve the selected operand
through `FMin(FMax(value,lower),upper)`. Idun's general portable MATH1 source
remains unchanged, while generator, manifest, export, and standalone-link tests
guard the synchronized module. This hardware-independent refresh has not been
accepted on an attached cartridge/C64. The follow-up native-only compiler
widening captures all initializer, argument, destination, and print storage
roles in that fixed root. Its permuted source-backed PRG prints 5.0 through
generic ALINK closure. No Idun compiler or target-runtime change is required;
Linux ACTC already compiles the general portable call. The next native-only
widening captures every caller and callee storage role in the bounded finite
two-REAL-parameter select. The new permuted shared fixture also compiles, links,
and executes through Linux ACTC/ALINK without an Idun implementation change.
The next pass-A slice separates the bounded two-parameter return selector from
caller argument storage. A reordered shared fixture returns its second parameter
as 2.0 through both products. At that checkpoint native inventories were 1,334
broad, 173 non-runtime source-backed, and 291 compiled-runtime relocation-oracle cases;
pass A is 7,418 bytes with 774 bytes free and pass K is 4,594 bytes with 3,598
bytes free.

The following shared `FTrunc` slice adds a 107-byte dependency-free OBJ1 module
to both products. Native ACTC handles its bounded named-REAL assignment,
direct-print, and condition positions. Linux ACTC now parses and constant-folds
the intrinsic, emits `RT_F_TRUNC` for dynamic values, and no longer emits a
portable FTrunc function body from MATH1. Exact host and Idun VICE vectors cover
all binary32 exponent classes and deterministic random inputs. At that checkpoint native
inventories are 1,335 broad, 173 non-runtime source-backed, and 292
compiled-runtime relocation-oracle cases. The other MATH1 implementation bodies
still require call-graph pruning or dependency-sized object generation.

The following shared `FFloor` slice adds a 135-byte OBJ1 module that imports
only `RT_F_TRUNC.OBJ`. Linux ACTC parses, constant-folds, and emits the
intrinsic, and MATH1 no longer emits its portable floor body. Native ACTC owns
bounded assignment, direct-print, and REAL-condition forms. Exact host checks,
116 Idun VICE vectors, and a focused native direct-PRG launch prove binary32
semantics, aliased-pointer safety, transitive dependency closure, and sibling
pruning. At that checkpoint native inventories were 1,336 broad, 173 non-runtime
source-backed, and 293 compiled-runtime relocation-oracle cases. The native
MATH1 gap was 33 public routines; remaining Idun source bodies still need
reachable-only packaging.

The next shared `FCeil` slice adds a 42-byte OBJ1 module that imports
`RT_F_FLOOR.OBJ` and transitively `RT_F_TRUNC.OBJ`. Linux ACTC parses,
constant-folds, and emits the intrinsic, and MATH1 no longer emits its portable
ceiling body. Native ACTC owns bounded assignment, direct-print, and
REAL-condition forms. Exact host checks, 116 Idun VICE vectors, and a focused
native direct-PRG launch prove binary32 semantics, aliased-pointer safety,
`ceil -> floor -> trunc` closure, and sibling pruning. At that checkpoint native
inventories were 1,337 broad, 173 non-runtime source-backed, and 294
compiled-runtime relocation-oracle cases.

The following shared `FRound` slice adds a 152-byte OBJ1 module that imports
only `RT_F_TRUNC.OBJ`. It rounds nearest with halfway cases away from zero,
preserves NaN payloads, infinities, signed zero, and integral values, and avoids
the large-integral error caused by adding or subtracting 0.5. Linux ACTC
constant-folds constant calls and selects `RT_F_ROUND` only for dynamic calls;
native ACTC owns bounded assignment, direct-print, and REAL-condition forms.
Exact host checks, 116 Idun VICE vectors, and the focused native direct PRG
prove alias safety, `round -> trunc` closure, and sibling pruning. At that
checkpoint native inventories were 1,338 broad, 173 non-runtime source-backed,
and 295 compiled-runtime relocation-oracle cases. Native pass 6 was 8,074 bytes
with 118 bytes free; the native MATH1 gap was 31 public routines.

The next shared `FFrac` slice adds a 93-byte OBJ1 module that imports
`RT_F_TRUNC.OBJ` and `RT_F_SUB.OBJ` and computes `value-FTrunc(value)`. Linux
ACTC constant-folds constant calls and selects `RT_F_FRAC` only for dynamic
calls; native ACTC owns bounded assignment, direct-print, and REAL-condition
forms. Exact host checks, 116 Idun VICE vectors, and the focused native direct
PRG prove alias safety, signed finite fractions, integral cancellation,
exceptional-value behavior, complete closure, and sibling pruning. At that
checkpoint native inventories were 1,339 broad, 173 non-runtime source-backed,
and 296 compiled-runtime relocation-oracle cases. Native pass 6 was 8,085 bytes
with 107 bytes free; the native MATH1 gap was 30 public routines.

The following shared `FMod` slice adds a 245-byte OBJ1 module that imports
`RT_F_DIV.OBJ`, `RT_F_TRUNC.OBJ`, `RT_F_MUL.OBJ`, and `RT_F_SUB.OBJ` and
computes `value-FTrunc(value/divisor)*divisor`. Linux ACTC constant-folds
constant calls and selects `RT_F_MOD` only for dynamic calls; native ACTC owns
bounded assignment, direct-print, and REAL-condition forms. Exact host checks
cover 332 vectors in each of the ordinary, left-alias, and right-alias modes.
The 116-pair Idun VICE fixture and
focused native direct PRG prove full exceptional-value behavior, complete
closure, and sibling pruning. At that checkpoint native inventories were 1,340
broad, 173 non-runtime source-backed, and 297 compiled-runtime
relocation-oracle cases. Native pass 6 was 8,094 bytes with 98 bytes free; the
native MATH1 gap was 29 public routines.

The next shared `FHypot` slice adds the 503-byte `RT_F_HYPOT.OBJ`. It is safe
when either source aliases its destination and uses a scaled maximum/minimum
calculation through absolute value, minimum, maximum, division,
multiplication, addition, and square root. Linux ACTC constant-folds constant
calls and selects `RT_F_HYPOT` only for dynamic calls; native ACTC owns bounded
assignment, direct-print, and REAL-condition forms. Exact host checks cover
2,316 vectors in each of the ordinary, left-alias, and right-alias modes. The
116-pair Idun VICE fixture, focused native direct PRG, and complete native
MATH1 matrix prove end-to-end behavior, complete closure, and sibling pruning.
The same slice fixes native ALINK paged-object import discovery, with an
11-import regression crossing the source-window boundary. At that checkpoint native
inventories were 1,341 broad, 173 non-runtime source-backed, and 298
compiled-runtime relocation-oracle cases. Native pass 6 is 8,093 bytes with 99
bytes free; the native MATH1 gap is 28 public routines.

The 2026-07-21 native selected-binary return slice routes REAL `RETURN(...)`
through the body overlay's bounded value parser. Pass K accepts a two-REAL-
parameter function returning one selected arithmetic, min/max, remainder, or
hypotenuse expression and writes it through a hidden non-aliasing result cell.
The shared `real_function_binary_hypot.act` fixture compiles and links with
Linux ACTC/ALINK and native ACTC/ALINK; the native direct PRG selects only the
twelve-module conversion/hypotenuse closure and writes binary32 5.0 in VICE.
At that checkpoint native inventories were 1,342 broad, 174 non-runtime source-backed, and 298
compiled-runtime relocation-oracle cases. Pass K is 5,877 bytes with 2,315
bytes free. The following compiler preparation lets native passes 6 and 7
traverse bounded REAL operands while retaining their capacity gates: pass 6 is
8,094 bytes with 98 bytes free, and pass 7 is 6,587 bytes with 1,605 bytes free.
A regression also crosses the production 1,280-byte source window inside a
mixed unary/binary/ternary tree. Native pass L now lowers that bounded postfix
stream for a straight-line module-REAL subset. Direct native ALINK/VICE cases
execute nested binary and unary/binary/ternary trees, print `2`, preserve DBG1
source-variable records through `__idata`, and prune unreferenced helpers. Pass
L also lowers nonrecursive two-REAL-parameter functions called directly by
`MAIN`; the shared `real_function_nested_postfix.act` fixture compiles and links
with Linux ACTC, while native ACTC/ALINK emits and launches the pointer call ABI
and prints `5` in VICE. The follow-up shared
`real_function_local_nested_postfix.act` fixture adds bounded static REAL local
storage with a DBG1 local record; native VICE verifies binary32 5.0 in the
result and 3.0 in the local while preserving the same reachable helper closure.
Pass L now accepts two functions in that bounded form. The shared
`real_two_function_nested_postfix.act` fixture emits separate exports, storage,
and DBG1 banks; native VICE verifies results 5.0 and 3.0 plus both locals. Idun
ACTC now lowers direct `FMin` and `FMax` expressions to their standalone runtime
objects and executes the same fixture with identical results. The new shared
`real_function_call_chain_postfix.act` fixture adds ordinary `MAIN -> CHAIN` and
`CHAIN -> LENGTH` OBJ1 relocations. Native VICE verifies binary32 5.0 in both
the module result and `CHAIN.BASE`; Idun executes the same source with the same
result. The follow-up `real_function_nested_local_call_postfix.act` feeds
`LENGTH(A,B)` directly into `FMax`; both toolchains produce 5.0, while native
VICE also checks the nested-call temporary and reachable-only helper closure.
The shared `real_function_user_call_arguments_postfix.act` fixture returns
`LOWER(LOWER(A,A),LOWER(B,B))`. Native pass L spills all three call results to
distinct temporaries; native VICE and Idun both produce 3.0 without static-cell
aliasing. The shared `real_function_forward_frame_postfix.act` fixture reverses
the declaration direction with `FIRST -> SECOND` while `FAbs(A)` remains live.
Native ACTC stack-preserves the caller's static cells, stages the A/X result,
and restores the caller before producing 3.0; Idun produces the same result.
Native self and mutual cycles remain rejected.
The shared `real_function_if_else_postfix.act` fixture then executes both paths
of one nonnested REAL-function conditional. Native pass M imports `rt_f_cmp`,
relocates long branches to internal `__rf0`/`__re0` code exports, and prints
`34`; Idun ACTC/ALINK executes the same source with identical FIRST/SECOND
results. Pass N adds shared `real_function_sequential_if_else_postfix.act` and
`real_function_nested_if_else_postfix.act` control fixtures; native and Idun
products print `43` and `143`, respectively. Pass O adds shared
`real_function_four_sequential_if_postfix.act` and
`real_function_four_deep_if_postfix.act`; both products print `43` and `154`.
Pass P adds shared `real_function_early_return_if_postfix.act` and
`real_function_early_return_four_deep_postfix.act`; both products print `33`
and `154`. Pass Q adds shared `real_function_loops_postfix.act`; its post-test
and pre-test REAL-function loops produce 4.0 and 3.0 in both native VICE and
Idun's generated-6502 execution path. Pass R adds shared
`real_function_loop_exit_postfix.act`; its plain and guarded nearest-loop exits
produce 4.0 and 3.0 in both products. Pass S adds shared
`real_function_for_postfix.act`; its ascending default-step and descending
`STEP -2` CARD-counter loops produce 4.0 and 7.0 in both products. Pass T adds
shared `real_function_dynamic_for_postfix.act`; named CARD initial/final bounds
in nested loops produce 7.0 twice in both products. Pass U adds shared
`math1_angle_conversions_postfix.act`; folded pi and one-parameter
`DegToRad`/`RadToDeg` compile and link in both products, and native VICE prints
pi followed by `180`. Public intrinsic packaging then adds separate
`RT_F_DEG_TO_RAD.OBJ` and `RT_F_RAD_TO_DEG.OBJ` wrappers. Idun folds constant
calls and imports only the selected wrapper for dynamic calls; native VICE
executes both independently selected paths. Pass U also combines folded
literals with pass-P controls. Shared
`real_function_literal_clamp_comma_locals_postfix.act` uses four comma-grouped
REAL locals, multiplication, three comparisons, and three immediate returns;
native and Idun generated-6502 execution both produce `-1`, `0`, and `1`.
Current native inventories are
1,379 broad, 196 non-runtime source-backed, and 313 compiled-runtime
relocation-oracle cases; pass 6 is 8,084 bytes with 108 bytes free, pass 7 is
7,129 bytes with 1,063 bytes free, pass L is 6,140 bytes with 2,052
bytes free, pass M is 7,009 bytes with 1,183 bytes free, pass N is 7,131 bytes with 1,061 bytes free, pass O is 7,134 bytes with 1,058 bytes free, pass P is
7,158 bytes with 1,034 bytes free, pass Q is 7,162 bytes with 1,030 bytes free,
and pass R is 7,345 bytes with 847 bytes free under its 768-byte gate. Pass S is
7,839 bytes with 353 bytes free under its 256-byte gate. Pass T is 8,158 bytes with 34 bytes free under its 32-byte gate. Pass U is 7,488 bytes with 704 bytes free under its 640-byte
gate. `RT_F_EXP.OBJ` is now synchronized as an independently selected
1,465-byte dependency root; Idun and native ACTC both lower `FExp` to it, and
native ALINK accepts its 233 relocations through the expanded 255-record table.
`RT_F_LN.OBJ` is synchronized as an independently selected 1,382-byte
dependency root; both compilers lower `FLn` to it, production ALINK accepts its
33 exports and 180 relocations, and the focused native direct PRG prints
`0.693147...` for `FLn(2)`.
Separate 71-byte `RT_F_LOG2.OBJ` and `RT_F_LOG10.OBJ` roots are synchronized.
Both compilers lower the corresponding unary calls to these alias-safe
wrappers, each imports only `RT_F_LN.OBJ` and `RT_F_DIV.OBJ`, and focused
native direct PRGs print `3` for `FLog2(8)` and `FLog10(1000)` while pruning
the sibling.
The shared 548-byte `RT_F_POW.OBJ` is now synchronized. Both compilers lower
`FPow(base,exponent)` to it, its direct closure remains link-selected, and the
native and Idun generated PRGs both produce `1024` for `FPow(2,10)`.
The shared 586-byte `RT_F_SIN.OBJ` and private 225-byte
`RT_F_WRAP_PI.OBJ` are now synchronized. Both compilers lower `FSin(value)` to
the same alias-safe range-reduction and degree-11 polynomial closure; the
focused native direct PRG prints `0.909297...` for `FSin(2)` while pruning
unrelated roots.
The shared 609-byte `RT_F_COS.OBJ` is now synchronized. Both compilers lower
`FCos(value)` to the same alias-safe range-reduction and degree-10 even
polynomial closure; the focused native direct PRG prints `-0.416146...` for
`FCos(2)` while pruning unrelated roots.
The shared 113-byte `RT_F_TAN.OBJ` is now synchronized. Both compilers lower
`FTan(value)` to this alias-safe root, which imports sine, cosine, and division
and lets ALINK deduplicate their shared closure. Native VICE prints
`-2.185040...` for `FTan(2)`, and Idun's generated PRG executes
`FTan(pi/4)`.
The shared 1,032-byte `RT_F_ATAN.OBJ` is now synchronized. Both compilers lower
`FATan(value)` to this alias-safe root, which preserves signed zero, maps
infinities to signed binary32 pi/2, canonicalizes NaN, and imports only
division, subtraction, addition, and multiplication. Native VICE prints
`1.107148...` for `FATan(2)`, and Idun's generated PRG executes `FATan(-2)`.
The shared 493-byte `RT_F_ATAN2.OBJ` is now synchronized. Both compilers lower
`FATan2(y,x)` to this alias-safe root, which implements signed-zero, zero-axis,
infinity, NaN, and all four quadrant rules and imports only division, FATan,
addition, and subtraction. Native VICE prints `0.785398...` for
`FATan2(1,1)`, and Idun's generated PRG executes `FATan2(-1,-1)`.
The shared 220-byte `RT_F_ASIN.OBJ` is now synchronized. Both compilers lower
`FASin(value)` to this alias-safe root, which preserves signed zero, returns
signed pi/2 at the endpoints, canonicalizes NaN and magnitudes above one, and
imports only multiplication, subtraction, square root, and FATan2. Native VICE
prints `1.570796...` for `FASin(1)`, and Idun's generated PRG executes
`FASin(0.5)`.
The shared 71-byte `RT_F_ACOS.OBJ` is now synchronized. Both compilers lower
`FACos(value)` to this alias-safe root, which evaluates FASin in private
storage and subtracts it from binary32 pi/2. It directly imports only
`RT_F_ASIN.OBJ` and `RT_F_SUB.OBJ`; the focused native direct PRG prints
`3.141592...` for `FACos(-1)`, and Idun's generated PRG executes
`FACos(-0.5)`.
The shared 71-byte `RT_F_SEC.OBJ` is now synchronized. Both compilers lower
`FSec(value)` to this alias-safe root, which evaluates FCos in private storage
and divides binary32 one by that result. It directly imports only
`RT_F_COS.OBJ` and `RT_F_DIV.OBJ`; the focused native direct PRG prints
`-2.402998...` for `FSec(2)`, and Idun's generated PRG executes `FSec(0)`.
The native MATH1 gap is now 13 public routines, and reentrant
local frames, general `FOR` bound expressions/runtime steps, nested counter-to-REAL body
composition, mixed loop/conditional nesting, returns from inside loops, more
than four controls,
deeper nesting, unrestricted user-call
argument trees and nested call expressions, mixed types, arbitrary signatures,
and recursive frames remain pending.

For a two-checkout release, run:

```sh
make sync-native-check NATIVE_ACTION_ROOT=/path/to/actionc64u
make all
make test-sanitize
make test-prg
make verify-aarch64
make apk-existing
make apk-verify
```

The first command checks every shared module and generator against the native
manifest. It deliberately ignores only `rt_dbf_create.obj` and
`rt_dbf_file_open_write.obj`, whose filesystem behavior differs by operating
system.

The 2026-07-17 hardware attempt verified C64 Ultimate API access, corrected
and persisted the required `$DE00`/turbo configuration, and proved that the Pi
can flash both `init.binary` and `idun64.binary`. Validation then stopped below
the Action tools: cartridge reset reported `i2c write failed`, I2C bus 1 had no
control device, the C64 remained at BASIC, and `idunsh -o drives` timed out.
The exact recovery preflight is in `docs/operator_guide.md`.

The packaged milestone was synchronized to `/home/idun/idun_fork`, built,
tested, exported, installed, and smoke-tested there. The later native
cross-suite validation used an isolated Pi checkout so the separately managed
primary Idun fork and the pre-existing `/home/idun/action` tree were not
modified.
