.setcpu "6502"
CHROUT = $FFD2
CR = 13

.segment "CODE"
start:
    ; Emit the literal string one byte at a time.
    ldx #$00
print_loop:
    lda msg,x
    beq done
    jsr CHROUT
    inx
    bne print_loop

done:
    lda #CR
    jsr CHROUT
    rts

msg:
    .byte "HELLO",0
