# Runtime Runner Removal Status

The old runtime-runner direction has been retired.

Current rule:

- `ALINK.PRG` emits the final `BIN/<MODULE>.PRG`.
- The linked PRG is the program that runs.
- Runtime helpers are selected and placed by ALINK.
- No separate generic runtime program is part of the maintained launch path.

This replaces the older plan of slimming a separate runner. There is no runner
to diet in the active product path; the remaining work belongs in direct PRG
linking, runtime helper selection, and launch verification.

Implementation expectations:

- Do not reintroduce a runtime-runner command.
- Do not add new instruction-stream runtime features.
- Put optional helper families behind link-time selection.
- Keep `ACTC.PRG -> ALINK.PRG -> BIN/MAIN.PRG` green under UDOS/VICE.
