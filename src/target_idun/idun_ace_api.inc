; Minimal Idun/ACE declarations used by the Action target service.
;
; Derived from idun-project/idun-cartridge cbm/sys/acehead.asm and
; cbm/idun-io.asm (MIT License, Copyright 2023 Brian Holdsworth).

aceStatB       = $0f00
aceArgc        = aceStatB + 4
aceArgv        = aceStatB + 6
aceCallB       = $1303
open           = aceCallB + 0
aceProcExit    = aceCallB + 153
aceToolAddress = $6d00
lftable        = $0fb0

aceID1 = $cb
aceID2 = $06
aceID3 = 16

idDataport = $de00
idRxBufLen = $de01
turboOff   = $d07a
turboOn    = $d07b

zp = $f8
zw = $fa
mp = $fc
