.setcpu "6502"
CHROUT = $FFD2
CR = 13

.segment "ZEROPAGE"
sum_lo:      .res 1
sum_hi:      .res 1
i_lo:        .res 1
i_hi:        .res 1
work_lo:     .res 1
work_hi:     .res 1
started:     .res 1
count_chr:   .res 1

.segment "CODE"
start:
    ; sum = 0, i = 1
    lda #$00
    sta sum_lo
    sta sum_hi
    sta i_hi
    lda #$01
    sta i_lo

sum_loop:
    ; stop when i == 101
    lda i_lo
    cmp #101
    bne do_add
    lda i_hi
    beq print_sum

do_add:
    clc
    lda sum_lo
    adc i_lo
    sta sum_lo
    lda sum_hi
    adc i_hi
    sta sum_hi
    inc i_lo
    bne sum_loop
    inc i_hi
    jmp sum_loop

print_sum:
    jsr print_u16
    lda #CR
    jsr CHROUT
    rts

; Print unsigned 16-bit sum_hi:sum_lo in decimal.
print_u16:
    lda sum_lo
    sta work_lo
    lda sum_hi
    sta work_hi
    lda #$00
    sta started

    lda #<10000
    ldy #>10000
    jsr emit_decimal_digit
    lda #<1000
    ldy #>1000
    jsr emit_decimal_digit
    lda #<100
    ldy #>100
    jsr emit_decimal_digit
    lda #<10
    ldy #>10
    jsr emit_decimal_digit

    lda work_lo
    clc
    adc #'0'
    jsr CHROUT
    rts

; Input divisor in A:Y. Emits one digit if needed.
emit_decimal_digit:
    sta div_lo+1
    sty div_hi+1
    lda #'0'
    sta count_chr
sub_loop:
    sec
    lda work_lo
div_lo:
    sbc #$00
    tax
    lda work_hi
div_hi:
    sbc #$00
    bcc sub_done
    stx work_lo
    sta work_hi
    inc count_chr
    bne sub_loop
sub_done:
    lda started
    bne emit_now
    lda count_chr
    cmp #'0'
    beq no_emit
emit_now:
    lda #$01
    sta started
    lda count_chr
    jsr CHROUT
no_emit:
    rts
