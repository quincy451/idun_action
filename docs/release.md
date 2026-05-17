# Release

The current release image is UDOS-native.

Release contents should include:

- UDOS boot/resident files
- `ACTC.PRG`
- `ALINK.PRG`
- supported workspace/project helper tools
- direct PRG-oriented samples and library objects

Release verification should prove that the exported Action workspace does not
ship obsolete runtime-runner artifacts and that direct PRG launch gates remain
green under VICE.
