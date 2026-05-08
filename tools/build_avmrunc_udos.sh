#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UDOS_DIR="$ROOT_DIR/../udos"
BUILD_DIR="$ROOT_DIR/build/udos_tools"
SRC="$ROOT_DIR/src/tools_udos/avmrun/avmrun.asm"
CFG="$ROOT_DIR/src/tools_udos/avmrun/avmrunc.cfg"
LABELS="$UDOS_DIR/build/udos-resident.labels"
RELEASE_LABELS="$UDOS_DIR/build/release/udos-resident.labels"
INC="$BUILD_DIR/udos_services.inc"
OBJ="$BUILD_DIR/avmrunc.o"
BIN="$BUILD_DIR/avmrunc.bin"
PRG="$BUILD_DIR/AVMRUNC.PRG"
CURRENT_LABELS="$BUILD_DIR/avmrunc.current.labels"
CURRENT_MAP="$BUILD_DIR/avmrunc.current.map"
OVERLAY_BUILD="$ROOT_DIR/tools/build_avmrun_overlay_printreal.sh"
REALOPS_OVERLAY_BUILD="$ROOT_DIR/tools/build_avmrun_overlay_realops.sh"
INTERP_OVERLAY_BUILD="$ROOT_DIR/tools/build_avmrun_overlay_interp.sh"

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
ca65 -g -DALLOW_TEXT_AVM=0 -DAVMRUN_COMPAT=1 -DFILE_BUFFER_ADDR=19264 -o "$OBJ" "$SRC" -I "$BUILD_DIR"
ld65 -C "$CFG" -o "$BIN" "$OBJ" -Ln "$CURRENT_LABELS" -m "$CURRENT_MAP"
cat >> "$CURRENT_LABELS" <<'EOF'
al 003C80 .real_print_low
al 003C82 .real_print_high
al 003C84 .real_print_int
al 003C86 .real_print_rem
al 003C8E .real_print_mask
al 003C96 .real_print_work
al 003C9E .real_print_flag
al 003C9F .real_print_shift
al 003CA0 .real_print_num
al 003CA8 .real_print_sign
al 003CA9 .real_lhs_lo
al 003CAB .real_lhs_hi
al 003CAD .real_rhs_lo
al 003CAF .real_rhs_hi
al 003CB1 .real_result_lo
al 003CB3 .real_result_hi
al 003CB5 .real_lhs_mant
al 003CB9 .real_rhs_mant
al 003CBD .real_lhs_exp
al 003CBE .real_rhs_exp
al 003CBF .real_lhs_sign
al 003CC0 .real_rhs_sign
al 003CC1 .real_align_shift
al 003CC2 .real_flip_rhs_sign
al 003CC3 .payload_end_ptr
al 003CC5 .file_end_ptr
al 003CC7 .real_work_shift
al 003CC8 .real_exp_work
al 003CCA .real_work_a
al 003CD0 .real_work_b
al 003CD6 .real_work_c
al 003CD9 .saved_memcfg
al 003CDA .avm_flags
al 003CDB .native_helper_ready_flags
al 003CDC .native_helper_expected_len
al 003CDE .native_helper_printstd_entry_ptr
al 003CE0 .native_helper_printstd_entry_nl_ptr
al 003CE2 .native_helper_printstd_entry_u16_ptr
al 003CE4 .native_helper_printstd_entry_u16_nl_ptr
al 003CE6 .native_helper_printreal_entry_ptr
al 003CE8 .native_helper_debug_stage
al 003CE9 .native_helper_irq_saved
al 003CEA .native_helper_printreal_char_buffer
al 003CEC .native_helper_printreal_trace_active
al 003CED .native_helper_printreal_char_count
al 003CEE .native_helper_printreal_first_char
al 003CEF .native_helper_printreal_last_char
al 003CF0 .native_helper_printreal_saved_iptr
al 003CF2 .native_helper_printreal_saved_iptr_offset
al 003CF3 .native_helper_printreal_saved_pptr
al 003CF4 .native_helper_printreal_saved_rptr
al 003CF5 .avmrun_overlay_ready
al 003CF6 .avmrun_overlay_requested_kind
al 003CF7 .avmrun_overlay_loaded_kind
al 003CF8 .avmrun_overlay_requested_cmd
al 003CF9 .avmrun_overlay_loaded_len
al 003C00 .filename_buffer
al 003CFB .avmrun_overlay_service_status
al 003CFC .avmrun_overlay_entry_minus_one
al 003CFD .native_helper_sidspr_arg
al 003CFE .dbf_active_handle
al 003C00 .interp_error_ptr
al 003C02 .interp_sp
al 003C03 .interp_rsp
al 003C04 .interp_string_ptr
al 003C06 .interp_stack_lo
al 003C16 .interp_stack_hi
al 003C26 .interp_rstack_lo
al 003C36 .interp_rstack_hi
al 003C46 .avmrun_interp_result
al 003C47 .avmrun_interp_service_kind
al 003C48 .avmrun_interp_service_cmd
al 003C49 .avmrun_interp_resume_state
al 003C4A .avmrun_interp_service_failed
EOF
printf '\x00\x18' > "$PRG"
cat "$BIN" >> "$PRG"
AVMRUN_LABELS="$CURRENT_LABELS" "$OVERLAY_BUILD" >/dev/null
AVMRUN_LABELS="$CURRENT_LABELS" "$REALOPS_OVERLAY_BUILD" >/dev/null
AVMRUN_LABELS="$CURRENT_LABELS" "$INTERP_OVERLAY_BUILD" >/dev/null
printf '%s\n' "$PRG"
