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

    jsr build_avo_content_overlay
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

build_avo_content_overlay:
    jsr emit_avo_header
    jsr emit_debug_file_list
    bcs build_avo_content_overlay_fail
    jsr emit_debug_proc_decl_list
    bcs build_avo_content_overlay_fail
    jsr emit_debug_body_op_list
    bcs build_avo_content_overlay_fail
    jsr emit_debug_var_list
    bcs build_avo_content_overlay_fail
    jsr emit_export_list
    bcs build_avo_content_overlay_fail
    jsr emit_body_ops_list
    bcs build_avo_content_overlay_fail
    jsr emit_external_list
    bcs build_avo_content_overlay_fail
    jsr emit_string_list
    bcs build_avo_content_overlay_fail
    jsr emit_int_list
    bcs build_avo_content_overlay_fail
    jsr emit_var_list
    bcs build_avo_content_overlay_fail

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

build_avo_content_overlay_fail:
    sec
    rts

emit_avo_header:
    lda #'A'
    jsr emit_char_overlay
    lda #'V'
    jsr emit_char_overlay
    lda #'O'
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
    lda (ACTC_OVERLAY_WORK_ZP),y
    pha
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    pla
    jsr emit_word_decimal
    jsr emit_newline
    inc entry_index_data
    jmp emit_export_list_loop
emit_export_list_done:
    clc
    rts

emit_body_ops_list:
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
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    ldy #$00
emit_body_ops_list_body_loop:
    lda (ACTC_OVERLAY_SCAN_ZP),y
    beq emit_body_ops_list_ret
    jsr emit_char_overlay
    iny
    bne emit_body_ops_list_body_loop
emit_body_ops_list_ret:
    cpy #$00
    beq emit_body_ops_list_emit_ret
    dey
    lda (ACTC_OVERLAY_SCAN_ZP),y
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
    lda (ACTC_OVERLAY_SCAN_ZP),y
    beq emit_scan_zp_string_done
    jsr emit_char_overlay
    iny
    bne emit_scan_zp_string_loop
emit_scan_zp_string_done:
    rts

emit_lower_scan_zp_string:
    ldy #$00
emit_lower_scan_zp_string_loop:
    lda (ACTC_OVERLAY_SCAN_ZP),y
    beq emit_lower_scan_zp_string_done
    jsr lowercase_ascii_overlay
    jsr emit_char_overlay
    iny
    bne emit_lower_scan_zp_string_loop
emit_lower_scan_zp_string_done:
    rts

emit_newline:
    lda #10
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

msg_bad_literal:
    .asciiz "BAD LITERAL"
msg_bad_var:
    .asciiz "BAD VAR"
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

actc_overlay_end:
