# ACTC

`ACTC.PRG` is the UDOS-native compiler front end.

Current contract:

- input: `SRC/<MODULE>.ACT`
- output: `OBJ/<MODULE>.OBJ`
- object format: text object records consumed by `ALINK.PRG`
- runtime policy: emit object-level calls/imports only; final runtime selection
  belongs to `ALINK.PRG`

`ACTC.PRG` should not emit a standalone runtime artifact and should not depend
on a separate launch program. The direct runtime product is created by ALINK.
