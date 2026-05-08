 .setcpu "6502"

.segment "ZEROPAGE"
state_lo: .res 1
state_hi: .res 1
count_lo: .res 1
count_hi: .res 1
lsb_tmp:  .res 1

.segment "CODE"
start:
    lda #<$ACE1
    sta state_lo
    lda #>$ACE1
    sta state_hi
    lda #<256
    sta count_lo
    lda #>256
    sta count_hi

loop:
    lda state_lo
    and #$01
    sta lsb_tmp

    lsr state_hi
    ror state_lo

    lda lsb_tmp
    beq :+
    lda state_hi
    eor #$B4
    sta state_hi
:
    lda count_lo
    bne dec_lo
    dec count_hi
dec_lo:
    dec count_lo
    lda count_lo
    ora count_hi
    bne loop
    rts
