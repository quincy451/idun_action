# ALINK Status

Current state:

- `ALINK.PRG` builds as a UDOS-native tool.
- The default live output is `BIN/<MODULE>.PRG`.
- `ALINK MAIN` is verified by `make -C ../udos vice-action-alink`.
- The higher-level `ACTC.PRG -> ALINK.PRG -> BIN/MAIN.PRG` launch path is
  verified by `make -C ../udos vice-action-actc-alink-launch`.
- Broad direct-PRG object/link coverage is verified by
  `make -C ../udos vice-action-alink-prg-matrix`.
- The linker-owned direct PRG include is `src/tools_udos/alink/direct_prg.inc`.

Current focus:

- continue widening object closure resolution
- keep direct PRG layout deterministic
- move optional helper families into link-selected modules
- keep stale runner assumptions out of tests, release images, and docs
