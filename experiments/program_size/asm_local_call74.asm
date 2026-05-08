.setcpu "6502"

.segment "ZEROPAGE"
x_lo: .res 1
x_hi: .res 1

.segment "CODE"
start:
    lda #$00
    sta x_lo
    sta x_hi
    .repeat 74
    jsr t
    .endrepeat
    rts

t:
    inc x_lo
    bne :+
    inc x_hi
:
    rts
