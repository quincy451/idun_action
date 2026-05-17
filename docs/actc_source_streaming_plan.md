# ACTC Source Streaming Plan

Date: 2026-04-22

## Goal

`ACTC.PRG` must eventually compile source files that are much larger than RAM,
up to the usable REU-backed workspace. The practical ceiling is the 16 MiB DNP
image size minus REU space already reserved by UDOS/runtime services, not an
arbitrary 256 KiB source cap.

The current compiler only partially does this. It stages source into REU and can
refill `source_buffer` as direct scans advance, so it can now compile a narrow
line-oriented proof where the `PROC MAIN` name, a `PrintE` string literal, or
long inline spaces before a `PrintIE` literal cross the first 20 KiB window
boundary. It also has the first expression proof where a long `PrintIE(...)`
expression and a long variable symbol cross the same boundary, the first boolean
pre-scan proof where `AND` appears beyond an 8-bit `Y` wrap, and the first
parameter-list punctuation proof where `(` appears at `Y=$FF`. It still
performs several full-source scans and still uses raw
`(scan_ptr),y` lookahead, so long tokens or long lines beyond the bounded
lookahead are not yet a supported general parser model.

## Required File ABI Work

The existing `svc_file_load_sc0` service is an all-or-limit loader. It can prove
larger contiguous loads, but it cannot stream a file in chunks or resume from an
offset. ACTC source streaming needs one of these UDOS/tool ABI additions:

- preferred: `svc_file_read_begin_sc0`, `svc_file_read_chunk_sc0`, and
  `svc_file_read_close_sc0`
- acceptable: an extended load service with explicit 32-bit file offset,
  destination pointer, and requested byte count

The chunk API is the better shape because it also maps cleanly to future linker
object streaming and runtime file I/O.

## Preferred Source Cache

The preferred large-source design is not repeated file I/O for every compiler
pass. ACTC should read each source file once through the chunked file-read ABI
and stage it into REU-backed source blocks. Later compiler passes should page
small windows from that REU cache into normal RAM.

This gives the compiler random or repeated sequential access to source text
without keeping the whole source in C64 RAM and without rereading a large file
from the filesystem for every pass.

The current production ACTC build uses `ACTC_REU_SOURCE_CACHE=1`. It stages
`SRC/<MODULE>.ACT` at REU base `$010000`, pages up to `SOURCE_LIMIT` bytes back
into `source_buffer`, loads an additional `SOURCE_LOOKAHEAD=255` bytes for
bounded direct lookahead, and refills the window when the scanner reaches the
window end. This is not the final parser architecture yet. The production UDOS
resident now exports the matching REU stage/read service entries, while the
automated proof uses the host harness' simulated REU.

The current refill hook is pointer based, not token based. It is enough for
line-oriented source where keywords, identifiers, strings, and expressions fit
inside the current window plus bounded lookahead. The next correctness step is a
real `SourceReader` that owns lookahead and carry buffers for longer tokens or
line endings that cross a window boundary.

The first helper beyond raw pointer refill is
`source_reader_commit_256_from_scan_ptr`, used when 8-bit `Y` lookahead wraps.
`skip_inline_spaces_at_scan_y` uses it directly through `advance_scan_y`, and
the first expression parser paths now use the same helper while preserving
parser registers across the REU read service. That prevents long runs of spaces
and the current long-expression proof from silently wrapping to the beginning of
the same scan window. Boolean pre-scan wraps now intentionally route into the
boolean parser instead of continuing from `Y=0` in the same window, and
speculative expression pre-scans now mark and restore the active REU source
window before returning to the real parse. Failed boolean keyword probes use the
same mark/restore path, so speculative parsing cannot leave the reader pointed
at the wrong window before the normal expression parser resumes. Assignment
parsing now also preserves the `=` operator position across variable lookup and
uses `advance_scan_y` for assignment punctuation, so long inline spaces before
`=` can cross an 8-bit `Y` wrap without parsing the right-hand side from the
wrong offset. Procedure parameter parsing now has the same first proof for an
opening `(` at `Y=$FF`. Runtime and constant group-speculation paths also keep
their own reader mark, so `(expr)` can be reparsed as a comparison left-hand side
after the speculative group parse crosses into another REU source window.

The source cache should track:

- source file identity and length
- 32-bit source offset
- REU base block/page for the file
- dirty flag, initially false because source text is read-only during compile
- small RAM page buffer and current cached offset

The first implementation can support one active source module. A later version
can cache multiple project modules so cross-module compile or whole-project
analysis does not repeatedly hit the filesystem.

## REU Service Shape

The current source-cache path uses two small service calls that match the
compiler's immediate need:

`svc_file_stage_reu_sc0`

- input: `X` points at a parameter block
- `+0/+1`: zero-terminated source path pointer
- `+2/+3/+4`: 24-bit REU destination base, little-endian
- output `+5`: `tool_file_status_*`
- output `+6/+7/+8`: 24-bit staged byte count

`svc_reu_read_sc0`

- input: `X` points at a parameter block
- `+0/+1/+2`: 24-bit REU source address, little-endian
- `+3/+4`: C64 destination pointer
- `+5/+6`: byte count
- output `+7`: `tool_file_status_*`

This is enough to prove one-time file staging plus RAM-window paging. Later
resident work can either keep this shape or replace staging with chunked file
read services that ACTC uses to fill REU blocks itself. A future
`svc_reu_write_sc0` is the matching primitive for moving compiler/linker table
payloads from RAM staging buffers into REU. ACTC now uses this path for
unresolved external names, procedure `body_ops`, string literals, variable
names, export names, integer literals, variable metadata, procedure metadata,
layout metadata, and string offsets.

## REU Lookup Tables

The same REU strategy should be used for compiler and linker lookup data once
source paging is proven.

ACTC candidates:

- symbol-name strings
- export/procedure tables
- variable metadata
- literal pools
- body-op streams
- source line index checkpoints for diagnostics and multi-pass seeking

Current ACTC table status:

- unresolved external names live in REU behind a 25-byte resident window
- procedure `body_ops` live in REU behind one `BODY_OPS_STRIDE` resident window
- string literals live in REU behind a 24-byte resident window
- variable names and export names live in REU behind 25-byte resident windows
- integer literals live in REU behind a 2-byte resident window
- variable metadata lives in REU behind a 3-byte resident window
- procedure parameter/local metadata lives in REU behind a 4-byte resident window
- procedure layout metadata lives in REU behind a 4-byte resident window
- string offsets live in REU behind a 1-byte resident window
- linker-side queues are still resident

ALINK candidates:

- loaded object directory
- external/pending symbol queues
- export lookup tables
- object body-op streams
- string and integer literal pools
- final map/debug records

The rule should be: keep hot fixed-width indexes and the current working set in
normal RAM, but place large variable-length data and cold lookup payloads in REU.
That avoids spending scarce C64 RAM on tables that are not touched every opcode
or parser step.

## Compiler Architecture Change

The replacement for `source_buffer` should be a `SourceReader` abstraction:

- fixed-size source window, initially 512 or 1024 bytes
- current pointer, remaining bytes, EOF flag, line number, and column number
- one-token lookahead for the parser
- carry buffer for tokens that cross a chunk boundary, especially identifiers,
  string literals, comments, and CR/LF pairs

The parser should stop walking raw memory directly. Instead it should ask the
reader for tokens. That makes source size independent of available contiguous
RAM.

## Pass Structure

A practical low-risk design is two streaming passes:

1. Pass 1 validates the module header, collects module variables, procedure
   headers, export names, parameter/local declarations, and enough metadata for
   calls and storage layout.
2. Pass 2 seeks within the REU source cache and emits body operations, literal
   tables, runtime imports, and object content.

Two passes avoid holding the full source in memory while preserving the current
compiler behavior, which depends on knowing procedure/export metadata before
final body emission.

## Object Output

Production ACTC no longer builds the complete object text in `content_buffer`.
With `STREAM_OUTPUT=1`, object emission mirrors production ALINK's streamed
output path:

- begin output for `OBJ/<MODULE>.OBJ`
- write header/import/export sections as they are finalized
- write body/literal sections from bounded staging buffers
- close output

The focused capacity proof emits an `OBJ/MAIN.OBJ` larger than the legacy
`640` byte object buffer through write begin/chunk/close services. Remaining
object-output capacity work is now about moving the compiler's source metadata,
literal pools, symbol tables, and body-op storage out of fixed normal-RAM arrays.
Most ACTC cold metadata has now moved to REU; the remaining capacity work is the
token-safe reader, the pass-overlay driver, and similar REU table pressure in
ALINK.

## Implementation Milestones

1. Raise the current production proof while there is still safe tool-window
   space. Current production `ACTC.PRG` uses `ACTC_REU_SOURCE_CACHE=1`,
   `SOURCE_LIMIT=20480`, and proves a `49152` byte source compile with
   `PROC MAIN()` discovered near offset `49120` through REU source staging.
2. Add and prove the tool ABI REU source-cache service shape under the harness.
   Current proof stages source beyond the first `20480` bytes into simulated REU
   and pages later windows back into RAM with a 255-byte lookahead guard.
3. Implement production resident-side REU staging, read, and write services.
   Current resident ABI exports `svc_file_stage_reu_sc0`, `svc_reu_read_sc0`,
   and `svc_reu_write_sc0`; target-side stress proof is still pending.
4. Add a REU source-cache loader that copies a source file into REU blocks once.
5. Add the first ACTC scanner refill hook that pages fixed RAM windows from the
   REU cache.
6. Move whitespace/comment scanning and symbol/string reading behind a
   token-boundary-safe source reader.
7. Convert module-header and declaration collection to REU-backed pass 1.
8. Convert body operation collection and runtime-import detection to REU-backed
   pass 2.
9. Convert object emission from `content_buffer` to chunked write services.
   Current production `ACTC.PRG` has this path with `STREAM_OUTPUT=1`,
   `CONTENT_BUFFER_SIZE=16`, and `OUTPUT_CHUNK_SIZE=128`.
10. Move large ACTC and ALINK lookup payloads into REU-backed tables. Most ACTC
    cold lookup payloads are now REU-backed; ALINK queues remain.
11. Add synthetic large-source proofs at 64 KiB, 128 KiB, 256 KiB, 1 MiB, and
    then up toward the 16 MiB-minus-reserved-REU ceiling.

## Current Status

The current production compiler now stages source through REU, refills the scan
window as the raw pointer advances, keeps 255 bytes of bounded lookahead, and
streams object output. It is useful for proving source, symbols, long inline
spaces, one long expression, one boolean pre-scan wrap, one assignment operator
wrap, one procedure parameter delimiter wrap, and group-speculation restore
across the first 20 KiB boundary, plus objects beyond the old RAM output buffer
and REU-backed compiler metadata tables, but it is not the final architecture
for large Action programs.
The next
compiler-capacity breakthrough is the parser refactor described here: replace
direct `source_buffer` lookahead with a token-boundary safe `SourceReader`.
