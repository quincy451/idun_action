.setcpu "6502"
SETLFS = $FFBA
SETNAM = $FFBD
OPEN   = $FFC0
CLOSE  = $FFC3
CHKIN  = $FFC6
CHKOUT = $FFC9
CLRCHN = $FFCC
CHRIN  = $FFCF
CHROUT = $FFD2
READST = $FFB7

.segment "CODE"
start:
    ; Open source file for sequential read.
    lda #src_end - src_name
    ldx #<src_name
    ldy #>src_name
    jsr SETNAM
    lda #2
    ldx #8
    ldy #2
    jsr SETLFS
    jsr OPEN

    ; Open destination file for sequential write.
    lda #dst_end - dst_name
    ldx #<dst_name
    ldy #>dst_name
    jsr SETNAM
    lda #3
    ldx #8
    ldy #3
    jsr SETLFS
    jsr OPEN

    lda #2
    jsr CHKIN
    lda #3
    jsr CHKOUT

copy_loop:
    jsr CHRIN
    pha
    jsr READST
    and #$40
    bne done
    pla
    jsr CHROUT
    jmp copy_loop

done:
    pla
    jsr CLRCHN
    lda #2
    jsr CLOSE
    lda #3
    jsr CLOSE
    rts

src_name:
    .byte "SOURCE.TXT,S,R"
src_end:
dst_name:
    .byte "COPYOUT.TXT,S,W"
dst_end:
