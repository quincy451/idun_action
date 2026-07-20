# Idun Documentation Map

The Idun fork runs its development tools as Alpine Linux processes and emits
directly runnable C64 PRGs. This index separates the active Idun product
contract from preserved native-UDOS design material.

## Authoritative Product Documents

- `../README.md`: product overview, commands, builds, and verification.
- `active_direction.md`: active code paths and development rules.
- `architecture.md`: Linux tool, OBJ1, linker, and C64 target split.
- `actc_status.md` and `actc.md`: current Linux compiler behavior.
- `alink_status.md`, `linker.md`, and `alink_spec.txt`: current direct-PRG
  linker behavior and object contract.
- `language_guide.md`: supported Action source and target semantics.
- `idun_target_service.md`: the UDOS-free C64 debug/profile agent.
- `operator_guide.md`, `setup_linux.md`, and `alpine_packages.md`: operation,
  installation, and packaging.
- `idun_fork_handoff.md`: reproducible build and validation snapshot.
- `udos_feature_parity.md`: cross-product parity boundary and native work
  order.
- `new_math_func.txt` and `new_gfx_func.txt`: implemented MATH1/GFX1 API and
  validation contracts.

When two Idun documents disagree, the active implementation and tests take
precedence, followed by the documents above.

## Shared Target References

`real32.md`, `reu.md`, `reu_abi.md`, `dbf1.md`, `input1.md`, and the SID/sprite
and graphics notes describe C64-side formats or APIs that can apply to both
products. Shared 6502 modules remain owned by the native ActionC64U checkout
and are synchronized through `resources/shared_6502_manifest.json`, except for
the two documented DBF filesystem adapters.

## Historical Native References

The following files are retained to explain the native C64U/UDOS ancestry;
they are not instructions for building or extending the active Idun product:

- `actc_overlay_pass_plan.md`, `actc_source_streaming_plan.md`, and
  `actc_roadmap.md`;
- `editor_roadmap.md`, `tool_abi_harness.md`, and `runtime_programs_spec.txt`;
- `cpm65_cmdline.md`, `udos_resume.md`, `retired_vm_notes.md`,
  `runtime_runner_removal.md`, and `bytecode.md`;
- native-only portions of `overlays.md`, `release.md`, `setup_wsl.md`, and
  `vice.md`.

The corresponding preserved source under `src/tools_udos/` is formally
retired for this fork. See `retired_udos_tools.md` and
`resources/retired_udos_tools.json` for the replacement inventory. Do not copy
UDOS services, compiler overlays, REU workspace mechanics, or DNP packaging
into the Linux product merely to make implementations look alike.

## Cross-Product Rule

Parity is required for portable Action syntax, public library APIs, OBJ1
meaning, link-selected common 6502 dependencies, and observable direct-PRG
behavior. Linux filesystems, terminal processes, SQLite, sockets, AArch64/APK
packaging, and the Idun target transport are Idun mechanisms. UDOS resident
services, native 6502 tools, compiler overlays, REU compiler storage, and
D64/DNP release media are native mechanisms.
