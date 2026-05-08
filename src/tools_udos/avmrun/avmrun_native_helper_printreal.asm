.include "avmrun_native_helper_abi.inc"
.include "avmrun_overlay_resident.inc"

.export avmrun_native_helper_printreal_header
.export avmrun_native_helper_printreal_entry
.export avmrun_native_helper_printreal_end

.segment "CODE"

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
restore_native_helper_irq_state = AVMRUN_RES_restore_native_helper_irq_state
native_helper_printreal_char_buffer = AVMRUN_RES_native_helper_printreal_char_buffer
native_helper_printreal_saved_iptr = AVMRUN_RES_native_helper_printreal_saved_iptr
native_helper_printreal_saved_iptr_offset = AVMRUN_RES_native_helper_printreal_saved_iptr_offset
native_helper_printreal_saved_pptr = AVMRUN_RES_native_helper_printreal_saved_pptr
native_helper_printreal_saved_rptr = AVMRUN_RES_native_helper_printreal_saved_rptr
TOOL_DEBUG12 = $03DC
TOOL_DEBUG13 = $03DD
TOOL_DEBUG14 = $03DE
TOOL_DEBUG0 = $03D0
TOOL_DEBUG1 = $03D1
TOOL_DEBUG2 = $03D2
TOOL_DEBUG3 = $03D3
TOOL_DEBUG4 = $03D4
TOOL_DEBUG5 = $03D5
TOOL_DEBUG6 = $03D6
TOOL_DEBUG7 = $03D7
TOOL_DEBUG10 = $03DA
TOOL_DEBUG11 = $03DB
TOOL_DEBUG15 = $03DF

avmrun_native_helper_printreal_header:
    .byte AVMRUN_NATIVE_HELPER_MAGIC_0
    .byte AVMRUN_NATIVE_HELPER_MAGIC_1
    .byte AVMRUN_NATIVE_HELPER_MAGIC_2
    .byte AVMRUN_NATIVE_HELPER_MAGIC_3
    .byte AVMRUN_NATIVE_HELPER_ABI_VERSION
    .byte AVMRUN_NATIVE_HELPER_KIND_PRINTREAL
    .word avmrun_native_helper_printreal_entry_table - avmrun_native_helper_printreal_header
    .word avmrun_native_helper_printreal_end - avmrun_native_helper_printreal_header
    .byte 1
    .byte 0

avmrun_native_helper_printreal_entry_table:
    .byte AVMRUN_NATIVE_HELPER_ENTRY_PRINTREAL_MAIN
    .word avmrun_native_helper_printreal_entry - avmrun_native_helper_printreal_header

avmrun_native_helper_printreal_entry:
    lda #'E'
    sta TOOL_DEBUG12
    lda 0,x
    sta real_print_flag
    lda 2,x
    sta real_print_high
    lda 3,x
    sta real_print_high+1
    lda 4,x
    sta real_print_low
    lda 5,x
    sta real_print_low+1
    jsr save_vm_state
    tsx
    stx TOOL_DEBUG10
    lda #'S'
    sta TOOL_DEBUG13
    jsr native_printreal_common
    lda #'R'
    sta TOOL_DEBUG14
    jsr restore_vm_state
    lda iptr
    sta TOOL_DEBUG0
    lda iptr+1
    sta TOOL_DEBUG1
    lda iptr_offset
    sta TOOL_DEBUG2
    ldy iptr_offset
    lda (iptr),y
    sta TOOL_DEBUG3
    iny
    lda (iptr),y
    sta TOOL_DEBUG4
    iny
    lda (iptr),y
    sta TOOL_DEBUG5
    tsx
    stx TOOL_DEBUG11
    rts

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
    lda #'A'
    sta TOOL_DEBUG14
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
    lda #'B'
    sta TOOL_DEBUG14
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
    lda #'C'
    sta TOOL_DEBUG14
    lda real_print_work
    sta real_print_int
    lda real_print_work+1
    sta real_print_int+1
    lda real_print_int
    sta TOOL_DEBUG6
    lda real_print_int+1
    sta TOOL_DEBUG7
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
    lda #'D'
    sta TOOL_DEBUG14

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
    lda #'I'
    sta TOOL_DEBUG14
    jsr print_u16_word_tmp
    lda #'J'
    sta TOOL_DEBUG14
    lda real_print_rem
    ora real_print_rem+1
    ora real_print_rem+2
    ora real_print_rem+3
    ora real_print_rem+4
    ora real_print_rem+5
    ora real_print_rem+6
    ora real_print_rem+7
    sta TOOL_DEBUG15
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
    sta helper_digit_flag
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
    sta helper_hex_tmp
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
    inc helper_hex_tmp
    bne print_digit_divisor_x_sub_loop
print_digit_divisor_x_done:
    lda helper_digit_flag
    bne print_digit_divisor_x_emit
    lda helper_hex_tmp
    beq print_digit_divisor_x_skip
print_digit_divisor_x_emit:
    lda helper_hex_tmp
    clc
    adc #'0'
    jsr print_char_a
    lda #$01
    sta helper_digit_flag
print_digit_divisor_x_skip:
    rts

print_char_a:
    lda #'P'
    sta TOOL_DEBUG15
    sta native_helper_printreal_char_buffer
    lda #$00
    sta native_helper_printreal_char_buffer+1
    tya
    pha
    txa
    pha
    lda #<native_helper_printreal_char_buffer
    sta svc_retptr
    lda #>native_helper_printreal_char_buffer
    sta svc_retptr+1
    lda #'Q'
    sta TOOL_DEBUG15
    jsr runtime_safe_console_write
    lda #'W'
    sta TOOL_DEBUG15
    pla
    tax
    pla
    tay
    rts

save_vm_state:
    lda iptr
    sta native_helper_printreal_saved_iptr
    lda iptr+1
    sta native_helper_printreal_saved_iptr+1
    lda iptr_offset
    sta native_helper_printreal_saved_iptr_offset
    lda pptr
    sta native_helper_printreal_saved_pptr
    lda rptr
    sta native_helper_printreal_saved_rptr
    rts

restore_vm_state:
    lda native_helper_printreal_saved_iptr
    sta iptr
    lda native_helper_printreal_saved_iptr+1
    sta iptr+1
    lda native_helper_printreal_saved_iptr_offset
    sta iptr_offset
    lda native_helper_printreal_saved_pptr
    sta pptr
    lda native_helper_printreal_saved_rptr
    sta rptr
    rts

decimal_divisors_lo:
    .byte <10000,<1000,<100,<10
decimal_divisors_hi:
    .byte >10000,>1000,>100,>10

helper_digit_flag:
    .byte $00
helper_hex_tmp:
    .byte $00

avmrun_native_helper_printreal_end:
