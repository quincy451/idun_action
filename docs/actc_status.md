# ACTC Status

Current state:

- UDOS-native `ACTC.PRG` builds successfully.
- The maintained compiler output is `OBJ/<MODULE>.OBJ`.
- The active end-to-end proof is direct PRG launch through ALINK.
- ACTC now emits real `m` machine-code records for the empty `MAIN` return
  case and the first no-data local-call graph slices (`single_call`, `fanout`).
- Legacy runner-oriented compiler paths have been removed from the maintained
  source tree.

Current focus:

- widen source coverage
- keep object metadata stable for ALINK
- move large compiler working sets toward REU-backed streaming
- keep `ACTC.PRG -> ALINK.PRG -> BIN/MAIN.PRG` green under UDOS/VICE
