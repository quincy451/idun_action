# Blockers And External Validation

There is no CP/M-65 or UDOS dependency in the active Idun/Linux build.

The Linux tools, workspace export, compiler/linker pipeline, direct PRG runtime,
fake Idun transport, and assembled resident-service helpers are host-verifiable.
The remaining external validation concerns hardware-facing behavior:

- the implemented Idun socket transport, IRQ run/halt, step, persistent
  breakpoints, and PC sampling need final attached-cartridge checks
- VICE-proven REU/DBF/KERNAL file I/O and host/link-tested graphics, SID,
  sprite, joystick, and mouse helpers need final physical C64 checks

Those hardware checks do not block building or using the Linux developer tools.
