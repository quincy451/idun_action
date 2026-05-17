# VICE Verification

Current VICE verification boots UDOS, mounts the Action workspace, runs the
UDOS-native tools, and verifies direct PRG output.

Primary gates:

- `make -C ../udos vice-resident`
- `make -C ../udos vice-action-alink`
- `make -C ../udos vice-action-actc-alink-launch`

Expected direct launch proof:

- `ALINK.PRG` writes `BIN/MAIN.PRG`
- UDOS launches that PRG directly
- the probe observes the expected marker/output and returns to the UDOS prompt
