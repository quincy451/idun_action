 .setcpu "6502"
SETLFS = $FFBA
SETNAM = $FFBD
OPEN   = $FFC0
CLOSE  = $FFC3
CHKIN  = $FFC6
CLRCHN = $FFCC
CHRIN  = $FFCF
READST = $FFB7
CHROUT = $FFD2

.segment "ZEROPAGE"
count_lo: .res 1
count_hi: .res 1
work_lo:  .res 1
work_hi:  .res 1
started:  .res 1

.segment "CODE"
start:
    lda #$00
    sta count_lo
    sta count_hi

    lda #$01
    ldx #$08
    ldy #$00
    jsr SETLFS
    lda #in_name_end-in_name
    ldx #<in_name
    ldy #>in_name
    jsr SETNAM
    jsr OPEN

    lda #$08
    jsr CHKIN

read_loop:
    jsr READST
    bne finish
    jsr CHRIN
    cmp #'0'
    bcc read_loop
    cmp #'9'+1
    bcs read_loop
    inc count_lo
    bne read_loop
    inc count_hi
    jmp read_loop

finish:
    jsr CLRCHN
    lda #$08
    jsr CLOSE

    lda count_lo
    sta work_lo
    lda count_hi
    sta work_hi
    lda #$00
    sta started

    lda work_hi
    ora work_lo
    bne print_loop
    lda #'0'
    jsr CHROUT
    rts

print_loop:
    ldx #$00
find_digit:
    lda work_hi
    cmp table_hi,x
    bcc next_digit
    bne sub_digit
    lda work_lo
    cmp table_lo,x
    bcc next_digit
sub_digit:
    lda work_lo
    sec
    sbc table_lo,x
    sta work_lo
    lda work_hi
    sbc table_hi,x
    sta work_hi
    inx
    inc digit_count
    jmp find_digit
next_digit:
    lda digit_count
    beq maybe_next_place
    clc
    adc #'0'
    jsr CHROUT
    lda #$01
    sta started
maybe_next_place:
    lda #$00
    sta digit_count
    cpx #$05
    bne advance_place
    lda started
    bne done
    lda #'0'
    jsr CHROUT
done:
    rts
advance_place:
    txa
    clc
    adc #$01
    tax
    jmp find_digit

.segment "BSS"
digit_count: .res 1

.segment "RODATA"
table_lo: .byte <10000,<1000,<100,<10,<1
table_hi: .byte >10000,>1000,>100,>10,>1
in_name: .asciiz "DIGITS.TXT,S,R"
in_name_end:
