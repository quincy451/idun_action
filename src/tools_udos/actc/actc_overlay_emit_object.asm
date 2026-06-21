.include "actc_overlay_abi.inc"

.export actc_overlay_header
.export actc_overlay_entry
.export actc_overlay_end

.segment "CODE"

actc_overlay_header:
    .byte 'A','C','O','V'
    .byte ACTC_OVERLAY_ABI_VERSION
    .byte ACTC_OVERLAY_PASS_EMIT_OBJECT
    .word ACTC_OVERLAY_EXEC_BASE
    .word actc_overlay_entry
    .word actc_overlay_end - actc_overlay_header
    .word $0000

actc_overlay_entry:
    stx ACTC_OVERLAY_CONTEXT_ZP
    sty ACTC_OVERLAY_CONTEXT_ZP+1
    ldy #ACTC_OVERLAY_CTX_PASS_ID
    lda #ACTC_OVERLAY_PASS_EMIT_OBJECT
    sta (ACTC_OVERLAY_CONTEXT_ZP),y

    jsr build_object_content_overlay
    bcs actc_overlay_fail

    ldy #ACTC_OVERLAY_CTX_STATUS
    lda #ACTC_OVERLAY_STATUS_OK
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    clc
    lda #ACTC_OVERLAY_STATUS_OK
    rts

actc_overlay_fail:
    ldy #ACTC_OVERLAY_CTX_STATUS
    lda #ACTC_OVERLAY_STATUS_FAILED
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    sec
    lda #ACTC_OVERLAY_STATUS_FAILED
    rts

build_object_content_overlay:
    jsr emit_object_header
    jsr emit_debug_file_list
    bcs build_object_content_overlay_fail
    jsr emit_debug_proc_decl_list
    bcs build_object_content_overlay_fail
    jsr emit_debug_body_op_list
    bcs build_object_content_overlay_fail
    jsr emit_debug_var_list
    bcs build_object_content_overlay_fail
    jsr emit_export_list
    bcs build_object_content_overlay_fail
    jsr emit_body_ops_list
    bcs build_object_content_overlay_fail
    jsr emit_machine_code_list
    bcs build_object_content_overlay_fail
    jsr emit_external_list
    bcs build_object_content_overlay_fail
    jsr emit_string_list
    bcs build_object_content_overlay_fail
    jsr emit_int_list
    bcs build_object_content_overlay_fail
    jsr emit_var_list
    bcs build_object_content_overlay_fail

    lda #'k'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda #ACTC_OVERLAY_CTX_IMPORT_FLAGS_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr emit_small_decimal
    jsr emit_newline

    lda #'n'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    jsr emit_module_symbol_lower
    jsr emit_newline
    clc
    rts

build_object_content_overlay_fail:
    sec
    rts

emit_object_header:
    lda #'O'
    jsr emit_char_overlay
    lda #'B'
    jsr emit_char_overlay
    lda #'J'
    jsr emit_char_overlay
    lda #'1'
    jsr emit_char_overlay
    jsr emit_newline
    rts

emit_debug_file_list:
    lda #'f'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda #'s'
    jsr emit_char_overlay
    lda #'r'
    jsr emit_char_overlay
    lda #'c'
    jsr emit_char_overlay
    lda #'/'
    jsr emit_char_overlay
    jsr emit_module_symbol_lower
    lda #'.'
    jsr emit_char_overlay
    lda #'a'
    jsr emit_char_overlay
    lda #'c'
    jsr emit_char_overlay
    lda #'t'
    jsr emit_char_overlay
    jsr emit_newline
    clc
    rts

emit_debug_proc_decl_list:
    lda #$00
    sta entry_index_data
emit_debug_proc_decl_list_loop:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_debug_proc_decl_list_done
    lda #'q'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda entry_index_data
    jsr emit_small_decimal
    lda #' '
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_LOAD_PROC_DEBUG_LINECOL_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_PROC_DEBUG_LINECOL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    lda #' '
    jsr emit_char_overlay
    lda #ACTC_OVERLAY_CTX_PROC_DEBUG_LINECOL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$02
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    jsr emit_newline
    inc entry_index_data
    jmp emit_debug_proc_decl_list_loop
emit_debug_proc_decl_list_done:
    clc
    rts

emit_debug_body_op_list:
    lda #$00
    sta entry_index_data
emit_debug_body_op_list_proc_loop:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    bne :+
    jmp emit_debug_body_op_list_done
:   
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_BODY_DEBUG_COUNT_PTR_LO
    jsr load_indexed_byte_from_context_ptr
    sta body_debug_count_local
    lda #$00
    sta body_debug_index_data
emit_debug_body_op_list_op_loop:
    lda body_debug_count_local
    cmp body_debug_index_data
    beq emit_debug_body_op_list_next_proc
    lda #'l'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda entry_index_data
    jsr emit_small_decimal
    lda #' '
    jsr emit_char_overlay
    lda body_debug_index_data
    jsr emit_small_decimal
    lda #' '
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    ldy body_debug_index_data
    lda #ACTC_OVERLAY_CTX_LOAD_BODY_DEBUG_LINECOL_FN_LO
    jsr call_proc_op_context_function
    lda #ACTC_OVERLAY_CTX_PROC_DEBUG_LINECOL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    lda #' '
    jsr emit_char_overlay
    lda #ACTC_OVERLAY_CTX_PROC_DEBUG_LINECOL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$02
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    jsr emit_newline
    inc body_debug_index_data
    jmp emit_debug_body_op_list_op_loop
emit_debug_body_op_list_next_proc:
    inc entry_index_data
    jmp emit_debug_body_op_list_proc_loop
emit_debug_body_op_list_done:
    clc
    rts

emit_debug_var_list:
    ldy #ACTC_OVERLAY_CTX_LOAD_VAR_DEBUG_LINECOL_FN_LO
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta saved_a_local
    ldy #ACTC_OVERLAY_CTX_LOAD_VAR_DEBUG_LINECOL_FN_HI
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    ora saved_a_local
    bne :+
    jmp emit_debug_var_list_done
:
    lda #$00
    sta entry_index_data
emit_debug_global_var_list_loop:
    lda #ACTC_OVERLAY_CTX_MODULE_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_debug_global_var_list_done
    lda #'V'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda #'g'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    jsr emit_debug_var_type_for_x
    lda entry_index_data
    jsr emit_small_decimal
    lda #' '
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_LOAD_VAR_DEBUG_LINECOL_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_PROC_DEBUG_LINECOL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    lda #' '
    jsr emit_char_overlay
    lda #ACTC_OVERLAY_CTX_PROC_DEBUG_LINECOL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$02
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    jsr emit_newline
    inc entry_index_data
    jmp emit_debug_global_var_list_loop
emit_debug_global_var_list_done:
    lda #$00
    sta entry_index_data
emit_debug_proc_var_list_loop:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_debug_var_list_done
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_LOAD_PROC_META_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_PROC_META_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta body_debug_count_local
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta proc_var_base_local
    lda #'p'
    sta proc_var_scope_local
    jsr emit_debug_proc_var_records_for_current_proc
    lda #ACTC_OVERLAY_CTX_PROC_META_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$02
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta body_debug_count_local
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta proc_var_base_local
    lda #'l'
    sta proc_var_scope_local
    jsr emit_debug_proc_var_records_for_current_proc
    inc entry_index_data
    jmp emit_debug_proc_var_list_loop
emit_debug_var_list_done:
    clc
    rts

emit_debug_proc_var_records_for_current_proc:
    lda body_debug_count_local
    bne :+
    jmp emit_debug_proc_var_records_done
:
    lda #$00
    sta body_debug_index_data
emit_debug_proc_var_records_loop:
    lda body_debug_index_data
    cmp body_debug_count_local
    bne :+
    jmp emit_debug_proc_var_records_done
: 
    lda proc_var_base_local
    clc
    adc body_debug_index_data
    sta proc_var_index_local
    lda #'V'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda proc_var_scope_local
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx proc_var_index_local
    jsr emit_debug_var_type_for_x
    lda entry_index_data
    jsr emit_small_decimal
    lda #' '
    jsr emit_char_overlay
    lda proc_var_index_local
    jsr emit_small_decimal
    lda #' '
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx proc_var_index_local
    lda #ACTC_OVERLAY_CTX_LOAD_VAR_DEBUG_LINECOL_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_PROC_DEBUG_LINECOL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    lda #' '
    jsr emit_char_overlay
    lda #ACTC_OVERLAY_CTX_PROC_DEBUG_LINECOL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$02
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    jsr emit_newline
    inc body_debug_index_data
    jmp emit_debug_proc_var_records_loop
emit_debug_proc_var_records_done:
    clc
    rts

emit_debug_var_type_for_x:
    pha
    txa
    pha
    lda #ACTC_OVERLAY_CTX_LOAD_VAR_META_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_VAR_META_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$03
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    pla
    tax
    pla
    rts

emit_export_list:
    jsr is_main_local_call_sequence_machine_object
    bcc emit_export_list_not_local_call_sequence
    jmp emit_machine_local_call_sequence_export_list
emit_export_list_not_local_call_sequence:
    jsr is_main_local_external_call_sequence_machine_object
    bcc emit_export_list_not_local_external_call_sequence
    jmp emit_machine_local_external_call_sequence_export_list
emit_export_list_not_local_external_call_sequence:
    jsr is_main_pure_external_call_sequence_machine_object
    bcc emit_export_list_standard
    jmp emit_machine_external_call_sequence_export_list
emit_export_list_standard:
    lda #$00
    sta entry_index_data
emit_export_list_loop:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_export_list_done
    lda #'x'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_EXPORT_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr emit_lower_scan_zp_string
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_LOAD_LAYOUT_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_LAYOUT_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    lda #' '
    jsr emit_char_overlay
    lda #ACTC_OVERLAY_CTX_LAYOUT_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$02
    lda entry_index_data
    bne emit_export_list_layout_size
    jsr is_empty_main_machine_object
    bcc emit_export_list_layout_size
    lda #16
    ldy #$00
    jsr emit_word_decimal
    jmp emit_export_list_newline
emit_export_list_layout_size:
    lda #ACTC_OVERLAY_CTX_LAYOUT_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$02
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
emit_export_list_newline:
    jsr emit_newline
    inc entry_index_data
    jmp emit_export_list_loop
emit_export_list_done:
    clc
    rts

emit_machine_external_call_sequence_export_list:
    ldx #$00
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr emit_count_external_call_sequence_body
    lda #16
    ldx body_debug_count_local
emit_machine_external_call_sequence_size_loop:
    cpx #$00
    beq emit_machine_external_call_sequence_size_done
    clc
    adc #$03
    dex
    bne emit_machine_external_call_sequence_size_loop
emit_machine_external_call_sequence_size_done:
    ldx #$00
    ldy #$00
    sty word_value_lo
    sty word_value_hi
    jsr emit_machine_export_line
    clc
    rts

emit_machine_local_external_call_sequence_export_list:
    jsr store_last_local_call_sequence_export_index
    lda proc_var_index_local
    sta entry_index_data
emit_machine_local_external_call_sequence_export_loop:
    lda entry_index_data
    cmp proc_var_index_local
    bne emit_machine_local_external_call_sequence_export_helper
    lda #$00
    tay
    sta word_value_lo
    sta word_value_hi
    jsr compute_local_external_call_sequence_total_size
    ldx entry_index_data
    jsr emit_machine_export_line
    jmp emit_machine_local_external_call_sequence_export_next
emit_machine_local_external_call_sequence_export_helper:
    lda entry_index_data
    sta proc_var_scope_local
    jsr compute_local_external_call_sequence_offset_for_proc_var_scope
    lda proc_var_base_local
    sta word_value_lo
    lda #$00
    sta word_value_hi
    ldx entry_index_data
    jsr compute_local_external_call_sequence_helper_size_for_x
    ldx entry_index_data
    jsr emit_machine_export_line
emit_machine_local_external_call_sequence_export_next:
    lda entry_index_data
    beq emit_machine_local_external_call_sequence_export_done
    dec entry_index_data
    jmp emit_machine_local_external_call_sequence_export_loop
emit_machine_local_external_call_sequence_export_done:
    clc
    rts

emit_machine_local_call_sequence_export_list:
    jsr store_last_local_call_sequence_export_index
    lda proc_var_index_local
    sta entry_index_data
emit_machine_local_call_sequence_export_loop:
    lda entry_index_data
    cmp proc_var_index_local
    bne emit_machine_local_call_sequence_export_helper
    lda #$00
    tay
    sta word_value_lo
    sta word_value_hi
    jsr compute_local_call_sequence_total_size
    ldx entry_index_data
    jsr emit_machine_export_line
    jmp emit_machine_local_call_sequence_export_next
emit_machine_local_call_sequence_export_helper:
    lda entry_index_data
    sta proc_var_scope_local
    jsr compute_local_call_sequence_offset_for_proc_var_scope
    lda proc_var_base_local
    sta word_value_lo
    lda #$00
    sta word_value_hi
    ldx entry_index_data
    jsr compute_local_call_sequence_helper_size_for_x
    ldx entry_index_data
    jsr emit_machine_export_line
emit_machine_local_call_sequence_export_next:
    lda entry_index_data
    beq emit_machine_local_call_sequence_export_done
    dec entry_index_data
    jmp emit_machine_local_call_sequence_export_loop
emit_machine_local_call_sequence_export_done:
    clc
    rts

emit_machine_export_line:
    sta compare_char_local
    stx saved_x_local
    lda #'x'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx saved_x_local
    lda #ACTC_OVERLAY_CTX_SET_EXPORT_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr emit_lower_scan_zp_string
    lda #' '
    jsr emit_char_overlay
    lda word_value_lo
    ldy word_value_hi
    jsr emit_word_decimal
    lda #' '
    jsr emit_char_overlay
    lda compare_char_local
    ldy #$00
    jsr emit_word_decimal
    jmp emit_newline

emit_body_ops_list:
    jsr is_main_local_call_sequence_machine_object
    bcc emit_body_ops_list_not_local_call_sequence
    jsr emit_machine_local_call_sequence_body_marker_list
    clc
    rts
emit_body_ops_list_not_local_call_sequence:
    jsr is_main_local_external_call_sequence_machine_object
    bcc emit_body_ops_list_not_local_external_call_sequence
    jsr emit_machine_local_external_call_sequence_body_marker_list
    clc
    rts
emit_body_ops_list_not_local_external_call_sequence:
    jsr is_main_pure_external_call_sequence_machine_object
    bcc emit_body_ops_list_standard
    jsr emit_machine_external_call_sequence_body_marker_line
    clc
    rts
emit_body_ops_list_standard:
    lda #$00
    sta entry_index_data
emit_body_ops_list_loop:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_body_ops_list_done
    lda #'b'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda entry_index_data
    bne emit_body_ops_list_portable
    jsr is_empty_main_machine_object
    bcc emit_body_ops_list_portable
    lda #'M'
    jsr emit_char_overlay
    jsr emit_newline
    inc entry_index_data
    jmp emit_body_ops_list_loop
emit_body_ops_list_portable:
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    ldy #$00
emit_body_ops_list_body_loop:
    jsr emit_object_peek_payload_y
    beq emit_body_ops_list_ret
    jsr emit_char_overlay
    iny
    bne emit_body_ops_list_body_loop
emit_body_ops_list_ret:
    cpy #$00
    beq emit_body_ops_list_emit_ret
    dey
    jsr emit_object_peek_payload_y
    cmp #'r'
    beq emit_body_ops_list_newline
emit_body_ops_list_emit_ret:
    lda #'r'
    jsr emit_char_overlay
emit_body_ops_list_newline:
    jsr emit_newline
    inc entry_index_data
    jmp emit_body_ops_list_loop
emit_body_ops_list_done:
    clc
    rts

emit_machine_code_list:
    jsr is_empty_main_machine_object
    bcc emit_machine_code_list_check_local_call
    lda #<empty_main_machine_record
    sta ACTC_OVERLAY_SCAN_ZP
    lda #>empty_main_machine_record
    sta ACTC_OVERLAY_SCAN_ZP+1
    jsr emit_scan_zp_string
    jsr emit_newline
    jmp emit_machine_code_list_done
emit_machine_code_list_check_local_call:
    jsr is_main_local_call_sequence_machine_object
    bcc emit_machine_code_list_check_local_external_call
    jsr emit_machine_local_call_sequence_code_list
    jmp emit_machine_code_list_done
emit_machine_code_list_check_local_external_call:
    jsr is_main_local_external_call_sequence_machine_object
    bcc emit_machine_code_list_check_external_call_sequence
    jsr emit_machine_local_external_call_sequence_code_list
    jmp emit_machine_code_list_done
emit_machine_code_list_check_external_call_sequence:
    jsr is_main_pure_external_call_sequence_machine_object
    bcc emit_machine_code_list_done
    jsr emit_machine_external_call_sequence_code_list
    jmp emit_machine_code_list_done
emit_machine_code_list_done:
    clc
    rts

emit_machine_external_call_sequence_code_list:
    lda #'m'
    jsr emit_char_overlay
    ldx #$00
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    lda #$00
    sta body_debug_index_data
emit_machine_external_call_sequence_code_loop:
    ldy body_debug_index_data
    jsr emit_object_peek_payload_y
    cmp #'r'
    beq emit_machine_external_call_sequence_code_epilogue
    cmp #'u'
    bne emit_machine_external_call_sequence_code_done
    jsr emit_machine_external_jsr_placeholder_bytes
    inc body_debug_index_data
    inc body_debug_index_data
    jmp emit_machine_external_call_sequence_code_loop
emit_machine_external_call_sequence_code_epilogue:
    lda #<external_call_sequence_epilogue_bytes
    sta ACTC_OVERLAY_SCAN_ZP
    lda #>external_call_sequence_epilogue_bytes
    sta ACTC_OVERLAY_SCAN_ZP+1
    jsr emit_scan_zp_string
    jsr emit_newline
    jsr emit_machine_external_call_sequence_reloc_list
emit_machine_external_call_sequence_code_done:
    clc
    rts

emit_machine_external_jsr_placeholder_bytes:
    lda #' '
    jsr emit_char_overlay
    lda #'2'
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
    lda #'0'
    jmp emit_char_overlay

emit_machine_external_call_sequence_reloc_list:
    ldx #$00
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    lda #$00
    sta body_debug_index_data
    lda #$01
    sta proc_var_base_local
    lda #$00
    sta proc_var_scope_local
emit_machine_external_call_sequence_reloc_loop:
    ldy body_debug_index_data
    jsr emit_object_peek_payload_y
    cmp #'r'
    beq emit_machine_external_call_sequence_reloc_done
    cmp #'u'
    bne emit_machine_external_call_sequence_reloc_done
    inc body_debug_index_data
    ldy body_debug_index_data
    jsr emit_object_peek_payload_y
    sta proc_var_index_local
    lda #'r'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda proc_var_base_local
    ldy proc_var_scope_local
    jsr emit_word_decimal
    lda #' '
    jsr emit_char_overlay
    lda #'u'
    jsr emit_char_overlay
    lda proc_var_index_local
    jsr emit_char_overlay
    jsr emit_newline
    clc
    lda proc_var_base_local
    adc #$03
    sta proc_var_base_local
    bcc :+
    inc proc_var_scope_local
:
    inc body_debug_index_data
    jmp emit_machine_external_call_sequence_reloc_loop
emit_machine_external_call_sequence_reloc_done:
    rts

emit_machine_local_external_call_sequence_code_list:
    jsr store_last_local_call_sequence_export_index
    lda #'m'
    jsr emit_char_overlay
    lda proc_var_index_local
    sta entry_index_data
emit_machine_local_external_call_sequence_code_export_loop:
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    lda #$00
    sta body_debug_index_data
    jsr emit_machine_local_external_call_sequence_body_jsrs
    lda entry_index_data
    cmp proc_var_index_local
    bne emit_machine_local_external_call_sequence_code_helper_return
    lda #<external_call_sequence_epilogue_bytes
    sta ACTC_OVERLAY_SCAN_ZP
    lda #>external_call_sequence_epilogue_bytes
    sta ACTC_OVERLAY_SCAN_ZP+1
    jsr emit_scan_zp_string
    jmp emit_machine_local_external_call_sequence_code_next
emit_machine_local_external_call_sequence_code_helper_return:
    lda #' '
    jsr emit_char_overlay
    lda #'6'
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
emit_machine_local_external_call_sequence_code_next:
    lda entry_index_data
    beq emit_machine_local_external_call_sequence_code_done
    dec entry_index_data
    jmp emit_machine_local_external_call_sequence_code_export_loop
emit_machine_local_external_call_sequence_code_done:
    jsr emit_newline
    jsr emit_machine_local_external_call_sequence_reloc_list
    clc
    rts

emit_machine_local_external_call_sequence_body_jsrs:
    ldy body_debug_index_data
    jsr emit_object_peek_payload_y
    cmp #'c'
    beq emit_machine_local_external_call_sequence_body_jsrs_local
    cmp #'u'
    beq emit_machine_local_external_call_sequence_body_jsrs_external
    rts
emit_machine_local_external_call_sequence_body_jsrs_local:
    inc body_debug_index_data
    ldy body_debug_index_data
    jsr emit_object_peek_payload_y
    sec
    sbc #'0'
    sta proc_var_scope_local
    jsr compute_local_external_call_sequence_offset_for_proc_var_scope
    jsr emit_machine_local_jsr_to_proc_var_base
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    inc body_debug_index_data
    jmp emit_machine_local_external_call_sequence_body_jsrs
emit_machine_local_external_call_sequence_body_jsrs_external:
    jsr emit_machine_external_jsr_placeholder_bytes
    inc body_debug_index_data
    inc body_debug_index_data
    jmp emit_machine_local_external_call_sequence_body_jsrs

emit_machine_local_jsr_to_proc_var_base:
    lda #' '
    jsr emit_char_overlay
    lda #'2'
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda proc_var_base_local
    jsr emit_hex_byte_overlay
    lda #' '
    jsr emit_char_overlay
    lda #'1'
    jsr emit_char_overlay
    lda #'0'
    jmp emit_char_overlay

emit_machine_local_external_call_sequence_reloc_list:
    jsr store_last_local_call_sequence_export_index
    lda #$00
    sta proc_var_base_local
    sta proc_var_scope_local
    lda proc_var_index_local
    sta entry_index_data
emit_machine_local_external_call_sequence_reloc_export_loop:
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    lda #$00
    sta body_debug_index_data
    jsr emit_machine_local_external_call_sequence_relocs_for_body
    lda entry_index_data
    cmp proc_var_index_local
    bne emit_machine_local_external_call_sequence_reloc_helper_size
    jsr compute_local_external_call_sequence_main_code_size
    jmp emit_machine_local_external_call_sequence_reloc_after_size
emit_machine_local_external_call_sequence_reloc_helper_size:
    ldx entry_index_data
    jsr compute_local_external_call_sequence_helper_size_for_x
emit_machine_local_external_call_sequence_reloc_after_size:
    clc
    adc proc_var_base_local
    sta proc_var_base_local
    bcc :+
    inc proc_var_scope_local
:
    lda entry_index_data
    beq emit_machine_local_external_call_sequence_reloc_done
    dec entry_index_data
    jmp emit_machine_local_external_call_sequence_reloc_export_loop
emit_machine_local_external_call_sequence_reloc_done:
    rts

emit_machine_local_external_call_sequence_relocs_for_body:
    lda #$00
    sta body_debug_count_local
emit_machine_local_external_call_sequence_relocs_for_body_loop:
    ldy body_debug_index_data
    jsr emit_object_peek_payload_y
    cmp #'c'
    beq emit_machine_local_external_call_sequence_reloc_local
    cmp #'u'
    beq emit_machine_local_external_call_sequence_reloc_external
    cmp #'r'
    beq emit_machine_local_external_call_sequence_reloc_body_done
    rts
emit_machine_local_external_call_sequence_reloc_local:
    inc body_debug_index_data
    inc body_debug_index_data
    jsr advance_local_external_reloc_body_offset_by_three
    jmp emit_machine_local_external_call_sequence_relocs_for_body_loop
emit_machine_local_external_call_sequence_reloc_external:
    inc body_debug_index_data
    ldy body_debug_index_data
    jsr emit_object_peek_payload_y
    sta compare_char_local
    lda #'r'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldy proc_var_scope_local
    lda proc_var_base_local
    clc
    adc body_debug_count_local
    bcc :+
    iny
:
    clc
    adc #$01
    bcc :+
    iny
:
    jsr emit_word_decimal
    lda #' '
    jsr emit_char_overlay
    lda #'u'
    jsr emit_char_overlay
    lda compare_char_local
    jsr emit_char_overlay
    jsr emit_newline
    inc body_debug_index_data
    jsr advance_local_external_reloc_body_offset_by_three
    jmp emit_machine_local_external_call_sequence_relocs_for_body_loop
emit_machine_local_external_call_sequence_reloc_body_done:
    rts

advance_local_external_reloc_body_offset_by_three:
    clc
    lda body_debug_count_local
    adc #$03
    sta body_debug_count_local
    rts

emit_machine_local_call_sequence_code_list:
    jsr store_last_local_call_sequence_export_index
    lda #'m'
    jsr emit_char_overlay
    lda proc_var_index_local
    sta entry_index_data
emit_machine_local_call_sequence_code_export_loop:
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    lda #$00
    sta body_debug_index_data
    jsr emit_machine_local_call_sequence_body_jsrs
    lda entry_index_data
    cmp proc_var_index_local
    bne emit_machine_local_call_sequence_code_helper_return
    lda #<external_call_sequence_epilogue_bytes
    sta ACTC_OVERLAY_SCAN_ZP
    lda #>external_call_sequence_epilogue_bytes
    sta ACTC_OVERLAY_SCAN_ZP+1
    jsr emit_scan_zp_string
    jmp emit_machine_local_call_sequence_code_next
emit_machine_local_call_sequence_code_helper_return:
    lda #' '
    jsr emit_char_overlay
    lda #'6'
    jsr emit_char_overlay
    lda #'0'
    jsr emit_char_overlay
emit_machine_local_call_sequence_code_next:
    lda entry_index_data
    beq emit_machine_local_call_sequence_code_done
    dec entry_index_data
    jmp emit_machine_local_call_sequence_code_export_loop
emit_machine_local_call_sequence_code_done:
    jsr emit_newline
    clc
    rts

emit_machine_local_call_sequence_body_jsrs:
    ldy body_debug_index_data
    jsr emit_object_peek_payload_y
    cmp #'c'
    bne emit_machine_local_call_sequence_body_jsrs_done
    inc body_debug_index_data
    ldy body_debug_index_data
    jsr emit_object_peek_payload_y
    sec
    sbc #'0'
    sta proc_var_scope_local
    jsr compute_local_call_sequence_offset_for_proc_var_scope
    jsr emit_machine_local_jsr_to_proc_var_base
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    inc body_debug_index_data
    jmp emit_machine_local_call_sequence_body_jsrs
emit_machine_local_call_sequence_body_jsrs_done:
    rts

emit_machine_local_call_sequence_body_marker_list:
    lda #$00
    sta entry_index_data
emit_machine_local_call_sequence_body_marker_loop:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_machine_local_call_sequence_body_marker_done
    jsr emit_machine_body_marker_line
    inc entry_index_data
    jmp emit_machine_local_call_sequence_body_marker_loop
emit_machine_local_call_sequence_body_marker_done:
    rts

store_last_local_call_sequence_export_index:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    sec
    sbc #$01
    sta proc_var_index_local
    rts

compute_local_call_sequence_total_size:
    jsr compute_local_call_sequence_main_code_size
    sta proc_var_base_local
    lda proc_var_index_local
    beq compute_local_call_sequence_total_size_done
    sec
    sbc #$01
    sta compare_char_local
compute_local_call_sequence_total_size_loop:
    ldx compare_char_local
    jsr compute_local_call_sequence_helper_size_for_x
    clc
    adc proc_var_base_local
    sta proc_var_base_local
    lda compare_char_local
    beq compute_local_call_sequence_total_size_done
    dec compare_char_local
    jmp compute_local_call_sequence_total_size_loop
compute_local_call_sequence_total_size_done:
    lda proc_var_base_local
    rts

compute_local_call_sequence_main_code_size:
    ldx proc_var_index_local
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr emit_count_local_call_sequence_body
    lda #16
    jmp add_three_times_body_debug_count

compute_local_call_sequence_helper_size_for_x:
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr emit_count_local_call_sequence_body
    lda #$01
    jmp add_three_times_body_debug_count

add_three_times_body_debug_count:
    ldx body_debug_count_local
add_three_times_body_debug_count_loop:
    cpx #$00
    beq add_three_times_body_debug_count_done
    clc
    adc #$03
    dex
    jmp add_three_times_body_debug_count_loop
add_three_times_body_debug_count_done:
    rts

compute_local_call_sequence_offset_for_proc_var_scope:
    lda proc_var_scope_local
    cmp proc_var_index_local
    bne compute_local_call_sequence_offset_for_helper
    lda #$00
    sta proc_var_base_local
    rts
compute_local_call_sequence_offset_for_helper:
    jsr compute_local_call_sequence_main_code_size
    sta proc_var_base_local
    lda proc_var_index_local
    sec
    sbc #$01
    sta compare_char_local
compute_local_call_sequence_offset_for_helper_loop:
    lda compare_char_local
    cmp proc_var_scope_local
    beq compute_local_call_sequence_offset_for_helper_done
    ldx compare_char_local
    jsr compute_local_call_sequence_helper_size_for_x
    clc
    adc proc_var_base_local
    sta proc_var_base_local
    dec compare_char_local
    jmp compute_local_call_sequence_offset_for_helper_loop
compute_local_call_sequence_offset_for_helper_done:
    rts

compute_local_external_call_sequence_total_size:
    jsr compute_local_external_call_sequence_main_code_size
    sta proc_var_base_local
    lda proc_var_index_local
    beq compute_local_external_call_sequence_total_size_done
    sec
    sbc #$01
    sta compare_char_local
compute_local_external_call_sequence_total_size_loop:
    ldx compare_char_local
    jsr compute_local_external_call_sequence_helper_size_for_x
    clc
    adc proc_var_base_local
    sta proc_var_base_local
    lda compare_char_local
    beq compute_local_external_call_sequence_total_size_done
    dec compare_char_local
    jmp compute_local_external_call_sequence_total_size_loop
compute_local_external_call_sequence_total_size_done:
    lda proc_var_base_local
    rts

compute_local_external_call_sequence_main_code_size:
    ldx proc_var_index_local
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr emit_count_local_external_call_sequence_body
    lda #16
    jmp add_three_times_body_debug_count

compute_local_external_call_sequence_helper_size_for_x:
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr emit_count_local_external_call_sequence_body
    lda #$01
    jmp add_three_times_body_debug_count

compute_local_external_call_sequence_offset_for_proc_var_scope:
    lda proc_var_scope_local
    cmp proc_var_index_local
    bne compute_local_external_call_sequence_offset_for_helper
    lda #$00
    sta proc_var_base_local
    rts
compute_local_external_call_sequence_offset_for_helper:
    jsr compute_local_external_call_sequence_main_code_size
    sta proc_var_base_local
    lda proc_var_index_local
    sec
    sbc #$01
    sta compare_char_local
compute_local_external_call_sequence_offset_for_helper_loop:
    lda compare_char_local
    cmp proc_var_scope_local
    beq compute_local_external_call_sequence_offset_for_helper_done
    ldx compare_char_local
    jsr compute_local_external_call_sequence_helper_size_for_x
    clc
    adc proc_var_base_local
    sta proc_var_base_local
    dec compare_char_local
    jmp compute_local_external_call_sequence_offset_for_helper_loop
compute_local_external_call_sequence_offset_for_helper_done:
    rts

emit_machine_local_external_call_sequence_body_marker_list:
    jsr store_last_local_call_sequence_export_index
    jsr emit_machine_local_external_call_sequence_flat_body_marker_line
    lda proc_var_index_local
    beq emit_machine_local_external_call_sequence_body_marker_done
    sec
    sbc #$01
    sta entry_index_data
emit_machine_local_external_call_sequence_body_marker_loop:
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr emit_machine_local_external_call_sequence_body_marker_line
    lda entry_index_data
    beq emit_machine_local_external_call_sequence_body_marker_done
    dec entry_index_data
    jmp emit_machine_local_external_call_sequence_body_marker_loop
emit_machine_local_external_call_sequence_body_marker_done:
    rts

emit_machine_local_external_call_sequence_flat_body_marker_line:
    lda #'b'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda proc_var_index_local
    sta entry_index_data
emit_machine_local_external_call_sequence_flat_body_marker_loop:
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr emit_machine_local_external_call_sequence_body_marker_refs
    lda entry_index_data
    bne emit_machine_local_external_call_sequence_flat_body_marker_continue
    jmp emit_machine_local_external_call_sequence_body_marker_machine
emit_machine_local_external_call_sequence_flat_body_marker_continue:
    dec entry_index_data
    jmp emit_machine_local_external_call_sequence_flat_body_marker_loop

emit_machine_local_external_call_sequence_body_marker_line:
    lda #'b'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda #$00
    sta body_marker_visit_mask
    ldx entry_index_data
    jsr emit_machine_local_external_call_sequence_body_marker_closure_refs_for_x
    jmp emit_machine_local_external_call_sequence_body_marker_machine

emit_machine_local_external_call_sequence_body_marker_closure_refs_for_x:
    stx saved_x_local
    jsr emit_machine_local_external_call_sequence_body_marker_index_mask
    and body_marker_visit_mask
    beq emit_machine_local_external_call_sequence_body_marker_closure_refs_new
    rts
emit_machine_local_external_call_sequence_body_marker_closure_refs_new:
    jsr emit_machine_local_external_call_sequence_body_marker_index_mask
    ora body_marker_visit_mask
    sta body_marker_visit_mask
    ldx saved_x_local
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr emit_machine_local_external_call_sequence_body_marker_refs
    ldy #$00
emit_machine_local_external_call_sequence_body_marker_closure_refs_loop:
    jsr emit_object_peek_payload_y
    cmp #'c'
    beq emit_machine_local_external_call_sequence_body_marker_closure_refs_local
    cmp #'u'
    beq emit_machine_local_external_call_sequence_body_marker_closure_refs_skip_external
    rts
emit_machine_local_external_call_sequence_body_marker_closure_refs_local:
    iny
    jsr emit_object_peek_payload_y
    sec
    sbc #'0'
    sta proc_var_scope_local
    iny
    tya
    pha
    lda ACTC_OVERLAY_SCAN_ZP
    pha
    lda ACTC_OVERLAY_SCAN_ZP+1
    pha
    ldx proc_var_scope_local
    jsr emit_machine_local_external_call_sequence_body_marker_closure_refs_for_x
    pla
    sta ACTC_OVERLAY_SCAN_ZP+1
    pla
    sta ACTC_OVERLAY_SCAN_ZP
    pla
    tay
    jmp emit_machine_local_external_call_sequence_body_marker_closure_refs_loop
emit_machine_local_external_call_sequence_body_marker_closure_refs_skip_external:
    iny
    iny
    jmp emit_machine_local_external_call_sequence_body_marker_closure_refs_loop

emit_machine_local_external_call_sequence_body_marker_index_mask:
    lda #$01
    ldx saved_x_local
    beq emit_machine_local_external_call_sequence_body_marker_index_mask_done
emit_machine_local_external_call_sequence_body_marker_index_mask_loop:
    asl a
    dex
    bne emit_machine_local_external_call_sequence_body_marker_index_mask_loop
emit_machine_local_external_call_sequence_body_marker_index_mask_done:
    rts

emit_machine_local_external_call_sequence_body_marker_refs:
    ldy #$00
emit_machine_local_external_call_sequence_body_marker_line_loop:
    jsr emit_object_peek_payload_y
    cmp #'c'
    beq emit_machine_local_external_call_sequence_body_marker_line_local
    cmp #'u'
    beq emit_machine_local_external_call_sequence_body_marker_line_external
    jmp emit_machine_local_external_call_sequence_body_marker_line_machine
emit_machine_local_external_call_sequence_body_marker_line_local:
    iny
    iny
    jmp emit_machine_local_external_call_sequence_body_marker_line_loop
emit_machine_local_external_call_sequence_body_marker_line_external:
    lda #'u'
    jsr emit_char_overlay
    iny
    jsr emit_object_peek_payload_y
    jsr emit_char_overlay
    iny
    jmp emit_machine_local_external_call_sequence_body_marker_line_loop
emit_machine_local_external_call_sequence_body_marker_line_machine:
    rts

emit_machine_local_external_call_sequence_body_marker_machine:
    lda #'M'
    jsr emit_char_overlay
    jsr emit_newline
    rts

emit_external_list:
    lda #$00
    sta entry_index_data
emit_external_list_loop:
    lda #ACTC_OVERLAY_CTX_EXTERN_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_external_list_done
    lda #'u'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_EXTERNAL_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr emit_lower_scan_zp_string
    jsr emit_newline
    inc entry_index_data
    jmp emit_external_list_loop
emit_external_list_done:
    clc
    rts

emit_string_list:
    lda #$00
    sta entry_index_data
emit_string_list_loop:
    lda #ACTC_OVERLAY_CTX_STRING_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_string_list_done
    lda #'s'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_STRING_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr emit_scan_zp_string
    jsr emit_newline
    inc entry_index_data
    jmp emit_string_list_loop
emit_string_list_done:
    clc
    rts

emit_int_list:
    lda #$00
    sta entry_index_data
emit_int_list_loop:
    lda #ACTC_OVERLAY_CTX_INT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_int_list_done
    lda #'i'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_LOAD_INT_LITERAL_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_INT_LITERAL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    jsr emit_newline
    inc entry_index_data
    jmp emit_int_list_loop
emit_int_list_done:
    clc
    rts

emit_var_list:
    lda #$00
    sta entry_index_data
emit_var_list_loop:
    lda #ACTC_OVERLAY_CTX_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_var_list_done
    lda #'v'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_VAR_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr emit_lower_scan_zp_string
    lda #' '
    jsr emit_char_overlay
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_LOAD_VAR_META_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_VAR_META_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$01
    lda (ACTC_OVERLAY_WORK_ZP),y
    bne emit_var_list_bad
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr emit_small_decimal
    lda #ACTC_OVERLAY_CTX_VAR_META_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$02
    lda (ACTC_OVERLAY_WORK_ZP),y
    cmp #$02
    beq emit_var_list_newline
    pha
    lda #' '
    jsr emit_char_overlay
    pla
    jsr emit_small_decimal
emit_var_list_newline:
    jsr emit_newline
    inc entry_index_data
    jmp emit_var_list_loop
emit_var_list_bad:
    ldy #ACTC_OVERLAY_CTX_DIAG_PTR_LO
    lda #<msg_bad_var
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    ldy #ACTC_OVERLAY_CTX_DIAG_PTR_HI
    lda #>msg_bad_var
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    sec
    rts
emit_var_list_done:
    clc
    rts

emit_module_symbol_lower:
    lda #ACTC_OVERLAY_CTX_MODULE_NAME_PTR_LO
    jsr load_context_ptr_to_scan_zp
    jmp emit_lower_scan_zp_string

emit_scan_zp_string:
    ldy #$00
emit_scan_zp_string_loop:
    jsr emit_object_peek_payload_y
    beq emit_scan_zp_string_done
    jsr emit_char_overlay
    iny
    bne emit_scan_zp_string_loop
emit_scan_zp_string_done:
    rts

emit_lower_scan_zp_string:
    ldy #$00
emit_lower_scan_zp_string_loop:
    jsr emit_object_peek_payload_y
    beq emit_lower_scan_zp_string_done
    jsr lowercase_ascii_overlay
    jsr emit_char_overlay
    iny
    bne emit_lower_scan_zp_string_loop
emit_lower_scan_zp_string_done:
    rts

is_empty_main_machine_object:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp #$01
    bne is_empty_main_machine_object_no
    lda #ACTC_OVERLAY_CTX_EXTERN_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_empty_main_machine_object_no
    lda #ACTC_OVERLAY_CTX_STRING_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_empty_main_machine_object_no
    lda #ACTC_OVERLAY_CTX_INT_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_empty_main_machine_object_no
    lda #ACTC_OVERLAY_CTX_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_empty_main_machine_object_no
    lda #ACTC_OVERLAY_CTX_MODULE_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_empty_main_machine_object_no
    lda #ACTC_OVERLAY_CTX_MODULE_NAME_PTR_LO
    jsr load_context_ptr_to_scan_zp
    jsr scan_zp_is_main_symbol
    bcc is_empty_main_machine_object_no
    ldx #$00
    lda #ACTC_OVERLAY_CTX_SET_EXPORT_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr scan_zp_is_main_symbol
    bcc is_empty_main_machine_object_no
    ldx #$00
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    ldy #$00
    jsr emit_object_peek_payload_y
    beq is_empty_main_machine_object_yes
    cmp #'r'
    bne is_empty_main_machine_object_no
    iny
    jsr emit_object_peek_payload_y
    bne is_empty_main_machine_object_no
is_empty_main_machine_object_yes:
    sec
    rts
is_empty_main_machine_object_no:
    clc
    rts

scan_zp_is_main_symbol:
    ldy #$00
    jsr emit_object_peek_payload_y
    jsr lowercase_ascii_overlay
    cmp #'m'
    bne scan_zp_is_main_symbol_no
    iny
    jsr emit_object_peek_payload_y
    jsr lowercase_ascii_overlay
    cmp #'a'
    bne scan_zp_is_main_symbol_no
    iny
    jsr emit_object_peek_payload_y
    jsr lowercase_ascii_overlay
    cmp #'i'
    bne scan_zp_is_main_symbol_no
    iny
    jsr emit_object_peek_payload_y
    jsr lowercase_ascii_overlay
    cmp #'n'
    bne scan_zp_is_main_symbol_no
    iny
    jsr emit_object_peek_payload_y
    bne scan_zp_is_main_symbol_no
    sec
    rts
scan_zp_is_main_symbol_no:
    clc
    rts

scan_zp_is_return_body:
    ldy #$00
    jsr emit_object_peek_payload_y
    beq scan_zp_is_return_body_yes
    cmp #'r'
    bne scan_zp_is_return_body_no
    iny
    jsr emit_object_peek_payload_y
    bne scan_zp_is_return_body_no
scan_zp_is_return_body_yes:
    sec
    rts
scan_zp_is_return_body_no:
    clc
    rts

is_main_pure_external_call_sequence_machine_object:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp #$01
    bne is_main_pure_external_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_EXTERN_COUNT_PTR_LO
    jsr load_count_from_context
    beq is_main_pure_external_call_sequence_machine_object_no
    cmp #36
    bcs is_main_pure_external_call_sequence_machine_object_no
    sta compare_char_local
    lda #ACTC_OVERLAY_CTX_STRING_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_pure_external_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_INT_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_pure_external_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_pure_external_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_MODULE_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_pure_external_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_MODULE_NAME_PTR_LO
    jsr load_context_ptr_to_scan_zp
    jsr scan_zp_is_main_symbol
    bcc is_main_pure_external_call_sequence_machine_object_no
    ldx #$00
    lda #ACTC_OVERLAY_CTX_SET_EXPORT_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr scan_zp_is_main_symbol
    bcc is_main_pure_external_call_sequence_machine_object_no
    ldx #$00
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr scan_zp_is_external_call_sequence_return_body
    bcc is_main_pure_external_call_sequence_machine_object_no
    sec
    rts
is_main_pure_external_call_sequence_machine_object_no:
    clc
    rts

scan_zp_is_external_call_sequence_return_body:
    ldy #$00
    sty body_debug_count_local
scan_zp_is_external_call_sequence_return_body_loop:
    jsr emit_object_peek_payload_y
    cmp #'u'
    beq scan_zp_is_external_call_sequence_return_body_call
    cmp #'r'
    beq scan_zp_is_external_call_sequence_return_body_ret
    jmp scan_zp_is_external_call_sequence_return_body_no
scan_zp_is_external_call_sequence_return_body_call:
    iny
    jsr emit_object_peek_payload_y
    jsr external_import_selector_to_index
    bcc scan_zp_is_external_call_sequence_return_body_no
    cmp compare_char_local
    bcs scan_zp_is_external_call_sequence_return_body_no
    inc body_debug_count_local
    iny
    jmp scan_zp_is_external_call_sequence_return_body_loop
scan_zp_is_external_call_sequence_return_body_ret:
    lda body_debug_count_local
    beq scan_zp_is_external_call_sequence_return_body_no
    iny
    jsr emit_object_peek_payload_y
    bne scan_zp_is_external_call_sequence_return_body_no
    sec
    rts
scan_zp_is_external_call_sequence_return_body_no:
    clc
    rts

external_import_selector_to_index:
    ; Object body selectors are one-byte base36 import IDs: 0-9, A-Z.
    cmp #'0'
    bcc external_import_selector_to_index_no
    cmp #':'
    bcc external_import_selector_to_index_digit
    cmp #'A'
    bcc external_import_selector_to_index_no
    cmp #'['
    bcs external_import_selector_to_index_no
    sec
    sbc #55
    sec
    rts
external_import_selector_to_index_digit:
    sec
    sbc #'0'
    sec
    rts
external_import_selector_to_index_no:
    clc
    rts

emit_count_external_call_sequence_body:
    ldy #$00
    sty body_debug_count_local
emit_count_external_call_sequence_body_loop:
    jsr emit_object_peek_payload_y
    cmp #'u'
    bne emit_count_external_call_sequence_body_done
    inc body_debug_count_local
    iny
    iny
    jmp emit_count_external_call_sequence_body_loop
emit_count_external_call_sequence_body_done:
    rts

is_main_local_call_sequence_machine_object:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp #$02
    bcc is_main_local_call_sequence_machine_object_no
    cmp #10
    bcs is_main_local_call_sequence_machine_object_no
    sta compare_char_local
    sec
    sbc #$01
    sta proc_var_index_local
    lda #ACTC_OVERLAY_CTX_EXTERN_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_local_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_STRING_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_local_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_INT_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_local_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_local_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_MODULE_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_local_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_MODULE_NAME_PTR_LO
    jsr load_context_ptr_to_scan_zp
    jsr scan_zp_is_main_symbol
    bcc is_main_local_call_sequence_machine_object_no
    ldx proc_var_index_local
    lda #ACTC_OVERLAY_CTX_SET_EXPORT_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr scan_zp_is_main_symbol
    bcc is_main_local_call_sequence_machine_object_no
    lda #$00
    sta entry_index_data
is_main_local_call_sequence_machine_object_body_loop:
    lda entry_index_data
    cmp compare_char_local
    beq is_main_local_call_sequence_machine_object_yes
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr scan_zp_is_local_call_sequence_return_body
    bcc is_main_local_call_sequence_machine_object_no
    lda entry_index_data
    cmp proc_var_index_local
    bne is_main_local_call_sequence_machine_object_next_body
    lda body_debug_count_local
    beq is_main_local_call_sequence_machine_object_no
is_main_local_call_sequence_machine_object_next_body:
    inc entry_index_data
    jmp is_main_local_call_sequence_machine_object_body_loop
is_main_local_call_sequence_machine_object_yes:
    sec
    rts
is_main_local_call_sequence_machine_object_no:
    clc
    rts

scan_zp_is_local_call_sequence_return_body:
    ldy #$00
    sty body_debug_count_local
scan_zp_is_local_call_sequence_return_body_loop:
    jsr emit_object_peek_payload_y
    cmp #'c'
    beq scan_zp_is_local_call_sequence_return_body_call
    cmp #'r'
    beq scan_zp_is_local_call_sequence_return_body_ret
    jmp scan_zp_is_local_call_sequence_return_body_no
scan_zp_is_local_call_sequence_return_body_call:
    iny
    jsr emit_object_peek_payload_y
    cmp #'0'
    bcc scan_zp_is_local_call_sequence_return_body_no
    cmp #':'
    bcs scan_zp_is_local_call_sequence_return_body_no
    sec
    sbc #'0'
    cmp compare_char_local
    bcs scan_zp_is_local_call_sequence_return_body_no
    inc body_debug_count_local
    iny
    jmp scan_zp_is_local_call_sequence_return_body_loop
scan_zp_is_local_call_sequence_return_body_ret:
    iny
    jsr emit_object_peek_payload_y
    bne scan_zp_is_local_call_sequence_return_body_no
    sec
    rts
scan_zp_is_local_call_sequence_return_body_no:
    clc
    rts

emit_count_local_call_sequence_body:
    ldy #$00
    sty body_debug_count_local
emit_count_local_call_sequence_body_loop:
    jsr emit_object_peek_payload_y
    cmp #'c'
    bne emit_count_local_call_sequence_body_done
    inc body_debug_count_local
    iny
    iny
    jmp emit_count_local_call_sequence_body_loop
emit_count_local_call_sequence_body_done:
    rts

is_main_local_external_call_sequence_machine_object:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp #$02
    bcc is_main_local_external_call_sequence_machine_object_no
    cmp #10
    bcs is_main_local_external_call_sequence_machine_object_no
    sta word_value_hi
    sec
    sbc #$01
    sta proc_var_index_local
    lda #ACTC_OVERLAY_CTX_EXTERN_COUNT_PTR_LO
    jsr load_count_from_context
    beq is_main_local_external_call_sequence_machine_object_no
    cmp #10
    bcs is_main_local_external_call_sequence_machine_object_no
    sta compare_char_local
    lda #ACTC_OVERLAY_CTX_STRING_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_local_external_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_INT_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_local_external_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_local_external_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_MODULE_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    bne is_main_local_external_call_sequence_machine_object_no
    lda #ACTC_OVERLAY_CTX_MODULE_NAME_PTR_LO
    jsr load_context_ptr_to_scan_zp
    jsr scan_zp_is_main_symbol
    bcc is_main_local_external_call_sequence_machine_object_no
    ldx proc_var_index_local
    lda #ACTC_OVERLAY_CTX_SET_EXPORT_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr scan_zp_is_main_symbol
    bcc is_main_local_external_call_sequence_machine_object_no
    lda #$00
    sta entry_index_data
is_main_local_external_call_sequence_machine_object_body_loop:
    lda entry_index_data
    cmp word_value_hi
    beq is_main_local_external_call_sequence_machine_object_yes
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr scan_zp_is_local_external_call_sequence_return_body
    bcc is_main_local_external_call_sequence_machine_object_no
    inc entry_index_data
    jmp is_main_local_external_call_sequence_machine_object_body_loop
is_main_local_external_call_sequence_machine_object_yes:
    sec
    rts
is_main_local_external_call_sequence_machine_object_no:
    clc
    rts

scan_zp_is_local_external_call_sequence_return_body:
    ldy #$00
    sty body_debug_count_local
scan_zp_is_local_external_call_sequence_return_body_loop:
    jsr emit_object_peek_payload_y
    cmp #'c'
    beq scan_zp_is_local_external_call_sequence_return_body_local_call
    cmp #'u'
    beq scan_zp_is_local_external_call_sequence_return_body_external_call
    cmp #'r'
    beq scan_zp_is_local_external_call_sequence_return_body_ret
    jmp scan_zp_is_local_external_call_sequence_return_body_no
scan_zp_is_local_external_call_sequence_return_body_local_call:
    iny
    jsr emit_object_peek_payload_y
    cmp #'0'
    bcc scan_zp_is_local_external_call_sequence_return_body_no
    cmp #':'
    bcs scan_zp_is_local_external_call_sequence_return_body_no
    sec
    sbc #'0'
    cmp word_value_hi
    bcs scan_zp_is_local_external_call_sequence_return_body_no
    inc body_debug_count_local
    iny
    jmp scan_zp_is_local_external_call_sequence_return_body_loop
scan_zp_is_local_external_call_sequence_return_body_external_call:
    iny
    jsr emit_object_peek_payload_y
    cmp #'0'
    bcc scan_zp_is_local_external_call_sequence_return_body_no
    cmp #':'
    bcs scan_zp_is_local_external_call_sequence_return_body_no
    sec
    sbc #'0'
    cmp compare_char_local
    bcs scan_zp_is_local_external_call_sequence_return_body_no
    inc body_debug_count_local
    iny
    jmp scan_zp_is_local_external_call_sequence_return_body_loop
scan_zp_is_local_external_call_sequence_return_body_ret:
    iny
    jsr emit_object_peek_payload_y
    bne scan_zp_is_local_external_call_sequence_return_body_no
    sec
    rts
scan_zp_is_local_external_call_sequence_return_body_no:
    clc
    rts

emit_count_local_external_call_sequence_body:
    ldy #$00
    lda #$00
    sta body_debug_count_local
emit_count_local_external_call_sequence_body_loop:
    jsr emit_object_peek_payload_y
    cmp #'c'
    beq emit_count_local_external_call_sequence_body_call
    cmp #'u'
    beq emit_count_local_external_call_sequence_body_call
    jmp emit_count_local_external_call_sequence_body_done
emit_count_local_external_call_sequence_body_call:
    inc body_debug_count_local
    iny
    iny
    jmp emit_count_local_external_call_sequence_body_loop
emit_count_local_external_call_sequence_body_done:
    rts

emit_machine_body_marker_line:
    lda #'b'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda #'M'
    jsr emit_char_overlay
    jmp emit_newline

emit_machine_external_call_sequence_body_marker_line:
    lda #'b'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda #$00
    sta entry_index_data
emit_machine_external_call_sequence_body_marker_loop:
    lda #ACTC_OVERLAY_CTX_EXTERN_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    beq emit_machine_external_call_sequence_body_marker_done
    lda #'u'
    jsr emit_char_overlay
    lda entry_index_data
    jsr emit_object_selector_overlay
    inc entry_index_data
    jmp emit_machine_external_call_sequence_body_marker_loop
emit_machine_external_call_sequence_body_marker_done:
    lda #'M'
    jsr emit_char_overlay
    jmp emit_newline

emit_object_selector_overlay:
    cmp #10
    bcc emit_object_selector_overlay_digit
    sec
    sbc #10
    clc
    adc #'A'
    jmp emit_char_overlay
emit_object_selector_overlay_digit:
    clc
    adc #'0'
    jmp emit_char_overlay

emit_newline:
    lda #10
    jmp emit_char_overlay

emit_hex_byte_overlay:
    sta proc_var_scope_local
    lsr a
    lsr a
    lsr a
    lsr a
    jsr emit_hex_nibble_overlay
    lda proc_var_scope_local
    and #$0F
    jmp emit_hex_nibble_overlay

emit_hex_nibble_overlay:
    cmp #$0A
    bcc emit_hex_nibble_overlay_digit
    clc
    adc #('A'-10)
    jmp emit_char_overlay
emit_hex_nibble_overlay_digit:
    clc
    adc #'0'
    jmp emit_char_overlay

emit_small_decimal:
    ldx #$00
emit_small_decimal_hundreds_loop:
    cmp #100
    bcc emit_small_decimal_tens_prep
    sec
    sbc #100
    inx
    bne emit_small_decimal_hundreds_loop
emit_small_decimal_tens_prep:
    stx compare_char_local
    ldx #$00
emit_small_decimal_tens_loop:
    cmp #10
    bcc emit_small_decimal_tens_done
    sec
    sbc #10
    inx
    bne emit_small_decimal_tens_loop
emit_small_decimal_tens_done:
    pha
    txa
    pha
    lda compare_char_local
    beq emit_small_decimal_emit_tens
    clc
    adc #'0'
    jsr emit_char_overlay
emit_small_decimal_emit_tens:
    pla
    bne :+
    lda compare_char_local
    beq emit_small_decimal_ones_pop
    lda #$00
:
    clc
    adc #'0'
    jsr emit_char_overlay
emit_small_decimal_ones_pop:
    pla
    clc
    adc #'0'
    jmp emit_char_overlay

emit_word_decimal:
    sta word_value_lo
    sty word_value_hi
    lda #$00
    sta digit_count_local
    ldx #$00
emit_word_decimal_10000_loop:
    lda word_value_hi
    cmp #$27
    bcc emit_word_decimal_10000_done
    bne emit_word_decimal_10000_sub
    lda word_value_lo
    cmp #$10
    bcc emit_word_decimal_10000_done
emit_word_decimal_10000_sub:
    lda word_value_lo
    sec
    sbc #$10
    sta word_value_lo
    lda word_value_hi
    sbc #$27
    sta word_value_hi
    inx
    bne emit_word_decimal_10000_loop
emit_word_decimal_10000_done:
    txa
    jsr emit_word_decimal_digit_if_needed
    ldx #$00
emit_word_decimal_1000_loop:
    lda word_value_hi
    cmp #$03
    bcc emit_word_decimal_1000_done
    bne emit_word_decimal_1000_sub
    lda word_value_lo
    cmp #$E8
    bcc emit_word_decimal_1000_done
emit_word_decimal_1000_sub:
    lda word_value_lo
    sec
    sbc #$E8
    sta word_value_lo
    lda word_value_hi
    sbc #$03
    sta word_value_hi
    inx
    bne emit_word_decimal_1000_loop
emit_word_decimal_1000_done:
    txa
    jsr emit_word_decimal_digit_if_needed
    ldx #$00
emit_word_decimal_100_loop:
    lda word_value_hi
    bne emit_word_decimal_100_sub
    lda word_value_lo
    cmp #100
    bcc emit_word_decimal_100_done
emit_word_decimal_100_sub:
    lda word_value_lo
    sec
    sbc #100
    sta word_value_lo
    lda word_value_hi
    sbc #$00
    sta word_value_hi
    inx
    bne emit_word_decimal_100_loop
emit_word_decimal_100_done:
    txa
    jsr emit_word_decimal_digit_if_needed
    ldx #$00
emit_word_decimal_10_loop:
    lda word_value_hi
    bne emit_word_decimal_10_sub
    lda word_value_lo
    cmp #10
    bcc emit_word_decimal_10_done
emit_word_decimal_10_sub:
    lda word_value_lo
    sec
    sbc #10
    sta word_value_lo
    lda word_value_hi
    sbc #$00
    sta word_value_hi
    inx
    bne emit_word_decimal_10_loop
emit_word_decimal_10_done:
    txa
    jsr emit_word_decimal_digit_if_needed
    lda word_value_lo
    clc
    adc #'0'
    jmp emit_char_overlay

emit_word_decimal_digit_if_needed:
    pha
    txa
    bne emit_word_decimal_digit_emit
    lda digit_count_local
    beq emit_word_decimal_digit_skip
emit_word_decimal_digit_emit:
    pla
    clc
    adc #'0'
    jsr emit_char_overlay
    lda #$01
    sta digit_count_local
    rts
emit_word_decimal_digit_skip:
    pla
    rts

lowercase_ascii_overlay:
    cmp #'A'
    bcc lowercase_ascii_overlay_done
    cmp #'Z'+1
    bcs lowercase_ascii_overlay_done
    ora #$20
lowercase_ascii_overlay_done:
    rts

load_count_from_context:
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    rts

load_indexed_byte_from_context_ptr:
    stx saved_x_local
    jsr load_context_ptr_to_work_zp
    ldy saved_x_local
    lda (ACTC_OVERLAY_WORK_ZP),y
    ldx saved_x_local
    rts

load_context_ptr_to_work_zp:
    sta saved_a_local
    sty saved_y_local
    tay
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_WORK_ZP
    iny
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_WORK_ZP+1
    lda saved_a_local
    ldy saved_y_local
    rts

load_context_ptr_to_scan_zp:
    sta saved_a_local
    sty saved_y_local
    tay
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_SCAN_ZP
    iny
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_SCAN_ZP+1
    lda saved_a_local
    ldy saved_y_local
    rts

load_resident_body_ptr_to_scan_zp:
    lda #ACTC_OVERLAY_CTX_BODY_PTR_SLOT_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta ACTC_OVERLAY_SCAN_ZP
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta ACTC_OVERLAY_SCAN_ZP+1
    rts

load_resident_export_ptr_to_scan_zp:
    lda #ACTC_OVERLAY_CTX_EXPORT_PTR_SLOT_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta ACTC_OVERLAY_SCAN_ZP
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta ACTC_OVERLAY_SCAN_ZP+1
    rts

emit_char_overlay:
    sta emitted_char_local
    lda #ACTC_OVERLAY_CTX_APPEND_CHAR_FN_LO
    jsr load_context_function_ptr
    lda emitted_char_local
    jsr call_loaded_target_with_a
    rts

call_indexed_context_function:
    stx saved_x_local
    jsr load_context_function_ptr
    lda #$00
    ldx saved_x_local
    jsr call_loaded_target_with_a
    ldx saved_x_local
    rts

call_proc_op_context_function:
    jsr load_context_function_ptr
    sec
    lda call_target_ptr
    sbc #$01
    sta call_target_minus_one
    lda call_target_ptr+1
    sbc #$00
    pha
    lda call_target_minus_one
    pha
    rts

load_context_function_ptr:
    sta saved_a_local
    sty saved_y_local
    tay
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta call_target_ptr
    iny
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta call_target_ptr+1
    lda saved_a_local
    ldy saved_y_local
    rts

call_loaded_target_with_a:
    sta call_arg_a
    sec
    lda call_target_ptr
    sbc #$01
    sta call_target_minus_one
    lda call_target_ptr+1
    sbc #$00
    pha
    lda call_target_minus_one
    pha
    lda call_arg_a
    rts

emit_object_peek_payload_y:
    ; Reads resident body/string/object payload windows selected by SET_*_PTR,
    ; not source text. Source-window paging belongs to SourceReader helpers.
    lda (ACTC_OVERLAY_SCAN_ZP),y
    rts

msg_bad_literal:
    .asciiz "BAD LITERAL"
msg_bad_var:
    .asciiz "BAD VAR"
empty_main_machine_record:
    .asciiz "m A9 A5 8D D0 03 A9 00 85 02 85 03 A2 02 4C 0F CF"
external_call_sequence_epilogue_bytes:
    .asciiz " A9 A5 8D D0 03 A9 00 85 02 85 03 A2 02 4C 0F CF"
call_target_minus_one:
    .byte $00
call_target_ptr:
    .word $0000
call_arg_a:
    .byte $00
entry_index_data:
    .byte $00
compare_char_local:
    .byte $00
digit_count_local:
    .byte $00
word_value_lo:
    .byte $00
word_value_hi:
    .byte $00
body_debug_count_local:
    .byte $00
body_debug_index_data:
    .byte $00
proc_var_base_local:
    .byte $00
proc_var_scope_local:
    .byte $00
proc_var_index_local:
    .byte $00
saved_a_local:
    .byte $00
saved_x_local:
    .byte $00
saved_y_local:
    .byte $00
emitted_char_local:
    .byte $00
body_marker_visit_mask:
    .byte $00

actc_overlay_end:
