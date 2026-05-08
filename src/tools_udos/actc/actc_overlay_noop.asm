.include "actc_overlay_abi.inc"

.export actc_overlay_header
.export actc_overlay_entry
.export actc_overlay_end

.segment "CODE"

actc_overlay_header:
    .byte 'A','C','O','V'
    .byte ACTC_OVERLAY_ABI_VERSION
    .byte ACTC_OVERLAY_PASS_NOOP
    .word ACTC_OVERLAY_EXEC_BASE
    .word actc_overlay_entry
    .word actc_overlay_end - actc_overlay_header
    .word $0000

actc_overlay_entry:
    stx actc_overlay_context_lo_seen
    sty actc_overlay_context_hi_seen
    stx ACTC_OVERLAY_CONTEXT_ZP
    sty ACTC_OVERLAY_CONTEXT_ZP+1
    ldy #ACTC_OVERLAY_CTX_STATUS
    lda #ACTC_OVERLAY_STATUS_OK
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    ldy #ACTC_OVERLAY_CTX_PASS_ID
    lda #ACTC_OVERLAY_PASS_NOOP
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    lda C64_MEMCFG
    sta actc_overlay_memcfg_seen
    clc
    lda #ACTC_OVERLAY_STATUS_OK
    rts

actc_overlay_context_lo_seen:
    .byte $00
actc_overlay_context_hi_seen:
    .byte $00
actc_overlay_memcfg_seen:
    .byte $00

actc_overlay_end:
