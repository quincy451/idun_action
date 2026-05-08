#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UDOS_DIR="$ROOT_DIR/../udos"
BUILD_DIR="$ROOT_DIR/build/udos_tools"
SRC="$ROOT_DIR/src/tools_udos/avmrun/avmrun.asm"
CFG="$ROOT_DIR/src/tools_udos/avmrun/avmrun.cfg"
LABELS="$UDOS_DIR/build/udos-resident.labels"
RELEASE_LABELS="$UDOS_DIR/build/release/udos-resident.labels"
INC="$BUILD_DIR/udos_services.inc"
OBJ="$BUILD_DIR/avmrun.o"
BIN="$BUILD_DIR/avmrun.bin"
PRG="$BUILD_DIR/AVMRUN.PRG"
CURRENT_LABELS="$BUILD_DIR/avmrun.current.labels"
CURRENT_MAP="$BUILD_DIR/avmrun.current.map"
NATIVE_PRINTREAL_BUILD="$ROOT_DIR/tools/build_avmrun_native_helper_printreal.sh"
NATIVE_PRINTSTD_BUILD="$ROOT_DIR/tools/build_avmrun_native_helper_printstd.sh"
NATIVE_GFX_BUILD="$ROOT_DIR/tools/build_avmrun_native_helper_gfx.sh"
NATIVE_SIDSPR_BUILD="$ROOT_DIR/tools/build_avmrun_native_helper_sidspr.sh"
NATIVE_DBF_BUILD="$ROOT_DIR/tools/build_avmrun_native_helper_dbf.sh"
NATIVE_MATH_BUILD="$ROOT_DIR/tools/build_avmrun_native_helper_math.sh"
COMPAT_BUILD="$ROOT_DIR/tools/build_avmrunc_udos.sh"

mkdir -p "$BUILD_DIR"

if [[ -n "${UDOS_LABELS:-}" ]]; then
  LABELS="$UDOS_LABELS"
elif [[ -f "$RELEASE_LABELS" ]]; then
  LABELS="$RELEASE_LABELS"
elif [[ ! -f "$LABELS" ]]; then
  make -C "$UDOS_DIR" resident >/dev/null
fi

python3 "$ROOT_DIR/tools/generate_udos_service_inc.py" --labels "$LABELS" --output "$INC"

cd "$ROOT_DIR"
ca65 -g -DALLOW_TEXT_AVM=0 -DAVMRUN_COMPAT=0 -o "$OBJ" "$SRC" -I "$BUILD_DIR"
ld65 -C "$CFG" -o "$BIN" "$OBJ" -Ln "$CURRENT_LABELS" -m "$CURRENT_MAP"
cat >> "$CURRENT_LABELS" <<'EOF'
al 003AC0 .real_print_low
al 003AC2 .real_print_high
al 003AC4 .real_print_int
al 003AC6 .real_print_rem
al 003ACE .real_print_mask
al 003AD6 .real_print_work
al 003ADE .real_print_flag
al 003ADF .real_print_shift
al 003AE0 .real_print_num
al 003AE8 .real_print_sign
al 003AE9 .payload_end_ptr
al 003AEB .file_end_ptr
al 003AED .saved_memcfg
al 003AEE .avm_flags
al 003AEF .native_helper_ready_flags
al 003AF0 .native_helper_expected_len
al 003AF2 .native_helper_printstd_entry_ptr
al 003AF4 .native_helper_printstd_entry_nl_ptr
al 003AF6 .native_helper_printstd_entry_u16_ptr
al 003AF8 .native_helper_printstd_entry_u16_nl_ptr
al 003AFA .native_helper_printreal_entry_ptr
al 003AFC .native_helper_debug_stage
al 003AFD .native_helper_irq_saved
al 003AFE .native_helper_printreal_char_buffer
al 003B00 .native_helper_printreal_trace_active
al 003B01 .native_helper_printreal_char_count
al 003B02 .native_helper_printreal_first_char
al 003B03 .native_helper_printreal_last_char
al 003B04 .native_helper_printreal_saved_iptr
al 003B06 .native_helper_printreal_saved_iptr_offset
al 003B07 .native_helper_printreal_saved_pptr
al 003B08 .native_helper_printreal_saved_rptr
al 003B09 .native_helper_jsr_entry_minus_one
al 003B0A .dbf_active_handle
al 0039C0 .filename_buffer
al 0039C0 .interp_error_ptr
al 0039C2 .interp_sp
al 0039C3 .interp_rsp
al 0039C4 .interp_string_ptr
al 0039C6 .interp_stack_lo
al 0039D6 .interp_stack_hi
al 0039E6 .interp_rstack_lo
al 0039F6 .interp_rstack_hi
al 003A06 .avmrun_interp_result
al 003A07 .avmrun_interp_service_kind
al 003A08 .avmrun_interp_service_cmd
al 003A09 .avmrun_interp_resume_state
al 003A0A .avmrun_interp_service_failed
EOF
printf '\x00\x18' > "$PRG"
cat "$BIN" >> "$PRG"
AVMRUN_LABELS="$CURRENT_LABELS" "$NATIVE_PRINTREAL_BUILD" >/dev/null
AVMRUN_LABELS="$CURRENT_LABELS" "$NATIVE_PRINTSTD_BUILD" >/dev/null
"$NATIVE_GFX_BUILD" >/dev/null
"$NATIVE_SIDSPR_BUILD" >/dev/null
"$NATIVE_DBF_BUILD" >/dev/null
"$NATIVE_MATH_BUILD" >/dev/null
env -u AVMRUN_LABELS "$COMPAT_BUILD" >/dev/null
printf '%s\n' "$PRG"
