# Program-Owned Overlay Sections

## Active Semantics

ACTC accepts named overlay bodies:

```text
OVERLAY Math
PrintIE(42)
ENDOVERLAY

PROC main()
OverlayCall(Math)
RETURN
```

The compiler stores an overlay body in the same dynamically sized operation
vectors used for procedures. `MAIN` is still emitted at object offset zero,
regardless of source order. Each overlay receives an object export, and
`OverlayCall(name)` emits a local absolute JSR relocation to that export.

ALINK places the overlay code in the generated C64 PRG. The section is owned by
the program, requires no UDOS service, and has no dependency on
`RT_OVL_LOAD.OBJ` or `RT_OVL_CALL.OBJ`.

## Resident Tradeoff

The active implementation is resident rather than dynamically swapped. It
preserves overlay source organization and call behavior, but all referenced
overlay bodies occupy the loaded PRG at once. This is the correct baseline for
the Idun fork because it removes the unavailable runtime host without making
execution depend on disk or cartridge-control behavior that has not been
verified.

A later size optimization can teach ALINK to package overlay payloads and add a
small program-owned C64 loader. That optimization must retain:

- explicit overlay exports and call targets
- relocation of calls made from overlay bodies
- deterministic load addresses and debug sidecar mapping
- no UDOS resident-service calls

The historical name-payload `RT_OVL_*` objects remain excluded from the Idun
export until such a loader exists.
