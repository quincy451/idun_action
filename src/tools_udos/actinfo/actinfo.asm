.include "udos_services.inc"

.export start

CHROUT = $FFD2
CLRCHN = $FFCC
UDOS_RETURN = $033C
ACTINFO_TRACE = $03EC

.segment "ZPTEMP": zeropage
str_ptr:
    .res 2

.code

start:
    lda #$11
    sta ACTINFO_TRACE
    jsr CLRCHN
    lda #$12
    sta ACTINFO_TRACE
    lda #<banner
    ldy #>banner
    jsr print_string
    lda #$13
    sta ACTINFO_TRACE

    lda program_cmdline_buffer
    beq no_args

    lda #<args_prefix
    ldy #>args_prefix
    jsr print_string

    lda #<program_cmdline_buffer
    ldy #>program_cmdline_buffer
    jsr print_sc0_string
    jsr newline

    lda #<done_msg
    ldy #>done_msg
    jsr print_string
    jsr newline
    lda #$14
    sta ACTINFO_TRACE
    lda #$00
    jmp UDOS_RETURN

no_args:
    lda #<noargs_msg
    ldy #>noargs_msg
    jsr print_string
    jsr newline
    lda #$15
    sta ACTINFO_TRACE
    lda #$00
    jmp UDOS_RETURN

print_string:
    sta str_ptr
    sty str_ptr+1
    ldy #$00
print_string_loop:
    lda (str_ptr),y
    beq print_string_done
    jsr CHROUT
    iny
    bne print_string_loop
print_string_done:
    rts

print_sc0_string:
    sta str_ptr
    sty str_ptr+1
    ldy #$00
print_sc0_loop:
    lda (str_ptr),y
    beq print_sc0_done
    cmp #$01
    bcc print_sc0_emit
    cmp #$1B
    bcs print_sc0_emit
    clc
    adc #'A'-1
    bne print_sc0_emit
print_sc0_emit:
    jsr CHROUT
    iny
    bne print_sc0_loop
print_sc0_done:
    rts

newline:
    lda #$0d
    jsr CHROUT
    rts

banner:
    .asciiz "ACTINFO ABI 1"
args_prefix:
    .asciiz "ARGS "
noargs_msg:
    .asciiz "NO ARGS"
done_msg:
    .asciiz "ACTINFO DONE"
