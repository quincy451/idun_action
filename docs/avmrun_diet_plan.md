# AVMRUN Diet Plan

## Problem

Current `AVMRUN.PRG` is carrying too much responsibility:

- binary `AVM1` loader/validator
- legacy text-AVM decode compatibility
- intrinsic patching
- Acheron fast path
- fallback interpreter
- integer/native print helpers
- full `REAL32` arithmetic and decimal formatting

That makes `AVMRUN.PRG` both too large and too central. It also duplicates VM
engine logic already present elsewhere in the system.

## Goal

Keep one canonical AVM execution engine in the product, keep `AVMRUN.PRG`
small, and make optional language/runtime features arrive through the linked
program image instead of as permanent runner baggage.

## Recommended Architecture

Split responsibilities into three layers.

### 1. Resident UDOS Services

UDOS resident should provide only stable OS-style services:

- file and directory services
- console services
- REU services
- time/network/device services
- program launch/return services

These are always-present system services, not per-program runtime libraries.

### 2. AVMRUN Core

`AVMRUN.PRG` should keep only the minimum shared execution core:

- binary `AVM1` load/validate
- final image/section load
- one canonical AVM execution engine
- minimal native call bridge into UDOS services
- failure reporting

It should *not* permanently carry optional feature helpers such as:

- floating-point formatting
- trig/math libraries
- SID/music helpers
- graphics/sprite helpers
- TCP helpers
- database helpers
- 80-column console helpers

### 3. Linkable Runtime Modules

Optional facilities should be linked only when used.

Examples:

- `REAL` print/format helpers
- `REAL` arithmetic helpers if they are not part of the minimal VM core
- trig/math
- SID/audio
- graphics/sprites
- TCP/remote shell
- DBF-style file/database support
- 80-column console mode support

`ALINK` should dead-strip these at symbol/procedure granularity, so a program
that never touches them does not pay for them.

## Library Implementation Strategy

Use **raw 6502 runtime libraries as the canonical implementation**.

Use **Action include/source modules only as thin language bindings**.

### Why raw 6502 libraries should be canonical

- stable ABI independent of compiler frontend changes
- easier fine-grained dead-strip at link time
- easier to hand-optimize for size and speed
- reusable by both generated AVM programs and native UDOS tools
- better fit for hardware-heavy features such as SID, TCP, graphics, and REU

### What Action include modules should do

- declare public APIs
- provide constants/types
- provide thin wrappers or convenience shims
- avoid duplicating large implementation bodies in source form

For pure algorithms that are small and naturally expressed in Action, source
implementations are still acceptable, but they should be the exception rather
than the default for core runtime facilities.

## Program Packaging Direction

To make optional helpers truly link-only-when-used, the final linked program
must be able to carry more than one kind of payload.

Recommended direction:

- keep the main `AVM1` payload for the VM code
- add optional linked runtime sections for native helper blobs
- let `ALINK` emit only the helper sections actually referenced
- let `AVMRUN` load those sections into designated RAM/REU windows and patch
  `CALLN`/helper entrypoints accordingly

This keeps the runtime feature cost with the program that uses it, instead of
with every invocation of `AVMRUN`.

## Immediate AVMRUN Diet Steps

These are the first worthwhile cuts.

### Step 1. Remove legacy text-AVM decode from normal AVMRUN

Current text decode exists in `decode_avm_text`.

If binary `AVM1` is the real product path, remove it from the shipped build or
hide it behind a debug-only build flag.

Status: landed in the production build.

- `build_avmrun_udos.sh` now assembles `AVMRUN` with `ALLOW_TEXT_AVM=0`
- shipped `AVMRUN.PRG` rejects text `.AVT` input with `BAD AVM`
- current file size dropped from `9484` to `8699`

### Step 2. Stop carrying two normal execution engines

Choose one canonical execution path for normal runtime execution.

Recommended:

- keep the Acheron-backed execution path as the only normal runner path
- remove the duplicate linked Acheron copy from `AVMRUN`
- have `AVMRUN` enter the resident UDOS Acheron engine through a narrow tool
  ABI service
- then move the remaining fallback interpreter out of production `AVMRUN`
  or behind an on-demand path

This is the biggest structural size win available.

Status: the duplicate Acheron copy is gone from normal `AVMRUN`.

- production `AVMRUN.PRG` no longer links `acheron.o`
- UDOS resident now exposes `svc_vm_acheron_enter` on the fixed-page tool ABI
- the normal fast path enters the resident engine instead of carrying its own
  copy
- current runner file size dropped from `6015` to `3699`

This is the point where the shipped normal runtime path now has one canonical
AVM engine instead of two.

### Step 3. Minimize runner-global intrinsics

Keep only the smallest always-needed native bridge in `AVMRUN`.

Candidates to remain global:

- exit
- minimal console/file/service bridge

Candidates to move out of runner-global code:

- `REAL` print formatting
- non-core math
- richer device helpers

Status: first cut landed, then widened.

- the initial `REAL` print formatter move landed first
- `AVMRUN_OVL1.BIN` now owns the broader print helper family:
  - `Print`
  - `PrintE`
  - `PrintI`
  - `PrintIE`
  - `PrintR`
  - `PrintRE`
- production `AVMRUN.PRG` stages and loads that helper on demand instead of
  carrying those print helpers permanently in the resident runner body
- current runner file size dropped from `8699` to `6015`
- current print overlay size is `1119`

Status: second cut landed.

- interpreter-side `REAL` arithmetic/conversion now lives in
  `AVMRUN_OVL2.BIN`
- production `AVMRUN.PRG` stages and loads that helper only when interpreted
  `FADD` / `FSUB` / `FMUL` / `FDIV` / `FTOI` / `ITOF` execute
- current runner file size dropped from `8160` to `6202`
- current real-ops overlay size is `2100`

This keeps the non-REAL interpreter shell resident while moving the heaviest
optional math/conversion block out of the always-loaded runner body.

Status: third cut landed.

- the fallback interpreter shell now lives in `AVMRUN_OVL3.BIN`
- the resident runner now drives that fallback path as a suspend/resume overlay
  so the interpreted path can yield for `OVL1` print helpers and `OVL2` REAL
  helpers through the shared `$F000` exec window
- current runner file size dropped from `3699` to `1845`
- current interpreter overlay size is `2046`

This keeps the normal fast path resident while making the fallback path a true
on-demand payload instead of permanent runner code.

### Step 4. Move optional helper families behind linkable runtime modules

Start with the most obviously optional families:

- `REAL` print formatting
- trig/math extensions
- graphics/sprite support
- SID/audio support

Status: first linked-helper proof landed.

- `ALINK` now emits a native-helper trailer when linked `rt_print_f` is live
- the emitted payload uses a reserved `CALLN` pseudo-target for program-owned
  REAL print instead of the old runner-global `PRINTREAL` intrinsic
- `ALINK` no longer embeds that helper blob inside `ALINK.PRG`; it now stages
  `!RT_PRINT_F_HELPER.BIN` from the packaged tool set and streams it into the
  native-helper trailer only when the linked program actually needs it
- production `AVMRUN` now parses that helper trailer, loads the print helper
  into a dedicated low-RAM native-helper window at `$2400`, and patches that
  pseudo-target to the loaded native entry on the normal fast path
- the helper blob is now self-describing: `RT_PRINT_F_HELPER.BIN` starts with
  an `AVNH` header carrying helper ABI version, helper kind, entry offset, and
  total helper length, and `AVMRUN` validates that header before patching the
  call target
- the fallback interpreter still accepts the same pseudo-target and routes it
  through the existing print path, so the current harness/runtime proof surface
  stays green
- linked `PrintRE` is now proven on an actual `ALINK`-produced program through
  that program-owned helper trailer alone: `A=REAL(1)`, `B=REAL(8)`,
  `X=A/B`, `PrintRE(X)` still prints `0.125` even after removing
  `RT_PRINT_F_HELPER.BIN`, `RT_PRINT_STD_HELPER.BIN`, `AVMRUN_OVL1.BIN`,
  `AVMRUN_OVL2.BIN`, and `AVMRUN_OVL3.BIN` from the mounted workspace, so the
  shipped linked REAL print path no longer depends on loose helper sidecars or
  runner overlays for that proven case
- current runner file size is `3204`
- current linker file size is `13251`
- current linked REAL print helper blob size is `1075`

Status: second helper kind landed.

- `AVMRUN` now also understands a second `AVNH` helper kind for standard print
  helpers
- `RT_PRINT_STD_HELPER.BIN` is now packaged as a self-describing helper
  artifact with helper kind `2`
- native `Print` / `PrintE` / `PrintI` / `PrintIE` stubs in `AVMRUN` now try
  to load and use that helper on the normal fast path
- `ALINK` now also emits the linked standard-print pseudo-targets
  (`$FE00` / `$FE10` / `$FE30` / `$FE31`) instead of the old runner-global
  `$FFxx` print targets for standard print sites
- `ALINK` now stages `!RT_PRINT_STD_HELPER.BIN` from the packaged tool set and
  appends it as a second native-helper trailer entry when standard print is
  live, so standard print now follows the same program-owned helper model as
  `rt_print_f`
- the current harness proof surface for standard print still executes through
  the interpreter fallback path, so `AVMRUN_OVL1.BIN` and `AVMRUN_OVL3.BIN`
  remain the proven runtime path there even though the runtime sidecar
  dependency is gone
- production `AVMRUN.PRG` no longer has the loose standard-print sidecar
  fallback path; if linked standard print is present, the `AVM1` image must
  carry the helper trailer emitted by `ALINK`
- current packaged standard print helper blob size is `278`

Status: runner split landed.

- `AVMRUN.PRG` is now the production runner
- `AVMRUNC.PRG` is now the compat/interpreter runner
- production `AVMRUN.PRG` no longer carries resident compat/interpreter glue;
  payloads that need that path now fail with `NEEDS AVMRUN COMPAT`
- `AVMRUNC.PRG` keeps `AVMRUN_OVL1.BIN`, `AVMRUN_OVL2.BIN`, and
  `AVMRUN_OVL3.BIN` as the staged compat path
- current shipped sample/runtime probes such as `UDOSHELLO.AVM`,
  `UDOSFLOW.AVM`, and the narrow interpreted runtime arithmetic samples belong
  to `AVMRUNC.PRG`
- current linked helper-trailer proofs (`FASTSTD`, `FASTREAL`, linked
  `PrintRE(X)` without sidecars/overlays) belong to production `AVMRUN.PRG`

This is the first shipped proof that an optional runtime helper can be selected
by `ALINK`, carried by the linked program image, and consumed by `AVMRUN`
without turning it back into a permanent runner-global service.

## Feature Placement Rules

Use these rules going forward.

### Put it in resident UDOS only if:

- every session needs it
- it is an OS service, not an application/library feature
- multiple unrelated tools need the same always-on capability

### Put it in AVMRUN core only if:

- every AVM program needs it
- it is part of the single canonical execution engine
- it cannot realistically be moved into a program-linked helper section

### Put it in a linkable runtime module if:

- only some programs need it
- it is domain-specific
- it is large enough to matter
- dead-strip should eliminate it when unused

## Guidance For Planned Features

### TCP / remote shell

- raw 6502 runtime module
- thin Action binding layer
- UDOS resident only provides low-level transport/service ABI

### SID / audio

- raw 6502 runtime module
- optional helper family, not runner-global
- prefer semantic `Sid*` entrypoints over Atari-style distortion-driven
  `Sound` semantics
- keep `Sound` / `SndRst` only as compatibility sugar if they exist at all
- current design input:
  - `docs/sid_and_sprite_ideas.txt`
  - `docs/helper_family_abi_draft.md`

### Graphics / sprites

- raw 6502 runtime module
- optional helper family
- mode/state management should live in the linked runtime, not in AVMRUN core
- shape the public API around semantic datatypes and helper routines rather
  than raw register exposure
- current design input:
  - `docs/graphics_ideas.txt`
  - `docs/sid_and_sprite_ideas.txt`
  - `docs/helper_family_abi_draft.md`

### DBF-style database support

- raw 6502 runtime module
- optional helper family
- should be link-only-when-used
- prefer a handle-based API with explicit schema and record operations
- current design input:
  - `docs/dbf_test.c`
  - `docs/helper_family_abi_draft.md`

### Trig / math

- raw 6502 runtime module for canonical implementation
- optional helper family unless a subset becomes part of the minimal VM core

### 80-column mode

- optional console driver/runtime module
- not always allocated
- allocate buffers only when activated
- prefer REU-backed buffers and mode-specific state
- must provide explicit on/off entrypoints so normal 40-column sessions pay
  nothing

## Candidate First-Cut Public APIs

These are the strongest current inputs for the first helper-family bindings.

### SID / sprite layer

- `SpriteOn`
- `SpriteOff`
- `SpritePos`
- `SpritePtr`
- `SpriteData`
- `SpriteColor`
- `SpriteMC`
- `SpriteXExp`
- `SpriteYExp`
- `SpritePrio`
- `SetSpriteMC`
- `SpriteHit`
- `SpriteHitBg`
- `SidFreq`
- `SidPulse`
- `SidWave`
- `SidAD`
- `SidSR`
- `SidOn`
- `SidOff`
- `SidVol`
- `SidCutoff`
- `SidRes`
- `SidMode`
- `SidRoute`
- `SidRst`
- `SidOsc3`
- `SidEnv3`
- compatibility shims only if needed:
  - `Sound`
  - `SndRst`

### DBF layer

- `dbf_open`
- `dbf_currrecno`
- `dbf_total_recs`
- `dbf_read`
- `dbf_delrec`
- `dbf_delrecat`
- `dbf_write`
- `dbf_close`
- `dbf_compress`
- `dbf_creat`

These should stay as thin language bindings over optional raw 6502 helper
families selected by `ALINK`.

Current concrete helper-family contract:

- `docs/helper_family_abi_draft.md`
- first shipped helper-family wave now proven through:
  - `RT_SIDSPR1_HELPER.BIN`
  - `RT_GFX1_HELPER.BIN`
  - `RT_DBF1_HELPER.BIN`
- first Action-facing binding sketch:
  - `docs/sidspr1_bindings_draft.act`
- next Action-facing binding sketch:
  - `docs/math1_bindings_draft.act`

Current runner-diet boundary:

- production helper-safe load boundary: `0xA8B0`
- compat execution ceiling: `0x9EC0`
- restoring the older `49152`-byte payload target is now explicit follow-up
  work, not a current property of the runner

## Near-Term Implementation Order

1. Freeze the rule that AVMRUN is not the home for optional feature helpers.
2. Remove legacy text-AVM decode from production AVMRUN.
3. Separate debugger-only interpreter logic from normal runner logic.
4. Define runtime-module section format and ALINK emission rules.
5. Move `REAL` print formatting to the first optional helper section as the
   initial proof.
6. Apply the same pattern to the next feature families: math, graphics, SID,
   TCP, DBF, and 80-column support.
