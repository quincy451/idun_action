 .setcpu "6502"

.segment "ZEROPAGE"
sum_lo: .res 1
sum_hi: .res 1
i_lo:   .res 1
i_hi:   .res 1

.segment "CODE"
start:
    lda #$00
    sta sum_lo
    sta sum_hi
    lda #$01
    sta i_lo
    lda #$00
    sta i_hi

loop:
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
    bcc loop

    rts
