; Linker-emitted source map for native PRG debugging. Debug records remain in
; a sidecar so normal runnable images carry no debugger payload.

emit_debug_sidecar_or_fail:
    jsr build_debug_save_target_path
    jsr open_output_stream_to_target_or_fail
    lda #$00
    sta main_flags_lo
    sta main_flags_hi
    lda #'D'
    jsr append_debug_char
    lda #'B'
    jsr append_debug_char
    lda #'G'
    jsr append_debug_char
    lda #'1'
    jsr append_debug_char
    jsr append_debug_newline

    jsr save_current_module_name
    jsr reload_root_object_or_fail
    jsr parse_exports_or_fail
    ldx root_entry_export_index
    jsr load_export_meta_window_from_x_or_fail
    jsr set_current_object_context_to_root_export_or_fail
    lda #$01
    sta debug_is_root
    lda #$00
    sta debug_module_index
    jsr emit_debug_entry_record_or_fail
    jsr emit_current_object_debug_records_or_fail

    lda #$00
    sta linked_object_index
emit_debug_sidecar_external_loop:
    ldx linked_object_index
    cpx external_count
    beq emit_debug_sidecar_done
    jsr copy_external_name_to_module_name_from_x_or_fail
    jsr build_object_target_path
    jsr load_pending_object_or_library_or_fail
    jsr require_loaded_source_not_truncated_or_fail
    jsr require_supported_object_header_or_fail
    jsr parse_exports_or_fail
    jsr find_export_index_from_module_name
    bcc emit_debug_sidecar_external_have_export
    jmp debug_sidecar_bad_object
emit_debug_sidecar_external_have_export:
    jsr load_export_meta_window_from_x_or_fail
    ldx linked_object_index
    jsr set_current_object_context_from_pending_index_x_or_fail
    lda #$00
    sta debug_is_root
    lda linked_object_index
    clc
    adc #$01
    sta debug_module_index
    jsr emit_current_object_debug_records_or_fail
    inc linked_object_index
    jmp emit_debug_sidecar_external_loop

emit_debug_sidecar_done:
    jsr restore_saved_module_name
    jsr flush_output_stream_or_fail
    jmp close_output_stream

emit_debug_entry_record_or_fail:
    lda #'e'
    jsr append_debug_char
    jsr append_debug_space
    lda current_object_addr_lo
    ldy current_object_addr_hi
    jsr append_debug_word_decimal
    jmp append_debug_newline

emit_current_object_debug_records_or_fail:
    jsr emit_debug_module_record
    jsr prepare_current_object_debug_vars
    jsr reset_scan_ptr_after_header
emit_current_object_debug_records_loop:
    jsr skip_line_breaks
    ldy #$00
    lda (scan_ptr),y
    beq emit_current_object_debug_records_done
    lda #<line_debug_file
    sta const_ptr
    lda #>line_debug_file
    sta const_ptr+1
    jsr pattern_matches_scan_ptr
    bcs emit_current_object_debug_records_check_proc
    jsr emit_current_object_debug_file_or_fail
    jmp emit_current_object_debug_records_loop
emit_current_object_debug_records_check_proc:
    lda #<line_debug_proc
    sta const_ptr
    lda #>line_debug_proc
    sta const_ptr+1
    jsr pattern_matches_scan_ptr
    bcs emit_current_object_debug_records_check_line
    jsr emit_current_object_debug_proc_or_fail
    jmp emit_current_object_debug_records_loop
emit_current_object_debug_records_check_line:
    lda #<line_debug_native_line
    sta const_ptr
    lda #>line_debug_native_line
    sta const_ptr+1
    jsr pattern_matches_scan_ptr
    bcs emit_current_object_debug_records_check_var
    jsr emit_current_object_debug_line_or_fail
    jmp emit_current_object_debug_records_loop
emit_current_object_debug_records_check_var:
    lda #<line_debug_var
    sta const_ptr
    lda #>line_debug_var
    sta const_ptr+1
    jsr pattern_matches_scan_ptr
    bcs emit_current_object_debug_records_skip
    jsr emit_current_object_debug_var_or_fail
    jmp emit_current_object_debug_records_loop
emit_current_object_debug_records_skip:
    jsr skip_current_line
    jmp emit_current_object_debug_records_loop
emit_current_object_debug_records_done:
    rts

emit_debug_module_record:
    lda #'m'
    jsr append_debug_char
    jsr append_debug_space
    lda debug_module_index
    ldy #$00
    jsr append_debug_word_decimal
    jsr append_debug_space
    ldy #$00
emit_debug_module_record_loop:
    lda module_name,y
    beq emit_debug_module_record_done
    jsr append_debug_char
    iny
    bne emit_debug_module_record_loop
emit_debug_module_record_done:
    jmp append_debug_newline

emit_current_object_debug_file_or_fail:
    lda #<line_debug_file
    sta const_ptr
    lda #>line_debug_file
    sta const_ptr+1
    jsr advance_scan_ptr_by_const_ptr
    jsr parse_decimal_word_or_fail
    lda current_bit_lo
    sta debug_file_id_lo
    lda current_bit_hi
    sta debug_file_id_hi
    jsr require_space_or_fail
    lda #'f'
    jsr append_debug_char
    jsr append_debug_space
    lda debug_module_index
    ldy #$00
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda debug_file_id_lo
    ldy debug_file_id_hi
    jsr append_debug_word_decimal
    jsr append_debug_space
emit_current_object_debug_file_copy:
    ldy #$00
    lda (scan_ptr),y
    beq emit_current_object_debug_file_done
    cmp #10
    beq emit_current_object_debug_file_done
    cmp #13
    beq emit_current_object_debug_file_done
    jsr append_debug_char
    jsr advance_scan_ptr
    jmp emit_current_object_debug_file_copy
emit_current_object_debug_file_done:
    jmp append_debug_newline

emit_current_object_debug_proc_or_fail:
    lda #<line_debug_proc
    sta const_ptr
    lda #>line_debug_proc
    sta const_ptr+1
    jsr advance_scan_ptr_by_const_ptr
    jsr parse_debug_location_prefix_or_fail
    ldx debug_export_index
    jsr load_debug_export_address_from_x
    bcs emit_current_object_debug_proc_done
    lda #'q'
    jsr append_debug_char
    jsr append_debug_common_location
    jsr append_debug_space
    ldx debug_export_index
    jsr load_export_name_window_from_x_or_fail
    ldy #$00
emit_current_object_debug_proc_name:
    lda export_name_window,y
    beq emit_current_object_debug_proc_newline
    jsr append_debug_char
    iny
    bne emit_current_object_debug_proc_name
emit_current_object_debug_proc_newline:
    jsr append_debug_newline
emit_current_object_debug_proc_done:
    rts

emit_current_object_debug_line_or_fail:
    lda #<line_debug_native_line
    sta const_ptr
    lda #>line_debug_native_line
    sta const_ptr+1
    jsr advance_scan_ptr_by_const_ptr
    jsr parse_decimal_byte_or_fail
    sta debug_export_index
    jsr require_space_or_fail
    jsr parse_decimal_word_or_fail
    lda current_bit_lo
    sta debug_code_offset_lo
    lda current_bit_hi
    sta debug_code_offset_hi
    jsr require_space_or_fail
    jsr parse_debug_source_location_or_fail
    ldx debug_export_index
    jsr load_debug_export_address_from_x
    bcs emit_current_object_debug_line_done
    clc
    lda debug_address_lo
    adc debug_code_offset_lo
    sta debug_address_lo
    lda debug_address_hi
    adc debug_code_offset_hi
    sta debug_address_hi
    bcc :+
    jmp debug_sidecar_bad_object
:
    lda #'l'
    jsr append_debug_char
    jsr append_debug_common_location
    jsr append_debug_newline
emit_current_object_debug_line_done:
    rts

prepare_current_object_debug_vars:
    jsr parse_vars_or_fail
    lda #$00
    sta debug_data_available
    ldx #$00
prepare_current_object_debug_vars_export_loop:
    cpx export_count
    beq prepare_current_object_debug_vars_done
    stx debug_var_scan_index
    jsr load_export_name_window_from_x_or_fail
    ldy #$00
prepare_current_object_debug_vars_name_loop:
    lda export_name_window,y
    jsr lowercase_ascii
    cmp debug_name_data,y
    bne prepare_current_object_debug_vars_next
    lda debug_name_data,y
    beq prepare_current_object_debug_vars_found
    iny
    bne prepare_current_object_debug_vars_name_loop
prepare_current_object_debug_vars_next:
    ldx debug_var_scan_index
    inx
    bne prepare_current_object_debug_vars_export_loop
prepare_current_object_debug_vars_found:
    ldx debug_var_scan_index
    jsr load_debug_export_address_from_x
    bcs prepare_current_object_debug_vars_done
    lda debug_address_lo
    sta debug_data_address_lo
    lda debug_address_hi
    sta debug_data_address_hi
    lda #$01
    sta debug_data_available
prepare_current_object_debug_vars_done:
    rts

emit_current_object_debug_var_or_fail:
    lda #<line_debug_var
    sta const_ptr
    lda #>line_debug_var
    sta const_ptr+1
    jsr advance_scan_ptr_by_const_ptr
    ldy #$00
    lda (scan_ptr),y
    sta debug_var_scope
    jsr advance_scan_ptr
    jsr require_space_or_fail
    ldy #$00
    lda (scan_ptr),y
    sta debug_var_type
    jsr advance_scan_ptr
    jsr require_space_or_fail
    lda debug_var_scope
    cmp #'g'
    beq emit_current_object_debug_var_global
    cmp #'p'
    beq emit_current_object_debug_var_proc
    cmp #'l'
    beq emit_current_object_debug_var_proc
    jmp debug_sidecar_bad_object
emit_current_object_debug_var_global:
    lda #$00
    sta debug_var_export_index
    jsr parse_decimal_byte_or_fail
    sta debug_var_index
    jsr require_space_or_fail
    jsr parse_decimal_byte_or_fail
    jmp emit_current_object_debug_var_location
emit_current_object_debug_var_proc:
    jsr parse_decimal_byte_or_fail
    sta debug_var_export_index
    jsr require_space_or_fail
    jsr parse_decimal_byte_or_fail
    sta debug_var_index
    jsr require_space_or_fail
    jsr parse_decimal_byte_or_fail
emit_current_object_debug_var_location:
    jsr require_space_or_fail
    jsr parse_decimal_word_or_fail
    lda current_bit_lo
    sta debug_line_lo
    lda current_bit_hi
    sta debug_line_hi
    jsr require_space_or_fail
    jsr parse_decimal_word_or_fail
    lda current_bit_lo
    sta debug_col_lo
    lda current_bit_hi
    sta debug_col_hi
    lda debug_data_available
    bne :+
    rts
:
    ldx debug_var_index
    cpx var_count
    bcc :+
    jmp debug_sidecar_bad_object
:
    jsr load_var_meta_window_from_x_or_fail
    lda var_meta_window+VAR_META_WIDTH
    sta debug_var_width
    lda debug_data_address_lo
    sta debug_address_lo
    lda debug_data_address_hi
    sta debug_address_hi
    ldx #$00
emit_current_object_debug_var_offset_loop:
    cpx debug_var_index
    beq emit_current_object_debug_var_emit
    stx debug_var_scan_index
    jsr load_var_meta_window_from_x_or_fail
    clc
    lda debug_address_lo
    adc var_meta_window+VAR_META_WIDTH
    sta debug_address_lo
    bcc :+
    inc debug_address_hi
:
    ldx debug_var_scan_index
    inx
    bne emit_current_object_debug_var_offset_loop
emit_current_object_debug_var_emit:
    lda #'v'
    jsr append_debug_char
    jsr append_debug_space
    lda debug_var_scope
    jsr append_debug_char
    jsr append_debug_space
    lda debug_var_type
    jsr append_debug_char
    jsr append_debug_space
    lda debug_module_index
    ldy #$00
    jsr append_debug_word_decimal
    lda debug_var_scope
    cmp #'g'
    beq :+
    jsr append_debug_space
    lda debug_var_export_index
    ldy #$00
    jsr append_debug_word_decimal
:
    jsr append_debug_space
    lda debug_var_index
    ldy #$00
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda debug_address_lo
    ldy debug_address_hi
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda debug_var_width
    ldy #$00
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda #$00
    tay
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda debug_line_lo
    ldy debug_line_hi
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda debug_col_lo
    ldy debug_col_hi
    jsr append_debug_word_decimal
    jsr append_debug_space
    ldx debug_var_index
    jsr load_var_name_window_from_x_or_fail
    ldy #$00
emit_current_object_debug_var_name_loop:
    lda var_name_window,y
    beq emit_current_object_debug_var_done
    jsr append_debug_char
    iny
    bne emit_current_object_debug_var_name_loop
emit_current_object_debug_var_done:
    jmp append_debug_newline

parse_debug_location_prefix_or_fail:
    jsr parse_decimal_byte_or_fail
    sta debug_export_index
    jsr require_space_or_fail
parse_debug_source_location_or_fail:
    jsr parse_decimal_word_or_fail
    lda current_bit_lo
    sta debug_file_id_lo
    lda current_bit_hi
    sta debug_file_id_hi
    jsr require_space_or_fail
    jsr parse_decimal_word_or_fail
    lda current_bit_lo
    sta debug_line_lo
    lda current_bit_hi
    sta debug_line_hi
    jsr require_space_or_fail
    jsr parse_decimal_word_or_fail
    lda current_bit_lo
    sta debug_col_lo
    lda current_bit_hi
    sta debug_col_hi
    rts

load_debug_export_address_from_x:
    stx debug_export_index
    cpx export_count
    bcc :+
    jmp debug_sidecar_bad_object
:
    jsr load_export_meta_window_from_x_or_fail
    lda export_meta_window+EXPORT_META_OFFSET_LO
    sta current_bit_lo
    lda export_meta_window+EXPORT_META_OFFSET_HI
    sta current_bit_hi
    jsr current_object_export_target_is_selected
    bcs load_debug_export_address_skip
    sec
    lda export_meta_window+EXPORT_META_OFFSET_LO
    sbc current_object_export_start_lo
    sta debug_address_lo
    lda export_meta_window+EXPORT_META_OFFSET_HI
    sbc current_object_export_start_hi
    sta debug_address_hi
    clc
    lda debug_address_lo
    adc current_object_addr_lo
    sta debug_address_lo
    lda debug_address_hi
    adc current_object_addr_hi
    sta debug_address_hi
    bcc :+
    jmp debug_sidecar_bad_object
:
    clc
    rts
load_debug_export_address_skip:
    sec
    rts

append_debug_common_location:
    jsr append_debug_space
    lda debug_module_index
    ldy #$00
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda debug_export_index
    ldy #$00
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda debug_address_lo
    ldy debug_address_hi
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda debug_file_id_lo
    ldy debug_file_id_hi
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda debug_line_lo
    ldy debug_line_hi
    jsr append_debug_word_decimal
    jsr append_debug_space
    lda debug_col_lo
    ldy debug_col_hi
    jmp append_debug_word_decimal

append_debug_space:
    lda #' '
append_debug_char:
    jmp append_payload_byte

append_debug_newline:
    lda #10
    jmp append_debug_char

append_debug_word_decimal:
    sta debug_value_lo
    sty debug_value_hi
    lda #$00
    sta debug_digit_started
    ldx #$00
append_debug_decimal_10000_loop:
    lda debug_value_hi
    cmp #$27
    bcc append_debug_decimal_10000_done
    bne append_debug_decimal_10000_sub
    lda debug_value_lo
    cmp #$10
    bcc append_debug_decimal_10000_done
append_debug_decimal_10000_sub:
    sec
    lda debug_value_lo
    sbc #$10
    sta debug_value_lo
    lda debug_value_hi
    sbc #$27
    sta debug_value_hi
    inx
    bne append_debug_decimal_10000_loop
append_debug_decimal_10000_done:
    txa
    jsr append_debug_decimal_digit
    ldx #$00
append_debug_decimal_1000_loop:
    lda debug_value_hi
    cmp #$03
    bcc append_debug_decimal_1000_done
    bne append_debug_decimal_1000_sub
    lda debug_value_lo
    cmp #$E8
    bcc append_debug_decimal_1000_done
append_debug_decimal_1000_sub:
    sec
    lda debug_value_lo
    sbc #$E8
    sta debug_value_lo
    lda debug_value_hi
    sbc #$03
    sta debug_value_hi
    inx
    bne append_debug_decimal_1000_loop
append_debug_decimal_1000_done:
    txa
    jsr append_debug_decimal_digit
    ldx #$00
append_debug_decimal_100_loop:
    lda debug_value_hi
    bne append_debug_decimal_100_sub
    lda debug_value_lo
    cmp #100
    bcc append_debug_decimal_100_done
append_debug_decimal_100_sub:
    sec
    lda debug_value_lo
    sbc #100
    sta debug_value_lo
    lda debug_value_hi
    sbc #$00
    sta debug_value_hi
    inx
    bne append_debug_decimal_100_loop
append_debug_decimal_100_done:
    txa
    jsr append_debug_decimal_digit
    ldx #$00
append_debug_decimal_10_loop:
    lda debug_value_hi
    bne append_debug_decimal_10_sub
    lda debug_value_lo
    cmp #10
    bcc append_debug_decimal_10_done
append_debug_decimal_10_sub:
    sec
    lda debug_value_lo
    sbc #10
    sta debug_value_lo
    lda debug_value_hi
    sbc #$00
    sta debug_value_hi
    inx
    bne append_debug_decimal_10_loop
append_debug_decimal_10_done:
    txa
    jsr append_debug_decimal_digit
    lda debug_value_lo
    clc
    adc #'0'
    jmp append_debug_char

append_debug_decimal_digit:
    pha
    cmp #$00
    bne append_debug_decimal_digit_emit
    lda debug_digit_started
    beq append_debug_decimal_digit_skip
append_debug_decimal_digit_emit:
    pla
    clc
    adc #'0'
    jsr append_debug_char
    lda #$01
    sta debug_digit_started
    rts
append_debug_decimal_digit_skip:
    pla
    rts

build_debug_save_target_path:
    lda #'B'
    sta target_path+0
    lda #'I'
    sta target_path+1
    lda #'N'
    sta target_path+2
    lda #'/'
    sta target_path+3
    ldy #$00
build_debug_save_target_path_loop:
    lda module_name,y
    beq build_debug_save_target_path_suffix
    sta target_path+4,y
    iny
    bne build_debug_save_target_path_loop
build_debug_save_target_path_suffix:
    lda #'.'
    sta target_path+4,y
    iny
    lda #'D'
    sta target_path+4,y
    iny
    lda #'B'
    sta target_path+4,y
    iny
    lda #'G'
    sta target_path+4,y
    iny
    lda #$00
    sta target_path+4,y
    rts

debug_sidecar_bad_object:
    lda #<msg_bad_object
    ldy #>msg_bad_object
    jmp fail_with_ptr

line_debug_file:
    .byte "f ",0
line_debug_proc:
    .byte "q ",0
line_debug_native_line:
    .byte "L ",0
line_debug_var:
    .byte "V ",0
debug_name_data:
    .asciiz "__idata"

.segment "BSS"
debug_module_index:
    .res 1
debug_is_root:
    .res 1
debug_export_index:
    .res 1
debug_code_offset_lo:
    .res 1
debug_code_offset_hi:
    .res 1
debug_address_lo:
    .res 1
debug_address_hi:
    .res 1
debug_file_id_lo:
    .res 1
debug_file_id_hi:
    .res 1
debug_line_lo:
    .res 1
debug_line_hi:
    .res 1
debug_col_lo:
    .res 1
debug_col_hi:
    .res 1
debug_value_lo:
    .res 1
debug_value_hi:
    .res 1
debug_digit_started:
    .res 1
debug_data_available:
    .res 1
debug_data_address_lo:
    .res 1
debug_data_address_hi:
    .res 1
debug_var_scope:
    .res 1
debug_var_type:
    .res 1
debug_var_export_index:
    .res 1
debug_var_index:
    .res 1
debug_var_width:
    .res 1
debug_var_scan_index:
    .res 1

.code
