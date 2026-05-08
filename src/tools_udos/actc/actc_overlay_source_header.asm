.include "actc_overlay_abi.inc"

.export actc_overlay_header
.export actc_overlay_entry
.export actc_overlay_end

.segment "CODE"

actc_overlay_header:
    .byte 'A','C','O','V'
    .byte ACTC_OVERLAY_ABI_VERSION
    .byte ACTC_OVERLAY_PASS_SOURCE_HEADER
    .word ACTC_OVERLAY_EXEC_BASE
    .word actc_overlay_entry
    .word actc_overlay_end - actc_overlay_header
    .word $0000

actc_overlay_entry:
    stx ACTC_OVERLAY_CONTEXT_ZP
    sty ACTC_OVERLAY_CONTEXT_ZP+1
    ldy #ACTC_OVERLAY_CTX_PASS_ID
    lda #ACTC_OVERLAY_PASS_SOURCE_HEADER
    sta (ACTC_OVERLAY_CONTEXT_ZP),y

    ldy #ACTC_OVERLAY_CTX_SOURCE_WINDOW_PTR_LO
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_SCAN_ZP
    ldy #ACTC_OVERLAY_CTX_SOURCE_WINDOW_PTR_HI
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_SCAN_ZP+1
    ldy #ACTC_OVERLAY_CTX_MODULE_NAME_PTR_LO
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_WORK_ZP
    ldy #ACTC_OVERLAY_CTX_MODULE_NAME_PTR_HI
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_WORK_ZP+1
    lda #$00
    sta source_mark
    sta source_mark+1

    jsr skip_source_whitespace
    jsr match_module_keyword
    bcs source_header_fail_bad_module
    jsr skip_source_spaces
    jsr compare_requested_module
    bcs source_header_fail_bad_module

    ldy #ACTC_OVERLAY_CTX_SOURCE_MARK_LO
    lda source_mark
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    ldy #ACTC_OVERLAY_CTX_SOURCE_MARK_HI
    lda source_mark+1
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    ldy #ACTC_OVERLAY_CTX_SOURCE_MARK_BANK
    lda #$00
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    ldy #ACTC_OVERLAY_CTX_STATUS
    lda #ACTC_OVERLAY_STATUS_OK
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    clc
    lda #ACTC_OVERLAY_STATUS_OK
    rts

source_header_fail_bad_module:
    ldy #ACTC_OVERLAY_CTX_DIAG_PTR_LO
    lda #<msg_bad_module
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    ldy #ACTC_OVERLAY_CTX_DIAG_PTR_HI
    lda #>msg_bad_module
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
source_header_fail:
    ldy #ACTC_OVERLAY_CTX_STATUS
    lda #ACTC_OVERLAY_STATUS_FAILED
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    sec
    lda #ACTC_OVERLAY_STATUS_FAILED
    rts

skip_source_whitespace:
    ldy #$00
skip_source_whitespace_loop:
    lda (ACTC_OVERLAY_SCAN_ZP),y
    cmp #' '
    beq skip_source_whitespace_advance
    cmp #9
    beq skip_source_whitespace_advance
    cmp #10
    beq skip_source_whitespace_advance
    cmp #13
    beq skip_source_whitespace_advance
    rts
skip_source_whitespace_advance:
    jsr advance_source_scan
    jmp skip_source_whitespace_loop

skip_source_spaces:
    ldy #$00
skip_source_spaces_loop:
    lda (ACTC_OVERLAY_SCAN_ZP),y
    cmp #' '
    beq skip_source_spaces_advance
    cmp #9
    beq skip_source_spaces_advance
    rts
skip_source_spaces_advance:
    jsr advance_source_scan
    jmp skip_source_spaces_loop

match_module_keyword:
    ldx #$00
match_module_keyword_loop:
    lda module_keyword,x
    beq match_module_keyword_ok
    sta expected_char
    ldy #$00
    lda (ACTC_OVERLAY_SCAN_ZP),y
    beq match_module_keyword_fail
    jsr uppercase_ascii
    cmp expected_char
    bne match_module_keyword_fail
    jsr advance_source_scan
    inx
    bne match_module_keyword_loop
match_module_keyword_ok:
    clc
    rts
match_module_keyword_fail:
    sec
    rts

compare_requested_module:
    ldy #$00
compare_requested_module_loop:
    lda (ACTC_OVERLAY_SCAN_ZP),y
    beq compare_requested_module_fail
    jsr uppercase_ascii
    sta expected_char
    cpy #$00
    bne compare_requested_module_body
    jsr uppercase_symbol_start_valid
    bcc compare_requested_module_char_valid
    sec
    rts
compare_requested_module_body:
    jsr uppercase_symbol_body_valid
    bcc compare_requested_module_char_valid
    jmp compare_requested_module_done
compare_requested_module_char_valid:
    lda expected_char
    sta compare_char
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr uppercase_ascii
    cmp compare_char
    bne compare_requested_module_fail
    iny
    cpy #24
    bcc compare_requested_module_loop
compare_requested_module_fail:
    sec
    rts
compare_requested_module_done:
    cpy #$00
    beq compare_requested_module_fail
    lda (ACTC_OVERLAY_WORK_ZP),y
    jsr uppercase_ascii
    cmp #$00
    bne compare_requested_module_fail
    clc
    rts

uppercase_ascii:
    cmp #'a'
    bcc uppercase_ascii_done
    cmp #'z'+1
    bcs uppercase_ascii_done
    and #$DF
uppercase_ascii_done:
    rts

uppercase_symbol_start_valid:
    cmp #'A'
    bcc uppercase_symbol_start_valid_fail
    cmp #'Z'+1
    bcs uppercase_symbol_start_valid_fail
    clc
    rts
uppercase_symbol_start_valid_fail:
    sec
    rts

uppercase_symbol_body_valid:
    cmp #'A'
    bcc uppercase_symbol_body_valid_check_digit
    cmp #'Z'+1
    bcc uppercase_symbol_body_valid_ok
uppercase_symbol_body_valid_check_digit:
    cmp #'0'
    bcc uppercase_symbol_body_valid_check_underscore
    cmp #'9'+1
    bcc uppercase_symbol_body_valid_ok
uppercase_symbol_body_valid_check_underscore:
    cmp #'_'
    beq uppercase_symbol_body_valid_ok
    sec
    rts
uppercase_symbol_body_valid_ok:
    clc
    rts

advance_source_scan:
    inc ACTC_OVERLAY_SCAN_ZP
    bne :+
    inc ACTC_OVERLAY_SCAN_ZP+1
:
    inc source_mark
    bne :+
    inc source_mark+1
:
    rts

module_keyword:
    .asciiz "MODULE"
msg_bad_module:
    .asciiz "BAD MODULE"
source_mark:
    .word $0000
expected_char:
    .byte $00
compare_char:
    .byte $00

actc_overlay_end:
