# Source Debugger Roadmap

The old debugger plan was tied to a separate runtime host. The active direction
needs a debugger model that works with direct linked PRG output.

Current direction:

- keep debug metadata as linker-emitted sidecar data or embedded debug sections
- let ALINK map source/procedure metadata to final PRG addresses
- avoid requiring a separate program runner for normal execution
- design breakpoints and stepping around native 6502 code and linked helper
  modules

Open work:

- define a direct-PRG debug map format
- decide whether debugger support is external, resident-assisted, or built as a
  separate debug build mode
- keep normal release PRG output free of debug-only payload unless requested
