# Specification

Current product specification:

- Linux C++ build/workspace tools on the Idun cartridge
- object output from Linux `actc`
- direct C64 PRG output from Linux `alink`
- link-selected runtime helper modules
- launch of the resulting `.PRG` on the Commodore through Idun

The maintained product does not require UDOS or a separate generic runtime
program. Unsupported Action forms must produce a compiler diagnostic rather
than a partially generated object.
