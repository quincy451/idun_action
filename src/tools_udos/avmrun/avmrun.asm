.include "udos_services.inc"
.include "avmrun_overlay_abi.inc"
.include "avmrun_native_helper_abi.inc"

.export start
.export c64_memcfg
.exportzp iptr, iptr_offset, pptr, rptr
.import __BSS_RUN__, __BSS_SIZE__

.segment "STARTUP"
    jmp start

AVM_HEADER_SIZE = 10
AVM_HEADER_SIZE_V2 = 12
AVM_VERSION_V1 = 1
AVM_VERSION_V2 = 2
AVM_FLAG_ACHERON = 1
AVM_FLAG_NATIVE_HELPERS = 2
AVM_KNOWN_FLAGS = AVM_FLAG_ACHERON | AVM_FLAG_NATIVE_HELPERS
AVM_HELPER_TRAILER_MAGIC_0 = 'A'
AVM_HELPER_TRAILER_MAGIC_1 = 'V'
AVM_HELPER_TRAILER_MAGIC_2 = 'H'
AVM_HELPER_TRAILER_MAGIC_3 = '1'
TOOL_DEBUG0 = $03D0
TOOL_DEBUG1 = $03D1
TOOL_DEBUG2 = $03D2
TOOL_DEBUG3 = $03D3
TOOL_DEBUG4 = $03D4
TOOL_DEBUG5 = $03D5
TOOL_DEBUG6 = $03D6
TOOL_DEBUG7 = $03D7
TOOL_DEBUG8 = $03D8
TOOL_DEBUG9 = $03D9
TOOL_DEBUG10 = $03DA
TOOL_DEBUG11 = $03DB
TOOL_DEBUG12 = $03DC
TOOL_DEBUG13 = $03DD
TOOL_DEBUG14 = $03DE
TOOL_DEBUG15 = $03DF
C64_MEMCFG = $0001
C64_MEMCFG_CONFIG_MASK = $F8
C64_MEMCFG_TOOL_BITS = $06
C64_MEMCFG_RUNTIME_BITS = $04
c64_memcfg = C64_MEMCFG
pptr = $008B
rptr = $008C
iptr_offset = $008D
iptr = $008E
.ifndef FILE_BUFFER_ADDR
FILE_BUFFER_ADDR = $4750
.endif
.ifndef FILE_BUFFER_SIZE
FILE_BUFFER_SIZE = $C000
.endif
.ifndef ALLOW_TEXT_AVM
ALLOW_TEXT_AVM = 1
.endif
.ifndef AVMRUN_COMPAT
AVMRUN_COMPAT = 1
.endif
.if ALLOW_TEXT_AVM
.ifndef PAYLOAD_BUFFER_SIZE
PAYLOAD_BUFFER_SIZE = 256
.endif
.endif
INTERP_STACK_MAX = 16
.if AVMRUN_COMPAT
AVMRUN_INTERP_SCRATCH_BASE = $3C00
.else
AVMRUN_INTERP_SCRATCH_BASE = $39C0
.endif
AVMRUN_INTERP_ERROR_PTR = AVMRUN_INTERP_SCRATCH_BASE + $00
AVMRUN_INTERP_SP = AVMRUN_INTERP_SCRATCH_BASE + $02
AVMRUN_INTERP_RSP = AVMRUN_INTERP_SCRATCH_BASE + $03
AVMRUN_INTERP_STRING_PTR = AVMRUN_INTERP_SCRATCH_BASE + $04
AVMRUN_INTERP_STACK_LO = AVMRUN_INTERP_SCRATCH_BASE + $06
AVMRUN_INTERP_STACK_HI = AVMRUN_INTERP_STACK_LO + INTERP_STACK_MAX
AVMRUN_INTERP_RSTACK_LO = AVMRUN_INTERP_STACK_HI + INTERP_STACK_MAX
AVMRUN_INTERP_RSTACK_HI = AVMRUN_INTERP_RSTACK_LO + INTERP_STACK_MAX
AVMRUN_INTERP_RESULT = AVMRUN_INTERP_RSTACK_HI + INTERP_STACK_MAX
AVMRUN_INTERP_SERVICE_KIND = AVMRUN_INTERP_RESULT + $01
AVMRUN_INTERP_SERVICE_CMD = AVMRUN_INTERP_SERVICE_KIND + $01
AVMRUN_INTERP_RESUME_STATE = AVMRUN_INTERP_SERVICE_CMD + $01
AVMRUN_INTERP_SERVICE_FAILED = AVMRUN_INTERP_RESUME_STATE + $01
.if AVMRUN_COMPAT
AVMRUN_RUNTIME_SCRATCH_BASE = $3C80
.else
AVMRUN_RUNTIME_SCRATCH_BASE = $3AC0
.endif
.if AVMRUN_COMPAT
AVMRUN_RUNTIME_SCRATCH_END = AVMRUN_RUNTIME_SCRATCH_BASE + $7F
.else
AVMRUN_RUNTIME_SCRATCH_END = AVMRUN_RUNTIME_SCRATCH_BASE + $4B
.endif
; Binary AVM images are loaded outside AVMRUN BSS so runtime capacity is not
; limited by the tool image. Production builds compile with ALLOW_TEXT_AVM=0,
; so the legacy text decoder and its payload buffer are not resident.
; Interpreter-only state lives in the standard-helper execution window at
; $2C00 in production builds; the fallback interpreter never runs at the same
; time as the native standard-print helper.
; Remaining mutable runner state lives in fixed scratch below $2C00 so it does
; not inflate the always-resident image.
file_buffer = FILE_BUFFER_ADDR
.if AVMRUN_COMPAT
DBF_FILE_BUFFER_BASE = FILE_BUFFER_ADDR
DBF_FILE_BUFFER_SIZE = FILE_BUFFER_SIZE
DBF_PATH_SCRATCH_BASE = AVMRUN_NATIVE_HELPER_DBF_BASE + AVMRUN_NATIVE_HELPER_DBF_SIZE - $30
DBF_HEADER_SCRATCH_BASE = AVMRUN_NATIVE_HELPER_DBF_BASE + AVMRUN_NATIVE_HELPER_DBF_SIZE - $10
.else
; Production record-bearing DBF ops need a file workspace that does not alias
; the live AVM payload executing from file_buffer. Reuse the shared native-
; helper window and keep DBF scratch in the unused tail of interp scratch.
DBF_FILE_BUFFER_BASE = AVMRUN_NATIVE_HELPER_DBF_BASE
DBF_FILE_BUFFER_SIZE = FILE_BUFFER_ADDR - AVMRUN_NATIVE_HELPER_DBF_BASE
DBF_PATH_SCRATCH_BASE = AVMRUN_INTERP_SCRATCH_BASE + $C0
DBF_HEADER_SCRATCH_BASE = AVMRUN_INTERP_SCRATCH_BASE + $E0
.endif
dbf_file_buffer = DBF_FILE_BUFFER_BASE

OPCODE_PUSH8 = $10
OPCODE_PUSH16 = $11
OPCODE_STORE = $12
OPCODE_LOAD = $13
OPCODE_ADD = $14
OPCODE_SUB = $15
OPCODE_EQ = $16
OPCODE_NE = $17
OPCODE_JZ = $18
OPCODE_JMP = $19
OPCODE_DUP = $1A
OPCODE_DROP = $1B
OPCODE_LT = $1C
OPCODE_GT = $1D
OPCODE_BAND = $1E
OPCODE_BOR = $1F
OPCODE_BXOR = $20
OPCODE_SHL1 = $21
OPCODE_SHR1 = $22
OPCODE_FADD = $23
OPCODE_FSUB = $24
OPCODE_FMUL = $25
OPCODE_FDIV = $26
OPCODE_FTOI = $27
OPCODE_ITOF = $28
OPCODE_NATIVE = $2D
OPCODE_GROW = $2F
OPCODE_CALL = $45
OPCODE_JUMP = $46
OPCODE_RET = $48
OPCODE_CALLN = $49
OPCODE_CLRP = $5C
OPCODE_SETP8 = $5D
OPCODE_MOVEP = $5F
OPCODE_COPYR = $60
OPCODE_SETP16 = $61

INTRINSIC_PRINT = $FF00
INTRINSIC_PRINTE = $FF10
INTRINSIC_EXIT = $FF20
INTRINSIC_PRINTI = $FF30
INTRINSIC_PRINTIE = $FF31
INTRINSIC_PRINTREAL = $FF32
INTRINSIC_LINKED_PRINT = $FE00
INTRINSIC_LINKED_PRINTE = $FE10
INTRINSIC_LINKED_PRINTI = $FE30
INTRINSIC_LINKED_PRINTIE = $FE31
INTRINSIC_LINKED_PRINTREAL = $FE32
INTRINSIC_LINKED_MATH_FABS = $FA01
INTRINSIC_LINKED_MATH_FSQRT = $FA02
INTRINSIC_LINKED_DBF_CREATE = $FB01
INTRINSIC_LINKED_DBF_CURRRECNO = $FB02
INTRINSIC_LINKED_DBF_TOTALRECS = $FB03
INTRINSIC_LINKED_DBF_CLOSE = $FB04
INTRINSIC_LINKED_DBF_OPEN = $FB05
INTRINSIC_LINKED_DBF_APPENDBLANK = $FB06
INTRINSIC_LINKED_DBF_GO = $FB07
INTRINSIC_LINKED_DBF_READFIELD = $FB08
INTRINSIC_LINKED_DBF_WRITEFIELD = $FB09
INTRINSIC_LINKED_GFX_BITMAP_ON = $FC01
INTRINSIC_LINKED_GFX_BITMAP_OFF = $FC02
INTRINSIC_LINKED_GFX_MBITMAP_ON = $FC03
INTRINSIC_LINKED_GFX_BG_COLOR = $FC04
INTRINSIC_LINKED_GFX_BORDER_COLOR = $FC05
INTRINSIC_LINKED_GFX_VIC_BANK = $FC06
INTRINSIC_LINKED_GFX_SCREEN_BASE = $FC07
INTRINSIC_LINKED_GFX_BITMAP_BASE = $FC08
INTRINSIC_LINKED_GFX_BITMAP_FILL = $FC09
INTRINSIC_LINKED_GFX_SCREEN_CELL = $FC0A
INTRINSIC_LINKED_GFX_COLOR_CELL = $FC0B
INTRINSIC_LINKED_GFX_BITMAP_SHOW = $FC0C
INTRINSIC_LINKED_GFX_BITMAP_HIDE = $FC0D
INTRINSIC_LINKED_GFX_BITMAP_COPY = $FC0E
INTRINSIC_LINKED_GFX_SCREEN_COPY = $FC0F
INTRINSIC_LINKED_GFX_COLOR_COPY = $FC10
INTRINSIC_LINKED_GFX_BITMAP_CELL_COLORS = $FC11
INTRINSIC_LINKED_GFX_BITMAP_CELL_DATA = $FC12
INTRINSIC_LINKED_GFX_BITMAP_BLIT = $FC13
INTRINSIC_LINKED_GFX_TILE_DRAW = $FC14
INTRINSIC_LINKED_GFX_TILE_RECT_FILL = $FC15
INTRINSIC_LINKED_GFX_BITMAP_MASK_BLIT = $FC16
INTRINSIC_LINKED_GFX_TILE_MASK_DRAW = $FC17
INTRINSIC_LINKED_GFX_TILESET_DRAW = $FC18
INTRINSIC_LINKED_GFX_TILESET_RECT_FILL = $FC19
INTRINSIC_LINKED_GFX_TILESET_MASK_DRAW = $FC1A
INTRINSIC_LINKED_GFX_TILESET_MASK_RECT_FILL = $FC1B
INTRINSIC_LINKED_SIDSPR_SPRITE_ON = $FD01
INTRINSIC_LINKED_SIDSPR_SPRITE_OFF = $FD02
INTRINSIC_LINKED_SIDSPR_SPRITE_POS = $FD03
INTRINSIC_LINKED_SIDSPR_SPRITE_DATA = $FD04
INTRINSIC_LINKED_SIDSPR_SPRITE_COLOR = $FD05
INTRINSIC_LINKED_SIDSPR_SID_FREQ = $FD10
INTRINSIC_LINKED_SIDSPR_SID_WAVE = $FD11
INTRINSIC_LINKED_SIDSPR_SID_AD = $FD12
INTRINSIC_LINKED_SIDSPR_SID_SR = $FD13
INTRINSIC_LINKED_SIDSPR_SID_ON = $FD14
INTRINSIC_LINKED_SIDSPR_SID_OFF = $FD15
INTRINSIC_LINKED_SIDSPR_SID_VOL = $FD16
 .if AVMRUN_COMPAT
AVMRUN_NATIVE_HELPER_PRINTREAL_BASE = AVMRUN_OVERLAY_EXEC_BASE
 .else
AVMRUN_NATIVE_HELPER_PRINTREAL_BASE = $F000
 .endif
AVMRUN_NATIVE_HELPER_PRINTREAL_SIZE = $0800
.if AVMRUN_COMPAT
AVMRUN_NATIVE_HELPER_MATH_BASE = $3D00
AVMRUN_NATIVE_HELPER_GFX_BASE = $3D00
AVMRUN_NATIVE_HELPER_SIDSPR_BASE = $3D00
AVMRUN_NATIVE_HELPER_DBF_BASE = $3D00
AVMRUN_NATIVE_HELPER_PRINTSTD_BASE = $3D00
.else
AVMRUN_NATIVE_HELPER_PRINTSTD_BASE = $3B10
AVMRUN_NATIVE_HELPER_MATH_BASE = AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    AVMRUN_NATIVE_HELPER_SIDSPR_BASE = AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
AVMRUN_NATIVE_HELPER_GFX_BASE = $3B10
    AVMRUN_NATIVE_HELPER_DBF_BASE = AVMRUN_NATIVE_HELPER_GFX_BASE
.endif
AVMRUN_NATIVE_HELPER_MATH_SIZE = $0200
AVMRUN_NATIVE_HELPER_GFX_SIZE = $0E10
AVMRUN_NATIVE_HELPER_SIDSPR_SIZE = $0200
AVMRUN_NATIVE_HELPER_DBF_SIZE = $0300
AVMRUN_NATIVE_HELPER_PRINTSTD_SIZE = $0500
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
DBF_FILE_MAGIC_0 = 'D'
DBF_FILE_MAGIC_1 = 'B'
DBF_FILE_MAGIC_2 = 'F'
DBF_FILE_MAGIC_3 = '1'
DBF_FILE_HEADER_LEN = 10

.segment "ZPTEMP": zeropage
svc_retptr:
    .res 2
file_params:
    .res 9
src_ptr:
    .res 2
payload_ptr:
    .res 2
entry_ptr:
    .res 2
scan_ptr:
    .res 2
scan_end:
    .res 2
word_tmp:
    .res 2
digit_flag:
    .res 1
hex_tmp:
    .res 1

.code

start:
    jsr clear_bss
    lda C64_MEMCFG
    sta saved_memcfg
    jsr set_tool_mem_config
    ldx #svc_retptr
    jsr svc_program_get_cmdline_len
    lda svc_retptr
    ora svc_retptr+1
    bne have_args
    lda #<msg_no_file
    ldy #>msg_no_file
    jmp fail_with_ptr

have_args:
    ldx #svc_retptr
    jsr svc_program_get_cmdline_ptr
    lda svc_retptr
    sta src_ptr
    lda svc_retptr+1
    sta src_ptr+1
    jsr copy_first_arg

    lda #<filename_buffer
    sta file_params+0
    lda #>filename_buffer
    sta file_params+1
    lda #<file_buffer
    sta file_params+2
    lda #>file_buffer
    sta file_params+3
    lda #<FILE_BUFFER_SIZE
    sta file_params+4
    lda #>FILE_BUFFER_SIZE
    sta file_params+5
    lda #$00
    sta file_params+6
    sta file_params+7
    sta file_params+8

    ldx #file_params
    jsr svc_file_load_sc0

    lda file_params+6
    cmp #tool_file_status_ok
    beq file_loaded
    cmp #tool_file_status_nofile
    beq show_no_file
    cmp #tool_file_status_too_large
    beq show_too_large
    lda #<msg_load_fail
    ldy #>msg_load_fail
    jmp fail_with_ptr

show_no_file:
    lda #<msg_no_file
    ldy #>msg_no_file
    jmp fail_with_ptr

show_too_large:
    lda #<msg_too_large
    ldy #>msg_too_large
    jmp fail_with_ptr

file_loaded:
    lda file_params+8
    cmp #>FILE_BUFFER_SIZE
    bcc file_loaded_terminate
    bne file_loaded_skip_terminate
    lda file_params+7
    cmp #<FILE_BUFFER_SIZE
    bcs file_loaded_skip_terminate
file_loaded_terminate:
    clc
    lda #<file_buffer
    adc file_params+7
    sta src_ptr
    lda #>file_buffer
    adc file_params+8
    sta src_ptr+1
    ldy #$00
    lda #$00
    sta (src_ptr),y
file_loaded_skip_terminate:
    clc
    lda #<file_buffer
    adc file_params+7
    sta file_end_ptr
    lda #>file_buffer
    adc file_params+8
    sta file_end_ptr+1
    jsr prepare_loaded_payload
    bcc header_ok
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr

header_ok:
    lda #$00
    sta TOOL_DEBUG10
    jsr set_runtime_mem_config
    jsr patch_payload
    bcs header_ok_interpret
    jmp payload_ready
header_ok_interpret:
    lda #$A1
    sta TOOL_DEBUG10
.if AVMRUN_COMPAT
    jsr interpret_payload
    bcc interpreted_ok
    lda interp_error_ptr
    ora interp_error_ptr+1
    beq header_ok_interpret_unsupported
    lda interp_error_ptr
    ldy interp_error_ptr+1
    jmp fail_with_ptr
header_ok_interpret_unsupported:
    lda #<msg_unsupported
    ldy #>msg_unsupported
    jmp fail_with_ptr
.else
    jmp fail_needs_compat
.endif

interpreted_ok:
    jsr restore_mem_config
    lda #$00
    sta svc_retptr
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

payload_ready:
    lda entry_ptr
    sta svc_retptr
    lda entry_ptr+1
    sta svc_retptr+1
    jsr run_native_payload
    jsr restore_mem_config
    lda #$00
    sta svc_retptr
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

run_native_payload:
    ldx #svc_retptr
    jsr svc_vm_acheron_enter
    rts

clear_bss:
    lda #<__BSS_RUN__
    sta src_ptr
    lda #>__BSS_RUN__
    sta src_ptr+1
    lda #<(__BSS_RUN__ + __BSS_SIZE__)
    sta word_tmp
    lda #>(__BSS_RUN__ + __BSS_SIZE__)
    sta word_tmp+1
    lda src_ptr
    cmp word_tmp
    bne :+
    lda src_ptr+1
    cmp word_tmp+1
    beq clear_bss_done
:
    ldy #$00
    lda #$00
clear_bss_loop:
    sta (src_ptr),y
    inc src_ptr
    bne :+
    inc src_ptr+1
:   lda src_ptr
    cmp word_tmp
    bne clear_bss_continue
    lda src_ptr+1
    cmp word_tmp+1
    beq clear_bss_done
clear_bss_continue:
    lda #$00
    jmp clear_bss_loop
clear_bss_done:
    lda #<AVMRUN_RUNTIME_SCRATCH_BASE
    sta src_ptr
    lda #>AVMRUN_RUNTIME_SCRATCH_BASE
    sta src_ptr+1
    lda #<AVMRUN_RUNTIME_SCRATCH_END
    sta word_tmp
    lda #>AVMRUN_RUNTIME_SCRATCH_END
    sta word_tmp+1
    ldy #$00
    lda #$00
clear_runtime_scratch_loop:
    sta (src_ptr),y
    inc src_ptr
    bne :+
    inc src_ptr+1
:   lda src_ptr
    cmp word_tmp
    bne clear_runtime_scratch_continue
    lda src_ptr+1
    cmp word_tmp+1
    beq clear_runtime_scratch_done
clear_runtime_scratch_continue:
    lda #$00
    jmp clear_runtime_scratch_loop
clear_runtime_scratch_done:
    rts

fail_with_ptr:
    jsr print_ptr
    jsr runtime_safe_console_newline
    jsr restore_mem_config
    lda #$01
    sta svc_retptr
    lda #$00
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

fail_needs_compat:
    lda #<msg_needs_compat
    ldy #>msg_needs_compat
    jmp fail_with_ptr

prepare_loaded_payload:
    lda file_buffer+0
    cmp #'A'
    beq :+
.if ALLOW_TEXT_AVM
    jmp decode_avm_text
.else
    jmp validate_header_fail
.endif
:
    lda file_buffer+1
    cmp #'V'
    beq :+
.if ALLOW_TEXT_AVM
    jmp decode_avm_text
.else
    jmp validate_header_fail
.endif
:
    lda file_buffer+2
    cmp #'M'
    beq :+
.if ALLOW_TEXT_AVM
    jmp decode_avm_text
.else
    jmp validate_header_fail
.endif
:
    lda file_buffer+3
    cmp #'1'
    beq :+
.if ALLOW_TEXT_AVM
    jmp decode_avm_text
.else
    jmp validate_header_fail
.endif
:
    jmp validate_header

validate_header:
    lda file_buffer+0
    cmp #'A'
    beq :+
    jmp validate_header_fail
:
    lda file_buffer+1
    cmp #'V'
    beq :+
    jmp validate_header_fail
:
    lda file_buffer+2
    cmp #'M'
    beq :+
    jmp validate_header_fail
:
    lda file_buffer+3
    cmp #'1'
    beq :+
    jmp validate_header_fail
:
    lda file_buffer+4
    cmp #AVM_VERSION_V1
    beq validate_header_v1
    cmp #AVM_VERSION_V2
    beq validate_header_v2
    jmp validate_header_fail
validate_header_v1:
    lda file_buffer+5
    sta scan_end
    lda file_buffer+6
    sta scan_end+1
    lda scan_end
    sta src_ptr
    lda scan_end+1
    sta src_ptr+1
    lda file_buffer+7
    sta word_tmp
    lda file_buffer+8
    sta word_tmp+1
    lda #<(file_buffer + AVM_HEADER_SIZE)
    sta payload_ptr
    lda #>(file_buffer + AVM_HEADER_SIZE)
    sta payload_ptr+1
    jmp validate_header_common
validate_header_v2:
    lda file_buffer+5
    sta scan_end
    lda file_buffer+6
    sta scan_end+1
    lda file_buffer+10
    sta src_ptr
    lda file_buffer+11
    sta src_ptr+1
    lda src_ptr+1
    cmp scan_end+1
    bcc :+
    bne validate_header_fail
    lda src_ptr
    cmp scan_end
    bcc :+
    beq :+
    jmp validate_header_fail
:   lda file_buffer+7
    sta word_tmp
    lda file_buffer+8
    sta word_tmp+1
    lda #<(file_buffer + AVM_HEADER_SIZE_V2)
    sta payload_ptr
    lda #>(file_buffer + AVM_HEADER_SIZE_V2)
    sta payload_ptr+1
validate_header_common:
    lda file_buffer+9
    sta avm_flags
    and #AVM_FLAG_ACHERON
    beq validate_header_fail
    lda avm_flags
    and #($FF ^ AVM_KNOWN_FLAGS)
    bne validate_header_fail
    lda word_tmp+1
    cmp scan_end+1
    bcc :+
    bne validate_header_fail
    lda word_tmp
    cmp scan_end
    bcs validate_header_fail
:
    clc
    lda payload_ptr
    adc scan_end
    sta payload_end_ptr
    lda payload_ptr+1
    adc scan_end+1
    sta payload_end_ptr+1
    clc
    lda payload_ptr
    adc src_ptr
    sta scan_end
    lda payload_ptr+1
    adc src_ptr+1
    sta scan_end+1
    clc
    lda payload_ptr
    adc word_tmp
    sta entry_ptr
    lda payload_ptr+1
    adc word_tmp+1
    sta entry_ptr+1
    clc
    rts

validate_header_fail:
    sec
    rts

.if ALLOW_TEXT_AVM
decode_avm_text:
    lda file_buffer+0
    cmp #'e'
    beq :+
    jmp decode_avm_text_fail
:
    lda file_buffer+1
    cmp #'n'
    beq :+
    jmp decode_avm_text_fail
:
    lda file_buffer+2
    cmp #'t'
    beq :+
    jmp decode_avm_text_fail
:
    lda file_buffer+3
    cmp #'r'
    beq :+
    jmp decode_avm_text_fail
:
    lda file_buffer+4
    cmp #'y'
    beq :+
    jmp decode_avm_text_fail
:
    lda file_buffer+5
    cmp #' '
    beq :+
    jmp decode_avm_text_fail
:
    lda #<(file_buffer + 6)
    sta scan_ptr
    lda #>(file_buffer + 6)
    sta scan_ptr+1
    jsr parse_decimal_word_at_scan_ptr
    bcc :+
    jmp decode_avm_text_fail
:
    lda word_tmp
    sta entry_ptr
    lda word_tmp+1
    sta entry_ptr+1
    lda #$00
    sta scan_end
    sta scan_end+1
    jsr consume_line_break_at_scan_ptr
    bcc :+
    jmp decode_avm_text_fail
:
    ldy #$00
    lda (scan_ptr),y
    cmp #'c'
    bne decode_avm_text_expect_db
    iny
    lda (scan_ptr),y
    cmp #'o'
    beq :+
    jmp decode_avm_text_fail
:
    iny
    lda (scan_ptr),y
    cmp #'d'
    beq :+
    jmp decode_avm_text_fail
:
    iny
    lda (scan_ptr),y
    cmp #'e'
    beq :+
    jmp decode_avm_text_fail
:
    iny
    lda (scan_ptr),y
    cmp #' '
    beq :+
    jmp decode_avm_text_fail
:
    lda #$05
    jsr advance_scan_ptr
    ldy #$00
    lda (scan_ptr),y
    cmp #'$'
    bne :+
    lda #$01
    jsr advance_scan_ptr
    jsr parse_hex_byte_at_scan_ptr
    bcc :+
    jmp decode_avm_text_fail
:
    sta scan_end
    lda #$00
    sta scan_end+1
    jmp decode_avm_text_have_code_len
    jsr parse_decimal_word_at_scan_ptr
    bcc :+
    jmp decode_avm_text_fail
:
    lda word_tmp
    sta scan_end
    lda word_tmp+1
    sta scan_end+1
decode_avm_text_have_code_len:
    jsr consume_line_break_at_scan_ptr
    bcc :+
    jmp decode_avm_text_fail
:
decode_avm_text_expect_db:
    ldy #$00
    lda (scan_ptr),y
    cmp #'d'
    beq decode_avm_text_expect_db_prefix
    cmp #'h'
    beq decode_avm_text_expect_hex_prefix
    jmp decode_avm_text_fail
decode_avm_text_expect_db_prefix:
    iny
    lda (scan_ptr),y
    cmp #'b'
    beq :+
    jmp decode_avm_text_fail
:
    iny
    lda (scan_ptr),y
    cmp #' '
    beq :+
    jmp decode_avm_text_fail
:
    lda #$03
    jsr advance_scan_ptr
    jmp decode_avm_text_init_payload_ptr
decode_avm_text_expect_hex_prefix:
    iny
    lda (scan_ptr),y
    cmp #'e'
    beq :+
    jmp decode_avm_text_fail
:
    iny
    lda (scan_ptr),y
    cmp #'x'
    beq :+
    jmp decode_avm_text_fail
:
    iny
    lda (scan_ptr),y
    cmp #' '
    beq :+
    jmp decode_avm_text_fail
:
    lda #$04
    jsr advance_scan_ptr
decode_avm_text_init_payload_ptr:
    lda #<payload_buffer
    sta payload_ptr
    sta src_ptr
    lda #>payload_buffer
    sta payload_ptr+1
    sta src_ptr+1
    ldy #$00
    lda (scan_ptr),y
    cmp #'$'
    beq decode_avm_text_byte_loop
    jmp decode_avm_text_hex_loop
decode_avm_text_byte_loop:
    ldy #$00
    lda (scan_ptr),y
    beq decode_avm_text_byte_done
    cmp #10
    beq decode_avm_text_byte_done
    cmp #13
    beq decode_avm_text_byte_done
    cmp #'$'
    beq :+
    jmp decode_avm_text_fail
:
    lda #$01
    jsr advance_scan_ptr
    jsr parse_hex_byte_at_scan_ptr
    bcc :+
    jmp decode_avm_text_fail
:
    ldy #$00
    sta (src_ptr),y
    inc src_ptr
    bne :+
    inc src_ptr+1
:   lda src_ptr+1
    cmp #>(payload_buffer + PAYLOAD_BUFFER_SIZE)
    bcc :+
    beq :+
    jmp decode_avm_text_fail
:
    lda src_ptr
    cmp #<(payload_buffer + PAYLOAD_BUFFER_SIZE)
    bcc :+
    bne :+
    jmp decode_avm_text_fail
:   ldy #$00
    lda (scan_ptr),y
    cmp #','
    beq decode_avm_text_consume_comma
    cmp #$00
    beq decode_avm_text_byte_done
    cmp #10
    beq decode_avm_text_byte_done
    cmp #13
    beq decode_avm_text_byte_done
    jmp decode_avm_text_fail
decode_avm_text_consume_comma:
    lda #$01
    jsr advance_scan_ptr
    jmp decode_avm_text_byte_loop
decode_avm_text_byte_done:
    jmp decode_avm_text_done
decode_avm_text_hex_loop:
    ldy #$00
    lda (scan_ptr),y
    beq decode_avm_text_done
    cmp #10
    beq decode_avm_text_done
    cmp #13
    beq decode_avm_text_done
    jsr parse_hex_byte_at_scan_ptr
    bcc :+
    jmp decode_avm_text_fail
:
    ldy #$00
    sta (src_ptr),y
    inc src_ptr
    bne :+
    inc src_ptr+1
:   lda src_ptr+1
    cmp #>(payload_buffer + PAYLOAD_BUFFER_SIZE)
    bcc :+
    beq :+
    jmp decode_avm_text_fail
:
    lda src_ptr
    cmp #<(payload_buffer + PAYLOAD_BUFFER_SIZE)
    bcc :+
    bne :+
    jmp decode_avm_text_fail
:   jmp decode_avm_text_hex_loop
decode_avm_text_done:
    lda src_ptr
    cmp payload_ptr
    bne decode_avm_text_have_payload
    lda src_ptr+1
    cmp payload_ptr+1
    bne decode_avm_text_have_payload
    jmp decode_avm_text_fail
decode_avm_text_have_payload:
    lda scan_end
    ora scan_end+1
    beq decode_avm_text_use_payload_end
    clc
    lda payload_ptr
    adc scan_end
    sta scan_end
    lda payload_ptr+1
    adc scan_end+1
    sta scan_end+1
    jmp decode_avm_text_check_entry
decode_avm_text_use_payload_end:
    lda src_ptr
    sta scan_end
    lda src_ptr+1
    sta scan_end+1
decode_avm_text_check_entry:
    lda payload_ptr
    clc
    adc entry_ptr
    sta entry_ptr
    lda payload_ptr+1
    adc entry_ptr+1
    sta entry_ptr+1
    lda entry_ptr+1
    cmp scan_end+1
    bcc decode_avm_text_check_code_end
    bne decode_avm_text_entry_fail
    lda entry_ptr
    cmp scan_end
    bcc decode_avm_text_check_code_end
decode_avm_text_entry_fail:
    jmp decode_avm_text_fail
decode_avm_text_check_code_end:
    lda scan_end+1
    cmp src_ptr+1
    bcc decode_avm_text_success
    bne decode_avm_text_code_end_fail
    lda scan_end
    cmp src_ptr
    bcc decode_avm_text_success
    beq decode_avm_text_success
decode_avm_text_code_end_fail:
    jmp decode_avm_text_fail
decode_avm_text_success:
    clc
    rts
decode_avm_text_fail:
    sec
    rts

parse_decimal_word_at_scan_ptr:
    lda #$00
    sta word_tmp
    sta word_tmp+1
    sta digit_flag
parse_decimal_word_at_scan_ptr_loop:
    ldy #$00
    lda (scan_ptr),y
    cmp #'0'
    bcc parse_decimal_word_at_scan_ptr_done
    cmp #'9'+1
    bcs parse_decimal_word_at_scan_ptr_done
    sec
    sbc #'0'
    pha
    lda word_tmp
    sta hex_tmp
    lda word_tmp+1
    pha
    lda word_tmp
    asl a
    rol word_tmp+1
    sta word_tmp
    lda word_tmp
    asl a
    rol word_tmp+1
    asl a
    rol word_tmp+1
    clc
    adc hex_tmp
    sta word_tmp
    pla
    adc word_tmp+1
    sta word_tmp+1
    lda hex_tmp
    clc
    adc word_tmp
    sta word_tmp
    bcc :+
    inc word_tmp+1
:   pla
    clc
    adc word_tmp
    sta word_tmp
    bcc :+
    inc word_tmp+1
:   lda #$01
    sta digit_flag
    lda #$01
    jsr advance_scan_ptr
    jmp parse_decimal_word_at_scan_ptr_loop
parse_decimal_word_at_scan_ptr_done:
    lda digit_flag
    beq decode_avm_text_fail
    clc
    rts

consume_line_break_at_scan_ptr:
    ldy #$00
    lda (scan_ptr),y
    cmp #13
    beq consume_line_break_cr
    cmp #10
    beq consume_line_break_lf
    sec
    rts
consume_line_break_cr:
    lda #$01
    jsr advance_scan_ptr
    ldy #$00
    lda (scan_ptr),y
    cmp #10
    bne :+
    lda #$01
    jsr advance_scan_ptr
:   clc
    rts
consume_line_break_lf:
    lda #$01
    jsr advance_scan_ptr
    clc
    rts

parse_hex_byte_at_scan_ptr:
    jsr parse_hex_nibble_at_scan_ptr
    bcs parse_hex_byte_at_scan_ptr_fail
    asl a
    asl a
    asl a
    asl a
    sta hex_tmp
    jsr parse_hex_nibble_at_scan_ptr
    bcs parse_hex_byte_at_scan_ptr_fail
    ora hex_tmp
    clc
    rts
parse_hex_byte_at_scan_ptr_fail:
    sec
    rts

parse_hex_nibble_at_scan_ptr:
    ldy #$00
    lda (scan_ptr),y
    cmp #'0'
    bcc parse_hex_nibble_at_scan_ptr_bad
    cmp #'9'+1
    bcc parse_hex_nibble_at_scan_ptr_digit
    cmp #'a'
    bcc parse_hex_nibble_at_scan_ptr_upper
    cmp #'f'+1
    bcs parse_hex_nibble_at_scan_ptr_bad
    sec
    sbc #'a'-10
    pha
    lda #$01
    jsr advance_scan_ptr
    pla
    clc
    rts
parse_hex_nibble_at_scan_ptr_upper:
    cmp #'A'
    bcc parse_hex_nibble_at_scan_ptr_bad
    cmp #'F'+1
    bcs parse_hex_nibble_at_scan_ptr_bad
    sec
    sbc #'A'-10
    pha
    lda #$01
    jsr advance_scan_ptr
    pla
    clc
    rts
parse_hex_nibble_at_scan_ptr_digit:
    sec
    sbc #'0'
    pha
    lda #$01
    jsr advance_scan_ptr
    pla
    clc
    rts
parse_hex_nibble_at_scan_ptr_bad:
    sec
    rts
.endif

patch_payload:
    lda payload_ptr
    sta scan_ptr
    lda payload_ptr+1
    sta scan_ptr+1
patch_payload_loop:
    lda scan_ptr
    cmp scan_end
    bne :+
    lda scan_ptr+1
    cmp scan_end+1
    bne :+
    jmp patch_payload_done
:
    jsr scan_ptr_before_end
    bcc :+
    jmp patch_payload_fail
:
    ldy #$00
    lda (scan_ptr),y
    ; Bootstrap stack/memory opcodes are not byte-compatible with Acheron.
    cmp #OPCODE_PUSH8
    bne :+
    jmp patch_payload_fail
:
    cmp #OPCODE_PUSH16
    bne :+
    jmp patch_payload_fail
:
    cmp #OPCODE_STORE
    bne :+
    jmp patch_payload_fail
:
    cmp #OPCODE_LOAD
    bne :+
    jmp patch_payload_fail
:
    cmp #OPCODE_NATIVE
    bne :+
    jmp patch_payload_done
:
    cmp #OPCODE_RET
    bne :+
    jmp patch_zero_arg
:
    cmp #OPCODE_CLRP
    bne :+
    jmp patch_zero_arg
:
    cmp #OPCODE_SETP8
    bne :+
    jmp patch_byte_arg
:
    cmp #OPCODE_GROW
    bne :+
    jmp patch_byte_arg
:
    cmp #OPCODE_MOVEP
    bne :+
    jmp patch_byte_arg
:
    cmp #OPCODE_COPYR
    bne :+
    jmp patch_byte_arg
:
    cmp #OPCODE_CALL
    bne :+
    jmp patch_word_arg
:
    cmp #OPCODE_JUMP
    bne :+
    jmp patch_word_arg
:
    cmp #OPCODE_SETP16
    bne :+
    jmp patch_setp16
:
    cmp #OPCODE_CALLN
    bne :+
    jmp patch_calln
:
    sec
    rts

patch_zero_arg:
    lda #$01
    jsr advance_scan_ptr
    jmp patch_payload_loop

patch_byte_arg:
    jsr ensure_scan_room_2
    bcc :+
    jmp patch_payload_fail
:
    lda #$02
    jsr advance_scan_ptr
    jmp patch_payload_loop

patch_word_arg:
    jsr ensure_scan_room_3
    bcc :+
    jmp patch_payload_fail
:
    ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    clc
    lda word_tmp
    adc payload_ptr
    sta word_tmp
    lda word_tmp+1
    adc payload_ptr+1
    sta word_tmp+1
    ldy #$01
    lda word_tmp
    sta (scan_ptr),y
    iny
    lda word_tmp+1
    sta (scan_ptr),y
    lda #$03
    jsr advance_scan_ptr
    jmp patch_payload_loop

patch_setp16:
    jsr ensure_scan_room_3
    bcc :+
    jmp patch_payload_fail
:
    ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    clc
    lda word_tmp
    adc payload_ptr
    sta word_tmp
    lda word_tmp+1
    adc payload_ptr+1
    sta word_tmp+1
    ldy #$01
    lda word_tmp
    sta (scan_ptr),y
    iny
    lda word_tmp+1
    sta (scan_ptr),y
    lda #$03
    jsr advance_scan_ptr
    jmp patch_payload_loop

patch_calln:
    jsr ensure_scan_room_3
    bcc :+
    jmp patch_payload_fail
:
    ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    lda word_tmp
    cmp #<INTRINSIC_PRINT
    bne patch_check_printe
    lda word_tmp+1
    cmp #>INTRINSIC_PRINT
    bne patch_check_printe
    jmp patch_calln_print
patch_check_printe:
    lda word_tmp
    cmp #<INTRINSIC_PRINTE
    bne patch_check_printi
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTE
    bne patch_check_printi
    jmp patch_calln_printe
patch_check_printi:
    lda word_tmp
    cmp #<INTRINSIC_PRINTI
    bne patch_check_printie
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTI
    bne patch_check_printie
    jmp patch_calln_printi
patch_check_printie:
    lda word_tmp
    cmp #<INTRINSIC_PRINTIE
    bne patch_check_linked_print
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTIE
    bne patch_check_linked_print
    jmp patch_calln_printie
patch_check_linked_print:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_PRINT
    bne patch_check_linked_printe
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_PRINT
    bne patch_check_linked_printe
    jmp patch_calln_linked_print
patch_check_linked_printe:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_PRINTE
    bne patch_check_linked_printi
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_PRINTE
    bne patch_check_linked_printi
    jmp patch_calln_linked_printe
patch_check_linked_printi:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_PRINTI
    bne patch_check_linked_printie
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_PRINTI
    bne patch_check_linked_printie
    jmp patch_calln_linked_printi
patch_check_linked_printie:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_PRINTIE
    bne patch_check_printreal
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_PRINTIE
    bne patch_check_printreal
    jmp patch_calln_linked_printie
patch_check_printreal:
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_MATH_FABS
    bne :+
    lda word_tmp
    cmp #<INTRINSIC_LINKED_MATH_FABS
    bne :+
    jmp patch_calln_linked_math_fabs
:
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_MATH_FSQRT
    bne :+
    lda word_tmp
    cmp #<INTRINSIC_LINKED_MATH_FSQRT
    bne :+
    jmp patch_calln_linked_math_fsqrt
:
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_DBF_CREATE
    bne :+
    lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_CREATE
    bne :+
    jmp patch_calln_linked_dbf_create
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_CURRRECNO
    bne :+
    jmp patch_calln_linked_dbf_currrecno
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_TOTALRECS
    bne :+
    jmp patch_calln_linked_dbf_totalrecs
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_CLOSE
    bne :+
    jmp patch_calln_linked_dbf_close
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_OPEN
    bne :+
    jmp patch_calln_linked_dbf_open
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_APPENDBLANK
    bne :+
    jmp patch_calln_linked_dbf_appendblank
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_GO
    bne :+
    jmp patch_calln_linked_dbf_go
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_READFIELD
    bne :+
    jmp patch_calln_linked_dbf_readfield
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_WRITEFIELD
    bne :+
    jmp patch_calln_linked_dbf_writefield
:
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_ON
    bne :+
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_ON
    bne :+
    jmp patch_calln_linked_gfx_bitmap_on
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_OFF
    bne :+
    jmp patch_calln_linked_gfx_bitmap_off
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_MBITMAP_ON
    bne :+
    jmp patch_calln_linked_gfx_mbitmap_on
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BG_COLOR
    bne :+
    jmp patch_calln_linked_gfx_bg_color
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BORDER_COLOR
    bne :+
    jmp patch_calln_linked_gfx_border_color
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_VIC_BANK
    bne :+
    jmp patch_calln_linked_gfx_vic_bank
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_SCREEN_BASE
    bne :+
    jmp patch_calln_linked_gfx_screen_base
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_BASE
    bne :+
    jmp patch_calln_linked_gfx_bitmap_base
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_FILL
    bne :+
    jmp patch_calln_linked_gfx_bitmap_fill
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_SCREEN_CELL
    bne :+
    jmp patch_calln_linked_gfx_screen_cell
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_COLOR_CELL
    bne :+
    jmp patch_calln_linked_gfx_color_cell
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_SHOW
    bne :+
    jmp patch_calln_linked_gfx_bitmap_show
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_HIDE
    bne :+
    jmp patch_calln_linked_gfx_bitmap_hide
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_COPY
    bne :+
    jmp patch_calln_linked_gfx_bitmap_copy
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_SCREEN_COPY
    bne :+
    jmp patch_calln_linked_gfx_screen_copy
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_COLOR_COPY
    bne :+
    jmp patch_calln_linked_gfx_color_copy
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_CELL_COLORS
    bne :+
    jmp patch_calln_linked_gfx_bitmap_cell_colors
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_CELL_DATA
    bne :+
    jmp patch_calln_linked_gfx_bitmap_cell_data
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_BLIT
    bne :+
    jmp patch_calln_linked_gfx_bitmap_blit
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILE_DRAW
    bne :+
    jmp patch_calln_linked_gfx_tile_draw
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILE_RECT_FILL
    bne :+
    jmp patch_calln_linked_gfx_tile_rect_fill
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_MASK_BLIT
    bne :+
    jmp patch_calln_linked_gfx_bitmap_mask_blit
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILE_MASK_DRAW
    bne :+
    jmp patch_calln_linked_gfx_tile_mask_draw
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILESET_DRAW
    bne :+
    jmp patch_calln_linked_gfx_tileset_draw
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILESET_RECT_FILL
    bne :+
    jmp patch_calln_linked_gfx_tileset_rect_fill
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILESET_MASK_DRAW
    bne :+
    jmp patch_calln_linked_gfx_tileset_mask_draw
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILESET_MASK_RECT_FILL
    bne :+
    jmp patch_calln_linked_gfx_tileset_mask_rect_fill
:   lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SPRITE_ON
    bne patch_check_linked_printreal
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SPRITE_ON
    bne :+
    jmp patch_calln_linked_sidspr_sprite_on
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SPRITE_OFF
    bne :+
    jmp patch_calln_linked_sidspr_sprite_off
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SPRITE_POS
    bne :+
    jmp patch_calln_linked_sidspr_sprite_pos
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SPRITE_DATA
    bne :+
    jmp patch_calln_linked_sidspr_sprite_data
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SPRITE_COLOR
    bne :+
    jmp patch_calln_linked_sidspr_sprite_color
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_FREQ
    bne :+
    jmp patch_calln_linked_sidspr_sid_freq
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_WAVE
    bne :+
    jmp patch_calln_linked_sidspr_sid_wave
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_AD
    bne :+
    jmp patch_calln_linked_sidspr_sid_ad
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_SR
    bne :+
    jmp patch_calln_linked_sidspr_sid_sr
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_ON
    bne :+
    jmp patch_calln_linked_sidspr_sid_on
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_OFF
    bne :+
    jmp patch_calln_linked_sidspr_sid_off
:   lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_VOL
    bne :+
    jmp patch_calln_linked_sidspr_sid_vol
:   jmp patch_payload_fail
patch_check_linked_printreal:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_PRINTREAL
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_PRINTREAL
    bne :+
    jmp patch_calln_linked_printreal
:   lda word_tmp
    cmp #<INTRINSIC_PRINTREAL
    bne patch_check_exit_real
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTREAL
    bne patch_check_exit_real
    jmp patch_calln_printreal
patch_check_exit:
patch_check_exit_real:
    lda word_tmp
    cmp #<INTRINSIC_EXIT
    beq :+
    jmp patch_payload_fail
:
    lda word_tmp+1
    cmp #>INTRINSIC_EXIT
    beq :+
    jmp patch_payload_fail
:
    lda #<native_exit
    sta word_tmp
    lda #>native_exit
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_print:
    lda #<native_print
    sta word_tmp
    lda #>native_print
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_printe:
    lda #<native_printe
    sta word_tmp
    lda #>native_printe
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_printi:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_printi
    sta word_tmp
    lda #>native_printi
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_printie:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_printie
    sta word_tmp
    lda #>native_printie
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_print:
    jsr ensure_native_helper_printstd_loaded
    lda #<native_linked_print
    sta word_tmp
    lda #>native_linked_print
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_printe:
    jsr ensure_native_helper_printstd_loaded
    lda #<native_linked_printe
    sta word_tmp
    lda #>native_linked_printe
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_printi:
    jsr ensure_native_helper_printstd_loaded
    jmp patch_calln_printi
patch_calln_linked_printie:
    jsr ensure_native_helper_printstd_loaded
    jmp patch_calln_printie
patch_calln_printreal:
patch_calln_linked_printreal:
    lda #<native_printreal
    sta word_tmp
    lda #>native_printreal
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_math_fabs:
.if AVMRUN_COMPAT
    lda #<native_math_fabs
    sta word_tmp
    lda #>native_math_fabs
    sta word_tmp+1
.else
    lda #<fail_needs_compat
    sta word_tmp
    lda #>fail_needs_compat
    sta word_tmp+1
.endif
    jmp patch_calln_store
patch_calln_linked_math_fsqrt:
.if AVMRUN_COMPAT
    lda #<native_math_fsqrt
    sta word_tmp
    lda #>native_math_fsqrt
    sta word_tmp+1
.else
    lda #<fail_needs_compat
    sta word_tmp
    lda #>fail_needs_compat
    sta word_tmp+1
.endif
    jmp patch_calln_store
patch_calln_linked_dbf_create:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_dbf_create
    sta word_tmp
    lda #>native_dbf_create
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_dbf_currrecno:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_dbf_currrecno
    sta word_tmp
    lda #>native_dbf_currrecno
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_dbf_totalrecs:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_dbf_totalrecs
    sta word_tmp
    lda #>native_dbf_totalrecs
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_dbf_close:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_dbf_close
    sta word_tmp
    lda #>native_dbf_close
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_dbf_open:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_dbf_open
    sta word_tmp
    lda #>native_dbf_open
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_dbf_appendblank:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_dbf_appendblank
    sta word_tmp
    lda #>native_dbf_appendblank
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_dbf_go:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_dbf_go
    sta word_tmp
    lda #>native_dbf_go
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_dbf_readfield:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_dbf_readfield
    sta word_tmp
    lda #>native_dbf_readfield
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_dbf_writefield:
    jsr lower_previous_push16_to_setp16
    bcc :+
    jmp patch_payload_fail
:
    lda #<native_dbf_writefield
    sta word_tmp
    lda #>native_dbf_writefield
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_on:
    lda #<native_gfx_bitmap_on
    sta word_tmp
    lda #>native_gfx_bitmap_on
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_off:
    lda #<native_gfx_bitmap_off
    sta word_tmp
    lda #>native_gfx_bitmap_off
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_mbitmap_on:
    lda #<native_gfx_mbitmap_on
    sta word_tmp
    lda #>native_gfx_mbitmap_on
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bg_color:
    lda #<native_gfx_bg_color
    sta word_tmp
    lda #>native_gfx_bg_color
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_border_color:
    lda #<native_gfx_border_color
    sta word_tmp
    lda #>native_gfx_border_color
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_vic_bank:
    lda #<native_gfx_vic_bank
    sta word_tmp
    lda #>native_gfx_vic_bank
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_screen_base:
    lda #<native_gfx_screen_base
    sta word_tmp
    lda #>native_gfx_screen_base
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_base:
    lda #<native_gfx_bitmap_base
    sta word_tmp
    lda #>native_gfx_bitmap_base
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_fill:
    lda #<native_gfx_bitmap_fill
    sta word_tmp
    lda #>native_gfx_bitmap_fill
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_screen_cell:
    lda #<native_gfx_screen_cell
    sta word_tmp
    lda #>native_gfx_screen_cell
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_color_cell:
    lda #<native_gfx_color_cell
    sta word_tmp
    lda #>native_gfx_color_cell
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_show:
    lda #<native_gfx_bitmap_show
    sta word_tmp
    lda #>native_gfx_bitmap_show
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_hide:
    lda #<native_gfx_bitmap_hide
    sta word_tmp
    lda #>native_gfx_bitmap_hide
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_copy:
    lda #<native_gfx_bitmap_copy
    sta word_tmp
    lda #>native_gfx_bitmap_copy
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_screen_copy:
    lda #<native_gfx_screen_copy
    sta word_tmp
    lda #>native_gfx_screen_copy
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_color_copy:
    lda #<native_gfx_color_copy
    sta word_tmp
    lda #>native_gfx_color_copy
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_cell_colors:
    lda #<native_gfx_bitmap_cell_colors
    sta word_tmp
    lda #>native_gfx_bitmap_cell_colors
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_cell_data:
    lda #<native_gfx_bitmap_cell_data
    sta word_tmp
    lda #>native_gfx_bitmap_cell_data
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_blit:
    lda #<native_gfx_bitmap_blit
    sta word_tmp
    lda #>native_gfx_bitmap_blit
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_tile_draw:
    lda #<native_gfx_tile_draw
    sta word_tmp
    lda #>native_gfx_tile_draw
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_tile_rect_fill:
    lda #<native_gfx_tile_rect_fill
    sta word_tmp
    lda #>native_gfx_tile_rect_fill
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_bitmap_mask_blit:
    lda #<native_gfx_bitmap_mask_blit
    sta word_tmp
    lda #>native_gfx_bitmap_mask_blit
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_tile_mask_draw:
    lda #<native_gfx_tile_mask_draw
    sta word_tmp
    lda #>native_gfx_tile_mask_draw
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_tileset_draw:
    lda #<native_gfx_tileset_draw
    sta word_tmp
    lda #>native_gfx_tileset_draw
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_tileset_rect_fill:
    lda #<native_gfx_tileset_rect_fill
    sta word_tmp
    lda #>native_gfx_tileset_rect_fill
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_tileset_mask_draw:
    lda #<native_gfx_tileset_mask_draw
    sta word_tmp
    lda #>native_gfx_tileset_mask_draw
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_gfx_tileset_mask_rect_fill:
    lda #<native_gfx_tileset_mask_rect_fill
    sta word_tmp
    lda #>native_gfx_tileset_mask_rect_fill
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sprite_on:
    lda #<native_sidspr_sprite_on
    sta word_tmp
    lda #>native_sidspr_sprite_on
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sprite_off:
    lda #<native_sidspr_sprite_off
    sta word_tmp
    lda #>native_sidspr_sprite_off
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sprite_pos:
    lda #<native_sidspr_sprite_pos
    sta word_tmp
    lda #>native_sidspr_sprite_pos
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sprite_data:
    lda #<native_sidspr_sprite_data
    sta word_tmp
    lda #>native_sidspr_sprite_data
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sprite_color:
    lda #<native_sidspr_sprite_color
    sta word_tmp
    lda #>native_sidspr_sprite_color
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sid_freq:
    lda #<native_sidspr_sid_freq
    sta word_tmp
    lda #>native_sidspr_sid_freq
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sid_wave:
    lda #<native_sidspr_sid_wave
    sta word_tmp
    lda #>native_sidspr_sid_wave
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sid_ad:
    lda #<native_sidspr_sid_ad
    sta word_tmp
    lda #>native_sidspr_sid_ad
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sid_sr:
    lda #<native_sidspr_sid_sr
    sta word_tmp
    lda #>native_sidspr_sid_sr
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sid_on:
    lda #<native_sidspr_sid_on
    sta word_tmp
    lda #>native_sidspr_sid_on
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sid_off:
    lda #<native_sidspr_sid_off
    sta word_tmp
    lda #>native_sidspr_sid_off
    sta word_tmp+1
    jmp patch_calln_store
patch_calln_linked_sidspr_sid_vol:
    lda #<native_sidspr_sid_vol
    sta word_tmp
    lda #>native_sidspr_sid_vol
    sta word_tmp+1
patch_calln_store:
    ldy #$01
    lda word_tmp
    sta (scan_ptr),y
    iny
    lda word_tmp+1
    sta (scan_ptr),y
    lda #$03
    jsr advance_scan_ptr
    jmp patch_payload_loop

patch_payload_done:
    clc
    rts

patch_payload_fail:
    sec
    rts

ensure_native_helper_printstd_loaded:
    lda #$FF
    sta native_helper_irq_saved
    lda native_helper_ready_flags
    and #AVM_NATIVE_HELPER_KIND_PRINTSTD
    beq :+
    clc
    rts
:
    lda scan_ptr
    pha
    lda scan_ptr+1
    pha
    lda scan_end
    pha
    lda scan_end+1
    pha
    lda payload_end_ptr
    sta src_ptr
    lda payload_end_ptr+1
    sta src_ptr+1
    jsr native_helper_trailer_has_header
    bcc :+
    jmp ensure_native_helper_printstd_loaded_fail
:
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr native_helper_require_src_byte
    bcc :+
    jmp ensure_native_helper_printstd_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta digit_flag
    jsr advance_src_ptr
ensure_native_helper_printstd_loaded_loop:
    lda digit_flag
    bne :+
    jmp ensure_native_helper_printstd_loaded_fail
:
    dec digit_flag
    jsr native_helper_require_src_header
    bcc :+
    jmp ensure_native_helper_printstd_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta hex_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp+1
    jsr advance_src_ptr
    jsr native_helper_require_src_len
    bcc :+
    jmp ensure_native_helper_printstd_loaded_fail
:
    lda hex_tmp
    cmp #AVM_NATIVE_HELPER_KIND_PRINTSTD
    bne ensure_native_helper_printstd_loaded_skip
    lda word_tmp
    sta native_helper_expected_len
    lda word_tmp+1
    sta native_helper_expected_len+1
    php
    pla
    and #$04
    sta native_helper_irq_saved
    sei
    jsr copy_native_helper_printstd_to_exec
    bcc :+
    jmp ensure_native_helper_printstd_loaded_fail_irq
:
    jsr validate_loaded_native_helper_printstd
    bcc :+
    jmp ensure_native_helper_printstd_loaded_fail_irq
:
    lda native_helper_ready_flags
    ora #AVM_NATIVE_HELPER_KIND_PRINTSTD
    sta native_helper_ready_flags
    jmp ensure_native_helper_printstd_loaded_ok_irq
ensure_native_helper_printstd_loaded_skip:
    jsr advance_src_ptr_by_word_tmp
    bcc ensure_native_helper_printstd_loaded_loop
ensure_native_helper_printstd_loaded_ok:
    pla
    sta scan_end+1
    pla
    sta scan_end
    pla
    sta scan_ptr+1
    pla
    sta scan_ptr
    clc
    rts
ensure_native_helper_printstd_loaded_ok_irq:
    pla
    sta scan_end+1
    pla
    sta scan_end
    pla
    sta scan_ptr+1
    pla
    sta scan_ptr
    clc
    rts
ensure_native_helper_printstd_loaded_fail:
    pla
    sta scan_end+1
    pla
    sta scan_end
    pla
    sta scan_ptr+1
    pla
    sta scan_ptr
    sec
    rts
ensure_native_helper_printstd_loaded_fail_irq:
    pla
    sta scan_end+1
    pla
    sta scan_end
    pla
    sta scan_ptr+1
    pla
    sta scan_ptr
    sec
    rts

ensure_native_helper_printreal_loaded:
    lda #$FF
    sta native_helper_irq_saved
    lda payload_end_ptr
    sta src_ptr
    lda payload_end_ptr+1
    sta src_ptr+1
    jsr native_helper_trailer_has_header
    bcc :+
    jmp ensure_native_helper_printreal_loaded_fail
:
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr native_helper_require_src_byte
    bcc :+
    jmp ensure_native_helper_printreal_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta digit_flag
    jsr advance_src_ptr
ensure_native_helper_printreal_loaded_loop:
    lda digit_flag
    bne :+
    jmp ensure_native_helper_printreal_loaded_fail
:
    dec digit_flag
    jsr native_helper_require_src_header
    bcc :+
    jmp ensure_native_helper_printreal_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta hex_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp+1
    jsr advance_src_ptr
    jsr native_helper_require_src_len
    bcc :+
    jmp ensure_native_helper_printreal_loaded_fail
:
    lda hex_tmp
    cmp #AVM_NATIVE_HELPER_KIND_PRINTREAL
    bne ensure_native_helper_printreal_loaded_skip
    lda word_tmp
    sta native_helper_expected_len
    lda word_tmp+1
    sta native_helper_expected_len+1
    php
    pla
    and #$04
    sta native_helper_irq_saved
    sei
    jsr copy_native_helper_printreal_to_exec
    bcc :+
    jmp ensure_native_helper_printreal_loaded_fail_irq
:   jsr validate_loaded_native_helper_printreal
    bcc :+
    jmp ensure_native_helper_printreal_loaded_fail_irq
:
ensure_native_helper_printreal_loaded_ok_irq:
    clc
    rts
ensure_native_helper_printreal_loaded_fail_irq:
    sec
    rts
ensure_native_helper_printreal_loaded_ok:
    clc
    rts
ensure_native_helper_printreal_loaded_skip:
    jsr advance_src_ptr_by_word_tmp
    bcs :+
    jmp ensure_native_helper_printreal_loaded_loop
:
ensure_native_helper_printreal_loaded_fail:
    sec
    rts

ensure_native_helper_gfx_loaded:
    lda #$FF
    sta native_helper_irq_saved
    lda payload_end_ptr
    sta src_ptr
    lda payload_end_ptr+1
    sta src_ptr+1
    jsr native_helper_trailer_has_header
    bcc :+
    jmp ensure_native_helper_gfx_loaded_fail
:
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr native_helper_require_src_byte
    bcc :+
    jmp ensure_native_helper_gfx_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta digit_flag
    jsr advance_src_ptr
ensure_native_helper_gfx_loaded_loop:
    lda digit_flag
    bne :+
    jmp ensure_native_helper_gfx_loaded_fail
:
    dec digit_flag
    jsr native_helper_require_src_header
    bcc :+
    jmp ensure_native_helper_gfx_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta hex_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp+1
    jsr advance_src_ptr
    jsr native_helper_require_src_len
    bcc :+
    jmp ensure_native_helper_gfx_loaded_fail
:
    lda hex_tmp
    cmp #AVM_NATIVE_HELPER_KIND_GFX
    bne ensure_native_helper_gfx_loaded_skip
    lda word_tmp
    sta native_helper_expected_len
    lda word_tmp+1
    sta native_helper_expected_len+1
    php
    pla
    and #$04
    sta native_helper_irq_saved
    sei
    jsr copy_native_helper_gfx_to_exec
    bcc :+
    jmp ensure_native_helper_gfx_loaded_fail_irq
	:   jsr validate_loaded_native_helper_gfx
	    bcc :+
	    jmp ensure_native_helper_gfx_loaded_fail_irq
	:
.if AVMRUN_NATIVE_HELPER_GFX_BASE = AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
	    lda native_helper_ready_flags
	    and #($FF ^ AVM_NATIVE_HELPER_KIND_PRINTSTD)
	    sta native_helper_ready_flags
.endif
	    clc
	    rts
ensure_native_helper_gfx_loaded_skip:
    jsr advance_src_ptr_by_word_tmp
    bcs :+
    jmp ensure_native_helper_gfx_loaded_loop
:
ensure_native_helper_gfx_loaded_fail:
    sec
    rts
ensure_native_helper_gfx_loaded_fail_irq:
    sec
    rts

ensure_native_helper_sidspr_loaded:
    lda #$FF
    sta native_helper_irq_saved
    lda payload_end_ptr
    sta src_ptr
    lda payload_end_ptr+1
    sta src_ptr+1
    jsr native_helper_trailer_has_header
    bcc :+
    jmp ensure_native_helper_sidspr_loaded_fail
:
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr native_helper_require_src_byte
    bcc :+
    jmp ensure_native_helper_sidspr_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta digit_flag
    jsr advance_src_ptr
ensure_native_helper_sidspr_loaded_loop:
    lda digit_flag
    bne :+
    jmp ensure_native_helper_sidspr_loaded_fail
:
    dec digit_flag
    jsr native_helper_require_src_header
    bcc :+
    jmp ensure_native_helper_sidspr_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta hex_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp+1
    jsr advance_src_ptr
    jsr native_helper_require_src_len
    bcc :+
    jmp ensure_native_helper_sidspr_loaded_fail
:
    lda hex_tmp
    cmp #AVM_NATIVE_HELPER_KIND_SIDSPR
    bne ensure_native_helper_sidspr_loaded_skip
    lda word_tmp
    sta native_helper_expected_len
    lda word_tmp+1
    sta native_helper_expected_len+1
    php
    pla
    and #$04
    sta native_helper_irq_saved
    sei
    jsr copy_native_helper_sidspr_to_exec
    bcc :+
    jmp ensure_native_helper_sidspr_loaded_fail_irq
	:   jsr validate_loaded_native_helper_sidspr
	    bcc :+
	    jmp ensure_native_helper_sidspr_loaded_fail_irq
	:
.if AVMRUN_NATIVE_HELPER_SIDSPR_BASE = AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
	    lda native_helper_ready_flags
	    and #($FF ^ AVM_NATIVE_HELPER_KIND_PRINTSTD)
	    sta native_helper_ready_flags
.endif
	    clc
	    rts
ensure_native_helper_sidspr_loaded_skip:
    jsr advance_src_ptr_by_word_tmp
    bcs :+
    jmp ensure_native_helper_sidspr_loaded_loop
:
ensure_native_helper_sidspr_loaded_fail:
    sec
    rts
ensure_native_helper_sidspr_loaded_fail_irq:
    sec
    rts

ensure_native_helper_dbf_loaded:
    lda #$FF
    sta native_helper_irq_saved
    lda payload_end_ptr
    sta src_ptr
    lda payload_end_ptr+1
    sta src_ptr+1
    jsr native_helper_trailer_has_header
    bcc :+
    jmp ensure_native_helper_dbf_loaded_fail
:
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr native_helper_require_src_byte
    bcc :+
    jmp ensure_native_helper_dbf_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta digit_flag
    jsr advance_src_ptr
ensure_native_helper_dbf_loaded_loop:
    lda digit_flag
    bne :+
    jmp ensure_native_helper_dbf_loaded_fail
:
    dec digit_flag
    jsr native_helper_require_src_header
    bcc :+
    jmp ensure_native_helper_dbf_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta hex_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp+1
    jsr advance_src_ptr
    jsr native_helper_require_src_len
    bcc :+
    jmp ensure_native_helper_dbf_loaded_fail
:
    lda hex_tmp
    cmp #AVM_NATIVE_HELPER_KIND_DBF
    bne ensure_native_helper_dbf_loaded_skip
    lda word_tmp
    sta native_helper_expected_len
    lda word_tmp+1
    sta native_helper_expected_len+1
    php
    pla
    and #$04
    sta native_helper_irq_saved
    sei
    jsr copy_native_helper_dbf_to_exec
    bcc :+
    jmp ensure_native_helper_dbf_loaded_fail_irq
:
    jsr validate_loaded_native_helper_dbf
    bcc :+
    jmp ensure_native_helper_dbf_loaded_fail_irq
:
.if AVMRUN_NATIVE_HELPER_DBF_BASE = AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    lda native_helper_ready_flags
    and #($FF ^ AVM_NATIVE_HELPER_KIND_PRINTSTD)
    sta native_helper_ready_flags
.endif
    clc
    rts
ensure_native_helper_dbf_loaded_skip:
    jsr advance_src_ptr_by_word_tmp
    bcs :+
    jmp ensure_native_helper_dbf_loaded_loop
:
ensure_native_helper_dbf_loaded_fail:
    sec
    rts
ensure_native_helper_dbf_loaded_fail_irq:
    sec
    rts

ensure_native_helper_math_loaded:
    lda #$FF
    sta native_helper_irq_saved
    lda payload_end_ptr
    sta src_ptr
    lda payload_end_ptr+1
    sta src_ptr+1
    jsr native_helper_trailer_has_header
    bcc :+
    jmp ensure_native_helper_math_loaded_fail
:
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr advance_src_ptr
    jsr native_helper_require_src_byte
    bcc :+
    jmp ensure_native_helper_math_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta digit_flag
    jsr advance_src_ptr
ensure_native_helper_math_loaded_loop:
    lda digit_flag
    bne :+
    jmp ensure_native_helper_math_loaded_fail
:
    dec digit_flag
    jsr native_helper_require_src_header
    bcc :+
    jmp ensure_native_helper_math_loaded_fail
:
    ldy #$00
    lda (src_ptr),y
    sta hex_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp
    jsr advance_src_ptr
    ldy #$00
    lda (src_ptr),y
    sta word_tmp+1
    jsr advance_src_ptr
    jsr native_helper_require_src_len
    bcc :+
    jmp ensure_native_helper_math_loaded_fail
:
    lda hex_tmp
    cmp #AVM_NATIVE_HELPER_KIND_MATH
    bne ensure_native_helper_math_loaded_skip
    lda word_tmp
    sta native_helper_expected_len
    lda word_tmp+1
    sta native_helper_expected_len+1
    php
    pla
    and #$04
    sta native_helper_irq_saved
    sei
    jsr copy_native_helper_math_to_exec
    bcc :+
    jmp ensure_native_helper_math_loaded_fail_irq
:
    jsr validate_loaded_native_helper_math
    bcc :+
    jmp ensure_native_helper_math_loaded_fail_irq
:
.if AVMRUN_NATIVE_HELPER_MATH_BASE = AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    lda native_helper_ready_flags
    and #($FF ^ AVM_NATIVE_HELPER_KIND_PRINTSTD)
    sta native_helper_ready_flags
.endif
    clc
    rts
ensure_native_helper_math_loaded_skip:
    jsr advance_src_ptr_by_word_tmp
    bcs :+
    jmp ensure_native_helper_math_loaded_loop
:
ensure_native_helper_math_loaded_fail:
    sec
    rts
ensure_native_helper_math_loaded_fail_irq:
    sec
    rts

native_helper_trailer_has_header:
    jsr native_helper_require_src_header
    bcs native_helper_trailer_has_header_fail
    ldy #$00
    lda (src_ptr),y
    cmp #AVM_HELPER_TRAILER_MAGIC_0
    bne native_helper_trailer_has_header_fail
    jsr native_helper_compare_src_byte_1
    cmp #AVM_HELPER_TRAILER_MAGIC_1
    bne native_helper_trailer_has_header_fail
    jsr native_helper_compare_src_byte_2
    cmp #AVM_HELPER_TRAILER_MAGIC_2
    bne native_helper_trailer_has_header_fail
    jsr native_helper_compare_src_byte_3
    cmp #AVM_HELPER_TRAILER_MAGIC_3
    bne native_helper_trailer_has_header_fail
    clc
    rts
native_helper_trailer_has_header_fail:
    sec
    rts

native_helper_compare_src_byte_1:
    ldy #$01
    lda (src_ptr),y
    rts

native_helper_compare_src_byte_2:
    ldy #$02
    lda (src_ptr),y
    rts

native_helper_compare_src_byte_3:
    ldy #$03
    lda (src_ptr),y
    rts

native_helper_require_src_header:
    lda #$04
    sta word_tmp
    lda #$00
    sta word_tmp+1
    jmp native_helper_require_src_len

native_helper_require_src_byte:
    lda #$01
    sta word_tmp
    lda #$00
    sta word_tmp+1
    jmp native_helper_require_src_len

native_helper_require_src_len:
    clc
    lda src_ptr
    adc word_tmp
    sta svc_retptr
    lda src_ptr+1
    adc word_tmp+1
    sta svc_retptr+1
    lda svc_retptr+1
    cmp file_end_ptr+1
    bcc native_helper_require_src_len_ok
    bne native_helper_require_src_len_fail
    lda svc_retptr
    cmp file_end_ptr
    bcc native_helper_require_src_len_ok
    beq native_helper_require_src_len_ok
native_helper_require_src_len_fail:
    sec
    rts
native_helper_require_src_len_ok:
    clc
    rts

advance_src_ptr:
    inc src_ptr
    bne :+
    inc src_ptr+1
:   clc
    rts

advance_src_ptr_by_word_tmp:
    lda word_tmp
    ora word_tmp+1
    beq advance_src_ptr_by_word_tmp_done
advance_src_ptr_by_word_tmp_loop:
    jsr advance_src_ptr
    dec word_tmp
    lda word_tmp
    cmp #$FF
    bne :+
    dec word_tmp+1
:   lda word_tmp
    ora word_tmp+1
    bne advance_src_ptr_by_word_tmp_loop
advance_src_ptr_by_word_tmp_done:
    clc
    rts

copy_native_helper_printreal_to_exec:
    lda word_tmp+1
    cmp #>AVMRUN_NATIVE_HELPER_PRINTREAL_SIZE
    bcc :+
    bne copy_native_helper_printreal_to_exec_fail
    lda word_tmp
    bne copy_native_helper_printreal_to_exec_fail
:   lda #<AVMRUN_NATIVE_HELPER_PRINTREAL_BASE
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_PRINTREAL_BASE
    sta svc_retptr+1
copy_native_helper_printreal_to_exec_loop:
    lda word_tmp
    ora word_tmp+1
    beq copy_native_helper_printreal_to_exec_done
    ldy #$00
    lda (src_ptr),y
    sta (svc_retptr),y
    jsr advance_src_ptr
    inc svc_retptr
    bne :+
    inc svc_retptr+1
:   dec word_tmp
    lda word_tmp
    cmp #$FF
    bne copy_native_helper_printreal_to_exec_loop
    dec word_tmp+1
    jmp copy_native_helper_printreal_to_exec_loop
copy_native_helper_printreal_to_exec_done:
    clc
    rts
copy_native_helper_printreal_to_exec_fail:
    sec
    rts

copy_native_helper_gfx_to_exec:
    lda word_tmp+1
    cmp #>AVMRUN_NATIVE_HELPER_GFX_SIZE
    bcc :+
    bne copy_native_helper_gfx_to_exec_fail
    lda word_tmp
    cmp #<AVMRUN_NATIVE_HELPER_GFX_SIZE
    bcc :+
    beq :+
    jmp copy_native_helper_gfx_to_exec_fail
:   lda #<AVMRUN_NATIVE_HELPER_GFX_BASE
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_GFX_BASE
    sta svc_retptr+1
copy_native_helper_gfx_to_exec_loop:
    lda word_tmp
    ora word_tmp+1
    beq copy_native_helper_gfx_to_exec_done
    ldy #$00
    lda (src_ptr),y
    sta (svc_retptr),y
    jsr advance_src_ptr
    inc svc_retptr
    bne :+
    inc svc_retptr+1
:   dec word_tmp
    lda word_tmp
    cmp #$FF
    bne copy_native_helper_gfx_to_exec_loop
    dec word_tmp+1
    jmp copy_native_helper_gfx_to_exec_loop
copy_native_helper_gfx_to_exec_done:
    clc
    rts
copy_native_helper_gfx_to_exec_fail:
    sec
    rts

copy_native_helper_sidspr_to_exec:
    lda word_tmp+1
    cmp #>AVMRUN_NATIVE_HELPER_SIDSPR_SIZE
    bcc :+
    bne copy_native_helper_sidspr_to_exec_fail
    lda word_tmp
    cmp #<AVMRUN_NATIVE_HELPER_SIDSPR_SIZE
    bcc :+
    beq :+
    jmp copy_native_helper_sidspr_to_exec_fail
:   lda #<AVMRUN_NATIVE_HELPER_SIDSPR_BASE
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_SIDSPR_BASE
    sta svc_retptr+1
copy_native_helper_sidspr_to_exec_loop:
    lda word_tmp
    ora word_tmp+1
    beq copy_native_helper_sidspr_to_exec_done
    ldy #$00
    lda (src_ptr),y
    sta (svc_retptr),y
    jsr advance_src_ptr
    inc svc_retptr
    bne :+
    inc svc_retptr+1
:   dec word_tmp
    lda word_tmp
    cmp #$FF
    bne copy_native_helper_sidspr_to_exec_loop
    dec word_tmp+1
    jmp copy_native_helper_sidspr_to_exec_loop
copy_native_helper_sidspr_to_exec_done:
    clc
    rts
copy_native_helper_sidspr_to_exec_fail:
    sec
    rts

copy_native_helper_dbf_to_exec:
    lda word_tmp+1
    cmp #>AVMRUN_NATIVE_HELPER_DBF_SIZE
    bcc :+
    bne copy_native_helper_dbf_to_exec_fail
    lda word_tmp
    cmp #<AVMRUN_NATIVE_HELPER_DBF_SIZE
    bcc :+
    beq :+
    jmp copy_native_helper_dbf_to_exec_fail
:   lda #<AVMRUN_NATIVE_HELPER_DBF_BASE
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_DBF_BASE
    sta svc_retptr+1
copy_native_helper_dbf_to_exec_loop:
    lda word_tmp
    ora word_tmp+1
    beq copy_native_helper_dbf_to_exec_done
    ldy #$00
    lda (src_ptr),y
    sta (svc_retptr),y
    jsr advance_src_ptr
    inc svc_retptr
    bne :+
    inc svc_retptr+1
:   dec word_tmp
    lda word_tmp
    cmp #$FF
    bne copy_native_helper_dbf_to_exec_loop
    dec word_tmp+1
    jmp copy_native_helper_dbf_to_exec_loop
copy_native_helper_dbf_to_exec_done:
    clc
    rts
copy_native_helper_dbf_to_exec_fail:
    sec
    rts

copy_native_helper_math_to_exec:
    lda word_tmp+1
    cmp #>AVMRUN_NATIVE_HELPER_MATH_SIZE
    bcc :+
    bne copy_native_helper_math_to_exec_fail
    lda word_tmp
    cmp #<AVMRUN_NATIVE_HELPER_MATH_SIZE
    bcc :+
    beq :+
    jmp copy_native_helper_math_to_exec_fail
:   lda #<AVMRUN_NATIVE_HELPER_MATH_BASE
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_MATH_BASE
    sta svc_retptr+1
copy_native_helper_math_to_exec_loop:
    lda word_tmp
    ora word_tmp+1
    beq copy_native_helper_math_to_exec_done
    ldy #$00
    lda (src_ptr),y
    sta (svc_retptr),y
    jsr advance_src_ptr
    inc svc_retptr
    bne :+
    inc svc_retptr+1
:   dec word_tmp
    lda word_tmp
    cmp #$FF
    bne copy_native_helper_math_to_exec_loop
    dec word_tmp+1
    jmp copy_native_helper_math_to_exec_loop
copy_native_helper_math_to_exec_done:
    clc
    rts
copy_native_helper_math_to_exec_fail:
    sec
    rts

copy_native_helper_printstd_to_exec:
    lda word_tmp+1
    cmp #>AVMRUN_NATIVE_HELPER_PRINTSTD_SIZE
    bcc :+
    bne copy_native_helper_printstd_to_exec_fail
    lda word_tmp
    cmp #<AVMRUN_NATIVE_HELPER_PRINTSTD_SIZE
    bcc :+
    beq :+
    jmp copy_native_helper_printstd_to_exec_fail
:   lda #<AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    sta svc_retptr+1
copy_native_helper_printstd_to_exec_loop:
    lda word_tmp
    ora word_tmp+1
    beq copy_native_helper_printstd_to_exec_done
    ldy #$00
    lda (src_ptr),y
    sta (svc_retptr),y
    jsr advance_src_ptr
    inc svc_retptr
    bne :+
    inc svc_retptr+1
:   dec word_tmp
    lda word_tmp
    cmp #$FF
    bne copy_native_helper_printstd_to_exec_loop
    dec word_tmp+1
    jmp copy_native_helper_printstd_to_exec_loop
copy_native_helper_printstd_to_exec_done:
    clc
    rts
copy_native_helper_printstd_to_exec_fail:
    sec
    rts

validate_loaded_native_helper_printreal:
    lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+0
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_0
    beq :+
    jmp validate_loaded_native_helper_printreal_fail
:   lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+1
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_1
    beq :+
    jmp validate_loaded_native_helper_printreal_fail
:   lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+2
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_2
    beq :+
    jmp validate_loaded_native_helper_printreal_fail
:   lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+3
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_3
    beq :+
    jmp validate_loaded_native_helper_printreal_fail
:   lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+4
    cmp #AVMRUN_NATIVE_HELPER_ABI_VERSION
    beq :+
    jmp validate_loaded_native_helper_printreal_fail
:   lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+5
    cmp #AVM_NATIVE_HELPER_KIND_PRINTREAL
    beq :+
    jmp validate_loaded_native_helper_printreal_fail
:   lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_LO
    cmp native_helper_expected_len
    beq :+
    jmp validate_loaded_native_helper_printreal_fail
:   lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_HI
    cmp native_helper_expected_len+1
    beq :+
    jmp validate_loaded_native_helper_printreal_fail
:   lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+AVMRUN_NATIVE_HELPER_HEADER_ENTRY_COUNT
    cmp #$02
    beq :+
    jmp validate_loaded_native_helper_printreal_fail
:   lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_LO
    sta word_tmp
    lda AVMRUN_NATIVE_HELPER_PRINTREAL_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_HI
    sta word_tmp+1
    lda #$02
    jsr validate_loaded_native_helper_table_in_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_printreal_fail
:   clc
    lda #<AVMRUN_NATIVE_HELPER_PRINTREAL_BASE
    adc word_tmp
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_PRINTREAL_BASE
    adc word_tmp+1
    sta svc_retptr+1
    ldy #$00
    lda (svc_retptr),y
    cmp #AVMRUN_NATIVE_HELPER_ENTRY_PRINTREAL_MAIN
    beq :+
    jmp validate_loaded_native_helper_printreal_fail
:   iny
    lda (svc_retptr),y
    sta word_tmp
    iny
    lda (svc_retptr),y
    sta word_tmp+1
    jsr validate_loaded_native_helper_offset_in_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_printreal_fail
:   clc
    lda #<AVMRUN_NATIVE_HELPER_PRINTREAL_BASE
    adc word_tmp
    sta native_helper_printreal_entry_ptr
    lda #>AVMRUN_NATIVE_HELPER_PRINTREAL_BASE
    adc word_tmp+1
    sta native_helper_printreal_entry_ptr+1
    clc
    rts
validate_loaded_native_helper_printreal_fail:
    sec
    rts

validate_loaded_native_helper_printstd:
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+0
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_0
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+1
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_1
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+2
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_2
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+3
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_3
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+4
    cmp #AVMRUN_NATIVE_HELPER_ABI_VERSION
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+5
    cmp #AVM_NATIVE_HELPER_KIND_PRINTSTD
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_LO
    cmp native_helper_expected_len
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_HI
    cmp native_helper_expected_len+1
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+AVMRUN_NATIVE_HELPER_HEADER_ENTRY_COUNT
    cmp #$04
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_LO
    sta word_tmp
    lda AVMRUN_NATIVE_HELPER_PRINTSTD_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_HI
    sta word_tmp+1
    lda #$04
    jsr validate_loaded_native_helper_table_in_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_printstd_fail
:   clc
    lda #<AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    adc word_tmp
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    adc word_tmp+1
    sta svc_retptr+1
    lda #$00
    sta hex_tmp
    lda #$04
    sta digit_flag
validate_loaded_native_helper_printstd_table_loop:
    lda digit_flag
    bne :+
    jmp validate_loaded_native_helper_printstd_table_done
:   ldy #$00
    lda (svc_retptr),y
    cmp #AVMRUN_NATIVE_HELPER_ENTRY_PRINTSTD_STR
    beq validate_loaded_native_helper_printstd_entry_str
    cmp #AVMRUN_NATIVE_HELPER_ENTRY_PRINTSTD_STR_NL
    beq validate_loaded_native_helper_printstd_entry_str_nl
    cmp #AVMRUN_NATIVE_HELPER_ENTRY_PRINTSTD_U16
    beq validate_loaded_native_helper_printstd_entry_u16
    cmp #AVMRUN_NATIVE_HELPER_ENTRY_PRINTSTD_U16_NL
    beq validate_loaded_native_helper_printstd_entry_u16_nl
    jmp validate_loaded_native_helper_printstd_fail
validate_loaded_native_helper_printstd_entry_str:
    lda hex_tmp
    and #$01
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:   jsr load_native_helper_entry_offset_from_svc_retptr
    bcc :+
    jmp validate_loaded_native_helper_printstd_fail
:   jsr store_printstd_ptr_from_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_printstd_fail
:   lda hex_tmp
    ora #$01
    sta hex_tmp
    jmp validate_loaded_native_helper_printstd_table_next
validate_loaded_native_helper_printstd_entry_str_nl:
    lda hex_tmp
    and #$02
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:   jsr load_native_helper_entry_offset_from_svc_retptr
    bcc :+
    jmp validate_loaded_native_helper_printstd_fail
:   jsr store_printstd_nl_ptr_from_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_printstd_fail
:   lda hex_tmp
    ora #$02
    sta hex_tmp
    jmp validate_loaded_native_helper_printstd_table_next
validate_loaded_native_helper_printstd_entry_u16:
    lda hex_tmp
    and #$04
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:   jsr load_native_helper_entry_offset_from_svc_retptr
    bcc :+
    jmp validate_loaded_native_helper_printstd_fail
:   jsr store_printstd_u16_ptr_from_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_printstd_fail
:   lda hex_tmp
    ora #$04
    sta hex_tmp
    jmp validate_loaded_native_helper_printstd_table_next
validate_loaded_native_helper_printstd_entry_u16_nl:
    lda hex_tmp
    and #$08
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:   jsr load_native_helper_entry_offset_from_svc_retptr
    bcc :+
    jmp validate_loaded_native_helper_printstd_fail
:   jsr store_printstd_u16_nl_ptr_from_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_printstd_fail
:   lda hex_tmp
    ora #$08
    sta hex_tmp
validate_loaded_native_helper_printstd_table_next:
    clc
    lda svc_retptr
    adc #AVMRUN_NATIVE_HELPER_ENTRY_RECORD_SIZE
    sta svc_retptr
    lda svc_retptr+1
    adc #$00
    sta svc_retptr+1
    dec digit_flag
    jmp validate_loaded_native_helper_printstd_table_loop
validate_loaded_native_helper_printstd_table_done:
    lda hex_tmp
    cmp #$0F
    beq :+
    jmp validate_loaded_native_helper_printstd_fail
:   clc
    rts
validate_loaded_native_helper_printstd_fail:
    sec
    rts

validate_loaded_native_helper_gfx:
    lda AVMRUN_NATIVE_HELPER_GFX_BASE+0
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_0
    beq :+
    jmp validate_loaded_native_helper_gfx_fail
:   lda AVMRUN_NATIVE_HELPER_GFX_BASE+1
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_1
    beq :+
    jmp validate_loaded_native_helper_gfx_fail
:   lda AVMRUN_NATIVE_HELPER_GFX_BASE+2
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_2
    beq :+
    jmp validate_loaded_native_helper_gfx_fail
:   lda AVMRUN_NATIVE_HELPER_GFX_BASE+3
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_3
    beq :+
    jmp validate_loaded_native_helper_gfx_fail
:   lda AVMRUN_NATIVE_HELPER_GFX_BASE+4
    cmp #AVMRUN_NATIVE_HELPER_ABI_VERSION
    beq :+
    jmp validate_loaded_native_helper_gfx_fail
:   lda AVMRUN_NATIVE_HELPER_GFX_BASE+5
    cmp #AVM_NATIVE_HELPER_KIND_GFX
    beq :+
    jmp validate_loaded_native_helper_gfx_fail
:   lda AVMRUN_NATIVE_HELPER_GFX_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_LO
    cmp native_helper_expected_len
    beq :+
    jmp validate_loaded_native_helper_gfx_fail
:   lda AVMRUN_NATIVE_HELPER_GFX_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_HI
    cmp native_helper_expected_len+1
    beq :+
    jmp validate_loaded_native_helper_gfx_fail
:   lda AVMRUN_NATIVE_HELPER_GFX_BASE+AVMRUN_NATIVE_HELPER_HEADER_ENTRY_COUNT
    cmp #$17
    beq :+
    jmp validate_loaded_native_helper_gfx_fail
:   lda AVMRUN_NATIVE_HELPER_GFX_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_LO
    sta word_tmp
    lda AVMRUN_NATIVE_HELPER_GFX_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_HI
    sta word_tmp+1
    lda #$17
    jsr validate_loaded_native_helper_table_in_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_gfx_fail
:   clc
    rts
validate_loaded_native_helper_gfx_fail:
    sec
    rts

validate_loaded_native_helper_sidspr:
    lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+0
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_0
    beq :+
    jmp validate_loaded_native_helper_sidspr_fail
:   lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+1
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_1
    beq :+
    jmp validate_loaded_native_helper_sidspr_fail
:   lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+2
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_2
    beq :+
    jmp validate_loaded_native_helper_sidspr_fail
:   lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+3
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_3
    beq :+
    jmp validate_loaded_native_helper_sidspr_fail
:   lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+4
    cmp #AVMRUN_NATIVE_HELPER_ABI_VERSION
    beq :+
    jmp validate_loaded_native_helper_sidspr_fail
:   lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+5
    cmp #AVM_NATIVE_HELPER_KIND_SIDSPR
    beq :+
    jmp validate_loaded_native_helper_sidspr_fail
:   lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_LO
    cmp native_helper_expected_len
    beq :+
    jmp validate_loaded_native_helper_sidspr_fail
:   lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_HI
    cmp native_helper_expected_len+1
    beq :+
    jmp validate_loaded_native_helper_sidspr_fail
:   lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+AVMRUN_NATIVE_HELPER_HEADER_ENTRY_COUNT
    cmp #$0C
    beq :+
    jmp validate_loaded_native_helper_sidspr_fail
:   lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_LO
    sta word_tmp
    lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_HI
    sta word_tmp+1
    lda #$0C
    jsr validate_loaded_native_helper_table_in_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_sidspr_fail
:   clc
    rts
validate_loaded_native_helper_sidspr_fail:
    sec
    rts

validate_loaded_native_helper_dbf:
    lda AVMRUN_NATIVE_HELPER_DBF_BASE+0
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_0
    beq :+
    jmp validate_loaded_native_helper_dbf_fail
:   lda AVMRUN_NATIVE_HELPER_DBF_BASE+1
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_1
    beq :+
    jmp validate_loaded_native_helper_dbf_fail
:   lda AVMRUN_NATIVE_HELPER_DBF_BASE+2
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_2
    beq :+
    jmp validate_loaded_native_helper_dbf_fail
:   lda AVMRUN_NATIVE_HELPER_DBF_BASE+3
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_3
    beq :+
    jmp validate_loaded_native_helper_dbf_fail
:   lda AVMRUN_NATIVE_HELPER_DBF_BASE+4
    cmp #AVMRUN_NATIVE_HELPER_ABI_VERSION
    beq :+
    jmp validate_loaded_native_helper_dbf_fail
:   lda AVMRUN_NATIVE_HELPER_DBF_BASE+5
    cmp #AVM_NATIVE_HELPER_KIND_DBF
    beq :+
    jmp validate_loaded_native_helper_dbf_fail
:   lda AVMRUN_NATIVE_HELPER_DBF_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_LO
    cmp native_helper_expected_len
    beq :+
    jmp validate_loaded_native_helper_dbf_fail
:   lda AVMRUN_NATIVE_HELPER_DBF_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_HI
    cmp native_helper_expected_len+1
    beq :+
    jmp validate_loaded_native_helper_dbf_fail
:   lda AVMRUN_NATIVE_HELPER_DBF_BASE+AVMRUN_NATIVE_HELPER_HEADER_ENTRY_COUNT
    cmp #$09
    beq :+
    jmp validate_loaded_native_helper_dbf_fail
:   lda AVMRUN_NATIVE_HELPER_DBF_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_LO
    sta word_tmp
    lda AVMRUN_NATIVE_HELPER_DBF_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_HI
    sta word_tmp+1
    lda #$09
    jsr validate_loaded_native_helper_table_in_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_dbf_fail
:   clc
    rts
validate_loaded_native_helper_dbf_fail:
    sec
    rts

validate_loaded_native_helper_math:
    lda AVMRUN_NATIVE_HELPER_MATH_BASE+0
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_0
    beq :+
    jmp validate_loaded_native_helper_math_fail
:   lda AVMRUN_NATIVE_HELPER_MATH_BASE+1
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_1
    beq :+
    jmp validate_loaded_native_helper_math_fail
:   lda AVMRUN_NATIVE_HELPER_MATH_BASE+2
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_2
    beq :+
    jmp validate_loaded_native_helper_math_fail
:   lda AVMRUN_NATIVE_HELPER_MATH_BASE+3
    cmp #AVMRUN_NATIVE_HELPER_MAGIC_3
    beq :+
    jmp validate_loaded_native_helper_math_fail
:   lda AVMRUN_NATIVE_HELPER_MATH_BASE+4
    cmp #AVMRUN_NATIVE_HELPER_ABI_VERSION
    beq :+
    jmp validate_loaded_native_helper_math_fail
:   lda AVMRUN_NATIVE_HELPER_MATH_BASE+5
    cmp #AVM_NATIVE_HELPER_KIND_MATH
    beq :+
    jmp validate_loaded_native_helper_math_fail
:   lda AVMRUN_NATIVE_HELPER_MATH_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_LO
    cmp native_helper_expected_len
    beq :+
    jmp validate_loaded_native_helper_math_fail
:   lda AVMRUN_NATIVE_HELPER_MATH_BASE+AVMRUN_NATIVE_HELPER_HEADER_TOTAL_LEN_HI
    cmp native_helper_expected_len+1
    beq :+
    jmp validate_loaded_native_helper_math_fail
:   lda AVMRUN_NATIVE_HELPER_MATH_BASE+AVMRUN_NATIVE_HELPER_HEADER_ENTRY_COUNT
    cmp #$02
    beq :+
    jmp validate_loaded_native_helper_math_fail
:   lda AVMRUN_NATIVE_HELPER_MATH_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_LO
    sta word_tmp
    lda AVMRUN_NATIVE_HELPER_MATH_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_HI
    sta word_tmp+1
    lda #$02
    jsr validate_loaded_native_helper_table_in_word_tmp
    bcc :+
    jmp validate_loaded_native_helper_math_fail
:   clc
    rts
validate_loaded_native_helper_math_fail:
    sec
    rts

validate_loaded_native_helper_offset_in_word_tmp:
    lda word_tmp+1
    bne :+
    lda word_tmp
    cmp #AVMRUN_NATIVE_HELPER_HEADER_SIZE
    bcs :+
    sec
    rts
:   lda word_tmp+1
    cmp native_helper_expected_len+1
    bcc :+
    bne validate_loaded_native_helper_offset_in_word_tmp_fail
    lda word_tmp
    cmp native_helper_expected_len
    bcc :+
validate_loaded_native_helper_offset_in_word_tmp_fail:
    sec
    rts
:   clc
    rts

validate_loaded_native_helper_table_in_word_tmp:
    pha
    jsr validate_loaded_native_helper_offset_in_word_tmp
    bcs validate_loaded_native_helper_table_in_word_tmp_fail_pop
    lda word_tmp
    sta svc_retptr
    lda word_tmp+1
    sta svc_retptr+1
    pla
    sta digit_flag
validate_loaded_native_helper_table_in_word_tmp_loop:
    lda digit_flag
    beq validate_loaded_native_helper_table_in_word_tmp_compare
    clc
    lda svc_retptr
    adc #AVMRUN_NATIVE_HELPER_ENTRY_RECORD_SIZE
    sta svc_retptr
    lda svc_retptr+1
    adc #$00
    sta svc_retptr+1
    dec digit_flag
    jmp validate_loaded_native_helper_table_in_word_tmp_loop
validate_loaded_native_helper_table_in_word_tmp_compare:
    lda svc_retptr+1
    cmp native_helper_expected_len+1
    bcc validate_loaded_native_helper_table_in_word_tmp_ok
    bne validate_loaded_native_helper_table_in_word_tmp_fail
    lda svc_retptr
    cmp native_helper_expected_len
    bcc validate_loaded_native_helper_table_in_word_tmp_ok
    beq validate_loaded_native_helper_table_in_word_tmp_ok
validate_loaded_native_helper_table_in_word_tmp_fail:
    sec
    rts
validate_loaded_native_helper_table_in_word_tmp_ok:
    clc
    rts
validate_loaded_native_helper_table_in_word_tmp_fail_pop:
    pla
    sec
    rts

load_native_helper_entry_offset_from_svc_retptr:
    ldy #$01
    lda (svc_retptr),y
    sta word_tmp
    iny
    lda (svc_retptr),y
    sta word_tmp+1
    jmp validate_loaded_native_helper_offset_in_word_tmp

resolve_loaded_native_helper_sidspr_entry_to_word_tmp:
    pha
    lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_LO
    sta word_tmp
    lda AVMRUN_NATIVE_HELPER_SIDSPR_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_HI
    sta word_tmp+1
    lda #$0C
    jsr validate_loaded_native_helper_table_in_word_tmp
    bcc :+
    pla
    sec
    rts
:   pla
    sta digit_flag
    clc
    lda #<AVMRUN_NATIVE_HELPER_SIDSPR_BASE
    adc word_tmp
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_SIDSPR_BASE
    adc word_tmp+1
    sta svc_retptr+1
    lda #$0C
    sta hex_tmp
resolve_loaded_native_helper_sidspr_entry_loop:
    lda hex_tmp
    beq resolve_loaded_native_helper_sidspr_entry_fail
    ldy #$00
    lda (svc_retptr),y
    cmp digit_flag
    beq resolve_loaded_native_helper_sidspr_entry_found
    clc
    lda svc_retptr
    adc #AVMRUN_NATIVE_HELPER_ENTRY_RECORD_SIZE
    sta svc_retptr
    lda svc_retptr+1
    adc #$00
    sta svc_retptr+1
    dec hex_tmp
    jmp resolve_loaded_native_helper_sidspr_entry_loop
resolve_loaded_native_helper_sidspr_entry_found:
    jsr load_native_helper_entry_offset_from_svc_retptr
    bcc :+
    sec
    rts
:   clc
    lda #<AVMRUN_NATIVE_HELPER_SIDSPR_BASE
    adc word_tmp
    sta word_tmp
    lda #>AVMRUN_NATIVE_HELPER_SIDSPR_BASE
    adc word_tmp+1
    sta word_tmp+1
    clc
    rts
resolve_loaded_native_helper_sidspr_entry_fail:
    sec
    rts

resolve_loaded_native_helper_gfx_entry_to_word_tmp:
    pha
    lda AVMRUN_NATIVE_HELPER_GFX_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_LO
    sta word_tmp
    lda AVMRUN_NATIVE_HELPER_GFX_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_HI
    sta word_tmp+1
    lda #$17
    jsr validate_loaded_native_helper_table_in_word_tmp
    bcc :+
    pla
    sec
    rts
:   pla
    sta digit_flag
    clc
    lda #<AVMRUN_NATIVE_HELPER_GFX_BASE
    adc word_tmp
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_GFX_BASE
    adc word_tmp+1
    sta svc_retptr+1
    lda #$17
    sta hex_tmp
resolve_loaded_native_helper_gfx_entry_loop:
    lda hex_tmp
    beq resolve_loaded_native_helper_gfx_entry_fail
    ldy #$00
    lda (svc_retptr),y
    cmp digit_flag
    beq resolve_loaded_native_helper_gfx_entry_found
    clc
    lda svc_retptr
    adc #AVMRUN_NATIVE_HELPER_ENTRY_RECORD_SIZE
    sta svc_retptr
    lda svc_retptr+1
    adc #$00
    sta svc_retptr+1
    dec hex_tmp
    jmp resolve_loaded_native_helper_gfx_entry_loop
resolve_loaded_native_helper_gfx_entry_found:
    jsr load_native_helper_entry_offset_from_svc_retptr
    bcc :+
    sec
    rts
:   clc
    lda #<AVMRUN_NATIVE_HELPER_GFX_BASE
    adc word_tmp
    sta word_tmp
    lda #>AVMRUN_NATIVE_HELPER_GFX_BASE
    adc word_tmp+1
    sta word_tmp+1
    clc
    rts
resolve_loaded_native_helper_gfx_entry_fail:
    sec
    rts

resolve_loaded_native_helper_dbf_entry_to_word_tmp:
    pha
    lda AVMRUN_NATIVE_HELPER_DBF_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_LO
    sta word_tmp
    lda AVMRUN_NATIVE_HELPER_DBF_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_HI
    sta word_tmp+1
    lda #$09
    jsr validate_loaded_native_helper_table_in_word_tmp
    bcc :+
    pla
    sec
    rts
:   pla
    sta digit_flag
    clc
    lda #<AVMRUN_NATIVE_HELPER_DBF_BASE
    adc word_tmp
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_DBF_BASE
    adc word_tmp+1
    sta svc_retptr+1
    lda #$09
    sta hex_tmp
resolve_loaded_native_helper_dbf_entry_loop:
    lda hex_tmp
    beq resolve_loaded_native_helper_dbf_entry_fail
    ldy #$00
    lda (svc_retptr),y
    cmp digit_flag
    beq resolve_loaded_native_helper_dbf_entry_found
    clc
    lda svc_retptr
    adc #AVMRUN_NATIVE_HELPER_ENTRY_RECORD_SIZE
    sta svc_retptr
    lda svc_retptr+1
    adc #$00
    sta svc_retptr+1
    dec hex_tmp
    jmp resolve_loaded_native_helper_dbf_entry_loop
resolve_loaded_native_helper_dbf_entry_found:
    jsr load_native_helper_entry_offset_from_svc_retptr
    bcc :+
    sec
    rts
:   clc
    lda #<AVMRUN_NATIVE_HELPER_DBF_BASE
    adc word_tmp
    sta word_tmp
    lda #>AVMRUN_NATIVE_HELPER_DBF_BASE
    adc word_tmp+1
    sta word_tmp+1
    clc
    rts
resolve_loaded_native_helper_dbf_entry_fail:
    sec
    rts

resolve_loaded_native_helper_math_entry_to_word_tmp:
    pha
    lda AVMRUN_NATIVE_HELPER_MATH_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_LO
    sta word_tmp
    lda AVMRUN_NATIVE_HELPER_MATH_BASE+AVMRUN_NATIVE_HELPER_HEADER_TABLE_OFF_HI
    sta word_tmp+1
    lda #$02
    jsr validate_loaded_native_helper_table_in_word_tmp
    bcc :+
    pla
    sec
    rts
:   pla
    sta digit_flag
    clc
    lda #<AVMRUN_NATIVE_HELPER_MATH_BASE
    adc word_tmp
    sta svc_retptr
    lda #>AVMRUN_NATIVE_HELPER_MATH_BASE
    adc word_tmp+1
    sta svc_retptr+1
    lda #$02
    sta hex_tmp
resolve_loaded_native_helper_math_entry_loop:
    lda hex_tmp
    beq resolve_loaded_native_helper_math_entry_fail
    ldy #$00
    lda (svc_retptr),y
    cmp digit_flag
    beq resolve_loaded_native_helper_math_entry_found
    clc
    lda svc_retptr
    adc #AVMRUN_NATIVE_HELPER_ENTRY_RECORD_SIZE
    sta svc_retptr
    lda svc_retptr+1
    adc #$00
    sta svc_retptr+1
    dec hex_tmp
    jmp resolve_loaded_native_helper_math_entry_loop
resolve_loaded_native_helper_math_entry_found:
    jsr load_native_helper_entry_offset_from_svc_retptr
    bcc :+
    sec
    rts
:   clc
    lda #<AVMRUN_NATIVE_HELPER_MATH_BASE
    adc word_tmp
    sta word_tmp
    lda #>AVMRUN_NATIVE_HELPER_MATH_BASE
    adc word_tmp+1
    sta word_tmp+1
    clc
    rts
resolve_loaded_native_helper_math_entry_fail:
    sec
    rts

store_printstd_ptr_from_word_tmp:
    clc
    lda #<AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    adc word_tmp
    sta native_helper_printstd_entry_ptr
    lda #>AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    adc word_tmp+1
    sta native_helper_printstd_entry_ptr+1
    clc
    rts

store_printstd_nl_ptr_from_word_tmp:
    clc
    lda #<AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    adc word_tmp
    sta native_helper_printstd_entry_nl_ptr
    lda #>AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    adc word_tmp+1
    sta native_helper_printstd_entry_nl_ptr+1
    clc
    rts

store_printstd_u16_ptr_from_word_tmp:
    clc
    lda #<AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    adc word_tmp
    sta native_helper_printstd_entry_u16_ptr
    lda #>AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    adc word_tmp+1
    sta native_helper_printstd_entry_u16_ptr+1
    clc
    rts

store_printstd_u16_nl_ptr_from_word_tmp:
    clc
    lda #<AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    adc word_tmp
    sta native_helper_printstd_entry_u16_nl_ptr
    lda #>AVMRUN_NATIVE_HELPER_PRINTSTD_BASE
    adc word_tmp+1
    sta native_helper_printstd_entry_u16_nl_ptr+1
    clc
    rts

.if AVMRUN_COMPAT
interpret_payload:
    lda #AVMRUN_OVERLAY_CMD_INTERP_START
    sta avmrun_overlay_requested_cmd
interpret_payload_overlay_loop:
    lda #AVMRUN_OVERLAY_KIND_INTERP
    sta avmrun_overlay_requested_kind
    jsr avmrun_overlay_call_loaded
    bcs interpret_payload_fail
    lda avmrun_interp_result
    cmp #AVMRUN_INTERP_RESULT_DONE_OK
    beq interpret_payload_done
    cmp #AVMRUN_INTERP_RESULT_DONE_FAIL
    beq interpret_payload_fail
    cmp #AVMRUN_INTERP_RESULT_SERVICE
    bne interpret_payload_fail
    lda avmrun_interp_service_kind
    cmp #AVMRUN_OVERLAY_KIND_PRINT
    beq interpret_payload_service_print
    cmp #AVMRUN_OVERLAY_KIND_REALOPS
    beq interpret_payload_service_realops
    jmp interpret_payload_fail
interpret_payload_service_print:
    lda avmrun_interp_service_cmd
    jsr avmrun_overlay_call_print
    bcc interpret_payload_service_resume_ok
    bcs interpret_payload_service_resume_fail
interpret_payload_service_realops:
    lda avmrun_interp_service_cmd
    jsr avmrun_overlay_call_realops
    bcc interpret_payload_service_resume_ok
interpret_payload_service_resume_fail:
    lda #$01
    sta avmrun_interp_service_failed
    lda #AVMRUN_OVERLAY_CMD_INTERP_RESUME
    sta avmrun_overlay_requested_cmd
    jmp interpret_payload_overlay_loop
interpret_payload_service_resume_ok:
    lda #$00
    sta avmrun_interp_service_failed
    lda #AVMRUN_OVERLAY_CMD_INTERP_RESUME
    sta avmrun_overlay_requested_cmd
    jmp interpret_payload_overlay_loop
interpret_payload_done:
    clc
    rts
interpret_payload_fail:
    sec
    rts
.endif

lower_previous_push16_to_setp16:
    sec
    lda scan_ptr
    sbc #$03
    sta word_tmp
    lda scan_ptr+1
    sbc #$00
    sta word_tmp+1
    lda word_tmp+1
    cmp payload_ptr+1
    bcc lower_previous_push16_to_setp16_fail
    bne :+
    lda word_tmp
    cmp payload_ptr
    bcc lower_previous_push16_to_setp16_fail
:  ldy #$00
    lda (word_tmp),y
    cmp #OPCODE_PUSH16
    beq :+
    cmp #OPCODE_SETP16
    beq lower_previous_push16_to_setp16_ok
    bne lower_previous_push16_to_setp16_fail
:
    lda #OPCODE_SETP16
    sta (word_tmp),y
lower_previous_push16_to_setp16_ok:
    clc
    rts
lower_previous_push16_to_setp16_fail:
    sec
    rts

scan_ptr_before_end:
    lda scan_ptr+1
    cmp scan_end+1
    bcc scan_ptr_before_end_ok
    bne scan_ptr_before_end_fail
    lda scan_ptr
    cmp scan_end
    bcc scan_ptr_before_end_ok
scan_ptr_before_end_fail:
    sec
    rts
scan_ptr_before_end_ok:
    clc
    rts

ensure_scan_room_3:
    clc
    lda scan_ptr
    adc #$03
    sta word_tmp
    lda scan_ptr+1
    adc #$00
    sta word_tmp+1
    lda word_tmp+1
    cmp scan_end+1
    bcc ensure_scan_room_3_ok
    bne ensure_scan_room_3_fail
    lda word_tmp
    cmp scan_end
    bcc ensure_scan_room_3_ok
    beq ensure_scan_room_3_ok
ensure_scan_room_3_fail:
    sec
    rts
ensure_scan_room_3_ok:
    clc
    rts

ensure_scan_room_2:
    clc
    lda scan_ptr
    adc #$02
    sta word_tmp
    lda scan_ptr+1
    adc #$00
    sta word_tmp+1
    lda word_tmp+1
    cmp scan_end+1
    bcc ensure_scan_room_2_ok
    bne ensure_scan_room_2_fail
    lda word_tmp
    cmp scan_end
    bcc ensure_scan_room_2_ok
    beq ensure_scan_room_2_ok
ensure_scan_room_2_fail:
    sec
    rts
ensure_scan_room_2_ok:
    clc
    rts

advance_scan_ptr:
    clc
    adc scan_ptr
    sta scan_ptr
    bcc :+
    inc scan_ptr+1
:
    rts

native_print:
    jsr ensure_native_helper_printstd_loaded
    ldx pptr
.if AVMRUN_COMPAT
    bcs native_print_fallback
    jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    jmp (native_helper_printstd_entry_ptr)
native_print_fallback:
    jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    lda #AVMRUN_OVERLAY_CMD_PRINT_STRING
    jsr avmrun_overlay_call_print
    rts
.else
    bcc :+
    jsr restore_native_helper_irq_state
    jmp fail_needs_compat
:   jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    jmp (native_helper_printstd_entry_ptr)
.endif

native_linked_print:
    jsr ensure_native_helper_printstd_loaded
    ldx pptr
.if AVMRUN_COMPAT
    bcs native_linked_print_fallback
    jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    jsr resolve_svc_retptr_to_absolute_if_relative
    jmp (native_helper_printstd_entry_ptr)
native_linked_print_fallback:
    jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    jsr resolve_svc_retptr_to_absolute_if_relative
    lda #AVMRUN_OVERLAY_CMD_PRINT_STRING
    jsr avmrun_overlay_call_print
    rts
.else
    bcc :+
    jsr restore_native_helper_irq_state
    jmp fail_needs_compat
:   jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    jsr resolve_svc_retptr_to_absolute_if_relative
    jmp (native_helper_printstd_entry_ptr)
.endif

native_printe:
    jsr ensure_native_helper_printstd_loaded
    ldx pptr
.if AVMRUN_COMPAT
    bcs native_printe_fallback
    jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    jmp (native_helper_printstd_entry_nl_ptr)
native_printe_fallback:
    jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    lda #AVMRUN_OVERLAY_CMD_PRINT_STRING_NL
    jsr avmrun_overlay_call_print
    rts
.else
    bcc :+
    jsr restore_native_helper_irq_state
    jmp fail_needs_compat
:   jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    jmp (native_helper_printstd_entry_nl_ptr)
.endif

native_linked_printe:
    jsr ensure_native_helper_printstd_loaded
    ldx pptr
.if AVMRUN_COMPAT
    bcs native_linked_printe_fallback
    jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    jsr resolve_svc_retptr_to_absolute_if_relative
    jmp (native_helper_printstd_entry_nl_ptr)
native_linked_printe_fallback:
    jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    jsr resolve_svc_retptr_to_absolute_if_relative
    lda #AVMRUN_OVERLAY_CMD_PRINT_STRING_NL
    jsr avmrun_overlay_call_print
    rts
.else
    bcc :+
    jsr restore_native_helper_irq_state
    jmp fail_needs_compat
:   jsr restore_native_helper_irq_state
    jsr load_svc_retptr_from_x
    jsr resolve_svc_retptr_to_absolute_if_relative
    jmp (native_helper_printstd_entry_nl_ptr)
.endif

native_printi:
    jsr ensure_native_helper_printstd_loaded
    ldx pptr
.if AVMRUN_COMPAT
    bcc :+
    jsr restore_native_helper_irq_state
    jsr load_word_tmp_from_x
    lda #AVMRUN_OVERLAY_CMD_PRINT_U16
    jsr avmrun_overlay_call_print
    rts
:   jsr restore_native_helper_irq_state
    jmp (native_helper_printstd_entry_u16_ptr)
.else
    bcc :+
    jsr restore_native_helper_irq_state
    jmp fail_needs_compat
:   jsr restore_native_helper_irq_state
    jmp (native_helper_printstd_entry_u16_ptr)
.endif

native_printie:
    jsr ensure_native_helper_printstd_loaded
    ldx pptr
.if AVMRUN_COMPAT
    bcc :+
    jsr restore_native_helper_irq_state
    jsr load_word_tmp_from_x
    lda #AVMRUN_OVERLAY_CMD_PRINT_U16_NL
    jsr avmrun_overlay_call_print
    rts
:   jsr restore_native_helper_irq_state
    jmp (native_helper_printstd_entry_u16_nl_ptr)
.else
    bcc :+
    jsr restore_native_helper_irq_state
    jmp fail_needs_compat
:   jsr restore_native_helper_irq_state
    jmp (native_helper_printstd_entry_u16_nl_ptr)
.endif

native_printreal:
    jsr ensure_native_helper_printreal_loaded
    ldx pptr
.if AVMRUN_COMPAT
    bcs native_printreal_fallback
    jsr native_helper_printreal_jsr_entry
    jsr restore_native_helper_irq_state
    rts
native_printreal_fallback:
    jsr restore_native_helper_irq_state
    lda 0,x
    sta real_print_flag
    lda 2,x
    sta real_print_high
    lda 3,x
    sta real_print_high+1
    lda 4,x
    sta real_print_low
    lda 5,x
    sta real_print_low+1
    lda #AVMRUN_OVERLAY_CMD_PRINT_REAL
    jsr avmrun_overlay_call_print
    rts
.else
    bcc :+
    jsr restore_native_helper_irq_state
    jmp fail_needs_compat
:
    jsr native_helper_printreal_jsr_entry
    jsr restore_native_helper_irq_state
    rts
.endif

native_gfx_bitmap_on:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_ON
    jmp native_gfx_call_entry_a

native_gfx_bitmap_off:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_OFF
    jmp native_gfx_call_entry_a

native_gfx_mbitmap_on:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_MBITMAP_ON
    jmp native_gfx_call_entry_a

native_gfx_bg_color:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BG_COLOR
    jmp native_gfx_call_entry_a

native_gfx_border_color:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BORDER_COLOR
    jmp native_gfx_call_entry_a

native_gfx_vic_bank:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_VIC_BANK
    jmp native_gfx_call_entry_a

native_gfx_screen_base:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_SCREEN_BASE
    jmp native_gfx_call_entry_a

native_gfx_bitmap_base:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_BASE
    jmp native_gfx_call_entry_a

native_gfx_bitmap_fill:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_FILL
    jmp native_gfx_call_entry_a

native_gfx_screen_cell:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_SCREEN_CELL
    jmp native_gfx_call_entry_a

native_gfx_color_cell:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_COLOR_CELL
    jmp native_gfx_call_entry_a

native_gfx_bitmap_show:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_SHOW
    jmp native_gfx_call_entry_a

native_gfx_bitmap_hide:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_HIDE
    jmp native_gfx_call_entry_a

native_gfx_bitmap_copy:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_COPY
    jmp native_gfx_call_entry_a

native_gfx_screen_copy:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_SCREEN_COPY
    jmp native_gfx_call_entry_a

native_gfx_color_copy:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_COLOR_COPY
    jmp native_gfx_call_entry_a

native_gfx_bitmap_cell_colors:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_CELL_COLORS
    jmp native_gfx_call_entry_a

native_gfx_bitmap_cell_data:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_CELL_DATA
    jmp native_gfx_call_entry_a

native_gfx_bitmap_blit:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_BLIT
    jmp native_gfx_call_entry_a

native_gfx_tile_draw:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_TILE_DRAW
    jmp native_gfx_call_entry_a

native_gfx_tile_rect_fill:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_TILE_RECT_FILL
    jmp native_gfx_call_entry_a

native_gfx_bitmap_mask_blit:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_MASK_BLIT
    jmp native_gfx_call_entry_a

native_gfx_tile_mask_draw:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_GFX_TILE_MASK_DRAW
    jmp native_gfx_call_entry_a

native_gfx_tileset_draw:
    ldx pptr
    jsr load_svc_retptr_from_x
    lda 2,x
    sta file_params+2
    lda 3,x
    sta file_params+3
    lda 4,x
    sta file_params+4
    lda 5,x
    sta file_params+5
    lda file_params+5
    beq :+
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
:   ldy #$00
    lda (svc_retptr),y
    sta file_params+8
    cmp file_params+4
    bcc :+
    beq :+
    jmp native_gfx_tileset_draw_index_ok
:   lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
native_gfx_tileset_draw_index_ok:
    clc
    lda svc_retptr
    adc #$02
    sta word_tmp
    lda svc_retptr+1
    adc #$00
    sta word_tmp+1
    ldy #$00
    lda (word_tmp),y
    sta file_params+6
    iny
    lda (word_tmp),y
    sta hex_tmp
    lda #$00
    sta entry_ptr
    sta entry_ptr+1
native_gfx_tileset_draw_mul_loop:
    lda hex_tmp
    beq native_gfx_tileset_draw_mul_done
    clc
    lda entry_ptr
    adc file_params+6
    sta entry_ptr
    lda entry_ptr+1
    adc #$00
    sta entry_ptr+1
    dec hex_tmp
    jmp native_gfx_tileset_draw_mul_loop
native_gfx_tileset_draw_mul_done:
    lda entry_ptr
    sta file_params+6
    lda entry_ptr+1
    sta file_params+7
    lda entry_ptr
    sta svc_retptr
    lda entry_ptr+1
    sta svc_retptr+1
    asl svc_retptr
    rol svc_retptr+1
    lda entry_ptr
    sta hex_tmp
    lda entry_ptr+1
    sta digit_flag
    asl hex_tmp
    rol digit_flag
    asl hex_tmp
    rol digit_flag
    asl hex_tmp
    rol digit_flag
    clc
    lda hex_tmp
    adc svc_retptr
    sta file_params+6
    lda digit_flag
    adc svc_retptr+1
    sta file_params+7
    clc
    lda file_params+6
    adc #$02
    sta file_params+6
    lda file_params+7
    adc #$00
    sta file_params+7
    lda file_params+4
    sta hex_tmp
native_gfx_tileset_draw_tile_loop:
    lda hex_tmp
    beq native_gfx_tileset_draw_tile_ptr_ready
    clc
    lda word_tmp
    adc file_params+6
    sta word_tmp
    lda word_tmp+1
    adc file_params+7
    sta word_tmp+1
    dec hex_tmp
    jmp native_gfx_tileset_draw_tile_loop
native_gfx_tileset_draw_tile_ptr_ready:
    lda word_tmp
    sta file_params+0
    lda word_tmp+1
    sta file_params+1
    lda #<file_params
    sta pptr
    lda #>file_params
    sta pptr+1
    jsr native_gfx_tile_draw
    rts

native_gfx_tileset_rect_fill:
    ldx pptr
    jsr load_svc_retptr_from_x
    lda 2,x
    sta file_params+2
    lda 3,x
    sta file_params+3
    lda 4,x
    sta file_params+4
    lda 5,x
    sta file_params+5
    lda 6,x
    sta file_params+6
    lda 7,x
    sta file_params+7
    lda file_params+7
    beq :+
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
:   ldy #$00
    lda (svc_retptr),y
    sta file_params+8
    cmp file_params+6
    bcc :+
    beq :+
    jmp native_gfx_tileset_rect_fill_index_ok
:   lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
native_gfx_tileset_rect_fill_index_ok:
    clc
    lda svc_retptr
    adc #$02
    sta word_tmp
    lda svc_retptr+1
    adc #$00
    sta word_tmp+1
    lda file_params+6
    beq native_gfx_tileset_rect_fill_tile_ptr_ready
native_gfx_tileset_rect_fill_tile_loop:
    clc
    lda word_tmp
    adc #$0A
    sta word_tmp
    lda word_tmp+1
    adc #$00
    sta word_tmp+1
    dec file_params+6
    bne native_gfx_tileset_rect_fill_tile_loop
native_gfx_tileset_rect_fill_tile_ptr_ready:
    lda word_tmp
    sta file_params+0
    lda word_tmp+1
    sta file_params+1
    lda #<file_params
    sta pptr
    lda #>file_params
    sta pptr+1
    jsr native_gfx_tile_rect_fill
    rts

native_gfx_tileset_mask_draw:
    ldx pptr
    jsr load_svc_retptr_from_x
    lda 2,x
    sta file_params+2
    lda 3,x
    sta file_params+3
    lda 4,x
    sta file_params+4
    lda 5,x
    sta file_params+5
    lda file_params+5
    beq :+
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
:   ldy #$00
    lda (svc_retptr),y
    sta file_params+8
    cmp file_params+4
    bcc :+
    beq :+
    jmp native_gfx_tileset_mask_draw_index_ok
:   lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
native_gfx_tileset_mask_draw_index_ok:
    clc
    lda svc_retptr
    adc #$02
    sta word_tmp
    lda svc_retptr+1
    adc #$00
    sta word_tmp+1
    ldy #$00
    lda (word_tmp),y
    sta file_params+6
    iny
    lda (word_tmp),y
    sta hex_tmp
    lda #$00
    sta entry_ptr
    sta entry_ptr+1
native_gfx_tileset_mask_draw_mul_loop:
    lda hex_tmp
    beq native_gfx_tileset_mask_draw_mul_done
    clc
    lda entry_ptr
    adc file_params+6
    sta entry_ptr
    lda entry_ptr+1
    adc #$00
    sta entry_ptr+1
    dec hex_tmp
    jmp native_gfx_tileset_mask_draw_mul_loop
native_gfx_tileset_mask_draw_mul_done:
    lda entry_ptr
    sta file_params+6
    lda entry_ptr+1
    sta file_params+7
    lda entry_ptr
    sta svc_retptr
    lda entry_ptr+1
    sta svc_retptr+1
    asl svc_retptr
    rol svc_retptr+1
    lda entry_ptr
    sta hex_tmp
    lda entry_ptr+1
    sta digit_flag
    asl hex_tmp
    rol digit_flag
    asl hex_tmp
    rol digit_flag
    asl hex_tmp
    rol digit_flag
    asl hex_tmp
    rol digit_flag
    clc
    lda hex_tmp
    adc svc_retptr
    sta file_params+6
    lda digit_flag
    adc svc_retptr+1
    sta file_params+7
    clc
    lda file_params+6
    adc #$02
    sta file_params+6
    lda file_params+7
    adc #$00
    sta file_params+7
    lda file_params+4
    sta hex_tmp
native_gfx_tileset_mask_draw_tile_loop:
    lda hex_tmp
    beq native_gfx_tileset_mask_draw_tile_ptr_ready
    clc
    lda word_tmp
    adc file_params+6
    sta word_tmp
    lda word_tmp+1
    adc file_params+7
    sta word_tmp+1
    dec hex_tmp
    jmp native_gfx_tileset_mask_draw_tile_loop
native_gfx_tileset_mask_draw_tile_ptr_ready:
    lda word_tmp
    sta file_params+0
    lda word_tmp+1
    sta file_params+1
    lda #<file_params
    sta pptr
    lda #>file_params
    sta pptr+1
    jsr native_gfx_tile_mask_draw
    rts

native_gfx_tileset_mask_rect_fill:
    ldx pptr
    jsr load_svc_retptr_from_x
    lda 2,x
    sta gfx_tileset_row_start_x
    sta file_params+2
    lda 3,x
    sta file_params+3
    lda 4,x
    sta gfx_tileset_repeat_x
    lda 5,x
    sta gfx_tileset_repeat_y
    lda 6,x
    sta gfx_tileset_tile_index
    lda 7,x
    beq :+
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
:   ldy #$00
    lda (svc_retptr),y
    cmp 6,x
    bcc :+
    beq :+
    jmp native_gfx_tileset_mask_rect_fill_index_ok
:   lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
native_gfx_tileset_mask_rect_fill_index_ok:
    clc
    lda svc_retptr
    adc #$02
    sta word_tmp
    lda svc_retptr+1
    adc #$00
    sta word_tmp+1
    ldy #$00
    lda (word_tmp),y
    sta file_params+4
    iny
    lda (word_tmp),y
    sta hex_tmp
    lda #$00
    sta entry_ptr
    sta entry_ptr+1
native_gfx_tileset_mask_rect_fill_mul_loop:
    lda hex_tmp
    beq native_gfx_tileset_mask_rect_fill_mul_done
    clc
    lda entry_ptr
    adc file_params+4
    sta entry_ptr
    lda entry_ptr+1
    adc #$00
    sta entry_ptr+1
    dec hex_tmp
    jmp native_gfx_tileset_mask_rect_fill_mul_loop
native_gfx_tileset_mask_rect_fill_mul_done:
    lda entry_ptr
    sta file_params+6
    lda entry_ptr+1
    sta file_params+7
    lda entry_ptr
    sta svc_retptr
    lda entry_ptr+1
    sta svc_retptr+1
    asl svc_retptr
    rol svc_retptr+1
    lda entry_ptr
    sta hex_tmp
    lda entry_ptr+1
    sta digit_flag
    asl hex_tmp
    rol digit_flag
    asl hex_tmp
    rol digit_flag
    asl hex_tmp
    rol digit_flag
    asl hex_tmp
    rol digit_flag
    clc
    lda hex_tmp
    adc svc_retptr
    sta file_params+6
    lda digit_flag
    adc svc_retptr+1
    sta file_params+7
    clc
    lda file_params+6
    adc #$02
    sta file_params+6
    lda file_params+7
    adc #$00
    sta file_params+7
    lda gfx_tileset_tile_index
    sta hex_tmp
native_gfx_tileset_mask_rect_fill_tile_loop:
    lda hex_tmp
    beq native_gfx_tileset_mask_rect_fill_tile_ptr_ready
    clc
    lda word_tmp
    adc file_params+6
    sta word_tmp
    lda word_tmp+1
    adc file_params+7
    sta word_tmp+1
    dec hex_tmp
    jmp native_gfx_tileset_mask_rect_fill_tile_loop
native_gfx_tileset_mask_rect_fill_tile_ptr_ready:
    lda word_tmp
    sta gfx_tileset_tile_ptr
    lda word_tmp+1
    sta gfx_tileset_tile_ptr+1
    ldy #$00
    lda (word_tmp),y
    sta gfx_tileset_step_x
    iny
    lda (word_tmp),y
    sta gfx_tileset_step_y
    lda gfx_tileset_repeat_y
    beq native_gfx_tileset_mask_rect_fill_done
native_gfx_tileset_mask_rect_fill_row_loop:
    lda gfx_tileset_row_start_x
    sta file_params+2
    lda gfx_tileset_repeat_x
    sta gfx_tileset_col_count
    lda gfx_tileset_col_count
    beq native_gfx_tileset_mask_rect_fill_row_next
native_gfx_tileset_mask_rect_fill_col_loop:
    lda gfx_tileset_tile_ptr
    sta file_params+0
    lda gfx_tileset_tile_ptr+1
    sta file_params+1
    lda #<file_params
    sta pptr
    lda #>file_params
    sta pptr+1
    jsr native_gfx_tile_mask_draw
    clc
    lda file_params+2
    adc gfx_tileset_step_x
    sta file_params+2
    dec gfx_tileset_col_count
    bne native_gfx_tileset_mask_rect_fill_col_loop
native_gfx_tileset_mask_rect_fill_row_next:
    clc
    lda file_params+3
    adc gfx_tileset_step_y
    sta file_params+3
    dec gfx_tileset_repeat_y
    bne native_gfx_tileset_mask_rect_fill_row_loop
native_gfx_tileset_mask_rect_fill_done:
    rts

native_gfx_call_entry_a:
    pha
    jsr ensure_native_helper_gfx_loaded
    bcc :+
    pla
    jsr restore_native_helper_irq_state
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
:   pla
    jsr resolve_loaded_native_helper_gfx_entry_to_word_tmp
    bcc :+
    jsr restore_native_helper_irq_state
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
:   jsr restore_native_helper_irq_state
    ldx pptr
    jmp (word_tmp)

native_math_fabs:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_MATH_FABS
    jmp native_math_call_entry_a

native_math_fsqrt:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_MATH_FSQRT
    jmp native_math_call_entry_a

native_math_call_entry_a:
    pha
    jsr ensure_native_helper_math_loaded
    bcc :+
    pla
    jsr restore_native_helper_irq_state
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
:   pla
    jsr resolve_loaded_native_helper_math_entry_to_word_tmp
    bcc :+
    jsr restore_native_helper_irq_state
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
:   ldx pptr
    jsr call_word_tmp
    jsr restore_native_helper_irq_state
    rts

native_sidspr_sprite_on:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SPRITE_ON
    jmp native_sidspr_call_entry_a

native_sidspr_sprite_off:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SPRITE_OFF
    jmp native_sidspr_call_entry_a

native_sidspr_sprite_pos:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SPRITE_POS
    jmp native_sidspr_call_entry_a

native_sidspr_sprite_data:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SPRITE_DATA
    jmp native_sidspr_call_entry_a

native_sidspr_sprite_color:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SPRITE_COLOR
    jmp native_sidspr_call_entry_a

native_sidspr_sid_freq:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_FREQ
    jmp native_sidspr_call_entry_a

native_sidspr_sid_wave:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_WAVE
    jmp native_sidspr_call_entry_a

native_sidspr_sid_ad:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_AD
    jmp native_sidspr_call_entry_a

native_sidspr_sid_sr:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_SR
    jmp native_sidspr_call_entry_a

native_sidspr_sid_on:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_ON
    jmp native_sidspr_call_entry_a

native_sidspr_sid_off:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_OFF
    jmp native_sidspr_call_entry_a

native_sidspr_sid_vol:
    lda #AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_VOL
    jmp native_sidspr_call_entry_a

native_sidspr_call_entry_a:
    pha
    jsr ensure_native_helper_sidspr_loaded
    bcc :+
    pla
    jsr restore_native_helper_irq_state
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
:   pla
    jsr resolve_loaded_native_helper_sidspr_entry_to_word_tmp
    bcc :+
    jsr restore_native_helper_irq_state
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jmp fail_with_ptr
:   jsr restore_native_helper_irq_state
    ldx pptr
    jmp (word_tmp)

native_dbf_create:
    jsr native_dbf_prepare_request_ptr
    jsr native_dbf_load_request_path_to_word_tmp
    lda #DBF_FILE_MAGIC_0
    sta dbf_header_magic0
    lda #DBF_FILE_MAGIC_1
    sta dbf_header_magic1
    lda #DBF_FILE_MAGIC_2
    sta dbf_header_magic2
    lda #DBF_FILE_MAGIC_3
    sta dbf_header_magic3
    ldy #DBF_REQ_FIELD_COUNT
    lda (svc_retptr),y
    sta dbf_header_field_lo
    iny
    lda (svc_retptr),y
    sta dbf_header_field_hi
    lda #$00
    sta dbf_header_total_lo
    sta dbf_header_total_hi
    sta dbf_header_curr_lo
    sta dbf_header_curr_hi
    lda #<DBF_PATH_SCRATCH_BASE
    sta file_params+0
    lda #>DBF_PATH_SCRATCH_BASE
    sta file_params+1
    lda #<dbf_header_magic0
    sta file_params+2
    lda #>dbf_header_magic0
    sta file_params+3
    lda #<DBF_FILE_HEADER_LEN
    sta file_params+4
    lda #>DBF_FILE_HEADER_LEN
    sta file_params+5
    lda #tool_file_status_fail
    sta file_params+6
    jsr set_tool_mem_config
    ldx #file_params
    jsr svc_file_save_sc0
    jsr set_runtime_mem_config
    lda file_params+6
    cmp #tool_file_status_ok
    beq :+
    lda #$00
    sta dbf_active_handle
    jmp native_dbf_fail_request
:   lda #$01
    sta dbf_active_handle
    jmp native_dbf_store_request_from_header

native_dbf_open:
    jsr native_dbf_prepare_request_ptr
    jsr native_dbf_load_request_path_to_word_tmp
    lda #<DBF_PATH_SCRATCH_BASE
    sta file_params+0
    lda #>DBF_PATH_SCRATCH_BASE
    sta file_params+1
    lda #<dbf_file_buffer
    sta file_params+2
    lda #>dbf_file_buffer
    sta file_params+3
    lda #<DBF_FILE_BUFFER_SIZE
    sta file_params+4
    lda #>DBF_FILE_BUFFER_SIZE
    sta file_params+5
    lda #$00
    sta file_params+6
    sta file_params+7
    sta file_params+8
    jsr set_tool_mem_config
    ldx #file_params
    jsr svc_file_load_sc0
    jsr set_runtime_mem_config
    lda file_params+6
    cmp #tool_file_status_ok
    bne native_dbf_open_fail
    lda file_params+8
    bne :+
    lda file_params+7
    cmp #DBF_FILE_HEADER_LEN
    bcc native_dbf_open_fail
:   lda dbf_file_buffer+0
    cmp #DBF_FILE_MAGIC_0
    bne native_dbf_open_fail
    lda dbf_file_buffer+1
    cmp #DBF_FILE_MAGIC_1
    bne native_dbf_open_fail
    lda dbf_file_buffer+2
    cmp #DBF_FILE_MAGIC_2
    bne native_dbf_open_fail
    lda dbf_file_buffer+3
    cmp #DBF_FILE_MAGIC_3
    bne native_dbf_open_fail
    jsr native_dbf_copy_header_from_file_buffer
    lda #$01
    sta dbf_active_handle
    jmp native_dbf_store_request_from_header
native_dbf_open_fail:
    lda #$00
    sta dbf_active_handle
    jmp native_dbf_fail_request

native_dbf_currrecno:
    jsr native_dbf_prepare_request_ptr
    jsr native_dbf_validate_handle
    bcc :+
    jmp native_dbf_fail_request
:   jmp native_dbf_store_request_from_header

native_dbf_totalrecs:
    jsr native_dbf_prepare_request_ptr
    jsr native_dbf_validate_handle
    bcc :+
    jmp native_dbf_fail_request
:   jmp native_dbf_store_request_from_header

native_dbf_close:
    jsr native_dbf_prepare_request_ptr
    ldy #DBF_REQ_HANDLE
    lda (svc_retptr),y
    cmp dbf_active_handle
    beq :+
    jmp native_dbf_fail_request
:   lda dbf_active_handle
    bne :+
    jmp native_dbf_fail_request
:   lda #$00
    sta dbf_active_handle
    sta (svc_retptr),y
    ldy #DBF_REQ_STATUS
    lda #$01
    sta (svc_retptr),y
    rts

native_dbf_appendblank:
    jsr native_dbf_prepare_request_ptr
    jsr native_dbf_validate_handle
    bcc :+
    jmp native_dbf_fail_request
:   jsr native_dbf_load_request_path_to_word_tmp
    jsr native_dbf_compute_file_len_from_header
    jsr native_dbf_load_exact_file_to_buffer
    bcc :+
    jmp native_dbf_fail_request
:   jsr native_dbf_append_blank_record_to_buffer
    clc
    lda dbf_header_total_lo
    adc #$01
    sta dbf_header_total_lo
    lda dbf_header_total_hi
    adc #$00
    sta dbf_header_total_hi
    lda dbf_header_total_lo
    sta dbf_header_curr_lo
    lda dbf_header_total_hi
    sta dbf_header_curr_hi
    clc
    lda dbf_file_len_lo
    adc dbf_record_size_lo
    sta dbf_file_len_lo
    lda dbf_file_len_hi
    adc dbf_record_size_hi
    sta dbf_file_len_hi
    jsr native_dbf_write_header_to_file_buffer
    jsr native_dbf_save_file_from_buffer
    bcc :+
    jmp native_dbf_fail_request
:   jmp native_dbf_store_request_from_header

native_dbf_go:
    jsr native_dbf_prepare_request_ptr
    jsr native_dbf_validate_handle
    bcc :+
    jmp native_dbf_fail_request
:   jsr native_dbf_validate_requested_curr
    bcc :+
    jmp native_dbf_fail_request
:   ldy #DBF_REQ_CURR_LO
    lda (svc_retptr),y
    sta dbf_header_curr_lo
    iny
    lda (svc_retptr),y
    sta dbf_header_curr_hi
    jsr native_dbf_load_request_path_to_word_tmp
    jsr native_dbf_compute_file_len_from_header
    jsr native_dbf_load_exact_file_to_buffer
    bcc :+
    jmp native_dbf_fail_request
:   jsr native_dbf_write_header_to_file_buffer
    jsr native_dbf_save_file_from_buffer
    bcc :+
    jmp native_dbf_fail_request
:   jmp native_dbf_store_request_from_header

native_dbf_readfield:
    jsr native_dbf_prepare_request_ptr
    jsr native_dbf_validate_handle
    bcc :+
    jmp native_dbf_fail_request
:   jsr native_dbf_validate_field_index
    bcc :+
    jmp native_dbf_fail_request
:   jsr native_dbf_load_request_path_to_word_tmp
    jsr native_dbf_compute_file_len_from_header
    jsr native_dbf_load_exact_file_to_buffer
    bcc :+
    jmp native_dbf_fail_request
:   jsr native_dbf_compute_current_field_ptr
    bcc :+
    jmp native_dbf_fail_request
:   ldy #$00
    lda (src_ptr),y
    ldy #DBF_REQ_VALUE_LO
    sta (svc_retptr),y
    ldy #$01
    lda (src_ptr),y
    ldy #DBF_REQ_VALUE_HI
    sta (svc_retptr),y
    jmp native_dbf_store_request_handle_status

native_dbf_writefield:
    jsr native_dbf_prepare_request_ptr
    jsr native_dbf_validate_handle
    bcc :+
    jmp native_dbf_fail_request
:   jsr native_dbf_validate_field_index
    bcc :+
    jmp native_dbf_fail_request
:   jsr native_dbf_load_request_path_to_word_tmp
    jsr native_dbf_compute_file_len_from_header
    jsr native_dbf_load_exact_file_to_buffer
    bcc :+
    jmp native_dbf_fail_request
:   jsr native_dbf_compute_current_field_ptr
    bcc :+
    jmp native_dbf_fail_request
:   ldy #DBF_REQ_VALUE_LO
    lda (svc_retptr),y
    ldy #$00
    sta (src_ptr),y
    ldy #DBF_REQ_VALUE_HI
    lda (svc_retptr),y
    ldy #$01
    sta (src_ptr),y
    jsr native_dbf_write_header_to_file_buffer
    jsr native_dbf_save_file_from_buffer
    bcc :+
    jmp native_dbf_fail_request
:   jmp native_dbf_store_request_handle_status

native_dbf_prepare_request_ptr:
    ldx pptr
    jsr load_svc_retptr_from_x
    jmp resolve_svc_retptr_to_absolute_if_relative

native_dbf_load_request_path_to_word_tmp:
    ldy #DBF_REQ_PATH_LO
    lda (svc_retptr),y
    sta word_tmp
    iny
    lda (svc_retptr),y
    sta word_tmp+1
    jsr resolve_word_tmp_to_absolute_if_relative
    bcs :+
    jsr copy_word_tmp_cstr_to_dbf_path_buffer
:   rts

native_dbf_validate_requested_curr:
    ldy #DBF_REQ_CURR_LO
    lda (svc_retptr),y
    sta dbf_work_lo
    iny
    lda (svc_retptr),y
    sta dbf_work_hi
    lda dbf_work_lo
    ora dbf_work_hi
    bne :+
    sec
    rts
:   lda dbf_work_hi
    cmp dbf_header_total_hi
    bcc :+
    bne native_dbf_validate_requested_curr_fail
    lda dbf_work_lo
    cmp dbf_header_total_lo
    bcc :+
    beq :+
native_dbf_validate_requested_curr_fail:
    sec
    rts
:   clc
    rts

native_dbf_validate_field_index:
    ldy #DBF_REQ_FIELD_INDEX_LO
    lda (svc_retptr),y
    sta dbf_work_lo
    iny
    lda (svc_retptr),y
    sta dbf_work_hi
    lda dbf_work_hi
    cmp dbf_header_field_hi
    bcc :+
    bne native_dbf_validate_field_index_fail
    lda dbf_work_lo
    cmp dbf_header_field_lo
    bcc :+
native_dbf_validate_field_index_fail:
    sec
    rts
:   clc
    rts

native_dbf_validate_current_header:
    lda dbf_header_curr_lo
    ora dbf_header_curr_hi
    bne :+
    sec
    rts
:   lda dbf_header_curr_hi
    cmp dbf_header_total_hi
    bcc :+
    bne native_dbf_validate_current_header_fail
    lda dbf_header_curr_lo
    cmp dbf_header_total_lo
    bcc :+
    beq :+
native_dbf_validate_current_header_fail:
    sec
    rts
:   clc
    rts

native_dbf_compute_record_size:
    clc
    lda dbf_header_field_lo
    asl a
    sta dbf_record_size_lo
    lda dbf_header_field_hi
    rol a
    sta dbf_record_size_hi
    rts

native_dbf_compute_file_len_from_header:
    jsr native_dbf_compute_record_size
    lda #<DBF_FILE_HEADER_LEN
    sta dbf_file_len_lo
    lda #>DBF_FILE_HEADER_LEN
    sta dbf_file_len_hi
    lda dbf_header_total_lo
    sta dbf_work_lo
    lda dbf_header_total_hi
    sta dbf_work_hi
:
    lda dbf_work_lo
    ora dbf_work_hi
    beq :+
    clc
    lda dbf_file_len_lo
    adc dbf_record_size_lo
    sta dbf_file_len_lo
    lda dbf_file_len_hi
    adc dbf_record_size_hi
    sta dbf_file_len_hi
    sec
    lda dbf_work_lo
    sbc #$01
    sta dbf_work_lo
    lda dbf_work_hi
    sbc #$00
    sta dbf_work_hi
    jmp :-
:   rts

native_dbf_load_exact_file_to_buffer:
    lda #<DBF_PATH_SCRATCH_BASE
    sta file_params+0
    lda #>DBF_PATH_SCRATCH_BASE
    sta file_params+1
    lda #<dbf_file_buffer
    sta file_params+2
    lda #>dbf_file_buffer
    sta file_params+3
    lda dbf_file_len_lo
    sta file_params+4
    lda dbf_file_len_hi
    sta file_params+5
    lda #$00
    sta file_params+6
    sta file_params+7
    sta file_params+8
    jsr set_tool_mem_config
    ldx #file_params
    jsr svc_file_load_sc0
    jsr set_runtime_mem_config
    lda file_params+6
    cmp #tool_file_status_ok
    bne native_dbf_load_exact_file_to_buffer_fail
    lda file_params+7
    cmp dbf_file_len_lo
    bne native_dbf_load_exact_file_to_buffer_fail
    lda file_params+8
    cmp dbf_file_len_hi
    bne native_dbf_load_exact_file_to_buffer_fail
    clc
    rts
native_dbf_load_exact_file_to_buffer_fail:
    sec
    rts

native_dbf_save_file_from_buffer:
    lda #<DBF_PATH_SCRATCH_BASE
    sta file_params+0
    lda #>DBF_PATH_SCRATCH_BASE
    sta file_params+1
    lda #<dbf_file_buffer
    sta file_params+2
    lda #>dbf_file_buffer
    sta file_params+3
    lda dbf_file_len_lo
    sta file_params+4
    lda dbf_file_len_hi
    sta file_params+5
    lda #tool_file_status_fail
    sta file_params+6
    jsr set_tool_mem_config
    ldx #file_params
    jsr svc_file_save_sc0
    jsr set_runtime_mem_config
    lda file_params+6
    cmp #tool_file_status_ok
    beq :+
    sec
    rts
:   clc
    rts

native_dbf_write_header_to_file_buffer:
    lda #DBF_FILE_MAGIC_0
    sta dbf_file_buffer+0
    lda #DBF_FILE_MAGIC_1
    sta dbf_file_buffer+1
    lda #DBF_FILE_MAGIC_2
    sta dbf_file_buffer+2
    lda #DBF_FILE_MAGIC_3
    sta dbf_file_buffer+3
    lda dbf_header_field_lo
    sta dbf_file_buffer+4
    lda dbf_header_field_hi
    sta dbf_file_buffer+5
    lda dbf_header_total_lo
    sta dbf_file_buffer+6
    lda dbf_header_total_hi
    sta dbf_file_buffer+7
    lda dbf_header_curr_lo
    sta dbf_file_buffer+8
    lda dbf_header_curr_hi
    sta dbf_file_buffer+9
    rts

native_dbf_copy_header_from_file_buffer:
    lda dbf_file_buffer+0
    sta dbf_header_magic0
    lda dbf_file_buffer+1
    sta dbf_header_magic1
    lda dbf_file_buffer+2
    sta dbf_header_magic2
    lda dbf_file_buffer+3
    sta dbf_header_magic3
    lda dbf_file_buffer+4
    sta dbf_header_field_lo
    lda dbf_file_buffer+5
    sta dbf_header_field_hi
    lda dbf_file_buffer+6
    sta dbf_header_total_lo
    lda dbf_file_buffer+7
    sta dbf_header_total_hi
    lda dbf_file_buffer+8
    sta dbf_header_curr_lo
    lda dbf_file_buffer+9
    sta dbf_header_curr_hi
    rts

native_dbf_append_blank_record_to_buffer:
    clc
    lda #<dbf_file_buffer
    adc dbf_file_len_lo
    sta src_ptr
    lda #>dbf_file_buffer
    adc dbf_file_len_hi
    sta src_ptr+1
    lda dbf_header_field_lo
    sta dbf_work_lo
    lda dbf_header_field_hi
    sta dbf_work_hi
:
    lda dbf_work_lo
    ora dbf_work_hi
    beq :+
    ldy #$00
    lda #$00
    sta (src_ptr),y
    iny
    sta (src_ptr),y
    clc
    lda src_ptr
    adc #$02
    sta src_ptr
    lda src_ptr+1
    adc #$00
    sta src_ptr+1
    sec
    lda dbf_work_lo
    sbc #$01
    sta dbf_work_lo
    lda dbf_work_hi
    sbc #$00
    sta dbf_work_hi
    jmp :-
:   rts

native_dbf_compute_current_field_ptr:
    jsr native_dbf_validate_current_header
    bcc :+
    sec
    rts
:   lda #<(dbf_file_buffer + DBF_FILE_HEADER_LEN)
    sta src_ptr
    lda #>(dbf_file_buffer + DBF_FILE_HEADER_LEN)
    sta src_ptr+1
    lda dbf_header_curr_lo
    sta dbf_work_lo
    lda dbf_header_curr_hi
    sta dbf_work_hi
    sec
    lda dbf_work_lo
    sbc #$01
    sta dbf_work_lo
    lda dbf_work_hi
    sbc #$00
    sta dbf_work_hi
:
    lda dbf_work_lo
    ora dbf_work_hi
    beq :+
    clc
    lda src_ptr
    adc dbf_record_size_lo
    sta src_ptr
    lda src_ptr+1
    adc dbf_record_size_hi
    sta src_ptr+1
    sec
    lda dbf_work_lo
    sbc #$01
    sta dbf_work_lo
    lda dbf_work_hi
    sbc #$00
    sta dbf_work_hi
    jmp :-
:   ldy #DBF_REQ_FIELD_INDEX_LO
    lda (svc_retptr),y
    sta dbf_work_lo
    iny
    lda (svc_retptr),y
    sta dbf_work_hi
    asl dbf_work_lo
    rol dbf_work_hi
    clc
    lda src_ptr
    adc dbf_work_lo
    sta src_ptr
    lda src_ptr+1
    adc dbf_work_hi
    sta src_ptr+1
    clc
    rts

native_dbf_validate_handle:
    ldy #DBF_REQ_HANDLE
    lda (svc_retptr),y
    cmp dbf_active_handle
    beq :+
    sec
    rts
:   lda dbf_active_handle
    bne :+
    sec
    rts
:   clc
    rts

native_dbf_store_request_from_header:
    ldy #DBF_REQ_FIELD_COUNT
    lda dbf_header_field_lo
    sta (svc_retptr),y
    iny
    lda dbf_header_field_hi
    sta (svc_retptr),y
    ldy #DBF_REQ_TOTAL_LO
    lda dbf_header_total_lo
    sta (svc_retptr),y
    iny
    lda dbf_header_total_hi
    sta (svc_retptr),y
    ldy #DBF_REQ_CURR_LO
    lda dbf_header_curr_lo
    sta (svc_retptr),y
    iny
    lda dbf_header_curr_hi
    sta (svc_retptr),y
    jmp native_dbf_store_request_handle_status

native_dbf_store_request_handle_status:
    ldy #DBF_REQ_HANDLE
    lda dbf_active_handle
    sta (svc_retptr),y
    ldy #DBF_REQ_STATUS
    lda #$01
    sta (svc_retptr),y
    rts

native_dbf_fail_request:
    ldy #DBF_REQ_HANDLE
    lda #$00
    sta (svc_retptr),y
    ldy #DBF_REQ_STATUS
    sta (svc_retptr),y
    rts

load_svc_retptr_from_x:
    lda 0,x
    sta svc_retptr
    lda 1,x
    sta svc_retptr+1
    rts

load_word_tmp_from_x:
    lda 0,x
    sta word_tmp
    lda 1,x
    sta word_tmp+1
    rts

resolve_svc_retptr_to_absolute_if_relative:
    lda svc_retptr+1
    cmp payload_ptr+1
    bcc resolve_svc_retptr_relative
    bne resolve_svc_retptr_absolute
    lda svc_retptr
    cmp payload_ptr
    bcc resolve_svc_retptr_relative
resolve_svc_retptr_absolute:
    clc
    rts
resolve_svc_retptr_relative:
    clc
    lda svc_retptr
    adc payload_ptr
    sta svc_retptr
    lda svc_retptr+1
    adc payload_ptr+1
    sta svc_retptr+1
    clc
    rts

resolve_word_tmp_to_absolute_if_relative:
    lda word_tmp+1
    cmp payload_ptr+1
    bcc resolve_word_tmp_relative
    bne resolve_word_tmp_absolute
    lda word_tmp
    cmp payload_ptr
    bcc resolve_word_tmp_relative
resolve_word_tmp_absolute:
    clc
    rts
resolve_word_tmp_relative:
    clc
    lda word_tmp
    adc payload_ptr
    sta word_tmp
    lda word_tmp+1
    adc payload_ptr+1
    sta word_tmp+1
    clc
    rts

.if AVMRUN_COMPAT
avmrun_overlay_call_print:
    sta avmrun_overlay_requested_cmd
    lda #AVMRUN_OVERLAY_KIND_PRINT
    sta avmrun_overlay_requested_kind
    jmp avmrun_overlay_call_loaded

avmrun_overlay_call_realops:
    sta avmrun_overlay_requested_cmd
    cmp #AVMRUN_OVERLAY_CMD_REAL_ITOF
    bne :+
    lda word_tmp
    sta real_lhs_lo
    lda word_tmp+1
    sta real_lhs_lo+1
:
    lda #AVMRUN_OVERLAY_KIND_REALOPS
    sta avmrun_overlay_requested_kind
    jmp avmrun_overlay_call_loaded

avmrun_overlay_call_loaded:
    jsr avmrun_overlay_ensure_loaded
    bcs avmrun_overlay_call_loaded_fail
    jsr avmrun_overlay_jsr_entry
    clc
    rts
avmrun_overlay_call_loaded_fail:
    sec
    rts

avmrun_overlay_ensure_loaded:
    lda avmrun_overlay_ready
    beq avmrun_overlay_stage_begin
    lda avmrun_overlay_requested_kind
    cmp avmrun_overlay_loaded_kind
    bne avmrun_overlay_stage_begin
    jmp avmrun_overlay_ready_ok
avmrun_overlay_stage_begin:
    jsr set_tool_mem_config
    lda avmrun_overlay_requested_kind
    cmp #AVMRUN_OVERLAY_KIND_PRINTREAL
    bne avmrun_overlay_stage_check_realops
    lda #<avmrun_overlay_printreal_path
    sta file_params+0
    lda #>avmrun_overlay_printreal_path
    sta file_params+1
    jmp avmrun_overlay_stage_path_ready
avmrun_overlay_stage_check_realops:
    cmp #AVMRUN_OVERLAY_KIND_REALOPS
    bne avmrun_overlay_stage_check_interp
    lda #<avmrun_overlay_realops_path
    sta file_params+0
    lda #>avmrun_overlay_realops_path
    sta file_params+1
    jmp avmrun_overlay_stage_path_ready
avmrun_overlay_stage_check_interp:
    cmp #AVMRUN_OVERLAY_KIND_INTERP
    beq :+
    jmp avmrun_overlay_load_fail
:
    lda #<avmrun_overlay_interp_path
    sta file_params+0
    lda #>avmrun_overlay_interp_path
    sta file_params+1
avmrun_overlay_stage_path_ready:
    lda #AVMRUN_OVERLAY_REU_BASE_LO
    sta file_params+2
    lda #AVMRUN_OVERLAY_REU_BASE_HI
    sta file_params+3
    lda #AVMRUN_OVERLAY_REU_BASE_BANK
    sta file_params+4
    lda #$00
    sta file_params+5
    sta file_params+6
    sta file_params+7
    sta file_params+8
    tsx
    stx TOOL_DEBUG0
    lda $0101,x
    sta TOOL_DEBUG1
    lda file_params+0
    sta TOOL_DEBUG2
    lda file_params+1
    sta TOOL_DEBUG3
    lda file_params+2
    sta TOOL_DEBUG4
    lda file_params+3
    sta TOOL_DEBUG5
    lda file_params+4
    sta TOOL_DEBUG6
    lda file_params+5
    sta TOOL_DEBUG7
    ldx #file_params
    jsr svc_file_stage_reu_sc0
    lda file_params+5
    cmp #tool_file_status_ok
    beq :+
    jmp avmrun_overlay_load_fail
:
    lda file_params+6
    sta avmrun_overlay_loaded_len
    lda file_params+7
    sta avmrun_overlay_loaded_len+1
    lda file_params+8
    beq :+
    jmp avmrun_overlay_load_fail
:
    lda avmrun_overlay_loaded_len
    ora avmrun_overlay_loaded_len+1
    bne :+
    jmp avmrun_overlay_load_fail
:
    lda avmrun_overlay_loaded_len+1
    cmp #>AVMRUN_OVERLAY_EXEC_SIZE
    bcc :+
    bne avmrun_overlay_load_fail
    lda avmrun_overlay_loaded_len
    bne avmrun_overlay_load_fail
:
    lda #AVMRUN_OVERLAY_REU_BASE_LO
    sta file_params+0
    lda #AVMRUN_OVERLAY_REU_BASE_HI
    sta file_params+1
    lda #AVMRUN_OVERLAY_REU_BASE_BANK
    sta file_params+2
    lda #<AVMRUN_OVERLAY_EXEC_BASE
    sta file_params+3
    lda #>AVMRUN_OVERLAY_EXEC_BASE
    sta file_params+4
    lda avmrun_overlay_loaded_len
    sta file_params+5
    lda avmrun_overlay_loaded_len+1
    sta file_params+6
    lda #$00
    sta file_params+7
    ldx #file_params
    jsr svc_reu_read_sc0
    jsr set_runtime_mem_config
    lda file_params+7
    sta avmrun_overlay_service_status
    cmp #tool_file_status_ok
    bne avmrun_overlay_load_fail
    jsr avmrun_overlay_validate_loaded
    bcs avmrun_overlay_load_fail
    lda #$01
    sta avmrun_overlay_ready
    lda avmrun_overlay_requested_kind
    sta avmrun_overlay_loaded_kind
avmrun_overlay_ready_ok:
    clc
    rts

avmrun_overlay_load_fail:
    lda #$00
    sta avmrun_overlay_ready
    sta avmrun_overlay_loaded_kind
    sec
    rts

avmrun_overlay_validate_loaded:
    lda AVMRUN_OVERLAY_EXEC_BASE+0
    cmp #'A'
    bne avmrun_overlay_validate_fail
    lda AVMRUN_OVERLAY_EXEC_BASE+1
    cmp #'V'
    bne avmrun_overlay_validate_fail
    lda AVMRUN_OVERLAY_EXEC_BASE+2
    cmp #'O'
    bne avmrun_overlay_validate_fail
    lda AVMRUN_OVERLAY_EXEC_BASE+3
    cmp #'V'
    bne avmrun_overlay_validate_fail
    lda AVMRUN_OVERLAY_EXEC_BASE+4
    cmp #AVMRUN_OVERLAY_ABI_VERSION
    bne avmrun_overlay_validate_fail
    lda AVMRUN_OVERLAY_EXEC_BASE+5
    cmp #<AVMRUN_OVERLAY_EXEC_BASE
    bne avmrun_overlay_validate_fail
    lda AVMRUN_OVERLAY_EXEC_BASE+6
    cmp #>AVMRUN_OVERLAY_EXEC_BASE
    bne avmrun_overlay_validate_fail
    lda AVMRUN_OVERLAY_EXEC_BASE+9
    cmp avmrun_overlay_loaded_len
    bne avmrun_overlay_validate_fail
    lda AVMRUN_OVERLAY_EXEC_BASE+10
    cmp avmrun_overlay_loaded_len+1
    bne avmrun_overlay_validate_fail
    clc
    rts
avmrun_overlay_validate_fail:
    sec
    rts

avmrun_overlay_jsr_entry:
    sec
    lda AVMRUN_OVERLAY_EXEC_BASE+7
    sbc #$01
    sta avmrun_overlay_entry_minus_one
    lda AVMRUN_OVERLAY_EXEC_BASE+8
    sbc #$00
    pha
    lda avmrun_overlay_entry_minus_one
    pha
    rts
.endif

native_helper_printreal_jsr_entry:
    sec
    lda native_helper_printreal_entry_ptr
    sbc #$01
    sta native_helper_jsr_entry_minus_one
    lda native_helper_printreal_entry_ptr+1
    sbc #$00
    pha
    lda native_helper_jsr_entry_minus_one
    pha
    rts

native_exit:
    ; CALLN only wraps a native JSR and always resumes the VM afterward.
    ; To honor EXIT on the fast path, discard CALLN's return frame and return
    ; directly to payload_ready, which already owns runner cleanup + tool exit.
    pla
    pla
    rts

copy_first_arg:
    ldy #$00
copy_first_arg_loop:
    lda (src_ptr),y
    beq copy_first_arg_done
    cmp #' '
    beq copy_first_arg_done
    sta filename_buffer,y
    iny
    cpy #31
    bcc copy_first_arg_loop
copy_first_arg_done:
    lda #$00
    sta filename_buffer,y
    rts

copy_word_tmp_cstr_to_dbf_path_buffer:
    ldy #$00
copy_word_tmp_cstr_to_dbf_path_buffer_loop:
    lda (word_tmp),y
    sta DBF_PATH_SCRATCH_BASE,y
    beq copy_word_tmp_cstr_to_dbf_path_buffer_done
    iny
    cpy #31
    bcc copy_word_tmp_cstr_to_dbf_path_buffer_loop
    lda #$00
    sta DBF_PATH_SCRATCH_BASE,y
copy_word_tmp_cstr_to_dbf_path_buffer_done:
    lda #<DBF_PATH_SCRATCH_BASE
    sta word_tmp
    lda #>DBF_PATH_SCRATCH_BASE
    sta word_tmp+1
    clc
    rts

print_ptr:
    sta svc_retptr
    sty svc_retptr+1
    jmp runtime_safe_console_write

restore_mem_config:
    lda saved_memcfg
    sta C64_MEMCFG
    rts

set_tool_mem_config:
    lda saved_memcfg
    and #C64_MEMCFG_CONFIG_MASK
    ora #C64_MEMCFG_TOOL_BITS
    sta C64_MEMCFG
    rts

set_runtime_mem_config:
    lda saved_memcfg
    and #C64_MEMCFG_CONFIG_MASK
    ora #C64_MEMCFG_RUNTIME_BITS
    sta C64_MEMCFG
    rts

runtime_safe_console_write:
    jsr set_tool_mem_config
    ldx #svc_retptr
    jsr svc_console_write_sc0
    jmp set_runtime_mem_config

runtime_safe_console_newline:
    jsr set_tool_mem_config
    jsr svc_console_newline
    jmp set_runtime_mem_config

call_word_tmp:
    jmp (word_tmp)

restore_native_helper_irq_state:
    lda native_helper_irq_saved
    cmp #$FF
    beq restore_native_helper_irq_state_done
    cmp #$00
    bne restore_native_helper_irq_state_reset
    cli
restore_native_helper_irq_state_reset:
    lda #$FF
    sta native_helper_irq_saved
restore_native_helper_irq_state_done:
    rts

msg_no_file:
    .asciiz "NO FILE"
msg_too_large:
    .asciiz "TOO LARGE"
msg_load_fail:
    .asciiz "LOAD FAIL"
msg_bad_avm:
    .asciiz "BAD AVM"
msg_unsupported:
    .asciiz "UNSUPPORTED AVM"
msg_needs_compat:
    .asciiz "NEEDS AVMRUN COMPAT"
msg_real_to_int_range:
    .asciiz "REAL->INT RANGE"
.if AVMRUN_COMPAT
avmrun_overlay_printreal_path:
    .asciiz "!AVMRUN_OVL1.BIN"
avmrun_overlay_realops_path:
    .asciiz "!AVMRUN_OVL2.BIN"
avmrun_overlay_interp_path:
    .asciiz "!AVMRUN_OVL3.BIN"
.endif

.assert * <= AVMRUN_INTERP_SCRATCH_BASE, error, "AVMRUN code overlaps interp scratch"
dbf_header_magic0 = DBF_HEADER_SCRATCH_BASE + $00
dbf_header_magic1 = DBF_HEADER_SCRATCH_BASE + $01
dbf_header_magic2 = DBF_HEADER_SCRATCH_BASE + $02
dbf_header_magic3 = DBF_HEADER_SCRATCH_BASE + $03
dbf_header_field_lo = DBF_HEADER_SCRATCH_BASE + $04
dbf_header_field_hi = DBF_HEADER_SCRATCH_BASE + $05
dbf_header_total_lo = DBF_HEADER_SCRATCH_BASE + $06
dbf_header_total_hi = DBF_HEADER_SCRATCH_BASE + $07
dbf_header_curr_lo = DBF_HEADER_SCRATCH_BASE + $08
dbf_header_curr_hi = DBF_HEADER_SCRATCH_BASE + $09
dbf_record_size_lo = DBF_HEADER_SCRATCH_BASE + $0A
dbf_record_size_hi = DBF_HEADER_SCRATCH_BASE + $0B
dbf_file_len_lo = DBF_HEADER_SCRATCH_BASE + $0C
dbf_file_len_hi = DBF_HEADER_SCRATCH_BASE + $0D
dbf_work_lo = DBF_HEADER_SCRATCH_BASE + $0E
dbf_work_hi = DBF_HEADER_SCRATCH_BASE + $0F
.assert * <= AVMRUN_RUNTIME_SCRATCH_BASE, error, "AVMRUN code overlaps runtime scratch"

.segment "BSS"
.if ALLOW_TEXT_AVM
payload_buffer:
    .res PAYLOAD_BUFFER_SIZE
.endif

; Filename staging is only needed during the initial payload load, before the
; fallback interpreter window at $2C00 becomes live, so it aliases that
; on-demand scratch instead of reserving resident BSS.
filename_buffer = AVMRUN_INTERP_SCRATCH_BASE + $00
real_print_low = AVMRUN_RUNTIME_SCRATCH_BASE + $00
real_print_high = AVMRUN_RUNTIME_SCRATCH_BASE + $02
real_print_int = AVMRUN_RUNTIME_SCRATCH_BASE + $04
real_print_rem = AVMRUN_RUNTIME_SCRATCH_BASE + $06
real_print_mask = AVMRUN_RUNTIME_SCRATCH_BASE + $0E
real_print_work = AVMRUN_RUNTIME_SCRATCH_BASE + $16
real_print_flag = AVMRUN_RUNTIME_SCRATCH_BASE + $1E
real_print_shift = AVMRUN_RUNTIME_SCRATCH_BASE + $1F
real_print_num = AVMRUN_RUNTIME_SCRATCH_BASE + $20
real_print_sign = AVMRUN_RUNTIME_SCRATCH_BASE + $28
.if AVMRUN_COMPAT
real_lhs_lo = AVMRUN_RUNTIME_SCRATCH_BASE + $29
real_lhs_hi = AVMRUN_RUNTIME_SCRATCH_BASE + $2B
real_rhs_lo = AVMRUN_RUNTIME_SCRATCH_BASE + $2D
real_rhs_hi = AVMRUN_RUNTIME_SCRATCH_BASE + $2F
real_result_lo = AVMRUN_RUNTIME_SCRATCH_BASE + $31
real_result_hi = AVMRUN_RUNTIME_SCRATCH_BASE + $33
real_lhs_mant = AVMRUN_RUNTIME_SCRATCH_BASE + $35
real_rhs_mant = AVMRUN_RUNTIME_SCRATCH_BASE + $39
real_lhs_exp = AVMRUN_RUNTIME_SCRATCH_BASE + $3D
real_rhs_exp = AVMRUN_RUNTIME_SCRATCH_BASE + $3E
real_lhs_sign = AVMRUN_RUNTIME_SCRATCH_BASE + $3F
real_rhs_sign = AVMRUN_RUNTIME_SCRATCH_BASE + $40
real_align_shift = AVMRUN_RUNTIME_SCRATCH_BASE + $41
real_flip_rhs_sign = AVMRUN_RUNTIME_SCRATCH_BASE + $42
payload_end_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $43
file_end_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $45
real_work_shift = AVMRUN_RUNTIME_SCRATCH_BASE + $47
real_exp_work = AVMRUN_RUNTIME_SCRATCH_BASE + $48
real_work_a = AVMRUN_RUNTIME_SCRATCH_BASE + $4A
real_work_b = AVMRUN_RUNTIME_SCRATCH_BASE + $50
real_work_c = AVMRUN_RUNTIME_SCRATCH_BASE + $56
saved_memcfg = AVMRUN_RUNTIME_SCRATCH_BASE + $59
avm_flags = AVMRUN_RUNTIME_SCRATCH_BASE + $5A
.else
payload_end_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $29
file_end_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $2B
saved_memcfg = AVMRUN_RUNTIME_SCRATCH_BASE + $2D
avm_flags = AVMRUN_RUNTIME_SCRATCH_BASE + $2E
.endif

interp_error_ptr = AVMRUN_INTERP_ERROR_PTR
interp_sp = AVMRUN_INTERP_SP
interp_rsp = AVMRUN_INTERP_RSP
interp_string_ptr = AVMRUN_INTERP_STRING_PTR
interp_stack_lo = AVMRUN_INTERP_STACK_LO
interp_stack_hi = AVMRUN_INTERP_STACK_HI
interp_rstack_lo = AVMRUN_INTERP_RSTACK_LO
interp_rstack_hi = AVMRUN_INTERP_RSTACK_HI
avmrun_interp_result = AVMRUN_INTERP_RESULT
avmrun_interp_service_kind = AVMRUN_INTERP_SERVICE_KIND
avmrun_interp_service_cmd = AVMRUN_INTERP_SERVICE_CMD
avmrun_interp_resume_state = AVMRUN_INTERP_RESUME_STATE
avmrun_interp_service_failed = AVMRUN_INTERP_SERVICE_FAILED
.if AVMRUN_COMPAT
native_helper_ready_flags = AVMRUN_RUNTIME_SCRATCH_BASE + $5B
native_helper_expected_len = AVMRUN_RUNTIME_SCRATCH_BASE + $5C
native_helper_printstd_entry_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $5E
native_helper_printstd_entry_nl_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $60
native_helper_printstd_entry_u16_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $62
native_helper_printstd_entry_u16_nl_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $64
native_helper_printreal_entry_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $66
native_helper_debug_stage = AVMRUN_RUNTIME_SCRATCH_BASE + $68
native_helper_irq_saved = AVMRUN_RUNTIME_SCRATCH_BASE + $69
native_helper_printreal_char_buffer = AVMRUN_RUNTIME_SCRATCH_BASE + $6A
native_helper_printreal_trace_active = AVMRUN_RUNTIME_SCRATCH_BASE + $6C
native_helper_printreal_char_count = AVMRUN_RUNTIME_SCRATCH_BASE + $6D
native_helper_printreal_first_char = AVMRUN_RUNTIME_SCRATCH_BASE + $6E
native_helper_printreal_last_char = AVMRUN_RUNTIME_SCRATCH_BASE + $6F
native_helper_printreal_saved_iptr = AVMRUN_RUNTIME_SCRATCH_BASE + $70
native_helper_printreal_saved_iptr_offset = AVMRUN_RUNTIME_SCRATCH_BASE + $72
native_helper_printreal_saved_pptr = AVMRUN_RUNTIME_SCRATCH_BASE + $73
native_helper_printreal_saved_rptr = AVMRUN_RUNTIME_SCRATCH_BASE + $74
avmrun_overlay_ready = AVMRUN_RUNTIME_SCRATCH_BASE + $75
avmrun_overlay_requested_kind = AVMRUN_RUNTIME_SCRATCH_BASE + $76
avmrun_overlay_loaded_kind = AVMRUN_RUNTIME_SCRATCH_BASE + $77
avmrun_overlay_requested_cmd = AVMRUN_RUNTIME_SCRATCH_BASE + $78
avmrun_overlay_loaded_len = AVMRUN_RUNTIME_SCRATCH_BASE + $79
avmrun_overlay_service_status = AVMRUN_RUNTIME_SCRATCH_BASE + $7B
avmrun_overlay_entry_minus_one = AVMRUN_RUNTIME_SCRATCH_BASE + $7C
native_helper_jsr_entry_minus_one = avmrun_overlay_entry_minus_one
native_helper_sidspr_arg = AVMRUN_RUNTIME_SCRATCH_BASE + $7D
dbf_active_handle = AVMRUN_RUNTIME_SCRATCH_BASE + $7E
.else
native_helper_ready_flags = AVMRUN_RUNTIME_SCRATCH_BASE + $2F
native_helper_expected_len = AVMRUN_RUNTIME_SCRATCH_BASE + $30
native_helper_printstd_entry_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $32
native_helper_printstd_entry_nl_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $34
native_helper_printstd_entry_u16_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $36
native_helper_printstd_entry_u16_nl_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $38
native_helper_printreal_entry_ptr = AVMRUN_RUNTIME_SCRATCH_BASE + $3A
native_helper_debug_stage = AVMRUN_RUNTIME_SCRATCH_BASE + $3C
native_helper_irq_saved = AVMRUN_RUNTIME_SCRATCH_BASE + $3D
native_helper_printreal_char_buffer = AVMRUN_RUNTIME_SCRATCH_BASE + $3E
native_helper_printreal_trace_active = AVMRUN_RUNTIME_SCRATCH_BASE + $40
native_helper_printreal_char_count = AVMRUN_RUNTIME_SCRATCH_BASE + $41
native_helper_printreal_first_char = AVMRUN_RUNTIME_SCRATCH_BASE + $42
native_helper_printreal_last_char = AVMRUN_RUNTIME_SCRATCH_BASE + $43
native_helper_printreal_saved_iptr = AVMRUN_RUNTIME_SCRATCH_BASE + $44
native_helper_printreal_saved_iptr_offset = AVMRUN_RUNTIME_SCRATCH_BASE + $46
native_helper_printreal_saved_pptr = AVMRUN_RUNTIME_SCRATCH_BASE + $47
native_helper_printreal_saved_rptr = AVMRUN_RUNTIME_SCRATCH_BASE + $48
native_helper_jsr_entry_minus_one = AVMRUN_RUNTIME_SCRATCH_BASE + $49
dbf_active_handle = AVMRUN_RUNTIME_SCRATCH_BASE + $4A
.endif
gfx_tileset_repeat_x = AVMRUN_INTERP_SCRATCH_BASE + $70
gfx_tileset_repeat_y = AVMRUN_INTERP_SCRATCH_BASE + $71
gfx_tileset_step_x = AVMRUN_INTERP_SCRATCH_BASE + $72
gfx_tileset_step_y = AVMRUN_INTERP_SCRATCH_BASE + $73
gfx_tileset_row_start_x = AVMRUN_INTERP_SCRATCH_BASE + $74
gfx_tileset_tile_ptr = AVMRUN_INTERP_SCRATCH_BASE + $75
gfx_tileset_col_count = AVMRUN_INTERP_SCRATCH_BASE + $77
gfx_tileset_tile_index = AVMRUN_INTERP_SCRATCH_BASE + $78
