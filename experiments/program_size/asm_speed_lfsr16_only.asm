 .setcpu "6502"
CHROUT = $FFD2

.segment "ZEROPAGE"
state_lo: .res 1
state_hi: .res 1
count_lo: .res 1
count_hi: .res 1
lsb_tmp:  .res 1

.segment "CODE"
start:
    ldx #$00
start_msg_loop:
    lda start_msg,x
    beq init
    jsr CHROUT
    inx
    bne start_msg_loop

init:
    lda #<$ACE1
    sta state_lo
    lda #>$ACE1
    sta state_hi
    lda #<60000
    sta count_lo
    lda #>60000
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
    .byte "SPEED LFSR START",13,0
done_msg:
    .byte "SPEED LFSR DONE",13,0
