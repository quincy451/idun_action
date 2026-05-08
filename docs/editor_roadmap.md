# `ACTEDIT` Source Editor Roadmap

Current as of `2026-04-25`.

This document defines the intended UDOS-native source editor for Action
projects.

The editor is not a minor convenience. It is a core development tool, and it
must be designed around:

- large source files
- REU-backed storage
- 40-column screen limits
- integration with compile/build/debug flows

## Goal

Provide a real full-screen source editor for Action project files with:

- vertical scrolling
- horizontal scrolling
- insert/delete editing
- mark/copy/cut/paste/delete block operations
- load/save
- goto line
- find/replace
- project integration

Planned tool:

- `ACTEDIT.PRG`

## Current Baseline

Today the repo has:

- `ACTSRC.PRG` for manifest/source listing
- `ACTFILE.PRG` for source viewing/printing
- `ACTMON.PRG` for project-front-end dispatch
- `ACTEDIT.PRG` as a first REU-backed full-screen editor bootstrap slice

So today the project can inspect and make narrow interactive edits to sources
in a real full-screen tool, but it is still well short of the intended final
editor.

Current `ACTEDIT` bootstrap behavior:

- accepts `ACTEDIT <NAME>` and resolves `SRC/<NAME>.ACT`
- accepts `ACTEDIT SRC/<NAME>.ACT`
- stages the source file into REU
- renders a full-screen source view
- supports cursor-up/cursor-down line browsing
- uses left/right as an edit cursor with horizontal scroll
- supports typed character insertion on the current line
- supports delete-left editing on the current line
- supports `RETURN` line split and delete-at-column-0 line join
- supports logical-line mark/copy/cut/paste/delete with:
  - `F3` mark anchor
  - `F5` copy selection
  - `F6` cut selection
  - `F7` paste clipboard
  - `DELETE` delete selection without replacing the clipboard
- supports search/navigation helpers:
  - `F2` find next current token or current-line marked selection
  - `F4` find previous current token or current-line marked selection
- supports prompt-driven helpers:
  - `G` goto line
  - `R` replace next match for the current token or current-line marked
    selection
- supports non-text navigation helpers:
  - `HOME` line home, then file top when already at column `0`
  - `INS` line end, then file bottom when already at line end
  - `CLR/HOME` page up
  - `F8` page down
- supports a small REU-backed undo/redo journal:
  - `U` walks backward through the last few mutating edit states
  - `Y` walks forward through the currently redoable edit states
  - current bootstrap depth is `8`
- keeps dirty state
- preserves edited lines plus limited inserted/deleted line structure through a
  logical-line model whose patch/insert/delete descriptor tables live in
  REU-backed metadata windows, whose patch/insert line payload text lives in
  an append-only REU add buffer behind a shared resident edit-text window, and
  whose visible line loads now rebuild through a small resident piece window
  over that REU-backed state
- saves back to the source file with `F1` through streamed UDOS writes
- supports clean quit back to UDOS with `RUN/STOP`

Current `ACTEDIT` bootstrap footprint:

- `ACTEDIT.PRG`: `11973`
- resident span: `$0900-$37C2`
- resident `CODE`: `$2EC3`
- resident `ZPTEMP`: `$001B`

Current `ACTEDIT` bootstrap limits:

- still lacks a true REU-backed piece-table document core
- still rebuilds the visible piece window from the logical-line descriptor
  model rather than keeping a full persistent piece-descriptor table over
  original-file and add-buffer spans
- still lacks a much deeper undo/redo journal than the current `8`-entry ring

## Core Decision

The editor must be REU-backed from the start.

A plain in-RAM whole-file editor will fail too early and then force a rewrite.
That is the wrong path.

The editor should treat normal RAM as:

- screen/view state
- cursor state
- command state
- small working caches

And treat REU as:

- original file store
- appended edit store
- piece descriptors
- copy/paste buffer
- optional undo records

## Buffer Model

Planned document model: REU-backed piece table.

Why this is the right fit:

- original file stays immutable in REU
- inserted text appends to a second REU region
- the visible document is a sequence of pieces
- cut/copy/paste become descriptor edits instead of whole-file shifts
- save is a streaming walk over the piece list
- large-file support becomes practical

Planned REU regions:

- original file data
- add buffer
- piece descriptor table
- copy buffer
- optional undo journal

Planned resident RAM data:

- current piece/cache window
- current line index cache
- viewport render buffer
- status line state
- key-command state

## View Model

The editor is full-screen, not line-at-a-time shell editing.

Planned screen use on a 40x25 display:

- top status row
  - file/module name
  - dirty flag
  - mode
  - line/column
  - left-column offset
- main text viewport
  - the visible source window
- bottom command/message row
  - prompts
  - errors
  - search/replace input

Horizontal scrolling is required, not optional.

That means the editor tracks:

- current line
- current column
- top visible line
- left visible column

## Command Surface

The exact key map can change later. The command set should not.

Required first-class operations:

- cursor up/down/left/right
- page up/page down
- line home/end
- file home/end
- scroll left/right
- insert character
- delete character
- backspace
- split line
- join line
- mark start/end
- copy block
- cut block
- delete block
- paste block
- save
- quit
- goto line
- find
- replace

Useful later additions:

- single-line undo, then multi-step undo
- duplicate line/block
- comment/uncomment block
- compile/build/debug current module

## File Model

The editor should work directly with project source files:

- `SRC/<NAME>.ACT`

Planned entry paths:

- `ACTEDIT <NAME>`
- `ACTEDIT SRC/<NAME>.ACT`
- `ACTMON EDIT <NAME>`

Save should stream directly through the existing UDOS file-save services.

This should reuse the project/file helper layer already used by:

- `ACT2SAVE`
- `ACTFILE`
- `ACTSRC`
- `ACTMON`

## Large File Direction

The editor must not assume source files fit in plain C64 RAM.

Planned large-file strategy:

- load file into REU
- build piece table and line index from REU-backed source
- keep only a small render/index working set resident
- scroll and edit against that working set

This is consistent with the compiler direction already chosen:

- large source and metadata live in REU
- resident RAM holds only the active working window

## Copy Buffer

Block operations require a real copy buffer, not only line delete/paste.

Planned copy buffer behavior:

- block copy writes into REU-backed copy storage
- block cut edits the piece table and also fills that copy storage
- paste inserts a new piece sequence referencing copy-buffer data

This avoids repeated whole-document moves.

## Search / Replace

Search and replace should also be REU-aware.

Planned bootstrap behavior:

- literal ASCII search first
- forward search first
- replace current / replace all later

Regex-style search is not a goal.

## Integration With Compiler And Debugger

The editor should become the place where project work starts.

Planned later integration:

- compile current module
- build current module
- debug current module
- jump to error line after compile failure
- jump to current line from debugger

That means `ACTEDIT`, `ACTC`, `ALINK`, and `ACTDBG` should share the same
module/path conventions.

## Relationship To The Old ACTION! Editor

The old ACTION! editor is a useful behavioral reference, not a strict
compatibility target.

Good features worth keeping in spirit:

- horizontal scrolling
- block copy/delete/paste
- goto file top/end
- find/replace
- monitor/editor handoff

What matters is matching the capability set, not reproducing every historic
key binding exactly.

## Planned Phases

### Phase 1

- `ACTEDIT.PRG` exists
- load one source file
- cursor movement
- vertical scrolling
- horizontal scrolling
- quit cleanly back to UDOS
- REU-backed source staging
- insert/delete/backspace
- dirty-state tracking
- streamed save
- still pending in this phase:
  - split/join line

### Phase 2

- mark/copy/cut/delete/paste block operations
- goto line
- find
- replace current
- simple copy buffer persistence during one session

### Phase 3

- multi-step undo
- replace all
- compile/build hooks
- debugger handoff
- project-aware open/create flows through `ACTMON`

## Practical Next Implementation Steps

1. replace the current logical-line descriptor rebuild path with the full
   persistent REU-backed piece-table core
2. deepen undo/redo beyond the current `8`-entry journal
3. add richer project/debugger handoff through `ACTMON`
