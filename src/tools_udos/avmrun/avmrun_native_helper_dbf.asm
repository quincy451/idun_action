.include "avmrun_native_helper_abi.inc"
.export avmrun_native_helper_dbf_header
.export avmrun_native_helper_dbf_end

.segment "CODE"

DBF_REQ_STATUS = 0
DBF_REQ_HANDLE = 1
DBF_REQ_FIELD_COUNT = 2
DBF_REQ_TOTAL_LO = 4
DBF_REQ_TOTAL_HI = 5
DBF_REQ_CURR_LO = 6
DBF_REQ_CURR_HI = 7
DBF_REQ_PATH_LO = 8
DBF_REQ_PATH_HI = 9
DBF_REQ_FIELD_INDEX_LO = 10
DBF_REQ_FIELD_INDEX_HI = 11
DBF_REQ_VALUE_LO = 12
DBF_REQ_VALUE_HI = 13

dbf_req_ptr = $f9
dbf_req_ptr_hi = $fa

avmrun_native_helper_dbf_header:
    .byte AVMRUN_NATIVE_HELPER_MAGIC_0
    .byte AVMRUN_NATIVE_HELPER_MAGIC_1
    .byte AVMRUN_NATIVE_HELPER_MAGIC_2
    .byte AVMRUN_NATIVE_HELPER_MAGIC_3
    .byte AVMRUN_NATIVE_HELPER_ABI_VERSION
    .byte AVMRUN_NATIVE_HELPER_KIND_DBF
    .word avmrun_native_helper_dbf_entry_table - avmrun_native_helper_dbf_header
    .word avmrun_native_helper_dbf_end - avmrun_native_helper_dbf_header
    .byte 9
    .byte 0

avmrun_native_helper_dbf_entry_table:
    .byte AVMRUN_NATIVE_HELPER_ENTRY_DBF_CREATE
    .word avmrun_native_helper_dbf_create - avmrun_native_helper_dbf_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_DBF_OPEN
    .word avmrun_native_helper_dbf_open - avmrun_native_helper_dbf_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_DBF_CURRRECNO
    .word avmrun_native_helper_dbf_currrecno - avmrun_native_helper_dbf_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_DBF_TOTALRECS
    .word avmrun_native_helper_dbf_totalrecs - avmrun_native_helper_dbf_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_DBF_CLOSE
    .word avmrun_native_helper_dbf_close - avmrun_native_helper_dbf_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_DBF_APPENDBLANK
    .word avmrun_native_helper_dbf_appendblank - avmrun_native_helper_dbf_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_DBF_GO
    .word avmrun_native_helper_dbf_go - avmrun_native_helper_dbf_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_DBF_READFIELD
    .word avmrun_native_helper_dbf_readfield - avmrun_native_helper_dbf_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_DBF_WRITEFIELD
    .word avmrun_native_helper_dbf_writefield - avmrun_native_helper_dbf_header

avmrun_native_helper_dbf_prepare_req:
    lda 0,x
    sta dbf_req_ptr
    lda 1,x
    sta dbf_req_ptr_hi
    rts

avmrun_native_helper_dbf_mark_ok:
    ldy #DBF_REQ_HANDLE
    lda #$01
    sta (dbf_req_ptr),y
    ldy #DBF_REQ_STATUS
    sta (dbf_req_ptr),y
    rts

avmrun_native_helper_dbf_mark_fail:
    ldy #DBF_REQ_HANDLE
    lda #$00
    sta (dbf_req_ptr),y
    ldy #DBF_REQ_STATUS
    sta (dbf_req_ptr),y
    rts

avmrun_native_helper_dbf_require_handle:
    ldy #DBF_REQ_HANDLE
    lda (dbf_req_ptr),y
    bne :+
    sec
    rts
:   clc
    rts

avmrun_native_helper_dbf_create:
    jsr avmrun_native_helper_dbf_prepare_req
    ldy #DBF_REQ_TOTAL_LO
    lda #$00
    sta (dbf_req_ptr),y
    iny
    sta (dbf_req_ptr),y
    iny
    sta (dbf_req_ptr),y
    iny
    sta (dbf_req_ptr),y
    jmp avmrun_native_helper_dbf_mark_ok

avmrun_native_helper_dbf_open:
    jsr avmrun_native_helper_dbf_prepare_req
    jmp avmrun_native_helper_dbf_mark_ok

avmrun_native_helper_dbf_currrecno:
    jsr avmrun_native_helper_dbf_prepare_req
    jsr avmrun_native_helper_dbf_require_handle
    bcc :+
    jmp avmrun_native_helper_dbf_mark_fail
:   jmp avmrun_native_helper_dbf_mark_ok

avmrun_native_helper_dbf_totalrecs:
    jsr avmrun_native_helper_dbf_prepare_req
    jsr avmrun_native_helper_dbf_require_handle
    bcc :+
    jmp avmrun_native_helper_dbf_mark_fail
:   jmp avmrun_native_helper_dbf_mark_ok

avmrun_native_helper_dbf_close:
    jsr avmrun_native_helper_dbf_prepare_req
    jsr avmrun_native_helper_dbf_require_handle
    bcc :+
    jmp avmrun_native_helper_dbf_mark_fail
:   ldy #DBF_REQ_HANDLE
    lda #$00
    sta (dbf_req_ptr),y
    ldy #DBF_REQ_STATUS
    lda #$01
    sta (dbf_req_ptr),y
    rts

avmrun_native_helper_dbf_appendblank:
    jsr avmrun_native_helper_dbf_prepare_req
    jsr avmrun_native_helper_dbf_require_handle
    bcc :+
    jmp avmrun_native_helper_dbf_mark_fail
:   ldy #DBF_REQ_TOTAL_LO
    clc
    lda (dbf_req_ptr),y
    adc #$01
    sta (dbf_req_ptr),y
    iny
    lda (dbf_req_ptr),y
    adc #$00
    sta (dbf_req_ptr),y
    ldy #DBF_REQ_CURR_LO
    lda (dbf_req_ptr),y
    clc
    adc #$01
    sta (dbf_req_ptr),y
    iny
    lda (dbf_req_ptr),y
    adc #$00
    sta (dbf_req_ptr),y
    jmp avmrun_native_helper_dbf_mark_ok

avmrun_native_helper_dbf_go:
    jsr avmrun_native_helper_dbf_prepare_req
    jsr avmrun_native_helper_dbf_require_handle
    bcc :+
    jmp avmrun_native_helper_dbf_mark_fail
:   jmp avmrun_native_helper_dbf_mark_ok

avmrun_native_helper_dbf_readfield:
    jsr avmrun_native_helper_dbf_prepare_req
    jsr avmrun_native_helper_dbf_require_handle
    bcc :+
    jmp avmrun_native_helper_dbf_mark_fail
:   jmp avmrun_native_helper_dbf_mark_ok

avmrun_native_helper_dbf_writefield:
    jsr avmrun_native_helper_dbf_prepare_req
    jsr avmrun_native_helper_dbf_require_handle
    bcc :+
    jmp avmrun_native_helper_dbf_mark_fail
:   jmp avmrun_native_helper_dbf_mark_ok

avmrun_native_helper_dbf_end:
