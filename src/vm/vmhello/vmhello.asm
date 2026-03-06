; Staged vmhello proof source for ActionC64U.
; Intended flow:
;   1. clear_rstack
;   2. enter AcheronVM with jsr acheron
;   3. embedded bytecode uses calln to invoke print_native
;   4. bytecode executes native, returning to the 6502 rts path
;
; This source uses AcheronVM's ca65-style macros from generated acheron.inc.

.export start

BDOS = start - 3
BDOS_WRITE_STRING = 9

.include "acheron.inc"

.code

start:
    jsr clear_rstack
    jsr acheron
        calln print_native
        native
    rts

print_native:
    lda #<message
    ldx #>message
    ldy #BDOS_WRITE_STRING
    jsr BDOS
    rts

message:
    .byte "HELLO FROM ACHERONVM", 13, 10, 0
