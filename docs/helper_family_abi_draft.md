# Helper Family ABI Draft

Optional feature families must be selected by ALINK and owned by the final PRG.

Design rules:

- helpers are link-time inputs, not permanent runner-global services
- unused helper families must not appear in helper-free PRG output
- helper entry points and state blocks must be explicit linker-visible symbols
- generated PRG startup code must initialize any selected helper state before use
- helpers must return through normal linked-program control flow

Candidate families:

- standard printing
- REAL math and conversion
- graphics/resource helpers
- SID/sprite helpers
- DBF-style database helpers
- TCP/network helpers
- 80-column helpers

ALINK contract:

- detect helper imports from reachable code
- include only the needed helper modules
- resolve helper entry points to final PRG addresses
- place helper state in the linked image or documented runtime workspace
- fail the link if a required helper cannot be resolved
