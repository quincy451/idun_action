.include "actc_overlay_abi.inc"

.ifndef ACTC_KEEP_BODY_RESIDENT_FALLBACK
ACTC_KEEP_BODY_RESIDENT_FALLBACK = 0
.endif

.ifndef LOOP_MAX
LOOP_MAX = 16
.endif

.export actc_overlay_header
.export actc_overlay_entry
.export actc_overlay_end

.segment "CODE"

actc_overlay_header:
    .byte 'A','C','O','V'
    .byte ACTC_OVERLAY_ABI_VERSION
    .byte ACTC_OVERLAY_PASS_BODY_COLLECT
    .word ACTC_OVERLAY_EXEC_BASE
    .word actc_overlay_entry
    .word actc_overlay_end - actc_overlay_header
    .word $0000

actc_overlay_entry:
    stx ACTC_OVERLAY_CONTEXT_ZP
    sty ACTC_OVERLAY_CONTEXT_ZP+1
    ldy #ACTC_OVERLAY_CTX_PASS_ID
    lda #ACTC_OVERLAY_PASS_BODY_COLLECT
    sta (ACTC_OVERLAY_CONTEXT_ZP),y

    jsr collect_proc_body_ops_overlay
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

collect_proc_body_ops_overlay:
    lda #$00
    sta loop_depth_local
    lda #ACTC_OVERLAY_CTX_BEGIN_BODY_SCAN_FN_LO
    jsr call_context_function
    bcc collect_proc_body_ops_overlay_loop
    lda #<msg_load_fail
    ldy #>msg_load_fail
    jmp fail_with_diag

collect_proc_body_ops_overlay_loop:
    jsr load_current_char
    bne collect_proc_body_ops_overlay_have_char
    jmp collect_proc_body_ops_overlay_done
collect_proc_body_ops_overlay_have_char:
    cmp #10
    bne :+
    jmp collect_proc_body_ops_overlay_advance_blank
:   cmp #13
    bne :+
    jmp collect_proc_body_ops_overlay_advance_blank
:

    lda #ACTC_OVERLAY_CTX_SKIP_SOURCE_SPACES_FN_LO
    jsr call_context_function
    jsr load_current_char
    bne collect_proc_body_ops_overlay_after_space_check
    jmp collect_proc_body_ops_overlay_done
collect_proc_body_ops_overlay_after_space_check:
    lda #<pattern_proc
    ldy #>pattern_proc
    jsr pattern_matches_local_scan_ptr
    bcs :+
    jmp collect_proc_body_ops_overlay_proc_decl
:

    lda #ACTC_OVERLAY_CTX_CURRENT_PROC_INDEX_PTR_LO
    jsr load_byte_from_context_ptr
    cmp #$FF
    bne :+
    jmp collect_proc_body_ops_overlay_skip_line
:
    lda #ACTC_OVERLAY_CTX_STORE_CURRENT_BODY_DEBUG_MARK_FN_LO
    jsr call_context_function

    lda #ACTC_OVERLAY_CTX_MATCH_SCALAR_DECL_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_try_od
:   

    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_PTR_BY_CONST_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_SKIP_SOURCE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_COPY_SYMBOL_FROM_SCAN_PTR_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_var
:   sty symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_CURRENT_PROC_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #ACTC_OVERLAY_CTX_FIND_CURRENT_PROC_LOCAL_FN_LO
    jsr call_indexed_context_function_keep_x
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_var
:   txa
    ldx #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr store_a_to_context_byte_ptr
    ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    beq collect_proc_body_ops_overlay_local_skip_line
    cmp #10
    beq collect_proc_body_ops_overlay_local_skip_line
    cmp #13
    beq collect_proc_body_ops_overlay_local_skip_line
    cmp #'='
    beq :+
    jmp collect_proc_body_ops_overlay_bad_var
:   jmp collect_proc_body_ops_overlay_local_after_equals
collect_proc_body_ops_overlay_local_skip_line:
    jmp collect_proc_body_ops_overlay_skip_line
collect_proc_body_ops_overlay_local_after_equals:
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #ACTC_OVERLAY_CTX_REQUIRE_WORD_VAR_FN_LO
    jsr call_indexed_context_function_keep_x
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_var
:   ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'['
    beq collect_proc_body_ops_overlay_try_local_int_group
    jmp collect_proc_body_ops_overlay_try_local_int_parse_value

collect_proc_body_ops_overlay_try_local_int_group:
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   lda #ACTC_OVERLAY_CTX_EMIT_RUNTIME_VALUE_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #']'
    beq :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc collect_proc_body_ops_overlay_try_local_int_after_value
    jmp collect_proc_body_ops_overlay_bad_literal

collect_proc_body_ops_overlay_try_local_int_parse_value:
    lda #ACTC_OVERLAY_CTX_EMIT_RUNTIME_VALUE_FN_LO
    jsr call_context_function
    bcc collect_proc_body_ops_overlay_try_local_int_after_value
    jmp collect_proc_body_ops_overlay_bad_literal

collect_proc_body_ops_overlay_try_local_int_after_value:
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    lda #'S'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_try_od:
    lda #<pattern_od
    ldy #>pattern_od
    jsr pattern_matches_local_scan_ptr_keyword
    bcs collect_proc_body_ops_overlay_try_until
    jsr pop_loop_kind_local_or_fail
    beq :+
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_NO_ARG_FN_LO
    jsr load_context_function_ptr
    lda #'x'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line
:   lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_NO_ARG_FN_LO
    jsr load_context_function_ptr
    lda #'o'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_try_until:
    lda #<pattern_until
    ldy #>pattern_until
    jsr pattern_matches_local_scan_ptr_keyword
    bcs collect_proc_body_ops_overlay_try_do
    lda #<pattern_until
    ldy #>pattern_until
    jsr advance_scan_ptr_by_local_pattern
    lda #'t'
    jsr store_runtime_condition_with_a_local_or_fail
    bcs :+
    jmp collect_proc_body_ops_overlay_skip_line
:   jmp collect_proc_body_ops_overlay_bad_literal

collect_proc_body_ops_overlay_try_do:
    lda #<pattern_while
    ldy #>pattern_while
    jsr pattern_matches_local_scan_ptr_keyword
    bcs collect_proc_body_ops_overlay_try_do_keyword
    lda #$01
    jsr push_loop_kind_local_or_fail
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_NO_ARG_FN_LO
    jsr load_context_function_ptr
    lda #'d'
    jsr call_loaded_target_with_a
    lda #<pattern_while
    ldy #>pattern_while
    jsr advance_scan_ptr_by_local_pattern
    lda #'f'
    jsr store_runtime_condition_with_a_local_or_fail
    bcs :+
    jmp collect_proc_body_ops_overlay_skip_line
:   jmp collect_proc_body_ops_overlay_bad_literal

collect_proc_body_ops_overlay_try_do_keyword:
    lda #<pattern_do
    ldy #>pattern_do
    jsr pattern_matches_local_scan_ptr_keyword
    bcs collect_proc_body_ops_overlay_try_endif
    lda #$00
    jsr push_loop_kind_local_or_fail
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_NO_ARG_FN_LO
    jsr load_context_function_ptr
    lda #'d'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_try_endif:
    lda #<pattern_endif
    ldy #>pattern_endif
    jsr pattern_matches_local_scan_ptr_keyword
    bcs collect_proc_body_ops_overlay_try_fi
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_NO_ARG_FN_LO
    jsr load_context_function_ptr
    lda #'v'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_try_fi:
    lda #<pattern_fi
    ldy #>pattern_fi
    jsr pattern_matches_local_scan_ptr_keyword
    bcs collect_proc_body_ops_overlay_try_else
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_NO_ARG_FN_LO
    jsr load_context_function_ptr
    lda #'v'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_try_else:
    lda #<pattern_else
    ldy #>pattern_else
    jsr pattern_matches_local_scan_ptr_keyword
    bcs collect_proc_body_ops_overlay_try_if
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_NO_ARG_FN_LO
    jsr load_context_function_ptr
    lda #'w'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_try_if:
    lda #<pattern_if
    ldy #>pattern_if
    jsr pattern_matches_local_scan_ptr_keyword
    bcs collect_proc_body_ops_overlay_try_print_quote
    lda #<pattern_if
    ldy #>pattern_if
    jsr advance_scan_ptr_by_local_pattern
    lda #'h'
    jsr store_runtime_condition_with_a_local_or_fail
    bcs :+
    jmp collect_proc_body_ops_overlay_skip_line
:   jmp collect_proc_body_ops_overlay_bad_literal

collect_proc_body_ops_overlay_try_print_quote:
    lda #<pattern_print_quote
    ldy #>pattern_print_quote
    jsr pattern_matches_local_scan_ptr
    bcs collect_proc_body_ops_overlay_try_printe
    lda #<pattern_print_quote
    ldy #>pattern_print_quote
    jsr advance_scan_ptr_by_local_pattern
    lda #ACTC_OVERLAY_CTX_STORE_STRING_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    lda #'s'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_try_printe:
    lda #<pattern_printe_quote
    ldy #>pattern_printe_quote
    jsr pattern_matches_local_scan_ptr
    bcs collect_proc_body_ops_overlay_try_printre
    lda #<pattern_printe_quote
    ldy #>pattern_printe_quote
    jsr advance_scan_ptr_by_local_pattern
    lda #ACTC_OVERLAY_CTX_STORE_STRING_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    lda #'e'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_try_printre:
    lda #<pattern_printre
    ldy #>pattern_printre
    jsr pattern_matches_local_scan_ptr
    bcs collect_proc_body_ops_overlay_try_printr
    lda #<pattern_printre
    ldy #>pattern_printre
    jsr advance_scan_ptr_by_local_pattern
    lda #$01
    jsr store_runtime_real_print_with_newline_flag_local_or_fail
    bcs :+
    jmp collect_proc_body_ops_overlay_skip_line
:   
    jmp collect_proc_body_ops_overlay_bad_literal

collect_proc_body_ops_overlay_try_printr:
    lda #<pattern_printr
    ldy #>pattern_printr
    jsr pattern_matches_local_scan_ptr
    bcs collect_proc_body_ops_overlay_try_printie
    lda #<pattern_printr
    ldy #>pattern_printr
    jsr advance_scan_ptr_by_local_pattern
    lda #$00
    jsr store_runtime_real_print_with_newline_flag_local_or_fail
    bcs :+
    jmp collect_proc_body_ops_overlay_skip_line
:   
    jmp collect_proc_body_ops_overlay_bad_literal

collect_proc_body_ops_overlay_try_printie:
    lda #<pattern_printie
    ldy #>pattern_printie
    jsr pattern_matches_local_scan_ptr
    bcs collect_proc_body_ops_overlay_try_printi
    lda #<pattern_printie
    ldy #>pattern_printie
    jsr advance_scan_ptr_by_local_pattern
    lda #ACTC_OVERLAY_CTX_STORE_SMALL_DECIMAL_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    lda #'z'
    jsr store_runtime_expr_with_a_local_or_fail
    bcs :++
    jmp collect_proc_body_ops_overlay_skip_line
:   lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    lda #'i'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line
:   jmp collect_proc_body_ops_overlay_bad_literal

collect_proc_body_ops_overlay_try_printi:
    lda #<pattern_printi
    ldy #>pattern_printi
    jsr pattern_matches_local_scan_ptr
    bcs collect_proc_body_ops_overlay_try_return
    lda #<pattern_printi
    ldy #>pattern_printi
    jsr advance_scan_ptr_by_local_pattern
    lda #ACTC_OVERLAY_CTX_STORE_SMALL_DECIMAL_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    lda #'y'
    jsr store_runtime_expr_with_a_local_or_fail
    bcs :++
    jmp collect_proc_body_ops_overlay_skip_line
:   lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    lda #'j'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line
:   jmp collect_proc_body_ops_overlay_bad_literal

collect_proc_body_ops_overlay_try_return:
    lda #<pattern_return
    ldy #>pattern_return
    jsr pattern_matches_local_scan_ptr_keyword
    bcs collect_proc_body_ops_overlay_try_assignment
    lda #<pattern_return
    ldy #>pattern_return
    jsr advance_scan_ptr_by_local_pattern
    ldy #$00
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    beq collect_proc_body_ops_overlay_try_return_emit
    cmp #10
    beq collect_proc_body_ops_overlay_try_return_emit
    cmp #13
    beq collect_proc_body_ops_overlay_try_return_emit
    lda #ACTC_OVERLAY_CTX_EMIT_RUNTIME_VALUE_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcc collect_proc_body_ops_overlay_try_return_emit
    jmp collect_proc_body_ops_overlay_bad_literal
collect_proc_body_ops_overlay_try_return_emit:
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_NO_ARG_FN_LO
    jsr load_context_function_ptr
    lda #'r'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_try_assignment:
    lda #ACTC_OVERLAY_CTX_COPY_SYMBOL_FROM_SCAN_PTR_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_skip_line
:   sty symbol_end_y_local
    ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'='
    beq :+
    jmp collect_proc_body_ops_overlay_try_local_call
:   
    sty symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_FIND_VAR_INDEX_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_var
:   txa
    ldx #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr store_a_to_context_byte_ptr
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #ACTC_OVERLAY_CTX_REQUIRE_WORD_VAR_FN_LO
    jsr call_indexed_context_function_keep_x
    bcc collect_proc_body_ops_overlay_try_assignment_word
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #ACTC_OVERLAY_CTX_REQUIRE_REAL_VAR_FN_LO
    jsr call_indexed_context_function
    bcc collect_proc_body_ops_overlay_try_assignment_real
    jmp collect_proc_body_ops_overlay_bad_var

collect_proc_body_ops_overlay_try_assignment_word:
    ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   jsr try_emit_runtime_int_value_local_or_fail
    bcc collect_proc_body_ops_overlay_try_assignment_word_require_line_end
    lda int_parse_matched_local
    beq collect_proc_body_ops_overlay_try_assignment_word_emit_generic
    jmp collect_proc_body_ops_overlay_bad_literal
collect_proc_body_ops_overlay_try_assignment_word_emit_generic:
    lda #ACTC_OVERLAY_CTX_EMIT_RUNTIME_VALUE_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
collect_proc_body_ops_overlay_try_assignment_word_require_line_end:
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    lda #'S'
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_try_assignment_real:
    ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_literal
:   jsr emit_real_assignment_local_or_fail
    bcc collect_proc_body_ops_overlay_skip_line
    jmp collect_proc_body_ops_overlay_bad_literal

collect_proc_body_ops_overlay_try_local_call:
    ldy symbol_end_y_local
    jsr read_scan_char_at_y
    cmp #'('
    bne collect_proc_body_ops_overlay_skip_line
    lda #ACTC_OVERLAY_CTX_RESOLVE_CALL_TARGET_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_proc
:   ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_EMIT_CALL_ARGS_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_proc
:   lda #ACTC_OVERLAY_CTX_CALL_TARGET_KIND_PTR_LO
    jsr load_byte_from_context_ptr
    pha
    lda #ACTC_OVERLAY_CTX_CALL_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    pla
    jsr call_loaded_target_with_a
    jmp collect_proc_body_ops_overlay_skip_line

collect_proc_body_ops_overlay_skip_line:
    lda #ACTC_OVERLAY_CTX_SKIP_SOURCE_LINE_FN_LO
    jsr call_context_function
    jmp collect_proc_body_ops_overlay_loop

collect_proc_body_ops_overlay_proc_decl:
    lda #<pattern_proc
    ldy #>pattern_proc
    jsr advance_scan_ptr_by_local_pattern
    lda #ACTC_OVERLAY_CTX_SKIP_SOURCE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_COPY_SYMBOL_FROM_SCAN_PTR_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_proc
:   lda #ACTC_OVERLAY_CTX_FIND_EXPORT_INDEX_FN_LO
    jsr call_context_function
    bcc :+
    jmp collect_proc_body_ops_overlay_bad_proc
:   txa
    ldx #ACTC_OVERLAY_CTX_CURRENT_PROC_INDEX_PTR_LO
    jsr store_a_to_context_byte_ptr
    lda #ACTC_OVERLAY_CTX_STORE_CURRENT_BODY_DEBUG_MARK_FN_LO
    jsr call_context_function
    jsr emit_current_proc_param_binds_local_or_fail
    lda #ACTC_OVERLAY_CTX_SKIP_SOURCE_LINE_FN_LO
    jsr call_context_function
    jmp collect_proc_body_ops_overlay_loop

collect_proc_body_ops_overlay_advance_blank:
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_PTR_FN_LO
    jsr call_context_function
    jmp collect_proc_body_ops_overlay_loop

collect_proc_body_ops_overlay_bad_proc:
    lda #<msg_bad_proc
    ldy #>msg_bad_proc
    jmp fail_with_diag

collect_proc_body_ops_overlay_bad_var:
    lda #<msg_bad_var
    ldy #>msg_bad_var
    jmp fail_with_diag

collect_proc_body_ops_overlay_bad_literal:
    lda #<msg_bad_literal
    ldy #>msg_bad_literal
    jmp fail_with_diag

collect_proc_body_ops_overlay_done:
    lda #ACTC_OVERLAY_CTX_FINISH_BODY_SCAN_FN_LO
    jsr call_context_function
    bcc :+
    lda #<msg_save_fail
    ldy #>msg_save_fail
    jmp fail_with_diag
:   clc
    rts

load_current_char:
    ldy #$00
read_scan_char_at_y:
    sty saved_y_local
    jsr load_resident_scan_ptr_to_scan_zp
    ldy saved_y_local
    lda (ACTC_OVERLAY_SCAN_ZP),y
    php
    ldy saved_y_local
    plp
    rts

uppercase_ascii_local:
    cmp #'a'
    bcc uppercase_ascii_local_done
    cmp #'z'+1
    bcs uppercase_ascii_local_done
    and #$DF
uppercase_ascii_local_done:
    rts

push_loop_kind_local_or_fail:
    ldx loop_depth_local
    cpx #LOOP_MAX
    bcc :+
    lda #<msg_bad_proc
    ldy #>msg_bad_proc
    jmp fail_with_diag
:   sta loop_kind_stack_local,x
    inc loop_depth_local
    rts

pop_loop_kind_local_or_fail:
    ldx loop_depth_local
    bne :+
    lda #<msg_bad_proc
    ldy #>msg_bad_proc
    jmp fail_with_diag
:   dex
    stx loop_depth_local
    lda loop_kind_stack_local,x
    rts

emit_current_proc_param_binds_local_or_fail:
    lda #ACTC_OVERLAY_CTX_CURRENT_PROC_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #ACTC_OVERLAY_CTX_LOAD_PROC_META_FN_LO
    jsr call_indexed_context_function
    lda #ACTC_OVERLAY_CTX_PROC_META_WINDOW_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    beq emit_current_proc_param_binds_local_done
    sta param_bind_count_local
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta param_bind_base_local
emit_current_proc_param_binds_local_loop:
    lda param_bind_count_local
    beq emit_current_proc_param_binds_local_done
    clc
    lda param_bind_base_local
    adc param_bind_count_local
    sec
    sbc #$01
    tax
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    lda #'S'
    jsr call_loaded_target_with_a
    dec param_bind_count_local
    jmp emit_current_proc_param_binds_local_loop
emit_current_proc_param_binds_local_done:
    rts

emit_real_assignment_local_or_fail:
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'('
    bne :+
    jmp emit_real_small_int_assignment_local_or_fail
:   
    cmp #'0'
    bcc :+
    cmp #'9'+1
    bcs :+
    jmp emit_real_small_int_assignment_local_or_fail
:   
    jsr try_consume_real_open_local
    bcs :+
    jmp emit_real_explicit_value_local_or_fail
:   lda #ACTC_OVERLAY_CTX_COPY_SYMBOL_FROM_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    sec
    rts
:   sty symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_FIND_VAR_INDEX_FN_LO
    jsr call_context_function
    bcc :+
    sec
    rts
:   stx real_lhs_index_local
    ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcs emit_real_assignment_local_after_copy_check
    ldx real_lhs_index_local
    lda #ACTC_OVERLAY_CTX_REQUIRE_REAL_VAR_FN_LO
    jsr call_indexed_context_function
    bcc emit_real_assignment_local_copy
    ldx real_lhs_index_local
    lda #ACTC_OVERLAY_CTX_REQUIRE_REAL_BRIDGE_WORD_VAR_FN_LO
    jsr call_indexed_context_function
    bcc emit_real_assignment_local_bridge
    sec
    rts
emit_real_assignment_local_copy:
    jmp emit_real_copy_assignment_local_ok
emit_real_assignment_local_bridge:
    jmp emit_real_bridge_assignment_local_ok
emit_real_assignment_local_after_copy_check:
    ldx real_lhs_index_local
    lda #ACTC_OVERLAY_CTX_REQUIRE_REAL_VAR_FN_LO
    jsr call_indexed_context_function
    bcs emit_real_assignment_local_after_copy_check_fail
    jsr read_scan_char_at_y
    cmp #'+'
    beq :+
    cmp #'-'
    beq :+
    cmp #'*'
    beq :+
    cmp #'/'
    beq :+
    sec
    rts
emit_real_assignment_local_after_copy_check_fail:
    sec
    rts
:   sta real_operator_local
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    sec
    rts
:   lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_COPY_SYMBOL_FROM_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    sec
    rts
:   sty symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_FIND_VAR_INDEX_FN_LO
    jsr call_context_function
    bcc :+
    sec
    rts
:   lda #ACTC_OVERLAY_CTX_REQUIRE_REAL_VAR_FN_LO
    jsr call_indexed_context_function
    bcc :+
    sec
    rts
:   stx real_rhs_index_local
    ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcc :+
    sec
    rts
:   lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_lhs_index_local
    lda #'L'
    jsr call_loaded_target_with_a
    ldx real_lhs_index_local
    lda #'U'
    jsr call_loaded_target_with_a
    ldx real_rhs_index_local
    lda #'L'
    jsr call_loaded_target_with_a
    ldx real_rhs_index_local
    lda #'U'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_REAL_OPERATOR_EXTERNAL_FN_LO
    jsr load_context_function_ptr
    lda real_operator_local
    jsr call_loaded_target_with_a
    bcc :+
    sec
    rts
:   lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    lda #'u'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'T'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'S'
    jsr call_loaded_target_with_a
    clc
    rts

emit_real_copy_assignment_local_ok:
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_lhs_index_local
    lda #'L'
    jsr call_loaded_target_with_a
    ldx real_lhs_index_local
    lda #'U'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'T'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'S'
    jsr call_loaded_target_with_a
    clc
    rts

emit_real_bridge_assignment_local_ok:
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_lhs_index_local
    lda #'L'
    jsr call_loaded_target_with_a
    ldx real_lhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_REAL_BRIDGE_EXTERNAL_FN_LO
    jsr call_indexed_context_function_keep_x
    bcc :+
    sec
    rts
:   lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    lda #'u'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'T'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'S'
    jsr call_loaded_target_with_a
    clc
    rts

try_consume_int_open_local:
    sty symbol_start_y_local
    lda #ACTC_OVERLAY_CTX_SAVE_SOURCE_MARK_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'I'
    bne try_consume_int_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs try_consume_int_open_local_fail_restore
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'N'
    bne try_consume_int_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs try_consume_int_open_local_fail_restore
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'T'
    bne try_consume_int_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs try_consume_int_open_local_fail_restore
    jsr read_scan_char_at_y
    cmp #'('
    bne try_consume_int_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs try_consume_int_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    clc
    rts
try_consume_int_open_local_fail_restore:
    lda #ACTC_OVERLAY_CTX_RESTORE_SOURCE_MARK_FN_LO
    jsr call_context_function
    ldy symbol_start_y_local
    sec
    rts

try_emit_runtime_int_value_local_or_fail:
    lda #$00
    sta int_parse_matched_local
    jsr try_consume_int_open_local
    bcs try_emit_runtime_int_value_local_or_fail_miss
    lda #$01
    sta int_parse_matched_local
    jmp emit_runtime_int_explicit_value_after_open_local_or_fail
try_emit_runtime_int_value_local_or_fail_miss:
    sec
    rts

emit_runtime_int_explicit_value_after_open_local_or_fail:
    lda #ACTC_OVERLAY_CTX_COPY_SYMBOL_FROM_SCAN_Y_FN_LO
    jsr call_context_function
    bcs emit_runtime_int_explicit_value_after_open_local_or_fail_fail
    sty symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_FIND_VAR_INDEX_FN_LO
    jsr call_context_function
    bcs emit_runtime_int_explicit_value_after_open_local_or_fail_fail
    stx real_lhs_index_local
    lda #ACTC_OVERLAY_CTX_REQUIRE_REAL_VAR_FN_LO
    jsr call_indexed_context_function
    bcs emit_runtime_int_explicit_value_after_open_local_or_fail_fail
    ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    bne emit_runtime_int_explicit_value_after_open_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs emit_runtime_int_explicit_value_after_open_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    sty symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_lhs_index_local
    lda #'L'
    jsr call_loaded_target_with_a
    ldx real_lhs_index_local
    lda #'U'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_RT_F_TO_I_FN_LO
    jsr call_context_function
    bcs emit_runtime_int_explicit_value_after_open_local_or_fail_fail
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_rhs_index_local
    lda #'u'
    jsr call_loaded_target_with_a
    ldy symbol_end_y_local
    clc
    rts
emit_runtime_int_explicit_value_after_open_local_or_fail_fail:
    sec
    rts

try_consume_real_open_local:
    sty symbol_start_y_local
    lda #ACTC_OVERLAY_CTX_SAVE_SOURCE_MARK_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'R'
    bne try_consume_real_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs try_consume_real_open_local_fail_restore
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'E'
    bne try_consume_real_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs try_consume_real_open_local_fail_restore
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'A'
    bne try_consume_real_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs try_consume_real_open_local_fail_restore
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'L'
    bne try_consume_real_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs try_consume_real_open_local_fail_restore
    jsr read_scan_char_at_y
    cmp #'('
    bne try_consume_real_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs try_consume_real_open_local_fail_restore
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    clc
    rts
try_consume_real_open_local_fail_restore:
    lda #ACTC_OVERLAY_CTX_RESTORE_SOURCE_MARK_FN_LO
    jsr call_context_function
    ldy symbol_start_y_local
    sec
    rts

emit_real_explicit_bridge_assignment_local_or_fail:
    lda #ACTC_OVERLAY_CTX_COPY_SYMBOL_FROM_SCAN_Y_FN_LO
    jsr call_context_function
    bcs emit_real_explicit_bridge_assignment_local_or_fail_fail
    sty symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_FIND_VAR_INDEX_FN_LO
    jsr call_context_function
    bcs emit_real_explicit_bridge_assignment_local_or_fail_fail
    stx real_lhs_index_local
    lda #ACTC_OVERLAY_CTX_REQUIRE_REAL_BRIDGE_WORD_VAR_FN_LO
    jsr call_indexed_context_function
    bcs emit_real_explicit_bridge_assignment_local_or_fail_fail
    ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    bne emit_real_explicit_bridge_assignment_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs emit_real_explicit_bridge_assignment_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcs emit_real_explicit_bridge_assignment_local_or_fail_fail
    jmp emit_real_bridge_assignment_local_ok
emit_real_explicit_bridge_assignment_local_or_fail_fail:
    sec
    rts

emit_real_explicit_value_local_or_fail:
    sty symbol_start_y_local
    lda #ACTC_OVERLAY_CTX_SAVE_SOURCE_MARK_FN_LO
    jsr call_context_function
    jsr emit_real_explicit_bridge_assignment_local_or_fail
    bcs :+
    clc
    rts
:   lda #ACTC_OVERLAY_CTX_RESTORE_SOURCE_MARK_FN_LO
    jsr call_context_function
    ldy symbol_start_y_local
    jsr parse_positive_word_sum_local_or_fail
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_wide
:   
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    beq :+
    jmp emit_real_explicit_value_local_or_fail_wide
:   
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_wide
:   
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_wide
:   
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$01
    lda (ACTC_OVERLAY_WORK_ZP),y
    bne emit_real_explicit_value_local_or_fail_wide
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    beq emit_real_explicit_value_local_or_fail_zero
    lda #ACTC_OVERLAY_CTX_STORE_ZERO_INT_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta stored_byte_local
    ldy #$00
    lda #ACTC_OVERLAY_CTX_STORE_WORD_LITERAL_FN_LO
    jsr load_context_function_ptr
    lda stored_byte_local
    jsr call_loaded_target_with_a
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_RT_I_TO_F_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    stx real_lhs_index_local
    jmp emit_real_explicit_value_local_finish

emit_real_explicit_value_local_or_fail_zero:
    lda #ACTC_OVERLAY_CTX_STORE_ZERO_INT_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    stx real_rhs_index_local
    stx real_lhs_index_local
    jmp emit_real_literal_assignment_local_from_indexes

emit_real_explicit_value_local_or_fail_wide:
    lda #ACTC_OVERLAY_CTX_RESTORE_SOURCE_MARK_FN_LO
    jsr call_context_function
    ldy symbol_start_y_local
    jsr parse_positive_word_sum_local_or_fail
    bcs emit_real_explicit_value_local_or_fail_signed_prep
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    beq :+
    jmp emit_real_explicit_value_local_or_fail_signed_prep
:   
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_signed_prep
:   
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_signed_prep
:   
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta stored_byte_local
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    ora stored_byte_local
    bne :+
    jmp emit_real_explicit_value_local_or_fail_zero
:   
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    tax
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    txa
    sta stored_byte_local
    lda #ACTC_OVERLAY_CTX_STORE_WORD_LITERAL_FN_LO
    jsr load_context_function_ptr
    lda stored_byte_local
    jsr call_loaded_target_with_a
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_RT_I_TO_F_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    stx real_lhs_index_local
    jmp emit_real_explicit_value_local_finish

emit_real_explicit_value_local_or_fail_signed_prep:
    lda #ACTC_OVERLAY_CTX_RESTORE_SOURCE_MARK_FN_LO
    jsr call_context_function
    ldy symbol_start_y_local
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'0'
    beq :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'-'
    beq :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    jsr parse_optional_grouped_positive_word_sum_local_or_fail
    bcc :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    beq :+
    jmp emit_real_explicit_value_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs emit_real_explicit_value_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcs emit_real_explicit_value_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda #$00
    sec
    sbc (ACTC_OVERLAY_WORK_ZP),y
    tax
    iny
    lda #$00
    sbc (ACTC_OVERLAY_WORK_ZP),y
    tay
    txa
    sta stored_byte_local
    lda #ACTC_OVERLAY_CTX_STORE_WORD_LITERAL_FN_LO
    jsr load_context_function_ptr
    lda stored_byte_local
    jsr call_loaded_target_with_a
    bcs emit_real_explicit_value_local_or_fail_fail
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_RT_S_TO_F_FN_LO
    jsr call_context_function
    bcs emit_real_explicit_value_local_or_fail_fail
    stx real_lhs_index_local

emit_real_explicit_value_local_finish:
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_rhs_index_local
    lda #'p'
    jsr call_loaded_target_with_a
    ldx real_lhs_index_local
    lda #'u'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'T'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'S'
    jsr call_loaded_target_with_a
    clc
    rts

emit_real_explicit_value_local_or_fail_fail:
    sec
    rts

store_positive_word_value_local_to_expr_value:
    tya
    pha
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda positive_word_value_lo
    sta (ACTC_OVERLAY_WORK_ZP),y
    iny
    lda positive_word_value_hi
    sta (ACTC_OVERLAY_WORK_ZP),y
    pla
    tay
    clc
    rts

parse_positive_word_sum_local_or_fail:
.if ACTC_KEEP_BODY_RESIDENT_FALLBACK
    lda #ACTC_OVERLAY_CTX_PARSE_POSITIVE_WORD_SUM_FN_LO
    jsr call_context_function
    rts
.else
    jsr parse_positive_word_term_local_or_fail
    bcc :+
    sec
    rts
:   lda positive_word_value_lo
    sta positive_word_sum_lo
    lda positive_word_value_hi
    sta positive_word_sum_hi
parse_positive_word_sum_local_loop:
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    beq parse_positive_word_sum_local_done
    cmp #10
    beq parse_positive_word_sum_local_done
    cmp #13
    beq parse_positive_word_sum_local_done
    cmp #','
    beq parse_positive_word_sum_local_done
    cmp #')'
    beq parse_positive_word_sum_local_done
    cmp #']'
    beq parse_positive_word_sum_local_done
    cmp #'='
    beq parse_positive_word_sum_local_done
    cmp #'<'
    beq parse_positive_word_sum_local_done
    cmp #'>'
    beq parse_positive_word_sum_local_done
    cmp #'+'
    beq parse_positive_word_sum_local_add
    cmp #'-'
    beq parse_positive_word_sum_local_sub
    sec
    rts

parse_positive_word_sum_local_add:
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs parse_positive_word_sum_local_fail
    jsr parse_positive_word_term_local_or_fail
    bcs parse_positive_word_sum_local_fail
    clc
    lda positive_word_sum_lo
    adc positive_word_value_lo
    sta positive_word_sum_lo
    lda positive_word_sum_hi
    adc positive_word_value_hi
    sta positive_word_sum_hi
    bcc parse_positive_word_sum_local_loop
    sec
    rts

parse_positive_word_sum_local_sub:
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs parse_positive_word_sum_local_fail
    jsr parse_positive_word_term_local_or_fail
    bcs parse_positive_word_sum_local_fail
    lda positive_word_sum_lo
    sec
    sbc positive_word_value_lo
    sta positive_word_sum_lo
    lda positive_word_sum_hi
    sbc positive_word_value_hi
    sta positive_word_sum_hi
    bcs parse_positive_word_sum_local_loop
parse_positive_word_sum_local_fail:
    sec
    rts

parse_positive_word_sum_local_done:
    lda positive_word_sum_lo
    sta positive_word_value_lo
    lda positive_word_sum_hi
    sta positive_word_value_hi
    jmp store_positive_word_value_local_to_expr_value
.endif
parse_positive_word_term_local_or_fail:
    jsr parse_positive_word_factor_local_or_fail
    bcc :+
    jmp parse_positive_word_term_local_fail
:   lda positive_word_value_lo
    sta positive_word_term_lo
    lda positive_word_value_hi
    sta positive_word_term_hi
parse_positive_word_term_local_loop:
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'*'
    beq parse_positive_word_term_local_mul
    cmp #'/'
    beq parse_positive_word_term_local_div
    lda positive_word_term_lo
    sta positive_word_value_lo
    lda positive_word_term_hi
    sta positive_word_value_hi
    clc
    rts

parse_positive_word_term_local_mul:
    lda positive_word_term_lo
    sta positive_word_term_saved_lo
    lda positive_word_term_hi
    sta positive_word_term_saved_hi
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp parse_positive_word_term_local_fail
:   jsr parse_positive_word_factor_local_or_fail
    bcc :+
    jmp parse_positive_word_term_local_fail
:   lda positive_word_value_lo
    sta positive_word_temp_lo
    lda positive_word_value_hi
    sta positive_word_temp_hi
    lda #$00
    sta positive_word_term_lo
    sta positive_word_term_hi
parse_positive_word_term_local_mul_loop:
    lda positive_word_temp_lo
    ora positive_word_temp_hi
    beq parse_positive_word_term_local_loop
    clc
    lda positive_word_term_lo
    adc positive_word_term_saved_lo
    sta positive_word_term_lo
    lda positive_word_term_hi
    adc positive_word_term_saved_hi
    sta positive_word_term_hi
    bcs parse_positive_word_term_local_fail
    lda positive_word_temp_lo
    sec
    sbc #$01
    sta positive_word_temp_lo
    lda positive_word_temp_hi
    sbc #$00
    sta positive_word_temp_hi
    jmp parse_positive_word_term_local_mul_loop

parse_positive_word_term_local_div:
    lda positive_word_term_lo
    sta positive_word_term_saved_lo
    lda positive_word_term_hi
    sta positive_word_term_saved_hi
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs parse_positive_word_term_local_fail
    jsr parse_positive_word_factor_local_or_fail
    bcs parse_positive_word_term_local_fail
    lda positive_word_value_lo
    ora positive_word_value_hi
    bne :+
    sec
    rts
:   lda positive_word_value_lo
    sta positive_word_temp_lo
    lda positive_word_value_hi
    sta positive_word_temp_hi
    lda #$00
    sta positive_word_term_lo
    sta positive_word_term_hi
parse_positive_word_term_local_div_loop:
    lda positive_word_term_saved_hi
    cmp positive_word_temp_hi
    bcc parse_positive_word_term_local_div_done
    bne :+
    lda positive_word_term_saved_lo
    cmp positive_word_temp_lo
    bcc parse_positive_word_term_local_div_done
:   lda positive_word_term_saved_lo
    sec
    sbc positive_word_temp_lo
    sta positive_word_term_saved_lo
    lda positive_word_term_saved_hi
    sbc positive_word_temp_hi
    sta positive_word_term_saved_hi
    inc positive_word_term_lo
    bne parse_positive_word_term_local_div_loop
    inc positive_word_term_hi
    bne parse_positive_word_term_local_div_loop
parse_positive_word_term_local_div_done:
    jmp parse_positive_word_term_local_loop
parse_positive_word_term_local_fail:
    sec
    rts

parse_positive_word_factor_local_or_fail:
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'('
    beq parse_positive_word_factor_local_group
    jmp parse_positive_word_decimal_local_or_fail

parse_positive_word_factor_local_group:
    lda positive_word_sum_lo
    sta positive_word_outer_sum_lo
    lda positive_word_sum_hi
    sta positive_word_outer_sum_hi
    lda positive_word_term_saved_lo
    sta positive_word_outer_term_saved_lo
    lda positive_word_term_saved_hi
    sta positive_word_outer_term_saved_hi
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs parse_positive_word_term_local_fail
    jsr parse_positive_word_sum_local_or_fail
    bcs parse_positive_word_term_local_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    beq :+
    jmp parse_positive_word_decimal_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    lda positive_word_outer_sum_lo
    sta positive_word_sum_lo
    lda positive_word_outer_sum_hi
    sta positive_word_sum_hi
    lda positive_word_outer_term_saved_lo
    sta positive_word_term_saved_lo
    lda positive_word_outer_term_saved_hi
    sta positive_word_term_saved_hi
    clc
    rts

parse_optional_grouped_positive_word_sum_local_or_fail:
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'('
    beq :+
    jmp parse_positive_word_sum_local_or_fail
:   
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs parse_optional_grouped_positive_word_sum_local_or_fail_fail
    jsr parse_positive_word_sum_local_or_fail
    bcs parse_optional_grouped_positive_word_sum_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    bne parse_optional_grouped_positive_word_sum_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs parse_optional_grouped_positive_word_sum_local_or_fail_fail
    clc
    rts
parse_optional_grouped_positive_word_sum_local_or_fail_fail:
    sec
    rts

parse_positive_word_decimal_local_or_fail:
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #$00
    sta positive_word_value_lo
    sta positive_word_value_hi
    sta positive_word_digit_count
parse_positive_word_decimal_local_loop:
    jsr read_scan_char_at_y
    cmp #'0'
    bcc parse_positive_word_decimal_local_done_check
    cmp #'9'+1
    bcs parse_positive_word_decimal_local_done_check
    sec
    sbc #'0'
    sta stored_byte_local
    lda positive_word_value_lo
    sta positive_word_saved_lo
    lda positive_word_value_hi
    sta positive_word_saved_hi
    lda #$00
    sta positive_word_term_lo
    sta positive_word_term_hi
    ldx #10
parse_positive_word_decimal_local_mul10_loop:
    clc
    lda positive_word_term_lo
    adc positive_word_saved_lo
    sta positive_word_term_lo
    lda positive_word_term_hi
    adc positive_word_saved_hi
    sta positive_word_term_hi
    bcs parse_positive_word_decimal_local_or_fail_fail
    dex
    bne parse_positive_word_decimal_local_mul10_loop
    clc
    lda positive_word_term_lo
    adc stored_byte_local
    sta positive_word_value_lo
    lda positive_word_term_hi
    adc #$00
    sta positive_word_value_hi
    bcs parse_positive_word_decimal_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    inc positive_word_digit_count
    bne parse_positive_word_decimal_local_loop
parse_positive_word_decimal_local_done_check:
    lda positive_word_digit_count
    beq parse_positive_word_decimal_local_or_fail_fail
    clc
    rts
parse_positive_word_decimal_local_or_fail_fail:
    sec
    rts

emit_runtime_real_push_literal_local_from_indexes:
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_rhs_index_local
    lda #'p'
    jsr call_loaded_target_with_a
    ldx real_lhs_index_local
    lda #'p'
    jsr call_loaded_target_with_a
    clc
    rts

emit_runtime_real_wide_bridge_value_local_from_indexes:
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_rhs_index_local
    lda #'p'
    jsr call_loaded_target_with_a
    ldx real_lhs_index_local
    lda #'u'
    jsr call_loaded_target_with_a
    clc
    rts

emit_runtime_real_explicit_bridge_value_local_or_fail:
    lda #ACTC_OVERLAY_CTX_COPY_SYMBOL_FROM_SCAN_Y_FN_LO
    jsr call_context_function
    bcs emit_runtime_real_explicit_bridge_value_local_or_fail_fail
    sty symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_FIND_VAR_INDEX_FN_LO
    jsr call_context_function
    bcs emit_runtime_real_explicit_bridge_value_local_or_fail_fail
    stx real_lhs_index_local
    lda #ACTC_OVERLAY_CTX_REQUIRE_REAL_BRIDGE_WORD_VAR_FN_LO
    jsr call_indexed_context_function
    bcs emit_runtime_real_explicit_bridge_value_local_or_fail_fail
    ldy symbol_end_y_local
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    bne emit_runtime_real_explicit_bridge_value_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs emit_runtime_real_explicit_bridge_value_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_lhs_index_local
    lda #'L'
    jsr call_loaded_target_with_a
    ldx real_lhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_REAL_BRIDGE_EXTERNAL_FN_LO
    jsr call_indexed_context_function_keep_x
    bcs emit_runtime_real_explicit_bridge_value_local_or_fail_fail
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_rhs_index_local
    lda #'u'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    clc
    rts
emit_runtime_real_explicit_bridge_value_local_or_fail_fail:
    sec
    rts

emit_runtime_real_explicit_value_after_open_local_or_fail:
    sty symbol_start_y_local
    lda #ACTC_OVERLAY_CTX_SAVE_SOURCE_MARK_FN_LO
    jsr call_context_function
    jsr emit_runtime_real_explicit_bridge_value_local_or_fail
    bcc :+
    lda #ACTC_OVERLAY_CTX_RESTORE_SOURCE_MARK_FN_LO
    jsr call_context_function
    ldy symbol_start_y_local
    jsr parse_positive_word_sum_local_or_fail
    bcc :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_wide
:   lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    beq :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_wide
:   lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_wide
:   lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$01
    lda (ACTC_OVERLAY_WORK_ZP),y
    bne emit_runtime_real_explicit_value_after_open_local_or_fail_wide
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    bne emit_runtime_real_explicit_value_after_open_local_or_fail_nonzero
    lda #ACTC_OVERLAY_CTX_STORE_ZERO_INT_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_fail
:   stx real_rhs_index_local
    stx real_lhs_index_local
    jmp emit_runtime_real_push_literal_local_from_indexes
emit_runtime_real_explicit_value_after_open_local_or_fail_nonzero:
    lda #ACTC_OVERLAY_CTX_STORE_ZERO_INT_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_fail
:   stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta stored_byte_local
    ldy #$00
    lda #ACTC_OVERLAY_CTX_STORE_WORD_LITERAL_FN_LO
    jsr load_context_function_ptr
    lda stored_byte_local
    jsr call_loaded_target_with_a
    bcc :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_fail
:   stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_RT_I_TO_F_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_fail
:   stx real_lhs_index_local
    jmp emit_runtime_real_wide_bridge_value_local_from_indexes

emit_runtime_real_explicit_value_after_open_local_or_fail_wide:
    lda #ACTC_OVERLAY_CTX_RESTORE_SOURCE_MARK_FN_LO
    jsr call_context_function
    ldy symbol_start_y_local
    jsr parse_positive_word_sum_local_or_fail
    bcs emit_runtime_real_explicit_value_after_open_local_or_fail_signed
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    beq :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_signed
:   lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_signed
:   lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta stored_byte_local
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    ora stored_byte_local
    bne :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_zero
:   lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    tax
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    txa
    sta stored_byte_local
    lda #ACTC_OVERLAY_CTX_STORE_WORD_LITERAL_FN_LO
    jsr load_context_function_ptr
    lda stored_byte_local
    jsr call_loaded_target_with_a
    bcc :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_fail
:   stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_RT_I_TO_F_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_fail
:   stx real_lhs_index_local
    jmp emit_runtime_real_wide_bridge_value_local_from_indexes

emit_runtime_real_explicit_value_after_open_local_or_fail_signed:
    lda #ACTC_OVERLAY_CTX_RESTORE_SOURCE_MARK_FN_LO
    jsr call_context_function
    ldy symbol_start_y_local
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'0'
    beq :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_fail
:   lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_runtime_real_explicit_value_after_open_local_or_fail_fail
:   lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'-'
    bne emit_runtime_real_explicit_value_after_open_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs emit_runtime_real_explicit_value_after_open_local_or_fail_fail
    jsr parse_optional_grouped_positive_word_sum_local_or_fail
    bcs emit_runtime_real_explicit_value_after_open_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    bne emit_runtime_real_explicit_value_after_open_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs emit_runtime_real_explicit_value_after_open_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta stored_byte_local
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    ora stored_byte_local
    bne :+
emit_runtime_real_explicit_value_after_open_local_or_fail_zero:
    lda #ACTC_OVERLAY_CTX_STORE_ZERO_INT_LITERAL_FN_LO
    jsr call_context_function
    bcs emit_runtime_real_explicit_value_after_open_local_or_fail_fail
    stx real_rhs_index_local
    stx real_lhs_index_local
    jmp emit_runtime_real_push_literal_local_from_indexes
:   lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda #$00
    sec
    sbc (ACTC_OVERLAY_WORK_ZP),y
    tax
    iny
    lda #$00
    sbc (ACTC_OVERLAY_WORK_ZP),y
    tay
    txa
    sta stored_byte_local
    lda #ACTC_OVERLAY_CTX_STORE_WORD_LITERAL_FN_LO
    jsr load_context_function_ptr
    lda stored_byte_local
    jsr call_loaded_target_with_a
    bcs emit_runtime_real_explicit_value_after_open_local_or_fail_fail
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_RT_S_TO_F_FN_LO
    jsr call_context_function
    bcs emit_runtime_real_explicit_value_after_open_local_or_fail_fail
    stx real_lhs_index_local
    jmp emit_runtime_real_wide_bridge_value_local_from_indexes

emit_runtime_real_explicit_value_after_open_local_or_fail_fail:
    sec
    rts

emit_runtime_real_value_local_or_fail:
    lda #ACTC_OVERLAY_CTX_EMIT_RUNTIME_REAL_VALUE_FN_LO
    jsr call_context_function
    rts

store_runtime_expr_with_a_local_or_fail:
    sta runtime_print_op_local
    ldy #$00
    lda #ACTC_OVERLAY_CTX_EMIT_RUNTIME_VALUE_FN_LO
    jsr call_context_function
    bcs store_runtime_expr_with_a_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    bne store_runtime_expr_with_a_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_NO_ARG_FN_LO
    jsr load_context_function_ptr
    lda runtime_print_op_local
    jsr call_loaded_target_with_a
    clc
    rts
store_runtime_expr_with_a_local_or_fail_fail:
    sec
    rts

store_runtime_real_print_with_newline_flag_local_or_fail:
    sta runtime_print_op_local
    ldy #$00
    jsr emit_runtime_real_value_local_or_fail
    bcs store_runtime_real_print_with_newline_flag_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #')'
    bne store_runtime_real_print_with_newline_flag_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs store_runtime_real_print_with_newline_flag_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcs store_runtime_real_print_with_newline_flag_local_or_fail_fail
    lda runtime_print_op_local
    beq store_runtime_real_print_with_newline_flag_local_zero
    lda #ACTC_OVERLAY_CTX_STORE_WORD_LITERAL_FN_LO
    jsr load_context_function_ptr
    lda #$01
    ldy #$00
    jsr call_loaded_target_with_a
    bcs store_runtime_real_print_with_newline_flag_local_or_fail_fail
    bcc store_runtime_real_print_with_newline_flag_local_have_flag
store_runtime_real_print_with_newline_flag_local_zero:
    lda #ACTC_OVERLAY_CTX_STORE_ZERO_INT_LITERAL_FN_LO
    jsr call_context_function
    bcs store_runtime_real_print_with_newline_flag_local_or_fail_fail
store_runtime_real_print_with_newline_flag_local_have_flag:
    stx real_lhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_RT_PRINT_F_FN_LO
    jsr call_context_function
    bcs store_runtime_real_print_with_newline_flag_local_or_fail_fail
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_lhs_index_local
    lda #'p'
    jsr call_loaded_target_with_a
    ldx real_rhs_index_local
    lda #'u'
    jsr call_loaded_target_with_a
    clc
    rts
store_runtime_real_print_with_newline_flag_local_or_fail_fail:
    sec
    rts

store_runtime_condition_with_a_local_or_fail:
    sta runtime_condition_op_local
    ldy #$00
    lda #ACTC_OVERLAY_CTX_EMIT_RUNTIME_VALUE_FN_LO
    jsr call_context_function
    bcs store_runtime_condition_with_a_local_or_fail_fail
    lda runtime_condition_op_local
    cmp #'h'
    bne :+
    jsr require_then_or_line_end_local
    bcc store_runtime_condition_with_a_local_or_fail_done
    bcs store_runtime_condition_with_a_local_or_fail_fail
:   cmp #'f'
    bne :+
    jsr require_do_or_line_end_local
    bcc store_runtime_condition_with_a_local_or_fail_done
    bcs store_runtime_condition_with_a_local_or_fail_fail
:   lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcs store_runtime_condition_with_a_local_or_fail_fail
store_runtime_condition_with_a_local_or_fail_done:
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_NO_ARG_FN_LO
    jsr load_context_function_ptr
    lda runtime_condition_op_local
    jsr call_loaded_target_with_a
    clc
    rts
store_runtime_condition_with_a_local_or_fail_fail:
    sec
    rts

require_then_or_line_end_local:
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    beq require_then_or_line_end_local_ok
    cmp #10
    beq require_then_or_line_end_local_ok
    cmp #13
    beq require_then_or_line_end_local_ok
    jsr uppercase_ascii_local
    cmp #'T'
    bne require_then_or_line_end_local_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs require_then_or_line_end_local_fail
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'H'
    bne require_then_or_line_end_local_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs require_then_or_line_end_local_fail
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'E'
    bne require_then_or_line_end_local_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs require_then_or_line_end_local_fail
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'N'
    bne require_then_or_line_end_local_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs require_then_or_line_end_local_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    beq require_then_or_line_end_local_ok
    cmp #10
    beq require_then_or_line_end_local_ok
    cmp #13
    beq require_then_or_line_end_local_ok
require_then_or_line_end_local_fail:
    sec
    rts
require_then_or_line_end_local_ok:
    clc
    rts

require_do_or_line_end_local:
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    beq require_do_or_line_end_local_ok
    cmp #10
    beq require_do_or_line_end_local_ok
    cmp #13
    beq require_do_or_line_end_local_ok
    jsr uppercase_ascii_local
    cmp #'D'
    bne require_do_or_line_end_local_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs require_do_or_line_end_local_fail
    jsr read_scan_char_at_y
    jsr uppercase_ascii_local
    cmp #'O'
    bne require_do_or_line_end_local_fail
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs require_do_or_line_end_local_fail
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    beq require_do_or_line_end_local_ok
    cmp #10
    beq require_do_or_line_end_local_ok
    cmp #13
    beq require_do_or_line_end_local_ok
require_do_or_line_end_local_fail:
    sec
    rts
require_do_or_line_end_local_ok:
    clc
    rts

emit_real_small_int_assignment_local_or_fail:
    sty symbol_start_y_local
    lda #ACTC_OVERLAY_CTX_SAVE_SOURCE_MARK_FN_LO
    jsr call_context_function
    jsr parse_positive_word_sum_local_or_fail
    bcs emit_real_small_int_assignment_local_or_fail_wide
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcs emit_real_small_int_assignment_local_or_fail_wide
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$01
    lda (ACTC_OVERLAY_WORK_ZP),y
    bne emit_real_small_int_assignment_local_or_fail_wide
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    bne emit_real_small_int_assignment_local_or_fail_nonzero
    lda #ACTC_OVERLAY_CTX_STORE_ZERO_INT_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    stx real_rhs_index_local
    stx real_lhs_index_local
    jmp emit_real_literal_assignment_local_from_indexes
emit_real_small_int_assignment_local_or_fail_nonzero:
    lda #ACTC_OVERLAY_CTX_STORE_ZERO_INT_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr pack_a_as_positive_real_high_word_local
    lda #ACTC_OVERLAY_CTX_STORE_WORD_LITERAL_FN_LO
    jsr load_context_function_ptr
    lda stored_byte_local
    jsr call_loaded_target_with_a
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    stx real_lhs_index_local
    jmp emit_real_literal_assignment_local_from_indexes

emit_real_small_int_assignment_local_or_fail_wide:
    lda #ACTC_OVERLAY_CTX_RESTORE_SOURCE_MARK_FN_LO
    jsr call_context_function
    ldy symbol_start_y_local
    jsr parse_positive_word_sum_local_or_fail
    bcs emit_real_small_int_assignment_local_or_fail_signed
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcs emit_real_small_int_assignment_local_or_fail_signed
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta stored_byte_local
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    ora stored_byte_local
    bne :+
    jmp emit_real_small_int_assignment_local_or_fail_zero
:   
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    tax
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    tay
    txa
    sta stored_byte_local
    lda #ACTC_OVERLAY_CTX_STORE_WORD_LITERAL_FN_LO
    jsr load_context_function_ptr
    lda stored_byte_local
    jsr call_loaded_target_with_a
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_RT_I_TO_F_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:
    stx real_lhs_index_local
    jmp emit_real_wide_bridge_assignment_local_from_indexes

emit_real_small_int_assignment_local_or_fail_signed:
    lda #ACTC_OVERLAY_CTX_RESTORE_SOURCE_MARK_FN_LO
    jsr call_context_function
    ldy symbol_start_y_local
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'0'
    beq :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    jsr read_scan_char_at_y
    cmp #'-'
    beq :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    jsr parse_optional_grouped_positive_word_sum_local_or_fail
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_SKIP_INLINE_SPACES_FN_LO
    jsr call_context_function
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta stored_byte_local
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    ora stored_byte_local
    bne :+
    jmp emit_real_small_int_assignment_local_or_fail_zero
:   
    lda #ACTC_OVERLAY_CTX_EXPR_VALUE_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda #$00
    sec
    sbc (ACTC_OVERLAY_WORK_ZP),y
    tax
    iny
    lda #$00
    sbc (ACTC_OVERLAY_WORK_ZP),y
    tay
    txa
    sta stored_byte_local
    lda #ACTC_OVERLAY_CTX_STORE_WORD_LITERAL_FN_LO
    jsr load_context_function_ptr
    lda stored_byte_local
    jsr call_loaded_target_with_a
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_FIND_OR_STORE_RT_S_TO_F_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    stx real_lhs_index_local
    jmp emit_real_wide_bridge_assignment_local_from_indexes

emit_real_small_int_assignment_local_or_fail_zero:
    lda #ACTC_OVERLAY_CTX_STORE_ZERO_INT_LITERAL_FN_LO
    jsr call_context_function
    bcc :+
    jmp emit_real_small_int_assignment_local_or_fail_fail
:   
    stx real_rhs_index_local
    stx real_lhs_index_local
    jmp emit_real_literal_assignment_local_from_indexes

emit_real_small_int_assignment_local_or_fail_fail:
    sec
    rts

emit_real_zero_assignment_local_or_fail:
    lda #ACTC_OVERLAY_CTX_STORE_ZERO_INT_LITERAL_FN_LO
    jsr call_context_function
    bcs emit_real_zero_assignment_local_or_fail_fail
    stx real_rhs_index_local
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_Y_FN_LO
    jsr call_context_function
    bcs emit_real_zero_assignment_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_REQUIRE_LINE_END_FN_LO
    jsr call_context_function
    bcs emit_real_zero_assignment_local_or_fail_fail
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_rhs_index_local
    lda #'p'
    jsr call_loaded_target_with_a
    ldx real_rhs_index_local
    lda #'p'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'T'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'S'
    jsr call_loaded_target_with_a
    clc
    rts
emit_real_zero_assignment_local_or_fail_fail:
    sec
    rts

emit_real_literal_assignment_local_from_indexes:
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_rhs_index_local
    lda #'p'
    jsr call_loaded_target_with_a
    ldx real_lhs_index_local
    lda #'p'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'T'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'S'
    jsr call_loaded_target_with_a
    clc
    rts

emit_real_wide_bridge_assignment_local_from_indexes:
    lda #ACTC_OVERLAY_CTX_APPEND_BODY_OP_FN_LO
    jsr load_context_function_ptr
    ldx real_rhs_index_local
    lda #'p'
    jsr call_loaded_target_with_a
    ldx real_lhs_index_local
    lda #'u'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'T'
    jsr call_loaded_target_with_a
    lda #ACTC_OVERLAY_CTX_ASSIGNMENT_TARGET_INDEX_PTR_LO
    jsr load_x_from_context_byte_ptr
    lda #'S'
    jsr call_loaded_target_with_a
    clc
    rts

pack_a_as_positive_real_high_word_local:
    sta stored_byte_local
    ldx #$00
pack_a_as_positive_real_high_word_local_shift_loop:
    lda stored_byte_local
    cmp #$80
    bcs pack_a_as_positive_real_high_word_local_shift_done
    asl stored_byte_local
    inx
    bne pack_a_as_positive_real_high_word_local_shift_loop
pack_a_as_positive_real_high_word_local_shift_done:
    lda stored_byte_local
    sec
    sbc #$80
    sta stored_byte_local
    txa
    eor #$07
    clc
    adc #127
    sta saved_y_local
    and #$01
    beq :+
    lda stored_byte_local
    ora #$80
    sta stored_byte_local
:   lda saved_y_local
    lsr a
    tay
    lda stored_byte_local
    clc
    rts

load_resident_scan_ptr_to_scan_zp:
    ldy #ACTC_OVERLAY_CTX_SCAN_PTR_SLOT_PTR_LO
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_WORK_ZP
    iny
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_WORK_ZP+1
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta ACTC_OVERLAY_SCAN_ZP
    iny
    lda (ACTC_OVERLAY_WORK_ZP),y
    sta ACTC_OVERLAY_SCAN_ZP+1
    rts

pattern_matches_local_scan_ptr:
    jsr set_resident_const_ptr_from_ay
    lda #ACTC_OVERLAY_CTX_PATTERN_MATCHES_SCAN_PTR_FN_LO
    jmp call_context_function

pattern_matches_local_scan_ptr_keyword:
    jsr set_resident_const_ptr_from_ay
    lda #ACTC_OVERLAY_CTX_PATTERN_MATCHES_SCAN_PTR_KEYWORD_FN_LO
    jmp call_context_function

advance_scan_ptr_by_local_pattern:
    jsr set_resident_const_ptr_from_ay
    lda #ACTC_OVERLAY_CTX_ADVANCE_SCAN_PTR_BY_CONST_FN_LO
    jmp call_context_function

set_resident_const_ptr_from_ay:
    sta pattern_ptr_local
    sty pattern_ptr_local+1
    lda #ACTC_OVERLAY_CTX_CONST_PTR_SLOT_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda pattern_ptr_local
    sta (ACTC_OVERLAY_WORK_ZP),y
    iny
    lda pattern_ptr_local+1
    sta (ACTC_OVERLAY_WORK_ZP),y
    rts

load_byte_from_context_ptr:
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda (ACTC_OVERLAY_WORK_ZP),y
    rts

load_x_from_context_byte_ptr:
    jsr load_byte_from_context_ptr
    tax
    rts

store_a_to_context_byte_ptr:
    sta stored_byte_local
    txa
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda stored_byte_local
    sta (ACTC_OVERLAY_WORK_ZP),y
    rts

fail_with_diag:
    sta saved_a_local
    sty saved_y_local
    ldy #ACTC_OVERLAY_CTX_DIAG_PTR_LO
    lda saved_a_local
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    ldy #ACTC_OVERLAY_CTX_DIAG_PTR_HI
    lda saved_y_local
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    sec
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

call_context_function:
    jsr load_context_function_ptr
    lda #$00
    jmp call_loaded_target_with_a

call_indexed_context_function:
    stx saved_x_local
    jsr load_context_function_ptr
    lda #$00
    ldx saved_x_local
    jsr call_loaded_target_with_a
    ldx saved_x_local
    rts

call_indexed_context_function_keep_x:
    stx saved_x_local
    jsr load_context_function_ptr
    lda #$00
    ldx saved_x_local
    jmp call_loaded_target_with_a

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

pattern_proc:
    .asciiz "PROC"
pattern_if:
    .asciiz "IF"
pattern_while:
    .asciiz "WHILE"
pattern_do:
    .asciiz "DO"
pattern_od:
    .asciiz "OD"
pattern_until:
    .asciiz "UNTIL"
pattern_else:
    .asciiz "ELSE"
pattern_fi:
    .asciiz "FI"
pattern_endif:
    .asciiz "ENDIF"
pattern_return:
    .asciiz "RETURN"
pattern_print_quote:
    .byte "PRINT(",34,0
pattern_printe_quote:
    .byte "PRINTE(",34,0
pattern_printr:
    .asciiz "PRINTR("
pattern_printre:
    .asciiz "PRINTRE("
pattern_printi:
    .asciiz "PRINTI("
pattern_printie:
    .asciiz "PRINTIE("
msg_load_fail:
    .asciiz "LOAD FAIL"
msg_save_fail:
    .asciiz "SAVE FAIL"
msg_bad_proc:
    .asciiz "BAD PROC"
msg_bad_var:
    .asciiz "BAD VAR"
msg_bad_literal:
    .asciiz "BAD LITERAL"
call_target_minus_one:
    .byte $00
call_target_ptr:
    .word $0000
call_arg_a:
    .byte $00
pattern_ptr_local:
    .word $0000
symbol_start_y_local:
    .byte $00
symbol_end_y_local:
    .byte $00
saved_a_local:
    .byte $00
saved_x_local:
    .byte $00
saved_y_local:
    .byte $00
stored_byte_local:
    .byte $00
param_bind_count_local:
    .byte $00
param_bind_base_local:
    .byte $00
real_lhs_index_local:
    .byte $00
real_rhs_index_local:
    .byte $00
real_operator_local:
    .byte $00
runtime_print_op_local:
    .byte $00
runtime_condition_op_local:
    .byte $00
runtime_saved_int_count_local:
    .byte $00
runtime_saved_extern_count_local:
    .byte $00
runtime_saved_body_end_local:
    .byte $00
int_parse_matched_local:
    .byte $00
positive_word_value_lo:
    .byte $00
positive_word_value_hi:
    .byte $00
positive_word_sum_lo:
    .byte $00
positive_word_sum_hi:
    .byte $00
positive_word_outer_sum_lo:
    .byte $00
positive_word_outer_sum_hi:
    .byte $00
positive_word_saved_lo:
    .byte $00
positive_word_saved_hi:
    .byte $00
positive_word_outer_term_saved_lo:
    .byte $00
positive_word_outer_term_saved_hi:
    .byte $00
positive_word_term_saved_lo:
    .byte $00
positive_word_term_saved_hi:
    .byte $00
positive_word_term_lo:
    .byte $00
positive_word_term_hi:
    .byte $00
positive_word_temp_lo:
    .byte $00
positive_word_temp_hi:
    .byte $00
positive_word_digit_count:
    .byte $00
loop_depth_local:
    .byte $00
loop_kind_stack_local:
    .res LOOP_MAX

actc_overlay_end:
