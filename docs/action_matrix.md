# ActionC64U Matrix

| Area | Current Status | Proof |
| --- | --- | --- |
| UDOS resident | Native 6502 shell/resident path | `make -C ../udos resident` and VICE resident gates |
| ACTC compiler | Emits linker objects | `make -C ../udos vice-action-actc` |
| ALINK linker | Emits direct `BIN/<MODULE>.PRG` | `make -C ../udos vice-action-alink` |
| Compile/link/launch | Direct PRG launch under UDOS | `make -C ../udos vice-action-actc-alink-launch` |
| Runtime helpers | Link-selected modules owned by final PRG | shape-specific direct launch probes |
| Release export | Ships UDOS-native tools and PRG-oriented samples | `python3 -m unittest udos.tests.test_release_fs` |

Removed direction:

- CP/M-era runner flow
- separate generic runtime launch program
- instruction-stream runtime product as the maintained linker output

Next work:

- widen ACTC source coverage
- widen ALINK dependency closure and helper selection
- keep final output as direct PRG
