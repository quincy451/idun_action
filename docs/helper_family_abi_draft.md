# Helper Family ABI Draft

## Purpose

This document defines the next layer above the current print-helper proof.

The goal is:

- keep `AVMRUN.PRG` small and execution-focused
- keep optional subsystems out of runner-global resident code
- let `ALINK.PRG` pull in only the helper families a program actually uses
- keep the canonical implementation in raw 6502 helper binaries with thin
  language bindings

This draft covers the first concrete optional helper families for:

- graphics
- sprites
- SID/audio
- DBF-style database access

It does not make these families resident UDOS services and it does not add new
AVM core opcodes for them.

## Core Rule

Optional domain features should use this stack:

1. Action-facing declarations and sugar
2. text `AVO1` runtime wrapper modules when needed
3. packaged raw 6502 helper artifacts selected by `ALINK`
4. `AVMRUN` helper loading and native helper patching through the existing
   `AVNH` model

That means:

- the language surface can be high level
- the runtime implementation remains compact and hardware-aware
- unused families vanish entirely from the final linked program

## Shared Runtime Contract

All new helper families should follow these rules.

### 1. One family, many entrypoints

A helper artifact is a family, not a single function blob.

Examples:

- one graphics helper family can expose screen, bitmap, tile, and blit entrypoints
- one SID/sprite helper family can expose both `Sid*` and `Sprite*` entrypoints
- one DBF helper family can expose open/read/write/delete/compress entrypoints

This avoids emitting dozens of tiny helper files and keeps load/patch overhead
bounded.

### 2. Program-owned helper payloads

If a program uses a helper family, `ALINK` should append that helper family to
its final `AVM1` native-helper trailer.

Runtime consequence:

- `AVMRUN` loads the helper from the linked program image
- no loose runtime sidecar should be required for the shipped path
- the current print-helper model remains the template

Loose packaged helper files may still exist as linker inputs, but not as normal
runtime dependencies.

### 3. Stable family header + entry table

Each helper family should continue to use an `AVNH`-style self-describing
header.

Minimum required metadata:

- magic
- helper ABI version
- family kind
- total helper length
- entry table offset
- entry count

The entry table should be numeric and fixed-width:

- `entry_id`
- `entry_offset`

That avoids special-case runtime parsing for every family.

### 4. Semantic entrypoints, not raw register ABI

Helper entrypoints should describe actions, not hardware register addresses.

Good:

- `SpritePos`
- `SidFreq`
- `DbfOpen`
- `BitmapShow`

Bad:

- `VicWriteD015`
- `SidWriteD418`
- `RawColorRamPoke`

Power users can still use explicit low-level facilities separately. The helper
family ABI should stay semantic.

### 5. Handles for live objects, typed assets for resources

The family ABI should distinguish:

- resource data
- live runtime object/state

Examples:

- sprite art bytes are not the same thing as a live hardware sprite slot
- a bitmap asset is not the same thing as the current active display mode
- a DBF file schema is not the same thing as an open file handle

This keeps the Action-facing type system honest and keeps helper state small.

### 6. Family-local scratch, not runner-global BSS

Family scratch should live inside the helper execution region or family-local
state block, not in permanent `AVMRUN` resident storage.

That keeps the production runner small and lets family cost scale with use.

## Family IDs

Reserve the next helper-family kinds along these lines:

- `1`: standard print
- `2`: REAL print
- `3`: graphics core
- `4`: SID/sprite
- `5`: DBF

Exact numeric assignments can change, but the model should be:

- one family id per subsystem
- one entry table per family
- many semantic entrypoints per family

Current frozen first-wave family ids:

- `1`: print REAL
- `2`: print standard
- `3`: graphics core
- `4`: SID/sprite
- `5`: DBF

Reserved next-wave family ids:

- `6`: math
- `7`: TCP/network
- `8`: 80-column text

## Graphics Family

Suggested family name:

- `RT_GFX1_HELPER.BIN`

### Scope

This family should cover display-mode and bitmap/tile level operations.

It should not try to solve every future raster trick in the first cut.

First-cut scope:

- screen/bitmap mode setup
- asset validation and load helpers
- bitmap show/copy primitives
- tile/character set upload helpers
- mask/blit helpers for valid asset types

### Public Action-facing types

The current design notes point to a split like this:

- `SPRITEDATA`
- `MSPRITEDATA`
- `SPRITE`
- `MSPRITE`
- `BITMAP`
- `MBITMAP`
- `CHARSET`
- `MCHARSET`
- `TILESET`
- `MTILESET`
- `BMASK`
- `MCMASK`

The important rule is:

- assets are data containers
- live objects are runtime instances

### Graphics entrypoints

Recommended first-cut entry ids and semantic names:

- `GfxModeSet`
- `GfxModeOff`
- `BitmapShow`
- `BitmapHide`
- `BitmapBlit`
- `BitmapMaskBlit`
- `BitmapCellColorSet`
- `CharsetLoad`
- `CharsetActivate`
- `TilesetLoad`
- `TileDraw`
- `TileRectFill`

### Asset constraints

The helper family should enforce C64-valid constraints early.

High-res bitmap fragments:

- width multiple of `8`
- height multiple of `8`

Multicolor bitmap fragments:

- logical width multiple of `4`
- height multiple of `8`

Arbitrary non-cell-aligned art should be a mask/blit type, not a plain bitmap
asset.

### Color semantics

Graphics helpers should work in terms of slot-aware color assignment, not raw
freeform color pokes.

That means the binding surface should naturally express:

- global background
- cell slot colors
- sprite color
- sprite multicolor shared slots

The runtime should reject or force explicit replacement when a requested color
violates the hardware representation for the current mode.

## SID/Sprite Family

Suggested family name:

- `RT_SIDSPR1_HELPER.BIN`

This family intentionally groups SID and hardware sprites together because both
are small, hardware-near, and game-facing. It is a good candidate for the first
real gameplay-oriented helper family.

### Why group them

- both are strongly tied to the VIC-II/SID hardware model
- both benefit from semantic wrappers over ugly register packing
- both are likely to be used together by the same programs
- neither belongs in `AVMRUN` core

### Sprite model

The best high-level split is:

- `SPRITEDATA` / `MSPRITEDATA` = art/resource bytes
- `SPRITE` / `MSPRITE` = live hardware sprite object using one of the 8 slots

That lets the language expose object-like operations while the helper handles:

- sprite slot allocation or explicit slot targeting
- X MSB packing
- enable bits
- shared multicolor state
- collision latch reads

### Sprite entrypoints

Recommended first cut:

- `SpriteOn`
- `SpriteOff`
- `SpritePos`
- `SpriteData`
- `SpritePtr`
- `SpriteColor`
- `SpriteMC`
- `SpriteXExp`
- `SpriteYExp`
- `SpritePrio`
- `SetSpriteMC`
- `SpriteHit`
- `SpriteHitBg`

### SID entrypoints

Recommended first cut:

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

Compatibility-only sugar if wanted later:

- `Sound`
- `SndRst`

The real API should stay `Sid*`, not Atari-distortion-shaped.

Current binding sketch:

- `docs/sidspr1_bindings_draft.act`

### State model

This family should not force permanent resident state in the runner.

Expected family-local state only:

- optional cached live sprite ownership table
- optional logical signed X/Y table if off-screen positions are supported
- current shared sprite multicolor values
- minimal SID shadow state only if needed for read/modify/write friendliness

## DBF Family

Suggested family name:

- `RT_DBF1_HELPER.BIN`

### Scope

This family should implement a handle-based DBF runtime, not just a parser.

First-cut scope:

- open
- read current record
- write current record
- delete current record
- delete at record
- close
- compress
- create
- record count / current record query

### Public Action-facing types

Suggested thin binding types:

- `DBF` for an open handle id
- `DBFFIELDDEF` for schema creation/open metadata

The API sketch from `dbf_test.c` is already the right shape: explicit handles,
explicit field descriptors, and explicit operations.

### DBF entrypoints

Recommended first cut:

- `DbfOpen`
- `DbfCurrRecNo`
- `DbfTotalRecs`
- `DbfRead`
- `DbfWrite`
- `DbfDelRec`
- `DbfDelRecAt`
- `DbfClose`
- `DbfCompress`
- `DbfCreate`

### State model

The helper owns:

- open-handle table
- per-handle schema metadata
- current-record state
- scratch for record decode/encode

The runner should not know anything about DBF layout.

### Binding shape

Keep the Action surface thin.

Good:

- `dbf_open(name, count, defs)`
- `dbf_read(handle, fields)`
- `dbf_write(handle, fields)`

Do not make DBF a language keyword or special statement form.

## Math Family

Suggested family name:

- `RT_MATH1_HELPER.BIN`

### Scope

This family should cover semantic numeric functions that do not belong in the
core `AVM` opcode set and are not already handled well by the current
operator-specific REAL runtime modules.

First-cut scope:

- absolute value
- square root
- sine/cosine
- exponent/log
- min/max helpers

The important boundary is:

- keep `A+B`, `A-B`, `A*B`, `A/B`, `REAL(x)`, and `INT(x)` on the current
  narrow runtime-module path
- use `MATH1` for explicit function-shaped numeric work

### Public Action-facing types

No new runtime object type is needed here.

This family should expose plain function-style bindings over existing `REAL`
and integer value types.

### Math entrypoints

Recommended first cut:

- `FAbs`
- `FSqrt`
- `FSin`
- `FCos`
- `FExp`
- `FLog`
- `FMin`
- `FMax`

Current binding sketch:

- `docs/math1_bindings_draft.act`

### State model

This family should stay effectively stateless.

Expected family-local state only:

- temporary scratch for argument/result staging
- optional precomputed constant table if one materially reduces helper size

The runner should not keep permanent math-family state.

## Linker Contract

`ALINK` should eventually treat helper families as ordinary optional runtime
families selected by unresolved helper imports.

Expected linker behavior:

1. see a live helper import such as `rt_sid_freq`, `rt_sprite_pos`, or
   `rt_dbf_open`
2. pull the corresponding wrapper `AVO1` module if needed
3. stage the raw helper family artifact
4. append one family entry to the program-owned native-helper trailer
5. patch helper call sites to the reserved family/entry pseudo-targets

That means the family trailer needs to carry:

- family id
- helper length
- helper bytes

The helper itself carries the entry table.

## AVMRUN Contract

Production `AVMRUN` should only do three things for these families:

1. locate the requested helper family in the linked trailer
2. load the helper into the existing helper execution window
3. patch the requested family entrypoint on demand

`AVMRUN` should not gain subsystem-specific logic for graphics, SID, sprites,
or DBF.

If a family needs complex state transitions, that state lives in the helper
family implementation.

## Recommended Implementation Order

1. Freeze the helper-family metadata format around a general entry table.
2. Keep print helpers as the compatibility-proof baseline.
3. Implement `RT_SIDSPR1_HELPER.BIN` first.

Why first:

- smaller than full graphics
- more immediately useful than DBF for interactive demos
- exercises both resource-style and live-object-style API design
- does not require full screen-mode management on day one

4. The first shipped helper-family wave is now real:

- `RT_SIDSPR1_HELPER.BIN`
- `RT_DBF1_HELPER.BIN`
- `RT_GFX1_HELPER.BIN`

5. Implement `RT_MATH1_HELPER.BIN` next.

Why next:

- smaller contract than TCP or 80-column support
- does not reopen file-ownership questions like DBF
- does not reopen display-state questions like graphics
- gives the next helper family a function-style API instead of a handle or
  resource/object API

## What This Draft Intentionally Avoids

- no new permanent `AVMRUN` core services for these domains
- no raw register keyword explosion in the language
- no claim that all future graphics or music features fit in the first helper
  revision
- no always-allocated 80-column or graphics memory model

## Immediate Next Work

1. Keep restoring runner headroom so the helper-family model does not keep
   consuming payload-window budget unchecked.
2. Freeze the first `MATH1` binding shape around explicit function-style calls.
3. Decide the first narrow `MATH1` proof target, preferably `FAbs` or `FSqrt`.
4. Avoid reopening runner-global subsystem logic while the next family lands.
