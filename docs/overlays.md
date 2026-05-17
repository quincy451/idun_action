# Overlay Direction

Overlay-style implementation remains useful for tool internals, but normal
linked programs should not rely on a separate runtime host.

For final programs, ALINK should either place required helper code directly in
the PRG or generate an explicitly program-owned linked payload.
