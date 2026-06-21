# ALINK Roadmap

Current target: `ALINK.PRG` owns final direct PRG construction.

Near-term work:

- keep `BIN/<MODULE>.PRG` as the default and only maintained runnable output
- continue widening object graph loading and external symbol closure resolution
- preserve dead-strip behavior while adding runtime helper families
- move optional helpers behind link-time selection
- keep cold linker tables REU-backed instead of growing resident table slabs
- keep generated PRG startup/return behavior deterministic under UDOS
- remove stale compatibility assumptions from docs, probes, and release exports

Proof gates:

- `make -C ../udos vice-action-alink`
- `make -C ../udos vice-action-actc-alink-launch`
- `make -C ../udos vice-action-actc-alink-launch-runtime-matrices`
- `make -C ../udos vice-action-alink-prg-matrix`
- `make -C ../udos vice-action-alink-prg-object-code-matrices`
- shape-specific launch gates for helper-bearing direct PRG output
