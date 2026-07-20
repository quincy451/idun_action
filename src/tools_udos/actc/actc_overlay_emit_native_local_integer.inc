; Native lowering for multi-procedure integer bodies. Procedures are emitted in
; one machine record with MAIN first, followed by helpers in reverse declaration
; order. Named exports carry local calls and control-flow relocations.

NATIVE_LOCAL_PROC_MAX = 9
NATIVE_LOCAL_CONTROL_MAX = 4
NATIVE_LOCAL_LABEL_MAX = 8
NATIVE_LOCAL_CONTROL_IF = 1
NATIVE_LOCAL_CONTROL_DO = 2

.macro NATIVE_LOCAL_JEQ target
    bne :+
    jmp target
:
.endmacro

.macro NATIVE_LOCAL_JNE target
    beq :+
    jmp target
:
.endmacro

.macro NATIVE_LOCAL_JCC target
    bcs :+
    jmp target
:
.endmacro

.macro NATIVE_LOCAL_JCS target
    bcc :+
    jmp target
:
.endmacro

is_main_native_integer_machine_object:
    lda #ACTC_OVERLAY_CTX_EXPORT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp #$02
    NATIVE_LOCAL_JCC native_local_object_no
    cmp #NATIVE_LOCAL_PROC_MAX+1
    NATIVE_LOCAL_JCS native_local_object_no
    sta native_local_proc_count
    sec
    sbc #$01
    sta native_local_main_proc

    lda #ACTC_OVERLAY_CTX_MODULE_NAME_PTR_LO
    jsr load_context_ptr_to_scan_zp
    jsr scan_zp_is_main_symbol
    NATIVE_LOCAL_JCC native_local_object_no
    ldx native_local_main_proc
    lda #ACTC_OVERLAY_CTX_SET_EXPORT_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr scan_zp_is_main_symbol
    NATIVE_LOCAL_JCC native_local_object_no

    lda #ACTC_OVERLAY_CTX_EXTERN_COUNT_PTR_LO
    jsr load_count_from_context
    NATIVE_LOCAL_JNE native_local_object_no
    lda #ACTC_OVERLAY_CTX_STRING_COUNT_PTR_LO
    jsr load_count_from_context
    NATIVE_LOCAL_JNE native_local_object_no

    jsr native_local_compute_data_size
    NATIVE_LOCAL_JCC native_local_object_no
    jsr native_local_count_debug_ops
    NATIVE_LOCAL_JCC native_local_object_no

    lda #$00
    sta native_local_total_code_lo
    sta native_local_total_code_hi
    sta native_local_debug_count
    lda #$01
    sta native_local_record_debug
    lda native_local_main_proc
    sta native_local_current_proc
native_local_layout_loop:
    ldx native_local_current_proc
    lda native_local_total_code_lo
    sta native_local_proc_offset_lo,x
    lda native_local_total_code_hi
    sta native_local_proc_offset_hi,x
    lda native_local_debug_count
    sta native_local_proc_debug_base,x
    jsr native_local_analyze_current_proc
    NATIVE_LOCAL_JCC native_local_object_no
    ldx native_local_current_proc
    lda native_local_label_count
    sta native_local_proc_label_count,x
    sec
    lda native_local_code_size_lo
    sbc native_local_proc_offset_lo,x
    sta native_local_proc_size_lo,x
    lda native_local_code_size_hi
    sbc native_local_proc_offset_hi,x
    sta native_local_proc_size_hi,x
    lda native_local_code_size_lo
    sta native_local_total_code_lo
    lda native_local_code_size_hi
    sta native_local_total_code_hi
    lda native_local_current_proc
    NATIVE_LOCAL_JEQ native_local_layout_done
    dec native_local_current_proc
    jmp native_local_layout_loop
native_local_layout_done:
    lda native_local_debug_count
    cmp native_local_expected_debug_count
    NATIVE_LOCAL_JNE native_local_object_no
    jsr native_local_compute_root_size
    sec
    rts
native_local_object_no:
    clc
    rts

native_local_count_debug_ops:
    lda #$00
    sta native_local_expected_debug_count
    ldx #$00
native_local_count_debug_ops_loop:
    cpx native_local_proc_count
    NATIVE_LOCAL_JEQ native_local_count_debug_ops_done
    lda #ACTC_OVERLAY_CTX_BODY_DEBUG_COUNT_PTR_LO
    jsr load_indexed_byte_from_context_ptr
    clc
    adc native_local_expected_debug_count
    NATIVE_LOCAL_JCS native_local_count_debug_ops_bad
    cmp #ACTC_OVERLAY_BODY_OP_LIMIT+1
    NATIVE_LOCAL_JCS native_local_count_debug_ops_bad
    sta native_local_expected_debug_count
    inx
    jmp native_local_count_debug_ops_loop
native_local_count_debug_ops_done:
    sec
    rts
native_local_count_debug_ops_bad:
    clc
    rts

native_local_compute_data_size:
    lda #$00
    sta native_local_data_size_lo
    sta native_local_data_size_hi
    sta entry_index_data
native_local_compute_data_size_loop:
    lda #ACTC_OVERLAY_CTX_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    NATIVE_LOCAL_JEQ native_local_compute_data_size_done
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_LOAD_VAR_META_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_VAR_META_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$02
    lda (ACTC_OVERLAY_WORK_ZP),y
    cmp #$02
    NATIVE_LOCAL_JNE native_local_compute_data_size_bad
    clc
    lda native_local_data_size_lo
    adc #$02
    sta native_local_data_size_lo
    bcc :+
    inc native_local_data_size_hi
:   inc entry_index_data
    jmp native_local_compute_data_size_loop
native_local_compute_data_size_done:
    sec
    rts
native_local_compute_data_size_bad:
    clc
    rts

native_local_compute_root_size:
    clc
    lda native_local_total_code_lo
    adc native_local_data_size_lo
    sta native_local_root_size_lo
    lda native_local_total_code_hi
    adc native_local_data_size_hi
    sta native_local_root_size_hi
    lda native_local_data_size_lo
    ora native_local_data_size_hi
    NATIVE_LOCAL_JEQ native_local_compute_root_size_done
    clc
    lda native_local_root_size_lo
    adc #$02
    sta native_local_root_size_lo
    NATIVE_LOCAL_JCC native_local_compute_root_size_done
    inc native_local_root_size_hi
native_local_compute_root_size_done:
    rts

native_local_analyze_current_proc:
    lda #$00
    sta native_local_stack_depth
    sta native_local_control_depth
    sta native_local_label_count
    sta native_local_lowering_seen
    sta native_local_body_pos
    ldx native_local_current_proc
    lda native_local_proc_offset_lo,x
    sta native_local_code_size_lo
    lda native_local_proc_offset_hi,x
    sta native_local_code_size_hi
    cpx native_local_main_proc
    NATIVE_LOCAL_JNE native_local_analyze_select_body
    lda native_local_data_size_lo
    ora native_local_data_size_hi
    NATIVE_LOCAL_JEQ native_local_analyze_select_body
    lda #13
    jsr native_local_add_code_size
native_local_analyze_select_body:
    ldx native_local_current_proc
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
native_local_analyze_loop:
    jsr native_local_record_debug_offset
    ldy native_local_body_pos
    jsr emit_object_peek_payload_y
    cmp #'p'
    NATIVE_LOCAL_JEQ native_local_analyze_literal
    cmp #'L'
    NATIVE_LOCAL_JEQ native_local_analyze_load
    cmp #'S'
    NATIVE_LOCAL_JEQ native_local_analyze_store
    cmp #'q'
    NATIVE_LOCAL_JEQ native_local_analyze_equal
    cmp #'d'
    NATIVE_LOCAL_JEQ native_local_analyze_do
    cmp #'w'
    NATIVE_LOCAL_JEQ native_local_analyze_else
    cmp #'v'
    NATIVE_LOCAL_JEQ native_local_analyze_endif
    cmp #'c'
    NATIVE_LOCAL_JEQ native_local_analyze_call
    cmp #'r'
    NATIVE_LOCAL_JEQ native_local_analyze_return
    jmp native_local_analyze_bad

native_local_analyze_literal:
    jsr native_local_read_selector
    NATIVE_LOCAL_JCC native_local_analyze_bad
    lda #ACTC_OVERLAY_CTX_INT_COUNT_PTR_LO
    jsr load_count_from_context
    cmp native_local_operand_index
    NATIVE_LOCAL_JEQ native_local_analyze_bad
    NATIVE_LOCAL_JCC native_local_analyze_bad
    jsr native_local_push
    NATIVE_LOCAL_JCC native_local_analyze_bad
    lda #$06
    jsr native_local_add_code_size
    jmp native_local_analyze_mark

native_local_analyze_load:
    jsr native_local_read_selector
    NATIVE_LOCAL_JCC native_local_analyze_bad
    lda native_local_operand_index
    jsr native_local_word_var_offset
    NATIVE_LOCAL_JCC native_local_analyze_bad
    jsr native_local_push
    NATIVE_LOCAL_JCC native_local_analyze_bad
    lda #$09
    jsr native_local_add_code_size
    jmp native_local_analyze_mark

native_local_analyze_store:
    jsr native_local_read_selector
    NATIVE_LOCAL_JCC native_local_analyze_bad
    lda native_local_operand_index
    jsr native_local_word_var_offset
    NATIVE_LOCAL_JCC native_local_analyze_bad
    jsr native_local_pop
    NATIVE_LOCAL_JCC native_local_analyze_bad
    lda #11
    jsr native_local_add_code_size
    jmp native_local_analyze_mark

native_local_analyze_equal:
    lda native_local_stack_depth
    cmp #$02
    NATIVE_LOCAL_JCC native_local_analyze_bad
    sec
    sbc #$02
    sta native_local_stack_depth
    ldy native_local_body_pos
    iny
    jsr emit_object_peek_payload_y
    cmp #'h'
    NATIVE_LOCAL_JEQ native_local_analyze_equal_if
    cmp #'t'
    NATIVE_LOCAL_JNE native_local_analyze_bad
    iny
    jsr emit_object_peek_payload_y
    cmp #'o'
    NATIVE_LOCAL_JNE native_local_analyze_bad
    ldx native_local_control_depth
    NATIVE_LOCAL_JEQ native_local_analyze_bad
    dex
    lda native_local_control_kind,x
    cmp #NATIVE_LOCAL_CONTROL_DO
    NATIVE_LOCAL_JNE native_local_analyze_bad
    stx native_local_control_depth
    lda #23
    jsr native_local_add_code_size
    jsr native_local_record_debug_offset
    jsr native_local_record_debug_offset
    lda native_local_body_pos
    clc
    adc #$03
    sta native_local_body_pos
    jmp native_local_analyze_mark_no_advance
native_local_analyze_equal_if:
    lda native_local_control_depth
    cmp #NATIVE_LOCAL_CONTROL_MAX
    NATIVE_LOCAL_JCS native_local_analyze_bad
    jsr native_local_allocate_label
    NATIVE_LOCAL_JCC native_local_analyze_bad
    ldx native_local_control_depth
    sta native_local_control_target,x
    lda #$FF
    sta native_local_control_end,x
    lda #NATIVE_LOCAL_CONTROL_IF
    sta native_local_control_kind,x
    inc native_local_control_depth
    lda #23
    jsr native_local_add_code_size
    jsr native_local_record_debug_offset
    lda native_local_body_pos
    clc
    adc #$02
    sta native_local_body_pos
    jmp native_local_analyze_mark_no_advance

native_local_analyze_do:
    lda native_local_stack_depth
    NATIVE_LOCAL_JNE native_local_analyze_bad
    lda native_local_control_depth
    cmp #NATIVE_LOCAL_CONTROL_MAX
    NATIVE_LOCAL_JCS native_local_analyze_bad
    jsr native_local_allocate_label
    NATIVE_LOCAL_JCC native_local_analyze_bad
    pha
    tax
    lda native_local_code_size_lo
    sta native_local_label_offset_lo,x
    lda native_local_code_size_hi
    sta native_local_label_offset_hi,x
    pla
    ldx native_local_control_depth
    sta native_local_control_target,x
    lda #$FF
    sta native_local_control_end,x
    lda #NATIVE_LOCAL_CONTROL_DO
    sta native_local_control_kind,x
    inc native_local_control_depth
    inc native_local_body_pos
    jmp native_local_analyze_mark_no_advance

native_local_analyze_else:
    ldx native_local_control_depth
    NATIVE_LOCAL_JEQ native_local_analyze_bad
    dex
    lda native_local_control_kind,x
    cmp #NATIVE_LOCAL_CONTROL_IF
    NATIVE_LOCAL_JNE native_local_analyze_bad
    lda native_local_control_end,x
    cmp #$FF
    NATIVE_LOCAL_JNE native_local_analyze_bad
    txa
    pha
    jsr native_local_allocate_label
    NATIVE_LOCAL_JCC native_local_analyze_else_bad_pop
    sta native_local_saved_label
    lda #$03
    jsr native_local_add_code_size
    pla
    tax
    lda native_local_saved_label
    sta native_local_control_end,x
    lda native_local_control_target,x
    tax
    lda native_local_code_size_lo
    sta native_local_label_offset_lo,x
    lda native_local_code_size_hi
    sta native_local_label_offset_hi,x
    inc native_local_body_pos
    jmp native_local_analyze_mark_no_advance
native_local_analyze_else_bad_pop:
    pla
    jmp native_local_analyze_bad

native_local_analyze_endif:
    ldx native_local_control_depth
    NATIVE_LOCAL_JEQ native_local_analyze_bad
    dex
    lda native_local_control_kind,x
    cmp #NATIVE_LOCAL_CONTROL_IF
    NATIVE_LOCAL_JNE native_local_analyze_bad
    lda native_local_control_end,x
    cmp #$FF
    bne :+
    lda native_local_control_target,x
:   tay
    lda native_local_code_size_lo
    sta native_local_label_offset_lo,y
    lda native_local_code_size_hi
    sta native_local_label_offset_hi,y
    stx native_local_control_depth
    inc native_local_body_pos
    jmp native_local_analyze_mark_no_advance

native_local_analyze_call:
    lda native_local_stack_depth
    NATIVE_LOCAL_JNE native_local_analyze_bad
    jsr native_local_read_selector
    NATIVE_LOCAL_JCC native_local_analyze_bad
    lda native_local_operand_index
    cmp native_local_main_proc
    NATIVE_LOCAL_JCS native_local_analyze_bad
    lda #$03
    jsr native_local_add_code_size
    jmp native_local_analyze_mark

native_local_analyze_return:
    ldy native_local_body_pos
    iny
    jsr emit_object_peek_payload_y
    NATIVE_LOCAL_JNE native_local_analyze_bad
    lda native_local_stack_depth
    ora native_local_control_depth
    beq :+
    jmp native_local_analyze_bad
:   lda native_local_lowering_seen
    NATIVE_LOCAL_JEQ native_local_analyze_bad
    lda native_local_current_proc
    cmp native_local_main_proc
    bne :+
    lda #16
    jsr native_local_add_code_size
    sec
    rts
:   lda #$01
    jsr native_local_add_code_size
    sec
    rts

native_local_analyze_mark:
    ; Selector operations leave body_pos immediately after their operand.
native_local_analyze_mark_no_advance:
    lda #$01
    sta native_local_lowering_seen
    jmp native_local_analyze_loop
native_local_analyze_bad:
    clc
    rts

native_local_record_debug_offset:
    lda native_local_record_debug
    NATIVE_LOCAL_JEQ native_local_record_debug_offset_done
    ldx native_local_debug_count
    cpx #ACTC_OVERLAY_BODY_OP_LIMIT
    NATIVE_LOCAL_JCS native_local_record_debug_offset_done
    lda native_local_code_size_lo
    sta native_int_debug_offsets_lo,x
    lda native_local_code_size_hi
    sta native_int_debug_offsets_hi,x
    inc native_local_debug_count
native_local_record_debug_offset_done:
    rts

native_int_load_debug_offset:
    ldx entry_index_data
    lda native_local_proc_debug_base,x
    clc
    adc body_debug_index_data
    tax
    lda native_int_debug_offsets_lo,x
    ldy native_int_debug_offsets_hi,x
    rts

native_local_read_selector:
    inc native_local_body_pos
    ldy native_local_body_pos
    jsr emit_object_peek_payload_y
    cmp #'0'
    NATIVE_LOCAL_JCC native_local_read_selector_bad
    cmp #':'
    NATIVE_LOCAL_JCS native_local_read_selector_bad
    sec
    sbc #'0'
    sta native_local_operand_index
    inc native_local_body_pos
    sec
    rts
native_local_read_selector_bad:
    clc
    rts

native_local_push:
    lda native_local_stack_depth
    cmp #96
    NATIVE_LOCAL_JCS native_local_stack_bad
    inc native_local_stack_depth
    sec
    rts
native_local_pop:
    lda native_local_stack_depth
    NATIVE_LOCAL_JEQ native_local_stack_bad
    dec native_local_stack_depth
    sec
    rts
native_local_stack_bad:
    clc
    rts

native_local_allocate_label:
    lda native_local_label_count
    cmp #NATIVE_LOCAL_LABEL_MAX
    NATIVE_LOCAL_JCS native_local_allocate_label_bad
    inc native_local_label_count
    sec
    rts
native_local_allocate_label_bad:
    clc
    rts

native_local_add_code_size:
    clc
    adc native_local_code_size_lo
    sta native_local_code_size_lo
    bcc :+
    inc native_local_code_size_hi
:   rts

native_local_word_var_offset:
    sta native_local_target_var
    lda #ACTC_OVERLAY_CTX_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    cmp native_local_target_var
    NATIVE_LOCAL_JEQ native_local_word_var_offset_bad
    NATIVE_LOCAL_JCC native_local_word_var_offset_bad
    lda native_local_target_var
    asl
    NATIVE_LOCAL_JCS native_local_word_var_offset_bad
    sec
    rts
native_local_word_var_offset_bad:
    clc
    rts

emit_native_integer_export_list:
    lda #$00
    sta native_local_export_offset_lo
    sta native_local_export_offset_hi
    lda native_local_root_size_lo
    sta native_local_export_size_lo
    lda native_local_root_size_hi
    sta native_local_export_size_hi
    ldx native_local_main_proc
    lda #ACTC_OVERLAY_CTX_SET_EXPORT_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr native_local_emit_export_line

    lda native_local_main_proc
    NATIVE_LOCAL_JEQ native_local_emit_proc_exports_done
    sec
    sbc #$01
    sta native_local_current_proc
native_local_emit_proc_exports_loop:
    ldx native_local_current_proc
    lda native_local_proc_offset_lo,x
    sta native_local_export_offset_lo
    lda native_local_proc_offset_hi,x
    sta native_local_export_offset_hi
    lda native_local_proc_size_lo,x
    sta native_local_export_size_lo
    lda native_local_proc_size_hi,x
    sta native_local_export_size_hi
    lda #ACTC_OVERLAY_CTX_SET_EXPORT_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr native_local_emit_export_line
    lda native_local_current_proc
    NATIVE_LOCAL_JEQ native_local_emit_proc_exports_done
    dec native_local_current_proc
    jmp native_local_emit_proc_exports_loop
native_local_emit_proc_exports_done:
    lda #$00
    sta native_local_record_debug
    lda native_local_main_proc
    sta native_local_current_proc
native_local_emit_label_proc_loop:
    jsr native_local_analyze_current_proc
    NATIVE_LOCAL_JCC native_local_emit_export_fail
    lda #$00
    sta native_local_label_index
native_local_emit_label_loop:
    lda native_local_label_index
    cmp native_local_label_count
    NATIVE_LOCAL_JEQ native_local_emit_label_next_proc
    tax
    lda native_local_label_offset_lo,x
    sta native_local_export_offset_lo
    lda native_local_label_offset_hi,x
    sta native_local_export_offset_hi
    lda #$01
    sta native_local_export_size_lo
    lda #$00
    sta native_local_export_size_hi
    ldx native_local_label_index
    jsr native_local_build_label_name
    jsr native_local_emit_export_line
    inc native_local_label_index
    jmp native_local_emit_label_loop
native_local_emit_label_next_proc:
    lda native_local_current_proc
    NATIVE_LOCAL_JEQ native_local_emit_data_exports
    dec native_local_current_proc
    jmp native_local_emit_label_proc_loop

native_local_emit_data_exports:
    lda native_local_data_size_lo
    ora native_local_data_size_hi
    NATIVE_LOCAL_JEQ native_local_emit_export_done
    lda native_local_total_code_lo
    sta native_local_export_offset_lo
    lda native_local_total_code_hi
    sta native_local_export_offset_hi
    lda native_local_data_size_lo
    sta native_local_export_size_lo
    lda native_local_data_size_hi
    sta native_local_export_size_hi
    lda #<native_local_name_data
    sta ACTC_OVERLAY_SCAN_ZP
    lda #>native_local_name_data
    sta ACTC_OVERLAY_SCAN_ZP+1
    jsr native_local_emit_export_line
    clc
    lda native_local_total_code_lo
    adc native_local_data_size_lo
    sta native_local_export_offset_lo
    lda native_local_total_code_hi
    adc native_local_data_size_hi
    sta native_local_export_offset_hi
    lda #$02
    sta native_local_export_size_lo
    lda #$00
    sta native_local_export_size_hi
    lda #<native_local_name_pointer
    sta ACTC_OVERLAY_SCAN_ZP
    lda #>native_local_name_pointer
    sta ACTC_OVERLAY_SCAN_ZP+1
    jsr native_local_emit_export_line
native_local_emit_export_done:
    clc
    rts
native_local_emit_export_fail:
    sec
    rts

native_local_emit_export_line:
    lda #'x'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    jsr emit_lower_scan_zp_string
    lda #' '
    jsr emit_char_overlay
    lda native_local_export_offset_lo
    ldy native_local_export_offset_hi
    jsr emit_word_decimal
    lda #' '
    jsr emit_char_overlay
    lda native_local_export_size_lo
    ldy native_local_export_size_hi
    jsr emit_word_decimal
    jmp emit_newline

native_local_build_label_name:
    txa
    clc
    adc #'0'
    sta native_local_label_name+5
    lda native_local_current_proc
    clc
    adc #'0'
    sta native_local_label_name+3
    lda #<native_local_label_name
    sta ACTC_OVERLAY_SCAN_ZP
    lda #>native_local_label_name
    sta ACTC_OVERLAY_SCAN_ZP+1
    rts

emit_native_integer_body_marker_list:
    lda native_local_proc_count
    sta native_local_marker_count
    ldx #$00
native_local_count_label_markers_loop:
    cpx native_local_proc_count
    NATIVE_LOCAL_JEQ native_local_count_label_markers_done
    clc
    lda native_local_marker_count
    adc native_local_proc_label_count,x
    sta native_local_marker_count
    inx
    jmp native_local_count_label_markers_loop
native_local_count_label_markers_done:
    lda native_local_data_size_lo
    ora native_local_data_size_hi
    NATIVE_LOCAL_JEQ native_local_emit_markers_loop
    inc native_local_marker_count
    inc native_local_marker_count
native_local_emit_markers_loop:
    lda native_local_marker_count
    NATIVE_LOCAL_JEQ native_local_emit_markers_done
    jsr emit_machine_body_marker_line
    dec native_local_marker_count
    jmp native_local_emit_markers_loop
native_local_emit_markers_done:
    clc
    rts

emit_native_integer_machine_code_list:
    lda #'m'
    jsr emit_char_overlay
    lda native_local_main_proc
    sta native_local_current_proc
native_local_emit_code_proc_loop:
    lda native_local_current_proc
    cmp native_local_main_proc
    NATIVE_LOCAL_JNE native_local_emit_code_select_body
    lda native_local_data_size_lo
    ora native_local_data_size_hi
    NATIVE_LOCAL_JEQ native_local_emit_code_select_body
    lda #<native_local_prologue
    ldy #>native_local_prologue
    ldx #(native_local_prologue_end-native_local_prologue)
    jsr native_local_emit_const_bytes
native_local_emit_code_select_body:
    ldx native_local_current_proc
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    lda #$00
    sta native_local_body_pos
    jsr native_local_emit_code_loop
    lda native_local_current_proc
    NATIVE_LOCAL_JEQ native_local_emit_code_done_procs
    dec native_local_current_proc
    jmp native_local_emit_code_proc_loop
native_local_emit_code_done_procs:
    jsr native_local_emit_data
    jsr emit_newline
    jmp native_local_emit_reloc_list

native_local_emit_code_loop:
    ldy native_local_body_pos
    jsr emit_object_peek_payload_y
    cmp #'p'
    NATIVE_LOCAL_JEQ native_local_emit_literal
    cmp #'L'
    NATIVE_LOCAL_JEQ native_local_emit_load
    cmp #'S'
    NATIVE_LOCAL_JEQ native_local_emit_store
    cmp #'q'
    NATIVE_LOCAL_JEQ native_local_emit_equal
    cmp #'d'
    NATIVE_LOCAL_JEQ native_local_emit_no_code
    cmp #'w'
    NATIVE_LOCAL_JEQ native_local_emit_else
    cmp #'v'
    NATIVE_LOCAL_JEQ native_local_emit_no_code
    cmp #'c'
    NATIVE_LOCAL_JEQ native_local_emit_call
    cmp #'r'
    NATIVE_LOCAL_JEQ native_local_emit_return
    sec
    rts

native_local_emit_literal:
    jsr native_local_read_selector
    ldx native_local_operand_index
    lda #ACTC_OVERLAY_CTX_LOAD_INT_LITERAL_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_INT_LITERAL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    lda #$A9
    jsr native_local_emit_byte
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr native_local_emit_byte
    lda #$48
    jsr native_local_emit_byte
    lda #$A9
    jsr native_local_emit_byte
    lda #ACTC_OVERLAY_CTX_INT_LITERAL_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$01
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr native_local_emit_byte
    lda #$48
    jsr native_local_emit_byte
    jmp native_local_emit_code_loop

native_local_emit_load:
    jsr native_local_read_selector
    lda native_local_operand_index
    jsr native_local_word_var_offset
    sta native_local_var_offset
    lda #$A0
    jsr native_local_emit_byte
    lda native_local_var_offset
    jsr native_local_emit_byte
    lda #<native_local_load_tail
    ldy #>native_local_load_tail
    ldx #(native_local_load_tail_end-native_local_load_tail)
    jsr native_local_emit_const_bytes
    jmp native_local_emit_code_loop

native_local_emit_store:
    jsr native_local_read_selector
    lda native_local_operand_index
    jsr native_local_word_var_offset
    sta native_local_var_offset
    lda #<native_local_store_head
    ldy #>native_local_store_head
    ldx #(native_local_store_head_end-native_local_store_head)
    jsr native_local_emit_const_bytes
    lda native_local_var_offset
    jsr native_local_emit_byte
    lda #<native_local_store_tail
    ldy #>native_local_store_tail
    ldx #(native_local_store_tail_end-native_local_store_tail)
    jsr native_local_emit_const_bytes
    jmp native_local_emit_code_loop

native_local_emit_equal:
    lda #<native_local_equal_bytes
    ldy #>native_local_equal_bytes
    ldx #(native_local_equal_bytes_end-native_local_equal_bytes)
    jsr native_local_emit_const_bytes
    ldy native_local_body_pos
    iny
    jsr emit_object_peek_payload_y
    cmp #'h'
    beq :+
    lda native_local_body_pos
    clc
    adc #$03
    sta native_local_body_pos
    jmp native_local_emit_code_loop
:   lda native_local_body_pos
    clc
    adc #$02
    sta native_local_body_pos
    jmp native_local_emit_code_loop

native_local_emit_no_code:
    inc native_local_body_pos
    jmp native_local_emit_code_loop

native_local_emit_else:
    lda #<native_local_else_bytes
    ldy #>native_local_else_bytes
    ldx #(native_local_else_bytes_end-native_local_else_bytes)
    jsr native_local_emit_const_bytes
    inc native_local_body_pos
    jmp native_local_emit_code_loop

native_local_emit_call:
    jsr native_local_read_selector
    lda #<native_local_call_bytes
    ldy #>native_local_call_bytes
    ldx #(native_local_call_bytes_end-native_local_call_bytes)
    jsr native_local_emit_const_bytes
    jmp native_local_emit_code_loop

native_local_emit_return:
    lda native_local_current_proc
    cmp native_local_main_proc
    NATIVE_LOCAL_JNE native_local_emit_helper_return
    lda #<native_local_exit_bytes
    ldy #>native_local_exit_bytes
    ldx #(native_local_exit_bytes_end-native_local_exit_bytes)
    jsr native_local_emit_const_bytes
    clc
    rts
native_local_emit_helper_return:
    lda #$60
    jsr native_local_emit_byte
    clc
    rts

native_local_emit_data:
    lda #$00
    sta entry_index_data
native_local_emit_data_loop:
    lda #ACTC_OVERLAY_CTX_VAR_COUNT_PTR_LO
    jsr load_count_from_context
    cmp entry_index_data
    NATIVE_LOCAL_JEQ native_local_emit_data_pointer
    ldx entry_index_data
    lda #ACTC_OVERLAY_CTX_LOAD_VAR_META_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_VAR_META_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr native_local_emit_byte
    lda #ACTC_OVERLAY_CTX_VAR_META_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$01
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr native_local_emit_byte
    inc entry_index_data
    jmp native_local_emit_data_loop
native_local_emit_data_pointer:
    lda native_local_data_size_lo
    ora native_local_data_size_hi
    NATIVE_LOCAL_JEQ native_local_emit_data_done
    lda #$00
    jsr native_local_emit_byte
    lda #$00
    jsr native_local_emit_byte
native_local_emit_data_done:
    rts

native_local_emit_const_bytes:
    sta native_local_const_ptr_lo
    sty native_local_const_ptr_hi
    stx native_local_const_len
    lda #$00
    sta native_local_const_index
native_local_emit_const_loop:
    lda native_local_const_index
    cmp native_local_const_len
    NATIVE_LOCAL_JEQ native_local_emit_const_done
    lda native_local_const_ptr_lo
    sta ACTC_OVERLAY_WORK_ZP
    lda native_local_const_ptr_hi
    sta ACTC_OVERLAY_WORK_ZP+1
    ldy native_local_const_index
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr native_local_emit_byte
    inc native_local_const_index
    jmp native_local_emit_const_loop
native_local_emit_const_done:
    rts

native_local_emit_byte:
    sta native_local_machine_byte
    lda #' '
    jsr emit_char_overlay
    lda native_local_machine_byte
    jmp emit_hex_byte_overlay

native_local_emit_reloc_list:
    lda native_local_data_size_lo
    ora native_local_data_size_hi
    NATIVE_LOCAL_JEQ native_local_emit_reloc_procs
    lda #$03
    ldy #$00
    jsr native_local_emit_pointer_reloc
    lda #$09
    ldy #$00
    jsr native_local_emit_pointer_reloc
native_local_emit_reloc_procs:
    lda native_local_main_proc
    sta native_local_current_proc
native_local_emit_reloc_proc_loop:
    ldx native_local_current_proc
    lda native_local_proc_offset_lo,x
    sta native_local_reloc_offset_lo
    lda native_local_proc_offset_hi,x
    sta native_local_reloc_offset_hi
    cpx native_local_main_proc
    bne :+
    lda native_local_data_size_lo
    ora native_local_data_size_hi
    beq :+
    lda #13
    jsr native_local_add_reloc_offset
:   lda #$00
    sta native_local_body_pos
    sta native_local_control_depth
    sta native_local_label_count
    ldx native_local_current_proc
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_body_ptr_to_scan_zp
    jsr native_local_emit_reloc_body
    NATIVE_LOCAL_JCS native_local_emit_reloc_fail
    lda native_local_current_proc
    NATIVE_LOCAL_JEQ native_local_emit_data_reloc
    dec native_local_current_proc
    jmp native_local_emit_reloc_proc_loop

native_local_emit_data_reloc:
    lda native_local_data_size_lo
    ora native_local_data_size_hi
    NATIVE_LOCAL_JEQ native_local_emit_reloc_done
    clc
    lda native_local_total_code_lo
    adc native_local_data_size_lo
    sta native_local_temp_offset_lo
    lda native_local_total_code_hi
    adc native_local_data_size_hi
    tay
    lda native_local_temp_offset_lo
    jsr native_local_emit_reloc_prefix
    lda #<native_local_name_data
    sta ACTC_OVERLAY_SCAN_ZP
    lda #>native_local_name_data
    sta ACTC_OVERLAY_SCAN_ZP+1
    jsr native_local_emit_named_target
native_local_emit_reloc_done:
    clc
    rts
native_local_emit_reloc_fail:
    sec
    rts

native_local_emit_reloc_body:
    ldy native_local_body_pos
    jsr emit_object_peek_payload_y
    cmp #'p'
    NATIVE_LOCAL_JEQ native_local_reloc_literal
    cmp #'L'
    NATIVE_LOCAL_JEQ native_local_reloc_load
    cmp #'S'
    NATIVE_LOCAL_JEQ native_local_reloc_store
    cmp #'q'
    NATIVE_LOCAL_JEQ native_local_reloc_equal
    cmp #'d'
    NATIVE_LOCAL_JEQ native_local_reloc_do
    cmp #'w'
    NATIVE_LOCAL_JEQ native_local_reloc_else
    cmp #'v'
    NATIVE_LOCAL_JEQ native_local_reloc_endif
    cmp #'c'
    NATIVE_LOCAL_JEQ native_local_reloc_call
    cmp #'r'
    NATIVE_LOCAL_JEQ native_local_reloc_body_done
    sec
    rts
native_local_reloc_literal:
    inc native_local_body_pos
    inc native_local_body_pos
    lda #$06
    jsr native_local_add_reloc_offset
    jmp native_local_emit_reloc_body
native_local_reloc_load:
    inc native_local_body_pos
    inc native_local_body_pos
    lda #$09
    jsr native_local_add_reloc_offset
    jmp native_local_emit_reloc_body
native_local_reloc_store:
    inc native_local_body_pos
    inc native_local_body_pos
    lda #11
    jsr native_local_add_reloc_offset
    jmp native_local_emit_reloc_body

native_local_reloc_do:
    jsr native_local_allocate_label
    NATIVE_LOCAL_JCC native_local_reloc_bad
    ldx native_local_control_depth
    sta native_local_control_target,x
    lda #$FF
    sta native_local_control_end,x
    lda #NATIVE_LOCAL_CONTROL_DO
    sta native_local_control_kind,x
    inc native_local_control_depth
    inc native_local_body_pos
    jmp native_local_emit_reloc_body

native_local_reloc_equal:
    ldy native_local_body_pos
    iny
    jsr emit_object_peek_payload_y
    cmp #'h'
    NATIVE_LOCAL_JEQ native_local_reloc_equal_if
    cmp #'t'
    NATIVE_LOCAL_JNE native_local_reloc_bad
    ldx native_local_control_depth
    NATIVE_LOCAL_JEQ native_local_reloc_bad
    dex
    lda native_local_control_kind,x
    cmp #NATIVE_LOCAL_CONTROL_DO
    NATIVE_LOCAL_JNE native_local_reloc_bad
    lda native_local_control_target,x
    sta native_local_saved_label
    stx native_local_control_depth
    lda #21
    jsr native_local_reloc_label_at_addend
    lda #23
    jsr native_local_add_reloc_offset
    lda native_local_body_pos
    clc
    adc #$03
    sta native_local_body_pos
    jmp native_local_emit_reloc_body
native_local_reloc_equal_if:
    jsr native_local_allocate_label
    NATIVE_LOCAL_JCC native_local_reloc_bad
    sta native_local_saved_label
    ldx native_local_control_depth
    sta native_local_control_target,x
    lda #$FF
    sta native_local_control_end,x
    lda #NATIVE_LOCAL_CONTROL_IF
    sta native_local_control_kind,x
    inc native_local_control_depth
    lda #21
    jsr native_local_reloc_label_at_addend
    lda #23
    jsr native_local_add_reloc_offset
    lda native_local_body_pos
    clc
    adc #$02
    sta native_local_body_pos
    jmp native_local_emit_reloc_body

native_local_reloc_else:
    ldx native_local_control_depth
    NATIVE_LOCAL_JEQ native_local_reloc_bad
    dex
    lda native_local_control_kind,x
    cmp #NATIVE_LOCAL_CONTROL_IF
    NATIVE_LOCAL_JNE native_local_reloc_bad
    txa
    pha
    jsr native_local_allocate_label
    NATIVE_LOCAL_JCC native_local_reloc_else_bad_pop
    sta native_local_saved_label
    pla
    tax
    lda native_local_saved_label
    sta native_local_control_end,x
    lda #$01
    jsr native_local_reloc_label_at_addend
    lda #$03
    jsr native_local_add_reloc_offset
    inc native_local_body_pos
    jmp native_local_emit_reloc_body
native_local_reloc_else_bad_pop:
    pla
    jmp native_local_reloc_bad

native_local_reloc_endif:
    ldx native_local_control_depth
    NATIVE_LOCAL_JEQ native_local_reloc_bad
    dex
    stx native_local_control_depth
    inc native_local_body_pos
    jmp native_local_emit_reloc_body

native_local_reloc_call:
    jsr native_local_read_selector
    clc
    lda native_local_reloc_offset_lo
    adc #$01
    sta native_local_temp_offset_lo
    lda native_local_reloc_offset_hi
    adc #$00
    tay
    lda native_local_temp_offset_lo
    jsr native_local_emit_reloc_prefix
    ldx native_local_operand_index
    lda #ACTC_OVERLAY_CTX_SET_EXPORT_PTR_FN_LO
    jsr call_indexed_context_function
    jsr load_resident_export_ptr_to_scan_zp
    jsr native_local_emit_named_target
    jsr native_local_restore_body_scan
    lda #$03
    jsr native_local_add_reloc_offset
    jmp native_local_emit_reloc_body

native_local_reloc_body_done:
    clc
    rts
native_local_reloc_bad:
    sec
    rts

native_local_reloc_label_at_addend:
    clc
    adc native_local_reloc_offset_lo
    sta native_local_temp_offset_lo
    lda native_local_reloc_offset_hi
    adc #$00
    tay
    lda native_local_temp_offset_lo
    jsr native_local_emit_reloc_prefix
    ldx native_local_saved_label
    jsr native_local_build_label_name
    jsr native_local_emit_named_target
    jmp native_local_restore_body_scan

native_local_restore_body_scan:
    ldx native_local_current_proc
    lda #ACTC_OVERLAY_CTX_SET_BODY_PTR_FN_LO
    jsr call_indexed_context_function
    jmp load_resident_body_ptr_to_scan_zp

native_local_emit_pointer_reloc:
    jsr native_local_emit_reloc_prefix
    lda #<native_local_name_pointer
    sta ACTC_OVERLAY_SCAN_ZP
    lda #>native_local_name_pointer
    sta ACTC_OVERLAY_SCAN_ZP+1
    jmp native_local_emit_named_target

native_local_emit_reloc_prefix:
    sta native_local_temp_offset_lo
    sty native_local_temp_offset_hi
    lda #'r'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    lda native_local_temp_offset_lo
    ldy native_local_temp_offset_hi
    jsr emit_word_decimal
    lda #' '
    jmp emit_char_overlay

native_local_emit_named_target:
    lda #'x'
    jsr emit_char_overlay
    lda #' '
    jsr emit_char_overlay
    jsr emit_lower_scan_zp_string
    jmp emit_newline

native_local_add_reloc_offset:
    clc
    adc native_local_reloc_offset_lo
    sta native_local_reloc_offset_lo
    bcc :+
    inc native_local_reloc_offset_hi
:   rts

native_local_prologue:
    .byte $A2,$00,$BD,$00,$00,$85,$06,$E8,$BD,$00,$00,$85,$07
native_local_prologue_end:
native_local_load_tail:
    .byte $B1,$06,$48,$C8,$B1,$06,$48
native_local_load_tail_end:
native_local_store_head:
    .byte $68,$AA,$68,$A0
native_local_store_head_end:
native_local_store_tail:
    .byte $91,$06,$C8,$8A,$91,$06
native_local_store_tail_end:
native_local_equal_bytes:
    .byte $68,$85,$05,$68,$85,$04,$68,$85,$03,$68,$C5,$04,$D0,$06,$A5,$03,$C5,$05,$F0,$03,$4C,$00,$00
native_local_equal_bytes_end:
native_local_else_bytes:
    .byte $4C,$00,$00
native_local_else_bytes_end:
native_local_call_bytes:
    .byte $20,$00,$00
native_local_call_bytes_end:
native_local_exit_bytes:
    .byte $A9,$A5,$8D,$D0,$03,$A9,$00,$85,$02,$85,$03,$A2,$02,$4C,$0F,$CF
native_local_exit_bytes_end:

native_local_name_data:
    .asciiz "__idata"
native_local_name_pointer:
    .asciiz "__iptr"
native_local_label_name:
    .byte '_','_','p','0','l','0',$00

native_local_proc_count:
    .byte $00
native_local_main_proc:
    .byte $00
native_local_current_proc:
    .byte $00
native_local_proc_offset_lo:
    .res NATIVE_LOCAL_PROC_MAX, $00
native_local_proc_offset_hi:
    .res NATIVE_LOCAL_PROC_MAX, $00
native_local_proc_size_lo:
    .res NATIVE_LOCAL_PROC_MAX, $00
native_local_proc_size_hi:
    .res NATIVE_LOCAL_PROC_MAX, $00
native_local_proc_label_count:
    .res NATIVE_LOCAL_PROC_MAX, $00
native_local_proc_debug_base:
    .res NATIVE_LOCAL_PROC_MAX, $00
native_local_total_code_lo:
    .byte $00
native_local_total_code_hi:
    .byte $00
native_local_code_size_lo:
    .byte $00
native_local_code_size_hi:
    .byte $00
native_local_data_size_lo:
    .byte $00
native_local_data_size_hi:
    .byte $00
native_local_root_size_lo:
    .byte $00
native_local_root_size_hi:
    .byte $00
native_local_export_offset_lo:
    .byte $00
native_local_export_offset_hi:
    .byte $00
native_local_export_size_lo:
    .byte $00
native_local_export_size_hi:
    .byte $00
native_local_stack_depth:
    .byte $00
native_local_control_depth:
    .byte $00
native_local_control_kind:
    .res NATIVE_LOCAL_CONTROL_MAX, $00
native_local_control_target:
    .res NATIVE_LOCAL_CONTROL_MAX, $00
native_local_control_end:
    .res NATIVE_LOCAL_CONTROL_MAX, $FF
native_local_label_count:
    .byte $00
native_local_label_index:
    .byte $00
native_local_label_offset_lo:
    .res NATIVE_LOCAL_LABEL_MAX, $00
native_local_label_offset_hi:
    .res NATIVE_LOCAL_LABEL_MAX, $00
native_local_saved_label:
    .byte $00
native_local_body_pos:
    .byte $00
native_local_operand_index:
    .byte $00
native_local_target_var:
    .byte $00
native_local_var_offset:
    .byte $00
native_local_lowering_seen:
    .byte $00
native_local_record_debug:
    .byte $00
native_local_expected_debug_count:
    .byte $00
native_local_debug_count:
    .byte $00
native_int_debug_offsets_lo:
    .res ACTC_OVERLAY_BODY_OP_LIMIT, $00
native_int_debug_offsets_hi:
    .res ACTC_OVERLAY_BODY_OP_LIMIT, $00
native_local_marker_count:
    .byte $00
native_local_const_ptr_lo:
    .byte $00
native_local_const_ptr_hi:
    .byte $00
native_local_const_len:
    .byte $00
native_local_const_index:
    .byte $00
native_local_machine_byte:
    .byte $00
native_local_reloc_offset_lo:
    .byte $00
native_local_reloc_offset_hi:
    .byte $00
native_local_temp_offset_lo:
    .byte $00
native_local_temp_offset_hi:
    .byte $00
