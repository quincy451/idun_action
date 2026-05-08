.include "avmrun_native_helper_abi.inc"
.include "avmrun_overlay_resident.inc"
.include "udos_services.inc"

.export avmrun_native_helper_printstd_header
.export avmrun_native_helper_printstd_entry
.export avmrun_native_helper_printstd_end

.segment "CODE"

C64_MEMCFG = $0001
C64_MEMCFG_CONFIG_MASK = $F8
C64_MEMCFG_TOOL_BITS = $06

svc_retptr = AVMRUN_RES_svc_retptr
src_ptr = AVMRUN_RES_src_ptr
word_tmp = AVMRUN_RES_word_tmp
digit_flag = AVMRUN_RES_digit_flag
hex_tmp = AVMRUN_RES_hex_tmp
iptr = AVMRUN_RES_iptr
iptr_offset = AVMRUN_RES_iptr_offset
pptr = AVMRUN_RES_pptr
rptr = AVMRUN_RES_rptr

.macro SAVE_VM_STATE
    lda iptr
    pha
    lda iptr+1
    pha
    lda iptr_offset
    pha
    lda pptr
    pha
    lda rptr
    pha
.endmacro

.macro RESTORE_VM_STATE
    pla
    sta rptr
    pla
    sta pptr
    pla
    sta iptr_offset
    pla
    sta iptr+1
    pla
    sta iptr
.endmacro

.macro CONSOLE_WRITE_SVC
    lda C64_MEMCFG
    pha
    and #C64_MEMCFG_CONFIG_MASK
    ora #C64_MEMCFG_TOOL_BITS
    sta C64_MEMCFG
    ldx #svc_retptr
    jsr svc_console_write_sc0
    pla
    sta C64_MEMCFG
.endmacro

.macro CONSOLE_NEWLINE_SVC
    lda C64_MEMCFG
    pha
    and #C64_MEMCFG_CONFIG_MASK
    ora #C64_MEMCFG_TOOL_BITS
    sta C64_MEMCFG
    jsr svc_console_newline
    pla
    sta C64_MEMCFG
.endmacro

.macro PRINT_CHAR_A
    sta src_ptr
    lda #$00
    sta src_ptr+1
    tya
    pha
    txa
    pha
    lda #<src_ptr
    sta svc_retptr
    lda #>src_ptr
    sta svc_retptr+1
    CONSOLE_WRITE_SVC
    pla
    tax
    pla
    tay
.endmacro

.macro PRINT_DEC_DIV lo, hi
.local sub_loop, done, emit, skip, ge
    lda #$00
    sta hex_tmp
sub_loop:
    lda word_tmp+1
    cmp #hi
    bcc done
    bne ge
    lda word_tmp
    cmp #lo
    bcc done
ge:
    sec
    lda word_tmp
    sbc #lo
    sta word_tmp
    lda word_tmp+1
    sbc #hi
    sta word_tmp+1
    inc hex_tmp
    bne sub_loop
done:
    lda digit_flag
    bne emit
    lda hex_tmp
    beq skip
emit:
    lda hex_tmp
    clc
    adc #'0'
    PRINT_CHAR_A
    lda #$01
    sta digit_flag
skip:
.endmacro

.macro PRINT_U16_WORD_TMP
    lda #$00
    sta digit_flag
    PRINT_DEC_DIV <10000, >10000
    PRINT_DEC_DIV <1000, >1000
    PRINT_DEC_DIV <100, >100
    PRINT_DEC_DIV <10, >10
    lda word_tmp
    clc
    adc #'0'
    PRINT_CHAR_A
.endmacro

avmrun_native_helper_printstd_header:
    .byte AVMRUN_NATIVE_HELPER_MAGIC_0
    .byte AVMRUN_NATIVE_HELPER_MAGIC_1
    .byte AVMRUN_NATIVE_HELPER_MAGIC_2
    .byte AVMRUN_NATIVE_HELPER_MAGIC_3
    .byte AVMRUN_NATIVE_HELPER_ABI_VERSION
    .byte AVMRUN_NATIVE_HELPER_KIND_PRINTSTD
    .word avmrun_native_helper_printstd_entry_table - avmrun_native_helper_printstd_header
    .word avmrun_native_helper_printstd_end - avmrun_native_helper_printstd_header
    .byte 4
    .byte 0

avmrun_native_helper_printstd_entry_table:
    .byte AVMRUN_NATIVE_HELPER_ENTRY_PRINTSTD_STR
    .word avmrun_native_helper_printstd_entry - avmrun_native_helper_printstd_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_PRINTSTD_STR_NL
    .word avmrun_native_helper_printstd_entry_nl - avmrun_native_helper_printstd_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_PRINTSTD_U16
    .word avmrun_native_helper_printstd_entry_u16 - avmrun_native_helper_printstd_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_PRINTSTD_U16_NL
    .word avmrun_native_helper_printstd_entry_u16_nl - avmrun_native_helper_printstd_header

avmrun_native_helper_printstd_entry:
    SAVE_VM_STATE
    CONSOLE_WRITE_SVC
    RESTORE_VM_STATE
    rts

avmrun_native_helper_printstd_entry_nl:
    SAVE_VM_STATE
    CONSOLE_WRITE_SVC
    CONSOLE_NEWLINE_SVC
    RESTORE_VM_STATE
    rts

avmrun_native_helper_printstd_entry_u16:
    lda 0,x
    sta word_tmp
    lda 1,x
    sta word_tmp+1
    SAVE_VM_STATE
    PRINT_U16_WORD_TMP
    RESTORE_VM_STATE
    rts

avmrun_native_helper_printstd_entry_u16_nl:
    lda 0,x
    sta word_tmp
    lda 1,x
    sta word_tmp+1
    SAVE_VM_STATE
    PRINT_U16_WORD_TMP
    CONSOLE_NEWLINE_SVC
    RESTORE_VM_STATE
    rts

avmrun_native_helper_printstd_end:
