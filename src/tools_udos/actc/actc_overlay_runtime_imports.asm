.include "actc_overlay_abi.inc"

.export actc_overlay_header
.export actc_overlay_entry
.export actc_overlay_end

IMPORT_PRINT_STR  = $01
IMPORT_PRINT_LINE = $02
IMPORT_FORMAT_INT = $04

.segment "CODE"

actc_overlay_header:
    .byte 'A','C','O','V'
    .byte ACTC_OVERLAY_ABI_VERSION
    .byte ACTC_OVERLAY_PASS_RUNTIME_IMPORTS
    .word ACTC_OVERLAY_EXEC_BASE
    .word actc_overlay_entry
    .word actc_overlay_end - actc_overlay_header
    .word $0000

actc_overlay_entry:
    stx ACTC_OVERLAY_CONTEXT_ZP
    sty ACTC_OVERLAY_CONTEXT_ZP+1
    ldy #ACTC_OVERLAY_CTX_PASS_ID
    lda #ACTC_OVERLAY_PASS_RUNTIME_IMPORTS
    sta (ACTC_OVERLAY_CONTEXT_ZP),y

    jsr detect_runtime_imports_overlay

    ldy #ACTC_OVERLAY_CTX_STATUS
    lda #ACTC_OVERLAY_STATUS_OK
    sta (ACTC_OVERLAY_CONTEXT_ZP),y
    clc
    lda #ACTC_OVERLAY_STATUS_OK
    rts

detect_runtime_imports_overlay:
    lda #$00
    sta import_flags_local

    lda #<pattern_print
    ldy #>pattern_print
    jsr find_pattern_for_overlay
    bcs :+
    lda import_flags_local
    ora #IMPORT_PRINT_STR
    sta import_flags_local
:
    lda #<pattern_printe
    ldy #>pattern_printe
    jsr find_pattern_for_overlay
    bcs :+
    lda import_flags_local
    ora #IMPORT_PRINT_LINE
    sta import_flags_local
:
    lda #<pattern_printi
    ldy #>pattern_printi
    jsr find_pattern_for_overlay
    bcs :+
    lda import_flags_local
    ora #IMPORT_FORMAT_INT|IMPORT_PRINT_STR
    sta import_flags_local
:
    lda #<pattern_printie
    ldy #>pattern_printie
    jsr find_pattern_for_overlay
    bcs :+
    lda import_flags_local
    ora #IMPORT_FORMAT_INT|IMPORT_PRINT_LINE
    sta import_flags_local
:
    lda #ACTC_OVERLAY_CTX_IMPORT_FLAGS_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda import_flags_local
    sta (ACTC_OVERLAY_WORK_ZP),y
    clc
    rts

find_pattern_for_overlay:
    sta pattern_ptr_local
    sty pattern_ptr_local+1
    lda #ACTC_OVERLAY_CTX_CONST_PTR_SLOT_PTR_LO
    jsr load_context_ptr_to_work_zp
    ldy #$00
    lda pattern_ptr_local
    sta (ACTC_OVERLAY_WORK_ZP),y
    iny
    lda pattern_ptr_local+1
    sta (ACTC_OVERLAY_WORK_ZP),y
    lda #ACTC_OVERLAY_CTX_FIND_PATTERN_FN_LO
    jsr call_context_function
    rts

load_context_ptr_to_work_zp:
    tay
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_WORK_ZP
    iny
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta ACTC_OVERLAY_WORK_ZP+1
    rts

call_context_function:
    tay
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta call_target_ptr
    iny
    lda (ACTC_OVERLAY_CONTEXT_ZP),y
    sta call_target_ptr+1
    sec
    lda call_target_ptr
    sbc #$01
    sta call_target_minus_one
    lda call_target_ptr+1
    sbc #$00
    pha
    lda call_target_minus_one
    pha
    rts

pattern_print:
    .asciiz "PRINT("
pattern_printe:
    .asciiz "PRINTE("
pattern_printi:
    .asciiz "PRINTI("
pattern_printie:
    .asciiz "PRINTIE("
call_target_minus_one:
    .byte $00
call_target_ptr:
    .word $0000
pattern_ptr_local:
    .word $0000
import_flags_local:
    .byte $00

actc_overlay_end:
