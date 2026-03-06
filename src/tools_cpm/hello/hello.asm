start:
    lda #<message
    ldx #>message
    ldy #9
    jsr start - 3
    rts

message:
    .byte "HELLO FROM ACTIONC64U", 13, 10, 0
