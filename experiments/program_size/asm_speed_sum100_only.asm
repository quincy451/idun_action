 .setcpu "6502"
CHROUT = $FFD2

.segment "ZEROPAGE"
sum_lo: .res 1
sum_hi: .res 1
i_lo:   .res 1
i_hi:   .res 1
out_lo: .res 1
out_hi: .res 1

.segment "CODE"
start:
    ldx #$00
start_msg_loop:
    lda start_msg,x
    beq init_outer
    jsr CHROUT
    inx
    bne start_msg_loop

init_outer:
    lda #<1000
    sta out_lo
    lda #>1000
    sta out_hi

out_loop:
    lda #$00
    sta sum_lo
    sta sum_hi
    lda #$01
    sta i_lo
    lda #$00
    sta i_hi

in_loop:
    clc
    lda sum_lo
    adc i_lo
    sta sum_lo
    lda sum_hi
    adc i_hi
    sta sum_hi

    inc i_lo
    bne :+
    inc i_hi
:
    lda i_lo
    cmp #$65
    lda i_hi
    sbc #$00
    bcc in_loop

    lda out_lo
    bne dec_outer_lo
    dec out_hi
dec_outer_lo:
    dec out_lo
    lda out_lo
    ora out_hi
    bne out_loop

    ldx #$00
done_msg_loop:
    lda done_msg,x
    beq done
    jsr CHROUT
    inx
    bne done_msg_loop
done:
    rts

start_msg:
    .byte "SPEED SUM START",13,0
done_msg:
    .byte "SPEED SUM DONE",13,0
