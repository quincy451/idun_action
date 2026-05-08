.include "avmrun_overlay_abi.inc"
.include "avmrun_overlay_resident.inc"

.export avmrun_overlay_header
.export avmrun_overlay_entry
.export avmrun_overlay_end

.segment "CODE"

avmrun_overlay_header:
    .byte 'A','V','O','V'
    .byte AVMRUN_OVERLAY_ABI_VERSION
    .word AVMRUN_OVERLAY_EXEC_BASE
    .word avmrun_overlay_entry
    .word avmrun_overlay_end - avmrun_overlay_header
    .word $0000

word_tmp = AVMRUN_RES_word_tmp
svc_retptr = AVMRUN_RES_svc_retptr
real_print_low = AVMRUN_RES_real_print_low
real_print_high = AVMRUN_RES_real_print_high
real_print_int = AVMRUN_RES_real_print_int
real_print_rem = AVMRUN_RES_real_print_rem
real_print_mask = AVMRUN_RES_real_print_mask
real_print_work = AVMRUN_RES_real_print_work
real_print_flag = AVMRUN_RES_real_print_flag
real_print_shift = AVMRUN_RES_real_print_shift
real_print_num = AVMRUN_RES_real_print_num
real_print_sign = AVMRUN_RES_real_print_sign
iptr = AVMRUN_RES_iptr
iptr_offset = AVMRUN_RES_iptr_offset
pptr = AVMRUN_RES_pptr
rptr = AVMRUN_RES_rptr
runtime_safe_console_write = AVMRUN_RES_runtime_safe_console_write
runtime_safe_console_newline = AVMRUN_RES_runtime_safe_console_newline
avmrun_overlay_requested_cmd = AVMRUN_RES_avmrun_overlay_requested_cmd

avmrun_overlay_entry:
    lda avmrun_overlay_requested_cmd
    cmp #AVMRUN_OVERLAY_CMD_PRINT_STRING
    beq overlay_print_string
    cmp #AVMRUN_OVERLAY_CMD_PRINT_STRING_NL
    beq overlay_print_string_nl
    cmp #AVMRUN_OVERLAY_CMD_PRINT_U16
    beq overlay_print_u16
    cmp #AVMRUN_OVERLAY_CMD_PRINT_U16_NL
    beq overlay_print_u16_nl
    cmp #AVMRUN_OVERLAY_CMD_PRINT_REAL
    beq overlay_print_real
    rts

overlay_print_string:
    jsr save_vm_state
    jsr runtime_safe_console_write
    jmp restore_vm_state

overlay_print_string_nl:
    jsr save_vm_state
    jsr runtime_safe_console_write
    jsr runtime_safe_console_newline
    jmp restore_vm_state

overlay_print_u16:
    jsr save_vm_state
    jsr print_u16_word_tmp
    jmp restore_vm_state

overlay_print_u16_nl:
    jsr save_vm_state
    jsr print_u16_word_tmp
    jsr runtime_safe_console_newline
    jmp restore_vm_state

overlay_print_real:
    jsr save_vm_state
    jsr native_printreal_common
    jmp restore_vm_state

native_printreal_common:
    lda real_print_high
    ora real_print_high+1
    bne native_printreal_common_decode
    lda #'0'
    jsr print_char_a
    jmp native_printreal_common_newline
native_printreal_common_decode:
    lda #$00
    sta real_print_sign
    lda real_print_high+1
    and #$80
    beq :+
    inc real_print_sign
:   lda real_print_high+1
    and #$7F
    sta real_print_work+1
    lda real_print_high
    sta real_print_work
    lda real_print_work+1
    asl a
    sta real_print_shift
    lda real_print_work
    and #$80
    beq :+
    inc real_print_shift
:   lda real_print_shift
    bne :+
    lda #'0'
    jsr print_char_a
    jmp native_printreal_common_newline
:   lda real_print_shift
    cmp #90
    bcs :+
    jmp native_printreal_common_unsupported
:   cmp #143
    bcc :+
    jmp native_printreal_common_unsupported
:
    lda real_print_low
    sta real_print_num
    lda real_print_low+1
    sta real_print_num+1
    lda real_print_high
    and #$7F
    ora #$80
    sta real_print_num+2
    lda #$00
    sta real_print_num+3
    sta real_print_num+4
    sta real_print_num+5
    sta real_print_num+6
    sta real_print_num+7
    lda #150
    sec
    sbc real_print_shift
    sta real_print_shift
    jsr native_printreal_build_mask
    jsr native_printreal_copy_num_to_work
    ldy real_print_shift
native_printreal_common_right_loop:
    cpy #$00
    beq native_printreal_common_right_done
    lsr real_print_work+7
    ror real_print_work+6
    ror real_print_work+5
    ror real_print_work+4
    ror real_print_work+3
    ror real_print_work+2
    ror real_print_work+1
    ror real_print_work
    dey
    bne native_printreal_common_right_loop
native_printreal_common_right_done:
    lda real_print_work
    sta real_print_int
    lda real_print_work+1
    sta real_print_int+1
    lda real_print_num
    and real_print_mask
    sta real_print_rem
    lda real_print_num+1
    and real_print_mask+1
    sta real_print_rem+1
    lda real_print_num+2
    and real_print_mask+2
    sta real_print_rem+2
    lda real_print_num+3
    and real_print_mask+3
    sta real_print_rem+3
    lda real_print_num+4
    and real_print_mask+4
    sta real_print_rem+4
    lda real_print_num+5
    and real_print_mask+5
    sta real_print_rem+5
    lda real_print_num+6
    and real_print_mask+6
    sta real_print_rem+6
    lda real_print_num+7
    and real_print_mask+7
    sta real_print_rem+7

native_printreal_common_emit:
    lda real_print_sign
    beq native_printreal_common_emit_int
    lda real_print_int
    ora real_print_int+1
    ora real_print_rem
    ora real_print_rem+1
    ora real_print_rem+2
    ora real_print_rem+3
    ora real_print_rem+4
    ora real_print_rem+5
    ora real_print_rem+6
    ora real_print_rem+7
    beq native_printreal_common_emit_int
    lda #'-'
    jsr print_char_a
native_printreal_common_emit_int:
    lda real_print_int
    sta word_tmp
    lda real_print_int+1
    sta word_tmp+1
    jsr print_u16_word_tmp
    lda real_print_rem
    ora real_print_rem+1
    ora real_print_rem+2
    ora real_print_rem+3
    ora real_print_rem+4
    ora real_print_rem+5
    ora real_print_rem+6
    ora real_print_rem+7
    bne :+
    jmp native_printreal_common_newline
:
    lda #'.'
    jsr print_char_a
native_printreal_common_fraction_loop:
    lda #$00
    sta real_print_work
    sta real_print_work+1
    sta real_print_work+2
    sta real_print_work+3
    sta real_print_work+4
    sta real_print_work+5
    sta real_print_work+6
    sta real_print_work+7
    ldy #10
native_printreal_common_mul10_loop:
    clc
    lda real_print_work
    adc real_print_rem
    sta real_print_work
    lda real_print_work+1
    adc real_print_rem+1
    sta real_print_work+1
    lda real_print_work+2
    adc real_print_rem+2
    sta real_print_work+2
    lda real_print_work+3
    adc real_print_rem+3
    sta real_print_work+3
    lda real_print_work+4
    adc real_print_rem+4
    sta real_print_work+4
    lda real_print_work+5
    adc real_print_rem+5
    sta real_print_work+5
    lda real_print_work+6
    adc real_print_rem+6
    sta real_print_work+6
    lda real_print_work+7
    adc real_print_rem+7
    sta real_print_work+7
    dey
    bne native_printreal_common_mul10_loop
    lda real_print_work
    sta real_print_num
    lda real_print_work+1
    sta real_print_num+1
    lda real_print_work+2
    sta real_print_num+2
    lda real_print_work+3
    sta real_print_num+3
    lda real_print_work+4
    sta real_print_num+4
    lda real_print_work+5
    sta real_print_num+5
    lda real_print_work+6
    sta real_print_num+6
    lda real_print_work+7
    sta real_print_num+7
    ldy real_print_shift
native_printreal_common_digit_shift_loop:
    cpy #$00
    beq native_printreal_common_digit_shift_done
    lsr real_print_num+7
    ror real_print_num+6
    ror real_print_num+5
    ror real_print_num+4
    ror real_print_num+3
    ror real_print_num+2
    ror real_print_num+1
    ror real_print_num
    dey
    bne native_printreal_common_digit_shift_loop
native_printreal_common_digit_shift_done:
    lda real_print_num
    clc
    adc #'0'
    jsr print_char_a
    lda real_print_work
    and real_print_mask
    sta real_print_rem
    lda real_print_work+1
    and real_print_mask+1
    sta real_print_rem+1
    lda real_print_work+2
    and real_print_mask+2
    sta real_print_rem+2
    lda real_print_work+3
    and real_print_mask+3
    sta real_print_rem+3
    lda real_print_work+4
    and real_print_mask+4
    sta real_print_rem+4
    lda real_print_work+5
    and real_print_mask+5
    sta real_print_rem+5
    lda real_print_work+6
    and real_print_mask+6
    sta real_print_rem+6
    lda real_print_work+7
    and real_print_mask+7
    sta real_print_rem+7
    lda real_print_rem
    ora real_print_rem+1
    ora real_print_rem+2
    ora real_print_rem+3
    ora real_print_rem+4
    ora real_print_rem+5
    ora real_print_rem+6
    ora real_print_rem+7
    beq :+
    jmp native_printreal_common_fraction_loop
:
native_printreal_common_newline:
    lda real_print_flag
    beq native_printreal_common_done
    jsr runtime_safe_console_newline
native_printreal_common_done:
    rts

native_printreal_common_unsupported:
    lda #'?'
    jsr print_char_a
    jmp native_printreal_common_newline

native_printreal_copy_num_to_work:
    lda real_print_num
    sta real_print_work
    lda real_print_num+1
    sta real_print_work+1
    lda real_print_num+2
    sta real_print_work+2
    lda real_print_num+3
    sta real_print_work+3
    lda real_print_num+4
    sta real_print_work+4
    lda real_print_num+5
    sta real_print_work+5
    lda real_print_num+6
    sta real_print_work+6
    lda real_print_num+7
    sta real_print_work+7
    rts

native_printreal_build_mask:
    lda #$01
    sta real_print_mask
    lda #$00
    sta real_print_mask+1
    sta real_print_mask+2
    sta real_print_mask+3
    sta real_print_mask+4
    sta real_print_mask+5
    sta real_print_mask+6
    sta real_print_mask+7
    ldy real_print_shift
native_printreal_build_mask_loop:
    cpy #$00
    beq native_printreal_build_mask_done
    asl real_print_mask
    rol real_print_mask+1
    rol real_print_mask+2
    rol real_print_mask+3
    rol real_print_mask+4
    rol real_print_mask+5
    rol real_print_mask+6
    rol real_print_mask+7
    dey
    bne native_printreal_build_mask_loop
native_printreal_build_mask_done:
    sec
    lda real_print_mask
    sbc #$01
    sta real_print_mask
    lda real_print_mask+1
    sbc #$00
    sta real_print_mask+1
    lda real_print_mask+2
    sbc #$00
    sta real_print_mask+2
    lda real_print_mask+3
    sbc #$00
    sta real_print_mask+3
    lda real_print_mask+4
    sbc #$00
    sta real_print_mask+4
    lda real_print_mask+5
    sbc #$00
    sta real_print_mask+5
    lda real_print_mask+6
    sbc #$00
    sta real_print_mask+6
    lda real_print_mask+7
    sbc #$00
    sta real_print_mask+7
    rts

print_u16_word_tmp:
    lda #$00
    sta overlay_digit_flag
    ldx #$00
print_u16_word_tmp_loop:
    cpx #$04
    beq print_u16_word_tmp_ones
    jsr print_digit_divisor_x
    inx
    bne print_u16_word_tmp_loop
print_u16_word_tmp_ones:
    lda word_tmp
    clc
    adc #'0'
    jmp print_char_a

print_digit_divisor_x:
    lda #$00
    sta overlay_hex_tmp
print_digit_divisor_x_sub_loop:
    lda word_tmp+1
    cmp decimal_divisors_hi,x
    bcc print_digit_divisor_x_done
    bne :+
    lda word_tmp
    cmp decimal_divisors_lo,x
    bcc print_digit_divisor_x_done
:   sec
    lda word_tmp
    sbc decimal_divisors_lo,x
    sta word_tmp
    lda word_tmp+1
    sbc decimal_divisors_hi,x
    sta word_tmp+1
    inc overlay_hex_tmp
    bne print_digit_divisor_x_sub_loop
print_digit_divisor_x_done:
    lda overlay_digit_flag
    bne print_digit_divisor_x_emit
    lda overlay_hex_tmp
    beq print_digit_divisor_x_skip
print_digit_divisor_x_emit:
    lda overlay_hex_tmp
    clc
    adc #'0'
    jsr print_char_a
    lda #$01
    sta overlay_digit_flag
print_digit_divisor_x_skip:
    rts

print_char_a:
    sta overlay_char_buffer
    lda #$00
    sta overlay_char_buffer+1
    tya
    pha
    txa
    pha
    lda #<overlay_char_buffer
    sta svc_retptr
    lda #>overlay_char_buffer
    sta svc_retptr+1
    jsr runtime_safe_console_write
    pla
    tax
    pla
    tay
    rts

save_vm_state:
    lda iptr
    sta overlay_saved_iptr
    lda iptr+1
    sta overlay_saved_iptr+1
    lda iptr_offset
    sta overlay_saved_iptr_offset
    lda pptr
    sta overlay_saved_pptr
    lda rptr
    sta overlay_saved_rptr
    rts

restore_vm_state:
    lda overlay_saved_iptr
    sta iptr
    lda overlay_saved_iptr+1
    sta iptr+1
    lda overlay_saved_iptr_offset
    sta iptr_offset
    lda overlay_saved_pptr
    sta pptr
    lda overlay_saved_rptr
    sta rptr
    rts

decimal_divisors_lo:
    .byte <10000,<1000,<100,<10
decimal_divisors_hi:
    .byte >10000,>1000,>100,>10

overlay_digit_flag:
    .byte $00
overlay_hex_tmp:
    .byte $00
overlay_char_buffer:
    .byte $00,$00
overlay_saved_iptr:
    .byte $00,$00
overlay_saved_iptr_offset:
    .byte $00
overlay_saved_pptr:
    .byte $00
overlay_saved_rptr:
    .byte $00

avmrun_overlay_end:
