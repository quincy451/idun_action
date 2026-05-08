.include "udos_services.inc"
.include "actdbg_overlay_abi.inc"
.include "actdbg_overlay_resident.inc"

.export actdbg_overlay_header
.export actdbg_overlay_entry
.export actdbg_overlay_end

SCREEN_COLS = 40
SCREEN_ROWS = 25
VIEW_OUTPUT = 1
INTERP_STACK_MAX = 16
BREAKPOINT_MAX = 4
MODULE_LIMIT = 31
ACTDBG_AVM_REU_BASE_LO = $00
ACTDBG_AVM_REU_BASE_HI = $00
ACTDBG_AVM_REU_BASE_BANK = $00

OPCODE_PUSH8 = $10
OPCODE_PUSH16 = $11
OPCODE_STORE = $12
OPCODE_LOAD = $13
OPCODE_ADD = $14
OPCODE_SUB = $15
OPCODE_EQ = $16
OPCODE_NE = $17
OPCODE_JZ = $18
OPCODE_JMP = $19
OPCODE_DUP = $1A
OPCODE_DROP = $1B
OPCODE_LT = $1C
OPCODE_GT = $1D
OPCODE_BAND = $1E
OPCODE_BOR = $1F
OPCODE_BXOR = $20
OPCODE_SHL1 = $21
OPCODE_SHR1 = $22
OPCODE_CALL = $45
OPCODE_RET = $48
OPCODE_CALLN = $49
OPCODE_SETP16 = $61

INTRINSIC_PRINT = $FF00
INTRINSIC_PRINTE = $FF10
INTRINSIC_EXIT = $FF20
INTRINSIC_PRINTI = $FF30
INTRINSIC_PRINTIE = $FF31

.segment "CODE"

actdbg_overlay_header:
    .byte 'D','G','O','V'
    .byte ACTDBG_OVERLAY_ABI_VERSION
    .word ACTDBG_OVERLAY_EXEC_BASE
    .word actdbg_overlay_entry
    .word actdbg_overlay_end - actdbg_overlay_header
    .word $0000

svc_retptr = ACTDBG_RES_svc_retptr
file_params = ACTDBG_RES_file_params
scan_ptr = ACTDBG_RES_scan_ptr
const_ptr = ACTDBG_RES_const_ptr
base_ptr = ACTDBG_RES_base_ptr
text_ptr = ACTDBG_RES_text_ptr
row_ptr = ACTDBG_RES_row_ptr
line_start_ptr = ACTDBG_RES_line_start_ptr
status_ptr = ACTDBG_RES_status_ptr
word_tmp = ACTDBG_RES_word_tmp
digit_flag = ACTDBG_RES_digit_flag
hex_tmp = ACTDBG_RES_hex_tmp
actdbg_best_proc_found = ACTDBG_RES_actdbg_best_proc_found
actdbg_best_proc_pc_lo = ACTDBG_RES_actdbg_best_proc_pc_lo
actdbg_best_proc_pc_hi = ACTDBG_RES_actdbg_best_proc_pc_hi
actdbg_best_line_found = ACTDBG_RES_actdbg_best_line_found
actdbg_best_line_pc_lo = ACTDBG_RES_actdbg_best_line_pc_lo
actdbg_best_line_pc_hi = ACTDBG_RES_actdbg_best_line_pc_hi
actdbg_dbg_candidate_module_lo = ACTDBG_RES_actdbg_dbg_candidate_module_lo
actdbg_dbg_candidate_module_hi = ACTDBG_RES_actdbg_dbg_candidate_module_hi
actdbg_dbg_candidate_export_lo = ACTDBG_RES_actdbg_dbg_candidate_export_lo
actdbg_dbg_candidate_export_hi = ACTDBG_RES_actdbg_dbg_candidate_export_hi
actdbg_dbg_candidate_pc_lo = ACTDBG_RES_actdbg_dbg_candidate_pc_lo
actdbg_dbg_candidate_pc_hi = ACTDBG_RES_actdbg_dbg_candidate_pc_hi
actdbg_dbg_candidate_file_lo = ACTDBG_RES_actdbg_dbg_candidate_file_lo
actdbg_dbg_candidate_file_hi = ACTDBG_RES_actdbg_dbg_candidate_file_hi
actdbg_dbg_candidate_line_lo = ACTDBG_RES_actdbg_dbg_candidate_line_lo
actdbg_dbg_candidate_line_hi = ACTDBG_RES_actdbg_dbg_candidate_line_hi
actdbg_dbg_candidate_col = ACTDBG_RES_actdbg_dbg_candidate_col
actdbg_target_module_lo = ACTDBG_RES_actdbg_target_module_lo
actdbg_target_module_hi = ACTDBG_RES_actdbg_target_module_hi
actdbg_target_export_lo = ACTDBG_RES_actdbg_target_export_lo
actdbg_target_export_hi = ACTDBG_RES_actdbg_target_export_hi
actdbg_target_file_lo = ACTDBG_RES_actdbg_target_file_lo
actdbg_target_file_hi = ACTDBG_RES_actdbg_target_file_hi
actdbg_target_line_lo = ACTDBG_RES_actdbg_target_line_lo
actdbg_target_line_hi = ACTDBG_RES_actdbg_target_line_hi
actdbg_target_col = ACTDBG_RES_actdbg_target_col
actdbg_cursor_module_lo = ACTDBG_RES_actdbg_cursor_module_lo
actdbg_cursor_module_hi = ACTDBG_RES_actdbg_cursor_module_hi
actdbg_cursor_file_lo = ACTDBG_RES_actdbg_cursor_file_lo
actdbg_cursor_file_hi = ACTDBG_RES_actdbg_cursor_file_hi
actdbg_cursor_line_lo = ACTDBG_RES_actdbg_cursor_line_lo
actdbg_cursor_line_hi = ACTDBG_RES_actdbg_cursor_line_hi
actdbg_cursor_col = ACTDBG_RES_actdbg_cursor_col
actdbg_source_col_offset = ACTDBG_RES_actdbg_source_col_offset
actdbg_break_lookup_found = ACTDBG_RES_actdbg_break_lookup_found
actdbg_break_lookup_pc_lo = ACTDBG_RES_actdbg_break_lookup_pc_lo
actdbg_break_lookup_pc_hi = ACTDBG_RES_actdbg_break_lookup_pc_hi
actdbg_break_active = ACTDBG_RES_actdbg_break_active
actdbg_break_pc_lo = ACTDBG_RES_actdbg_break_pc_lo
actdbg_break_pc_hi = ACTDBG_RES_actdbg_break_pc_hi
actdbg_proc_name = ACTDBG_RES_actdbg_proc_name
token_copy_limit = ACTDBG_RES_token_copy_limit
actdbg_break_hit = ACTDBG_RES_actdbg_break_hit
actdbg_view_mode = ACTDBG_RES_actdbg_view_mode
actdbg_step_mode = ACTDBG_RES_actdbg_step_mode
actdbg_step_target_rsp = ACTDBG_RES_actdbg_step_target_rsp
actdbg_step_target_pc_lo = ACTDBG_RES_actdbg_step_target_pc_lo
actdbg_step_target_pc_hi = ACTDBG_RES_actdbg_step_target_pc_hi
actdbg_vm_header_len = ACTDBG_RES_actdbg_vm_header_len
actdbg_avm_header = ACTDBG_RES_actdbg_avm_header
actdbg_vm_fetch_buffer = ACTDBG_RES_actdbg_vm_fetch_buffer
actdbg_vm_payload_lo = ACTDBG_RES_actdbg_vm_payload_lo
actdbg_vm_payload_hi = ACTDBG_RES_actdbg_vm_payload_hi
actdbg_vm_payload_bank = ACTDBG_RES_actdbg_vm_payload_bank
actdbg_vm_payload_len_lo = ACTDBG_RES_actdbg_vm_payload_len_lo
actdbg_vm_payload_len_hi = ACTDBG_RES_actdbg_vm_payload_len_hi
actdbg_vm_scan_lo = ACTDBG_RES_actdbg_vm_scan_lo
actdbg_vm_scan_hi = ACTDBG_RES_actdbg_vm_scan_hi
actdbg_vm_scan_end_lo = ACTDBG_RES_actdbg_vm_scan_end_lo
actdbg_vm_scan_end_hi = ACTDBG_RES_actdbg_vm_scan_end_hi
actdbg_vm_entry_lo = ACTDBG_RES_actdbg_vm_entry_lo
actdbg_vm_entry_hi = ACTDBG_RES_actdbg_vm_entry_hi
actdbg_vm_string_lo = ACTDBG_RES_actdbg_vm_string_lo
actdbg_vm_string_hi = ACTDBG_RES_actdbg_vm_string_hi
actdbg_current_pc_lo = ACTDBG_RES_actdbg_current_pc_lo
actdbg_current_pc_hi = ACTDBG_RES_actdbg_current_pc_hi
actdbg_vm_done = ACTDBG_RES_actdbg_vm_done
actdbg_vm_failed = ACTDBG_RES_actdbg_vm_failed
actdbg_vm_step_budget = ACTDBG_RES_actdbg_vm_step_budget
actdbg_vm_sp = ACTDBG_RES_actdbg_vm_sp
actdbg_vm_rsp = ACTDBG_RES_actdbg_vm_rsp
actdbg_output_row = ACTDBG_RES_actdbg_output_row
actdbg_output_col = ACTDBG_RES_actdbg_output_col
actdbg_room_check_lo = ACTDBG_RES_actdbg_room_check_lo
actdbg_room_check_hi = ACTDBG_RES_actdbg_room_check_hi
actdbg_avm_stage_len_lo = ACTDBG_RES_actdbg_avm_stage_len_lo
actdbg_avm_stage_len_hi = ACTDBG_RES_actdbg_avm_stage_len_hi
actdbg_avm_stage_len_bank = ACTDBG_RES_actdbg_avm_stage_len_bank
actdbg_vm_stack_lo = ACTDBG_RES_actdbg_vm_stack_lo
actdbg_vm_stack_hi = ACTDBG_RES_actdbg_vm_stack_hi
actdbg_vm_rstack_lo = ACTDBG_RES_actdbg_vm_rstack_lo
actdbg_vm_rstack_hi = ACTDBG_RES_actdbg_vm_rstack_hi
actdbg_output_row_buffer = ACTDBG_RES_actdbg_output_row_buffer
line_buffer = ACTDBG_RES_line_buffer

set_dbg_scan_to_body = ACTDBG_RES_set_dbg_scan_to_body
copy_dbg_line_to_buffer = ACTDBG_RES_copy_dbg_line_to_buffer
token_scan_begin = ACTDBG_RES_token_scan_begin
token_skip_forward = ACTDBG_RES_token_skip_forward
token_parse_u16 = ACTDBG_RES_token_parse_u16
token_copy_to_buffer = ACTDBG_RES_token_copy_to_buffer
ascii_to_screen = ACTDBG_RES_ascii_to_screen
load_output_row_buffer_from_reu_row_a = ACTDBG_RES_load_output_row_buffer_from_reu_row_a
store_output_row_buffer_to_reu_row_a = ACTDBG_RES_store_output_row_buffer_to_reu_row_a
show_output_screen = ACTDBG_RES_show_output_screen

actdbg_overlay_entry:
    lda ACTDBG_RES_actdbg_overlay_requested_cmd
    cmp #ACTDBG_OVERLAY_CMD_EXEC_INIT_RUNTIME
    bne :+
    jmp init_debug_runtime
:   cmp #ACTDBG_OVERLAY_CMD_EXEC_LOOKUP_LOCATION
    bne :+
    jmp lookup_dbg_location_for_current_pc
:   cmp #ACTDBG_OVERLAY_CMD_EXEC_STEP
    bne :+
    jmp debug_step_instruction
:   cmp #ACTDBG_OVERLAY_CMD_EXEC_CONTINUE
    bne :+
    jmp debug_continue_execution
:   cmp #ACTDBG_OVERLAY_CMD_EXEC_STEP_OVER
    bne :+
    jmp debug_step_over_execution
:   cmp #ACTDBG_OVERLAY_CMD_EXEC_STEP_OUT
    bne :+
    jmp debug_step_out_execution
:   sec
    lda #ACTDBG_OVERLAY_STATUS_FAILED
    rts

init_debug_runtime:
    lda actdbg_avm_header+0
    cmp #'A'
    beq :+
    jmp init_debug_runtime_fail
:   
    lda actdbg_avm_header+1
    cmp #'V'
    beq :+
    jmp init_debug_runtime_fail
:   
    lda actdbg_avm_header+2
    cmp #'M'
    beq :+
    jmp init_debug_runtime_fail
:   
    lda actdbg_avm_header+3
    cmp #'1'
    beq :+
    jmp init_debug_runtime_fail
:   
    lda actdbg_avm_header+4
    cmp #1
    bne :+
    jmp init_debug_runtime_v1
:   
    cmp #2
    bne :+
    jmp init_debug_runtime_v2
:   jmp init_debug_runtime_fail

init_debug_runtime_v1:
    lda #10
    sta actdbg_vm_header_len
    clc
    lda #ACTDBG_AVM_REU_BASE_LO
    adc actdbg_vm_header_len
    sta actdbg_vm_payload_lo
    lda #ACTDBG_AVM_REU_BASE_HI
    adc #$00
    sta actdbg_vm_payload_hi
    lda #ACTDBG_AVM_REU_BASE_BANK
    adc #$00
    sta actdbg_vm_payload_bank
    lda actdbg_avm_header+5
    sta actdbg_vm_scan_end_lo
    lda actdbg_avm_header+6
    sta actdbg_vm_scan_end_hi
    lda actdbg_avm_header+7
    sta actdbg_vm_entry_lo
    lda actdbg_avm_header+8
    sta actdbg_vm_entry_hi
    jmp init_debug_runtime_common

init_debug_runtime_v2:
    lda actdbg_avm_header+9
    cmp #1
    beq :+
    jmp init_debug_runtime_fail
:   
    lda #12
    sta actdbg_vm_header_len
    clc
    lda #ACTDBG_AVM_REU_BASE_LO
    adc actdbg_vm_header_len
    sta actdbg_vm_payload_lo
    lda #ACTDBG_AVM_REU_BASE_HI
    adc #$00
    sta actdbg_vm_payload_hi
    lda #ACTDBG_AVM_REU_BASE_BANK
    adc #$00
    sta actdbg_vm_payload_bank
    lda actdbg_avm_header+10
    sta actdbg_vm_scan_end_lo
    lda actdbg_avm_header+11
    sta actdbg_vm_scan_end_hi
    lda actdbg_avm_header+7
    sta actdbg_vm_entry_lo
    lda actdbg_avm_header+8
    sta actdbg_vm_entry_hi

init_debug_runtime_common:
    lda actdbg_avm_stage_len_bank
    bne init_debug_runtime_fail
    sec
    lda actdbg_avm_stage_len_lo
    sbc actdbg_vm_header_len
    sta actdbg_vm_payload_len_lo
    lda actdbg_avm_stage_len_hi
    sbc #$00
    sta actdbg_vm_payload_len_hi
    bcc init_debug_runtime_fail
    lda actdbg_vm_scan_end_hi
    cmp actdbg_vm_payload_len_hi
    bcc :+
    bne init_debug_runtime_fail
    lda actdbg_vm_scan_end_lo
    cmp actdbg_vm_payload_len_lo
    bcc :+
    bne init_debug_runtime_fail
:
    lda actdbg_vm_entry_hi
    cmp actdbg_vm_scan_end_hi
    bcc :+
    bne init_debug_runtime_fail
    lda actdbg_vm_entry_lo
    cmp actdbg_vm_scan_end_lo
    bcc :+
    jmp init_debug_runtime_fail
:
    lda actdbg_vm_entry_lo
    sta actdbg_vm_scan_lo
    lda actdbg_vm_entry_hi
    sta actdbg_vm_scan_hi
    lda #$00
    sta actdbg_vm_string_lo
    lda #$00
    sta actdbg_vm_string_hi
    sta actdbg_vm_sp
    sta actdbg_vm_rsp
    sta actdbg_vm_done
    sta actdbg_vm_failed
    jsr update_current_pc_from_scan_ptr
    clc
    rts

init_debug_runtime_fail:
    sec
    rts

update_current_pc_from_scan_ptr:
    lda actdbg_vm_scan_lo
    sta actdbg_current_pc_lo
    lda actdbg_vm_scan_hi
lookup_dbg_location_for_current_pc:
    lda #$00
    sta actdbg_best_proc_found
    sta actdbg_best_line_found
    jsr set_dbg_scan_to_body

lookup_dbg_proc_loop:
    jsr copy_dbg_line_to_buffer
    bcc :+
    jmp lookup_dbg_proc_done
:   lda line_buffer
    cmp #'q'
    bne lookup_dbg_proc_loop
    jsr token_scan_begin
    jsr token_skip_forward
    jsr token_parse_u16
    lda status_ptr
    sta actdbg_dbg_candidate_module_lo
    lda status_ptr+1
    sta actdbg_dbg_candidate_module_hi
    jsr token_parse_u16
    lda status_ptr
    sta actdbg_dbg_candidate_export_lo
    lda status_ptr+1
    sta actdbg_dbg_candidate_export_hi
    jsr token_parse_u16
    lda status_ptr
    sta actdbg_dbg_candidate_pc_lo
    lda status_ptr+1
    sta actdbg_dbg_candidate_pc_hi
    jsr token_parse_u16
    lda status_ptr
    sta actdbg_dbg_candidate_file_lo
    lda status_ptr+1
    sta actdbg_dbg_candidate_file_hi
    jsr token_parse_u16
    lda status_ptr
    sta actdbg_dbg_candidate_line_lo
    lda status_ptr+1
    sta actdbg_dbg_candidate_line_hi
    jsr token_parse_u16
    lda status_ptr
    sta actdbg_dbg_candidate_col
    lda actdbg_dbg_candidate_pc_hi
    cmp actdbg_current_pc_hi
    bcc :+
    bne lookup_dbg_proc_loop
    lda actdbg_dbg_candidate_pc_lo
    cmp actdbg_current_pc_lo
    bcc :+
    beq :+
    jmp lookup_dbg_proc_loop
:   lda actdbg_best_proc_found
    beq lookup_dbg_store_proc
    lda actdbg_dbg_candidate_pc_hi
    cmp actdbg_best_proc_pc_hi
    bcs :+
    jmp lookup_dbg_proc_loop
:   
    bne lookup_dbg_store_proc
    lda actdbg_dbg_candidate_pc_lo
    cmp actdbg_best_proc_pc_lo
    bcs :+
    jmp lookup_dbg_proc_loop
:   

lookup_dbg_store_proc:
    lda #$01
    sta actdbg_best_proc_found
    lda actdbg_dbg_candidate_module_lo
    sta actdbg_target_module_lo
    lda actdbg_dbg_candidate_module_hi
    sta actdbg_target_module_hi
    lda actdbg_dbg_candidate_export_lo
    sta actdbg_target_export_lo
    lda actdbg_dbg_candidate_export_hi
    sta actdbg_target_export_hi
    lda actdbg_dbg_candidate_file_lo
    sta actdbg_target_file_lo
    lda actdbg_dbg_candidate_file_hi
    sta actdbg_target_file_hi
    lda actdbg_dbg_candidate_line_lo
    sta actdbg_target_line_lo
    lda actdbg_dbg_candidate_line_hi
    sta actdbg_target_line_hi
    lda actdbg_dbg_candidate_col
    sta actdbg_target_col
    lda actdbg_dbg_candidate_pc_lo
    sta actdbg_best_proc_pc_lo
    lda actdbg_dbg_candidate_pc_hi
    sta actdbg_best_proc_pc_hi
    lda #MODULE_LIMIT
    sta token_copy_limit
    lda #<actdbg_proc_name
    ldy #>actdbg_proc_name
    jsr token_copy_to_buffer
    jmp lookup_dbg_proc_loop

lookup_dbg_proc_done:
    lda actdbg_best_proc_found
    bne :+
    sec
    rts
:   jsr set_dbg_scan_to_body

lookup_dbg_line_loop:
    jsr copy_dbg_line_to_buffer
    bcc :+
    jmp lookup_dbg_line_done
:   lda line_buffer
    cmp #'l'
    bne lookup_dbg_line_loop
    jsr token_scan_begin
    jsr token_skip_forward
    jsr token_parse_u16
    lda status_ptr
    cmp actdbg_target_module_lo
    beq :+
    jmp lookup_dbg_line_loop
:   lda status_ptr+1
    cmp actdbg_target_module_hi
    beq :+
    jmp lookup_dbg_line_loop
:   jsr token_parse_u16
    lda status_ptr
    cmp actdbg_target_export_lo
    beq :+
    jmp lookup_dbg_line_loop
:   lda status_ptr+1
    cmp actdbg_target_export_hi
    beq :+
    jmp lookup_dbg_line_loop
:   jsr token_parse_u16
    lda status_ptr
    sta actdbg_dbg_candidate_pc_lo
    lda status_ptr+1
    sta actdbg_dbg_candidate_pc_hi
    jsr token_parse_u16
    lda status_ptr
    sta actdbg_dbg_candidate_file_lo
    lda status_ptr+1
    sta actdbg_dbg_candidate_file_hi
    jsr token_parse_u16
    lda status_ptr
    sta actdbg_dbg_candidate_line_lo
    lda status_ptr+1
    sta actdbg_dbg_candidate_line_hi
    jsr token_parse_u16
    lda status_ptr
    sta actdbg_dbg_candidate_col
    lda actdbg_dbg_candidate_pc_hi
    cmp actdbg_current_pc_hi
    bcc :+
    bne lookup_dbg_line_loop
    lda actdbg_dbg_candidate_pc_lo
    cmp actdbg_current_pc_lo
    bcc :+
    beq :+
    jmp lookup_dbg_line_loop
:   lda actdbg_best_line_found
    beq lookup_dbg_store_line
    lda actdbg_dbg_candidate_pc_hi
    cmp actdbg_best_line_pc_hi
    bcs :+
    jmp lookup_dbg_line_loop
:   
    bne lookup_dbg_store_line
    lda actdbg_dbg_candidate_pc_lo
    cmp actdbg_best_line_pc_lo
    bcs :+
    jmp lookup_dbg_line_loop
:   

lookup_dbg_store_line:
    lda #$01
    sta actdbg_best_line_found
    lda actdbg_dbg_candidate_file_lo
    sta actdbg_target_file_lo
    lda actdbg_dbg_candidate_file_hi
    sta actdbg_target_file_hi
    lda actdbg_dbg_candidate_line_lo
    sta actdbg_target_line_lo
    lda actdbg_dbg_candidate_line_hi
    sta actdbg_target_line_hi
    lda actdbg_dbg_candidate_col
    sta actdbg_target_col
    lda actdbg_dbg_candidate_pc_lo
    sta actdbg_best_line_pc_lo
    lda actdbg_dbg_candidate_pc_hi
    sta actdbg_best_line_pc_hi
    jmp lookup_dbg_line_loop

lookup_dbg_line_done:
    clc
    rts
debug_step_instruction:
    lda actdbg_vm_done
    beq :+
    jmp debug_idle_return
:   
    lda actdbg_vm_failed
    beq :+
    jmp debug_idle_return
:   
    lda #$00
    sta actdbg_break_hit
    lda #$01
    sta actdbg_vm_step_budget
    jmp debug_run_vm

debug_continue_execution:
    lda actdbg_vm_done
    beq :+
    jmp debug_idle_return
:   
    lda actdbg_vm_failed
    beq :+
    jmp debug_idle_return
:   
    lda #$00
    sta actdbg_break_hit
    lda #$00
    sta actdbg_vm_step_budget
    jmp debug_run_vm

debug_step_over_execution:
    lda actdbg_vm_done
    bne debug_idle_return
    lda actdbg_vm_failed
    bne debug_idle_return
    lda #$00
    sta actdbg_break_hit
    sta actdbg_step_mode
    jsr debug_fetch_scan_1
    bcc :+
    sec
    rts
:   lda actdbg_vm_fetch_buffer+0
    cmp #OPCODE_CALL
    beq debug_step_over_call
    jmp debug_step_instruction
debug_step_over_call:
    lda #$01
    sta actdbg_step_mode
    lda actdbg_vm_rsp
    sta actdbg_step_target_rsp
    clc
    lda actdbg_vm_scan_lo
    adc #$03
    sta actdbg_step_target_pc_lo
    lda actdbg_vm_scan_hi
    adc #$00
    sta actdbg_step_target_pc_hi
    lda #$00
    sta actdbg_vm_step_budget
    jmp debug_run_vm

debug_step_out_execution:
    lda actdbg_vm_done
    bne debug_idle_return
    lda actdbg_vm_failed
    bne debug_idle_return
    lda #$00
    sta actdbg_break_hit
    lda actdbg_vm_rsp
    beq debug_continue_execution
    lda #$02
    sta actdbg_step_mode
    lda actdbg_vm_rsp
    sta actdbg_step_target_rsp
    lda #$00
    sta actdbg_vm_step_budget
    jmp debug_run_vm

debug_idle_return:
    clc
    rts

debug_run_vm:
    lda actdbg_vm_done
    beq :+
    jmp debug_run_done
:   
debug_run_loop:
    lda actdbg_vm_scan_hi
    cmp actdbg_vm_scan_end_hi
    bcc :+
    bne debug_mark_done
    lda actdbg_vm_scan_lo
    cmp actdbg_vm_scan_end_lo
    bcc :+
debug_mark_done:
    lda #$01
    sta actdbg_vm_done
    jmp debug_run_done
:   jsr debug_fetch_scan_1
    bcc :+
    jmp debug_run_fail
:   lda actdbg_vm_fetch_buffer+0
    cmp #OPCODE_PUSH8
    bne :+
    jmp debug_interp_push8
:   cmp #OPCODE_PUSH16
    bne :+
    jmp debug_interp_push16
:   cmp #OPCODE_STORE
    bne :+
    jmp debug_interp_store
:   cmp #OPCODE_LOAD
    bne :+
    jmp debug_interp_load
:   cmp #OPCODE_ADD
    bne :+
    jmp debug_interp_add
:   cmp #OPCODE_SUB
    bne :+
    jmp debug_interp_sub
:   cmp #OPCODE_EQ
    bne :+
    jmp debug_interp_eq
:   cmp #OPCODE_NE
    bne :+
    jmp debug_interp_ne
:   cmp #OPCODE_LT
    bne :+
    jmp debug_interp_lt
:   cmp #OPCODE_GT
    bne :+
    jmp debug_interp_gt
:   cmp #OPCODE_BAND
    bne :+
    jmp debug_interp_band
:   cmp #OPCODE_BOR
    bne :+
    jmp debug_interp_bor
:   cmp #OPCODE_BXOR
    bne :+
    jmp debug_interp_bxor
:   cmp #OPCODE_SHL1
    bne :+
    jmp debug_interp_shl1
:   cmp #OPCODE_SHR1
    bne :+
    jmp debug_interp_shr1
:   cmp #OPCODE_JZ
    bne :+
    jmp debug_interp_jz
:   cmp #OPCODE_JMP
    bne :+
    jmp debug_interp_jmp
:   cmp #OPCODE_DUP
    bne :+
    jmp debug_interp_dup
:   cmp #OPCODE_DROP
    bne :+
    jmp debug_interp_drop
:   cmp #OPCODE_SETP16
    bne :+
    jmp debug_interp_setp16
:   cmp #OPCODE_CALL
    bne :+
    jmp debug_interp_call
:   cmp #OPCODE_RET
    bne :+
    jmp debug_interp_ret
:   cmp #OPCODE_CALLN
    bne :+
    jmp debug_interp_calln
:   jmp debug_run_fail

debug_finish_instruction:
    jsr update_current_pc_from_scan_ptr
    lda actdbg_vm_done
    bne debug_run_done
    lda actdbg_step_mode
    beq :+
    jsr debug_check_step_goal_reached
    bcc :+
    lda #$00
    sta actdbg_step_mode
    jmp debug_run_done
:   
    lda actdbg_vm_step_budget
    bne debug_finish_budgeted
    jsr check_breakpoint_hit_current_pc
    bcc debug_finish_continue
    lda #$01
    sta actdbg_break_hit
    lda #$00
    sta actdbg_step_mode
    jmp debug_run_done
debug_finish_budgeted:
    dec actdbg_vm_step_budget
    beq debug_run_done
debug_finish_continue:
    jmp debug_run_loop

debug_run_done:
    clc
    rts

debug_run_fail:
    lda #$01
    sta actdbg_vm_failed
    sec
    rts

check_breakpoint_hit_current_pc:
    ldx #$00
check_breakpoint_hit_loop:
    cpx #BREAKPOINT_MAX
    bcs check_breakpoint_hit_fail
    lda actdbg_break_active,x
    beq check_breakpoint_hit_next
    lda actdbg_break_pc_lo,x
    cmp actdbg_current_pc_lo
    bne check_breakpoint_hit_next
    lda actdbg_break_pc_hi,x
    cmp actdbg_current_pc_hi
    beq check_breakpoint_hit_found
check_breakpoint_hit_next:
    inx
    jmp check_breakpoint_hit_loop
check_breakpoint_hit_found:
    sec
    rts
check_breakpoint_hit_fail:
    clc
    rts

debug_check_step_goal_reached:
    lda actdbg_step_mode
    cmp #$01
    beq debug_check_step_over_goal
    cmp #$02
    beq debug_check_step_out_goal
    clc
    rts

debug_check_step_over_goal:
    lda actdbg_vm_rsp
    cmp actdbg_step_target_rsp
    bne debug_check_step_goal_fail
    lda actdbg_current_pc_lo
    cmp actdbg_step_target_pc_lo
    bne debug_check_step_goal_fail
    lda actdbg_current_pc_hi
    cmp actdbg_step_target_pc_hi
    bne debug_check_step_goal_fail
    sec
    rts

debug_check_step_out_goal:
    lda actdbg_vm_rsp
    cmp actdbg_step_target_rsp
    bcc debug_check_step_goal_hit
debug_check_step_goal_fail:
    clc
    rts
debug_check_step_goal_hit:
    sec
    rts

debug_interp_push8:
    jsr debug_fetch_scan_2
    bcc :+
    jmp debug_run_fail
:   lda actdbg_vm_fetch_buffer+1
    sta word_tmp
    lda #$00
    sta word_tmp+1
    jsr debug_push_word_tmp
    bcc :+
    jmp debug_run_fail
:   lda #$02
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_push16:
    jsr debug_fetch_scan_3
    bcc :+
    jmp debug_run_fail
:   lda actdbg_vm_fetch_buffer+1
    sta word_tmp
    lda actdbg_vm_fetch_buffer+2
    sta word_tmp+1
    jsr debug_push_word_tmp
    bcc :+
    jmp debug_run_fail
:   lda #$03
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_store:
    jsr debug_fetch_scan_3
    bcc :+
    jmp debug_run_fail
:   lda actdbg_vm_fetch_buffer+1
    sta word_tmp
    lda actdbg_vm_fetch_buffer+2
    sta word_tmp+1
    jsr debug_pop_to_svc_retptr
    bcc :+
    jmp debug_run_fail
:   jsr debug_store_svc_retptr_at_word_tmp_offset
    bcc :+
    jmp debug_run_fail
:   
    lda #$03
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_load:
    jsr debug_fetch_scan_3
    bcc :+
    jmp debug_run_fail
:   lda actdbg_vm_fetch_buffer+1
    sta word_tmp
    lda actdbg_vm_fetch_buffer+2
    sta word_tmp+1
    jsr debug_load_word_at_word_tmp_offset
    bcc :+
    jmp debug_run_fail
:   
    jsr debug_push_word_tmp
    bcc :+
    jmp debug_run_fail
:   lda #$03
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_add:
    jsr debug_pop_to_word_tmp
    bcc :+
    jmp debug_run_fail
:   jsr debug_pop_to_svc_retptr
    bcc :+
    jmp debug_run_fail
:   clc
    lda svc_retptr
    adc word_tmp
    sta word_tmp
    lda svc_retptr+1
    adc word_tmp+1
    sta word_tmp+1
    jsr debug_push_word_tmp
    bcc :+
    jmp debug_run_fail
:   lda #$01
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_sub:
    jsr debug_pop_to_word_tmp
    bcc :+
    jmp debug_run_fail
:   jsr debug_pop_to_svc_retptr
    bcc :+
    jmp debug_run_fail
:   sec
    lda svc_retptr
    sbc word_tmp
    sta word_tmp
    lda svc_retptr+1
    sbc word_tmp+1
    sta word_tmp+1
    jsr debug_push_word_tmp
    bcc :+
    jmp debug_run_fail
:   lda #$01
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_eq:
    jsr debug_compare_to_bool_eq
    jmp debug_interp_compare_common

debug_interp_ne:
    jsr debug_compare_to_bool_ne
    jmp debug_interp_compare_common

debug_interp_lt:
    jsr debug_compare_to_bool_lt
    jmp debug_interp_compare_common

debug_interp_gt:
    jsr debug_compare_to_bool_gt
debug_interp_compare_common:
    bcc :+
    jmp debug_run_fail
:   jsr debug_push_word_tmp
    bcc :+
    jmp debug_run_fail
:   lda #$01
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_band:
    jsr debug_pop_to_word_tmp
    bcc :+
    jmp debug_run_fail
:   jsr debug_pop_to_svc_retptr
    bcc :+
    jmp debug_run_fail
:   lda svc_retptr
    and word_tmp
    sta word_tmp
    lda svc_retptr+1
    and word_tmp+1
    sta word_tmp+1
    jmp debug_interp_bitwise_push_common

debug_interp_bor:
    jsr debug_pop_to_word_tmp
    bcc :+
    jmp debug_run_fail
:   jsr debug_pop_to_svc_retptr
    bcc :+
    jmp debug_run_fail
:   lda svc_retptr
    ora word_tmp
    sta word_tmp
    lda svc_retptr+1
    ora word_tmp+1
    sta word_tmp+1
    jmp debug_interp_bitwise_push_common

debug_interp_bxor:
    jsr debug_pop_to_word_tmp
    bcc :+
    jmp debug_run_fail
:   jsr debug_pop_to_svc_retptr
    bcc :+
    jmp debug_run_fail
:   lda svc_retptr
    eor word_tmp
    sta word_tmp
    lda svc_retptr+1
    eor word_tmp+1
    sta word_tmp+1
    jmp debug_interp_bitwise_push_common

debug_interp_shl1:
    jsr debug_pop_to_word_tmp
    bcc :+
    jmp debug_run_fail
:   asl word_tmp
    rol word_tmp+1
    jmp debug_interp_bitwise_push_common

debug_interp_shr1:
    jsr debug_pop_to_word_tmp
    bcc :+
    jmp debug_run_fail
:   lsr word_tmp+1
    ror word_tmp
debug_interp_bitwise_push_common:
    jsr debug_push_word_tmp
    bcc :+
    jmp debug_run_fail
:   lda #$01
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_jz:
    jsr debug_fetch_scan_3
    bcc :+
    jmp debug_run_fail
:   lda actdbg_vm_fetch_buffer+1
    sta word_tmp
    lda actdbg_vm_fetch_buffer+2
    sta word_tmp+1
    jsr debug_pop_to_svc_retptr
    bcc :+
    jmp debug_run_fail
:   lda svc_retptr
    ora svc_retptr+1
    beq debug_interp_jz_taken
    lda #$03
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction
debug_interp_jz_taken:
    lda word_tmp
    sta actdbg_vm_scan_lo
    lda word_tmp+1
    sta actdbg_vm_scan_hi
    jmp debug_finish_instruction

debug_interp_jmp:
    jsr debug_fetch_scan_3
    bcc :+
    jmp debug_run_fail
:   lda actdbg_vm_fetch_buffer+1
    sta word_tmp
    lda actdbg_vm_fetch_buffer+2
    sta word_tmp+1
    lda word_tmp
    sta actdbg_vm_scan_lo
    lda word_tmp+1
    sta actdbg_vm_scan_hi
    jmp debug_finish_instruction

debug_interp_dup:
    jsr debug_peek_to_word_tmp
    bcc :+
    jmp debug_run_fail
:   jsr debug_push_word_tmp
    bcc :+
    jmp debug_run_fail
:   lda #$01
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_drop:
    lda actdbg_vm_sp
    bne :+
    jmp debug_run_fail
:   dec actdbg_vm_sp
    lda #$01
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_setp16:
    jsr debug_fetch_scan_3
    bcc :+
    jmp debug_run_fail
:   lda actdbg_vm_fetch_buffer+1
    sta word_tmp
    lda actdbg_vm_fetch_buffer+2
    sta word_tmp+1
    lda word_tmp
    sta actdbg_vm_string_lo
    lda word_tmp+1
    sta actdbg_vm_string_hi
    lda #$03
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_call:
    jsr debug_fetch_scan_3
    bcc :+
    jmp debug_run_fail
:   lda actdbg_vm_rsp
    cmp #INTERP_STACK_MAX
    bcc :+
    jmp debug_run_fail
:   ldx actdbg_vm_rsp
    clc
    lda actdbg_vm_scan_lo
    adc #$03
    sta actdbg_vm_rstack_lo,x
    lda actdbg_vm_scan_hi
    adc #$00
    sta actdbg_vm_rstack_hi,x
    inc actdbg_vm_rsp
    lda actdbg_vm_fetch_buffer+1
    sta word_tmp
    lda actdbg_vm_fetch_buffer+2
    sta word_tmp+1
    lda word_tmp
    sta actdbg_vm_scan_lo
    lda word_tmp+1
    sta actdbg_vm_scan_hi
    jmp debug_finish_instruction

debug_interp_ret:
    lda actdbg_vm_rsp
    bne :+
    lda #$01
    sta actdbg_vm_done
    jmp debug_finish_instruction
:   dec actdbg_vm_rsp
    ldx actdbg_vm_rsp
    lda actdbg_vm_rstack_lo,x
    sta actdbg_vm_scan_lo
    lda actdbg_vm_rstack_hi,x
    sta actdbg_vm_scan_hi
    jmp debug_finish_instruction

debug_interp_calln:
    jsr debug_fetch_scan_3
    bcc :+
    jmp debug_run_fail
:   lda actdbg_vm_fetch_buffer+1
    sta word_tmp
    lda actdbg_vm_fetch_buffer+2
    sta word_tmp+1
    lda word_tmp
    cmp #<INTRINSIC_PRINT
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_PRINT
    beq debug_interp_calln_print
:   lda word_tmp
    cmp #<INTRINSIC_PRINTE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTE
    beq debug_interp_calln_printe
:   lda word_tmp
    cmp #<INTRINSIC_PRINTI
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTI
    beq debug_interp_calln_printi
:   lda word_tmp
    cmp #<INTRINSIC_PRINTIE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTIE
    beq debug_interp_calln_printie
:   lda word_tmp
    cmp #<INTRINSIC_EXIT
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_EXIT
    beq debug_interp_calln_exit
:   jmp debug_run_fail

debug_interp_calln_print:
    jsr debug_native_print
    bcc :+
    jmp debug_run_fail
:   
    lda #$03
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_calln_printe:
    jsr debug_native_printe
    bcc :+
    jmp debug_run_fail
:   
    lda #$03
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_calln_printi:
    jsr debug_pop_to_word_tmp
    bcc :+
    jmp debug_run_fail
:   jsr debug_native_printi
    lda #$03
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_calln_printie:
    jsr debug_pop_to_word_tmp
    bcc :+
    jmp debug_run_fail
:   jsr debug_native_printie
    lda #$03
    jsr debug_advance_scan_ptr
    jmp debug_finish_instruction

debug_interp_calln_exit:
    lda #$03
    jsr debug_advance_scan_ptr
    lda #$01
    sta actdbg_vm_done
    jmp debug_finish_instruction

debug_push_word_tmp:
    ldx actdbg_vm_sp
    cpx #INTERP_STACK_MAX
    bcc :+
    sec
    rts
:   lda word_tmp
    sta actdbg_vm_stack_lo,x
    lda word_tmp+1
    sta actdbg_vm_stack_hi,x
    inc actdbg_vm_sp
    clc
    rts

debug_pop_to_word_tmp:
    lda actdbg_vm_sp
    beq debug_pop_fail
    dec actdbg_vm_sp
    ldx actdbg_vm_sp
    lda actdbg_vm_stack_lo,x
    sta word_tmp
    lda actdbg_vm_stack_hi,x
    sta word_tmp+1
    clc
    rts

debug_pop_to_svc_retptr:
    lda actdbg_vm_sp
    beq debug_pop_fail
    dec actdbg_vm_sp
    ldx actdbg_vm_sp
    lda actdbg_vm_stack_lo,x
    sta svc_retptr
    lda actdbg_vm_stack_hi,x
    sta svc_retptr+1
    clc
    rts

debug_peek_to_word_tmp:
    lda actdbg_vm_sp
    beq debug_pop_fail
    sec
    sbc #$01
    tax
    lda actdbg_vm_stack_lo,x
    sta word_tmp
    lda actdbg_vm_stack_hi,x
    sta word_tmp+1
    clc
    rts

debug_pop_fail:
    sec
    rts

debug_compare_to_bool_eq:
    jsr debug_pop_to_word_tmp
    bcc :+
    sec
    rts
:   jsr debug_pop_to_svc_retptr
    bcc :+
    sec
    rts
:   lda svc_retptr
    cmp word_tmp
    bne debug_compare_false
    lda svc_retptr+1
    cmp word_tmp+1
    bne debug_compare_false
    jmp debug_compare_true

debug_compare_to_bool_ne:
    jsr debug_pop_to_word_tmp
    bcc :+
    sec
    rts
:   jsr debug_pop_to_svc_retptr
    bcc :+
    sec
    rts
:   lda svc_retptr
    cmp word_tmp
    bne debug_compare_true
    lda svc_retptr+1
    cmp word_tmp+1
    bne debug_compare_true
    jmp debug_compare_false

debug_compare_to_bool_lt:
    jsr debug_pop_to_word_tmp
    bcc :+
    sec
    rts
:   jsr debug_pop_to_svc_retptr
    bcc :+
    sec
    rts
:   lda svc_retptr+1
    cmp word_tmp+1
    bcc debug_compare_true
    bne debug_compare_false
    lda svc_retptr
    cmp word_tmp
    bcc debug_compare_true
    jmp debug_compare_false

debug_compare_to_bool_gt:
    jsr debug_pop_to_word_tmp
    bcc :+
    sec
    rts
:   jsr debug_pop_to_svc_retptr
    bcc :+
    sec
    rts
:   lda svc_retptr+1
    cmp word_tmp+1
    bcc debug_compare_false
    bne debug_compare_true
    lda svc_retptr
    cmp word_tmp
    bcc debug_compare_false
    beq debug_compare_false
    jmp debug_compare_true

debug_compare_true:
    lda #$01
    sta word_tmp
    lda #$00
    sta word_tmp+1
    clc
    rts

debug_compare_false:
    lda #$00
    sta word_tmp
    sta word_tmp+1
    clc
    rts

debug_set_reu_params_from_word_tmp:
    clc
    lda actdbg_vm_payload_lo
    adc word_tmp
    sta file_params+0
    lda actdbg_vm_payload_hi
    adc word_tmp+1
    sta file_params+1
    lda actdbg_vm_payload_bank
    adc #$00
    sta file_params+2
    rts

debug_read_payload_to_fetch_len_a:
    pha
    jsr debug_set_reu_params_from_word_tmp
    lda #<actdbg_vm_fetch_buffer
    sta file_params+3
    lda #>actdbg_vm_fetch_buffer
    sta file_params+4
    pla
    sta file_params+5
    lda #$00
    sta file_params+6
    sta file_params+7
    ldx #file_params
    jsr svc_reu_read_sc0
    lda file_params+7
    cmp #tool_file_status_ok
    beq :+
    sec
    rts
:   clc
    rts

debug_fetch_scan_1:
    jsr debug_ensure_scan_room_1
    bcc :+
    sec
    rts
:   lda actdbg_vm_scan_lo
    sta word_tmp
    lda actdbg_vm_scan_hi
    sta word_tmp+1
    lda #$01
    jmp debug_read_payload_to_fetch_len_a

debug_fetch_scan_2:
    jsr debug_ensure_scan_room_2
    bcc :+
    sec
    rts
:   lda actdbg_vm_scan_lo
    sta word_tmp
    lda actdbg_vm_scan_hi
    sta word_tmp+1
    lda #$02
    jmp debug_read_payload_to_fetch_len_a

debug_fetch_scan_3:
    jsr debug_ensure_scan_room_3
    bcc :+
    sec
    rts
:   lda actdbg_vm_scan_lo
    sta word_tmp
    lda actdbg_vm_scan_hi
    sta word_tmp+1
    lda #$03
    jmp debug_read_payload_to_fetch_len_a

debug_ensure_payload_room_1_at_word_tmp:
    lda word_tmp+1
    cmp actdbg_vm_payload_len_hi
    bcc :+
    beq :++
    jmp debug_ensure_room_fail
:   clc
    rts
:   lda word_tmp
    cmp actdbg_vm_payload_len_lo
    bcc :+
    jmp debug_ensure_room_fail
:   clc
    rts

debug_ensure_payload_room_2_at_word_tmp:
    clc
    lda word_tmp
    adc #$02
    sta actdbg_room_check_lo
    lda word_tmp+1
    adc #$00
    sta actdbg_room_check_hi
    lda actdbg_room_check_hi
    cmp actdbg_vm_payload_len_hi
    bcc :+
    bne debug_ensure_room_fail
    lda actdbg_room_check_lo
    cmp actdbg_vm_payload_len_lo
    bcc :+
    beq :+
    jmp debug_ensure_room_fail
:   clc
    rts

debug_load_byte_at_word_tmp_to_a:
    jsr debug_ensure_payload_room_1_at_word_tmp
    bcc :+
    sec
    rts
:   lda #$01
    jsr debug_read_payload_to_fetch_len_a
    bcc :+
    sec
    rts
:   lda actdbg_vm_fetch_buffer+0
    clc
    rts

debug_load_word_at_word_tmp_offset:
    jsr debug_ensure_payload_room_2_at_word_tmp
    bcc :+
    sec
    rts
:   lda #$02
    jsr debug_read_payload_to_fetch_len_a
    bcc :+
    sec
    rts
:   lda actdbg_vm_fetch_buffer+0
    sta word_tmp
    lda actdbg_vm_fetch_buffer+1
    sta word_tmp+1
    clc
    rts

debug_store_svc_retptr_at_word_tmp_offset:
    jsr debug_ensure_payload_room_2_at_word_tmp
    bcc :+
    sec
    rts
:   jsr debug_set_reu_params_from_word_tmp
    lda #<svc_retptr
    sta file_params+3
    lda #>svc_retptr
    sta file_params+4
    lda #$02
    sta file_params+5
    lda #$00
    sta file_params+6
    sta file_params+7
    ldx #file_params
    jsr svc_reu_write_sc0
    lda file_params+7
    cmp #tool_file_status_ok
    beq :+
    sec
    rts
:   clc
    rts

debug_ensure_scan_room_1:
    lda actdbg_vm_scan_hi
    cmp actdbg_vm_scan_end_hi
    bcc :+
    bne debug_ensure_room_fail
    lda actdbg_vm_scan_lo
    cmp actdbg_vm_scan_end_lo
    bcc :+
debug_ensure_room_fail:
    sec
    rts
:   clc
    rts

debug_ensure_scan_room_2:
    clc
    lda actdbg_vm_scan_lo
    adc #$02
    sta word_tmp
    lda actdbg_vm_scan_hi
    adc #$00
    sta word_tmp+1
    jmp debug_check_room_word_tmp

debug_ensure_scan_room_3:
    clc
    lda actdbg_vm_scan_lo
    adc #$03
    sta word_tmp
    lda actdbg_vm_scan_hi
    adc #$00
    sta word_tmp+1
debug_check_room_word_tmp:
    lda word_tmp+1
    cmp actdbg_vm_scan_end_hi
    bcc :+
    bne debug_ensure_room_fail
    lda word_tmp
    cmp actdbg_vm_scan_end_lo
    bcc :+
    beq :+
    jmp debug_ensure_room_fail
:   clc
    rts

debug_advance_scan_ptr:
    clc
    adc actdbg_vm_scan_lo
    sta actdbg_vm_scan_lo
    bcc :+
    inc actdbg_vm_scan_hi
:   rts

debug_native_print:
    jsr output_write_cstr_from_string_offset
    bcc :+
    sec
    rts
:   
    jmp refresh_output_if_visible

debug_native_printe:
    jsr output_write_cstr_from_string_offset
    bcc :+
    sec
    rts
:   
    jsr output_newline
    jmp refresh_output_if_visible

debug_native_printi:
    jsr print_u16_word_tmp_to_output
    jmp refresh_output_if_visible

debug_native_printie:
    jsr print_u16_word_tmp_to_output
    jsr output_newline
    jmp refresh_output_if_visible

refresh_output_if_visible:
    lda actdbg_view_mode
    cmp #VIEW_OUTPUT
    bne :+
    jsr show_output_screen
:   clc
    rts

output_write_cstr_from_string_offset:
    lda actdbg_vm_string_lo
    sta word_tmp
    lda actdbg_vm_string_hi
    sta word_tmp+1
output_write_cstr_loop:
    jsr debug_load_byte_at_word_tmp_to_a
    bcc :+
    sec
    rts
:   beq output_write_cstr_done
    jsr output_put_char_a
    inc word_tmp
    bne output_write_cstr_loop
    inc word_tmp+1
    jmp output_write_cstr_loop
output_write_cstr_done:
    clc
    rts

output_put_char_a:
    cmp #$0D
    beq output_put_newline
    cmp #$0A
    beq output_put_newline
    pha
    lda actdbg_output_row
    jsr load_output_row_buffer_from_reu_row_a
    pla
    jsr ascii_to_screen
    ldy actdbg_output_col
    sta actdbg_output_row_buffer,y
    lda actdbg_output_row
    jsr store_output_row_buffer_to_reu_row_a
    inc actdbg_output_col
    lda actdbg_output_col
    cmp #SCREEN_COLS
    bcc :+
output_put_newline:
    jmp output_newline
:   rts

output_newline:
    lda #$00
    sta actdbg_output_col
    lda actdbg_output_row
    cmp #SCREEN_ROWS-1
    bcs :+
    inc actdbg_output_row
:   rts

print_u16_word_tmp_to_output:
    lda #$00
    sta digit_flag
    ldx #$00
print_u16_output_loop:
    cpx #$04
    beq print_u16_output_ones
    jsr print_output_digit_divisor_x
    inx
    bne print_u16_output_loop
print_u16_output_ones:
    lda word_tmp
    clc
    adc #'0'
    jmp output_put_char_a

print_output_digit_divisor_x:
    lda #$00
    sta hex_tmp
print_output_digit_sub_loop:
    lda word_tmp+1
    cmp decimal_divisors_hi,x
    bcc print_output_digit_done
    bne :+
    lda word_tmp
    cmp decimal_divisors_lo,x
    bcc print_output_digit_done
:   sec
    lda word_tmp
    sbc decimal_divisors_lo,x
    sta word_tmp
    lda word_tmp+1
    sbc decimal_divisors_hi,x
    sta word_tmp+1
    inc hex_tmp
    bne print_output_digit_sub_loop
print_output_digit_done:
    lda digit_flag
    bne print_output_digit_emit
    lda hex_tmp
    beq print_output_digit_skip
print_output_digit_emit:
    lda hex_tmp
    clc
    adc #'0'
    jsr output_put_char_a
    lda #$01
    sta digit_flag
print_output_digit_skip:
    rts

decimal_divisors_lo:
    .byte <10000,<1000,<100,<10
decimal_divisors_hi:
    .byte >10000,>1000,>100,>10


actdbg_overlay_end:
