.include "udos_services.inc"

.export start

HEADER_READ_LEN = 8
LOW_HEADER_LEN = 11
BULK_READ_LEN_LO = $01
BULK_READ_LEN_HI = $01
C64_MEMCFG = $01
C64_MEMCFG_CONFIG_MASK = $F8
C64_MEMCFG_TOOL_BITS = $06
C64_MEMCFG_RUNTIME_BITS = $04
TOOL_DEBUG0 = $03D0
TOOL_DEBUG1 = $03D1
TOOL_DEBUG2 = $03D2
TOOL_DEBUG3 = $03D3
TOOL_DEBUG4 = $03D4
TOOL_DEBUG5 = $03D5
TOOL_DEBUG6 = $03D6
TOOL_DEBUG7 = $03D7
AVMRUN_OVERLAY_ABI_VERSION = 1
STAGE_REU_BASE_LO = $00
STAGE_REU_BASE_HI = $00
STAGE_REU_BASE_BANK = $05
EXEC_BASE = $EA00
EXEC_LIMIT_LO = $00
EXEC_LIMIT_HI = $16
AVMRUN_FILE_BUFFER = $4750
AVMRUN_FILE_BUFFER_SIZE_LO = $00
AVMRUN_FILE_BUFFER_SIZE_HI = $C0
AVMRUN_RUNTIME_SCRATCH_BASE = $3C80
AVMRUN_PAYLOAD_END_PTR = AVMRUN_RUNTIME_SCRATCH_BASE + $43
AVMRUN_FILE_END_PTR = AVMRUN_RUNTIME_SCRATCH_BASE + $45
AVMRUN_SAVED_MEMCFG = AVMRUN_RUNTIME_SCRATCH_BASE + $59
AVMRUN_FLAGS = AVMRUN_RUNTIME_SCRATCH_BASE + $5A
AVMRUN_OVERLAY_READY = AVMRUN_RUNTIME_SCRATCH_BASE + $75
AVMRUN_OVERLAY_REQUESTED_KIND = AVMRUN_RUNTIME_SCRATCH_BASE + $76
AVMRUN_OVERLAY_LOADED_KIND = AVMRUN_RUNTIME_SCRATCH_BASE + $77
AVMRUN_OVERLAY_REQUESTED_CMD = AVMRUN_RUNTIME_SCRATCH_BASE + $78
AVMRUN_OVERLAY_LOADED_LEN = AVMRUN_RUNTIME_SCRATCH_BASE + $79
AVMRUN_OVERLAY_SERVICE_STATUS = AVMRUN_RUNTIME_SCRATCH_BASE + $7B

.segment "ZPTEMP": zeropage
svc_retptr:
    .res 2
file_params:
    .res 9
src_ptr:
    .res 2
write_ptr:
    .res 2
tmp_byte:
    .res 1

.code

start:
    ldx #svc_retptr
    jsr svc_program_get_cmdline_len
    lda svc_retptr
    ora svc_retptr+1
    bne have_args
    jsr copy_default_arg
    jmp have_filename

have_args:
    ldx #svc_retptr
    jsr svc_program_get_cmdline_ptr
    lda svc_retptr
    sta src_ptr
    lda svc_retptr+1
    sta src_ptr+1
    jsr copy_first_arg

have_filename:

    lda #<filename_buffer
    sta file_params+0
    lda #>filename_buffer
    sta file_params+1
    lda #STAGE_REU_BASE_LO
    sta file_params+2
    lda #STAGE_REU_BASE_HI
    sta file_params+3
    lda #STAGE_REU_BASE_BANK
    sta file_params+4
    lda #$00
    sta file_params+5
    sta file_params+6
    sta file_params+7
    sta file_params+8
    tsx
    stx TOOL_DEBUG0
    php
    pla
    sta TOOL_DEBUG1
    lda #$11
    sta TOOL_DEBUG2
    ldx #file_params
    jsr svc_file_stage_reu_sc0
    lda #$12
    sta TOOL_DEBUG2
    lda file_params+5
    sta TOOL_DEBUG3
    lda file_params+6
    sta TOOL_DEBUG4
    lda file_params+7
    sta TOOL_DEBUG5
    lda file_params+8
    sta TOOL_DEBUG6
    lda file_params+6
    sta staged_len_lo
    lda file_params+7
    sta staged_len_hi
    lda file_params+8
    sta staged_len_bank

    jsr print_stage_line

    lda file_params+5
    cmp #tool_file_status_ok
    beq stage_ok
    lda #$01
    sta svc_retptr
    lda #$00
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

stage_ok:
    lda C64_MEMCFG
    sta saved_memcfg_abs
    jsr set_runtime_mem_config
    jsr set_tool_mem_config
    lda #<prefetch_filename
    sta file_params+0
    lda #>prefetch_filename
    sta file_params+1
    lda #<AVMRUN_FILE_BUFFER
    sta file_params+2
    lda #>AVMRUN_FILE_BUFFER
    sta file_params+3
    lda #AVMRUN_FILE_BUFFER_SIZE_LO
    sta file_params+4
    lda #AVMRUN_FILE_BUFFER_SIZE_HI
    sta file_params+5
    lda #$00
    sta file_params+6
    sta file_params+7
    sta file_params+8
    lda #$21
    sta TOOL_DEBUG2
    ldx #file_params
    jsr svc_file_load_sc0
    lda #$22
    sta TOOL_DEBUG2
    lda file_params+6
    sta TOOL_DEBUG3
    lda file_params+7
    sta TOOL_DEBUG4
    lda file_params+8
    sta TOOL_DEBUG5
    lda file_params+6
    sta prefetch_status
    lda file_params+7
    sta prefetch_len_lo
    lda file_params+8
    sta prefetch_len_hi
    jsr print_prefetch_line
    jsr restore_mem_config
    lda #$00
    sta svc_retptr
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit
    jsr seed_avmrun_compat_scratch
    lda #<filename_buffer
    sta file_params+0
    lda #>filename_buffer
    sta file_params+1
    lda #STAGE_REU_BASE_LO
    sta file_params+2
    lda #STAGE_REU_BASE_HI
    sta file_params+3
    lda #STAGE_REU_BASE_BANK
    sta file_params+4
    lda #$00
    sta file_params+5
    sta file_params+6
    sta file_params+7
    sta file_params+8
    lda saved_memcfg_abs
    sta TOOL_DEBUG0
    lda C64_MEMCFG
    sta TOOL_DEBUG1
    jsr stage_overlay_with_shelladd_like_wrapper
    lda file_params+6
    sta staged_len_lo
    lda file_params+7
    sta staged_len_hi
    lda file_params+8
    sta staged_len_bank
    lda #$AA
    ldx #LOW_HEADER_LEN
    jsr fill_bulk_buffer
    lda #STAGE_REU_BASE_LO
    sta file_params+0
    lda #STAGE_REU_BASE_HI
    sta file_params+1
    lda #STAGE_REU_BASE_BANK
    sta file_params+2
    lda #<bulk_buffer
    sta file_params+3
    lda #>bulk_buffer
    sta file_params+4
    lda #LOW_HEADER_LEN
    sta file_params+5
    lda #$00
    sta file_params+6
    sta file_params+7
    ldx #file_params
    jsr svc_reu_read_sc0
    lda file_params+7
    sta head_read_status
    jsr print_head_line

    jsr set_tool_mem_config
    lda #$BB
    ldx #$00
    jsr fill_bulk_buffer_page
    lda #$BB
    ldx #$01
    jsr fill_bulk_buffer
    lda #STAGE_REU_BASE_LO
    sta file_params+0
    lda #STAGE_REU_BASE_HI
    sta file_params+1
    lda #STAGE_REU_BASE_BANK
    sta file_params+2
    lda #<bulk_buffer
    sta file_params+3
    lda #>bulk_buffer
    sta file_params+4
    lda #BULK_READ_LEN_LO
    sta file_params+5
    lda #BULK_READ_LEN_HI
    sta file_params+6
    lda #$00
    sta file_params+7
    ldx #file_params
    jsr svc_reu_read_sc0
    lda file_params+7
    sta low_read_status
    jsr print_low_line

    lda #STAGE_REU_BASE_LO
    sta file_params+0
    lda #STAGE_REU_BASE_HI
    sta file_params+1
    lda #STAGE_REU_BASE_BANK
    sta file_params+2
    jsr set_runtime_mem_config
    lda #$CC
    ldx #HEADER_READ_LEN
    jsr fill_exec_prefix
    jsr set_tool_mem_config
    lda #<EXEC_BASE
    sta file_params+3
    lda #>EXEC_BASE
    sta file_params+4
    lda staged_len_lo
    sta file_params+5
    lda staged_len_hi
    sta file_params+6
    lda #$00
    sta file_params+7
    ldx #file_params
    jsr svc_reu_read_sc0
    lda file_params+7
    sta exec_read_status
    jsr set_runtime_mem_config
    jsr validate_exec_overlay
    bcc validate_exec_ok
    lda #$00
    sta exec_validate_ok
    jmp validate_exec_done
validate_exec_ok:
    lda #$01
    sta exec_validate_ok
validate_exec_done:
    jsr restore_mem_config
    jsr print_exec_line
    jsr print_validate_line

    lda exec_read_status
    cmp #tool_file_status_ok
    bne exec_read_fail
    lda exec_validate_ok
    bne read_ok

exec_read_fail:
    lda #$01
    sta svc_retptr
    lda #$00
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

read_ok:
    lda #$00
    sta svc_retptr
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

validate_exec_overlay:
    lda staged_len_bank
    bne validate_exec_overlay_fail
    lda staged_len_hi
    cmp #EXEC_LIMIT_HI
    bcc :+
    bne validate_exec_overlay_fail
    lda staged_len_lo
    bne validate_exec_overlay_fail
:   lda EXEC_BASE+0
    cmp #'A'
    bne validate_exec_overlay_fail
    lda EXEC_BASE+1
    cmp #'V'
    bne validate_exec_overlay_fail
    lda EXEC_BASE+2
    cmp #'O'
    bne validate_exec_overlay_fail
    lda EXEC_BASE+3
    cmp #'V'
    bne validate_exec_overlay_fail
    lda EXEC_BASE+4
    cmp #AVMRUN_OVERLAY_ABI_VERSION
    bne validate_exec_overlay_fail
    lda EXEC_BASE+5
    cmp #<EXEC_BASE
    bne validate_exec_overlay_fail
    lda EXEC_BASE+6
    cmp #>EXEC_BASE
    bne validate_exec_overlay_fail
    lda EXEC_BASE+9
    cmp staged_len_lo
    bne validate_exec_overlay_fail
    lda EXEC_BASE+10
    cmp staged_len_hi
    bne validate_exec_overlay_fail
    clc
    rts
validate_exec_overlay_fail:
    sec
    rts

stage_overlay_with_shelladd_like_wrapper:
    jsr stage_overlay_with_shelladd_like_wrapper_1
    rts

stage_overlay_with_shelladd_like_wrapper_1:
    jsr stage_overlay_with_shelladd_like_wrapper_2
    rts

stage_overlay_with_shelladd_like_wrapper_2:
    jsr stage_overlay_with_shelladd_like_wrapper_3
    rts

stage_overlay_with_shelladd_like_wrapper_3:
    lda saved_memcfg_abs
    sta TOOL_DEBUG0
    lda C64_MEMCFG
    sta TOOL_DEBUG1
    tsx
    stx TOOL_DEBUG2
    php
    pla
    sta TOOL_DEBUG3
    lda $0101,x
    sta TOOL_DEBUG4
    lda $0102,x
    sta TOOL_DEBUG5
    lda $0103,x
    sta TOOL_DEBUG6
    lda $0104,x
    sta TOOL_DEBUG7
    ldx #file_params
    jsr svc_file_stage_reu_sc0
    rts

seed_avmrun_compat_scratch:
    lda #$56
    sta AVMRUN_PAYLOAD_END_PTR+0
    sta AVMRUN_FILE_END_PTR+0
    lda #$4B
    sta AVMRUN_PAYLOAD_END_PTR+1
    sta AVMRUN_FILE_END_PTR+1
    lda #$36
    sta AVMRUN_SAVED_MEMCFG
    lda #$01
    sta AVMRUN_FLAGS
    lda #$00
    sta AVMRUN_OVERLAY_READY
    sta AVMRUN_OVERLAY_LOADED_KIND
    sta AVMRUN_OVERLAY_LOADED_LEN+0
    sta AVMRUN_OVERLAY_LOADED_LEN+1
    sta AVMRUN_OVERLAY_SERVICE_STATUS
    lda #$03
    sta AVMRUN_OVERLAY_REQUESTED_KIND
    lda #$01
    sta AVMRUN_OVERLAY_REQUESTED_CMD
    rts

set_tool_mem_config:
    lda saved_memcfg_abs
    and #C64_MEMCFG_CONFIG_MASK
    ora #C64_MEMCFG_TOOL_BITS
    sta C64_MEMCFG
    rts

set_runtime_mem_config:
    lda saved_memcfg_abs
    and #C64_MEMCFG_CONFIG_MASK
    ora #C64_MEMCFG_RUNTIME_BITS
    sta C64_MEMCFG
    rts

restore_mem_config:
    lda saved_memcfg_abs
    sta C64_MEMCFG
    rts

fill_bulk_buffer_page:
    ldy #$00
:   sta bulk_buffer,y
    iny
    bne :-
    rts

fill_bulk_buffer:
    dex
    bmi :+
    ldy #$00
:   sta bulk_buffer,y
    iny
    dex
    bpl :-
:   rts

fill_exec_prefix:
    dex
    bmi :+
    ldy #$00
:   sta EXEC_BASE,y
    iny
    dex
    bpl :-
:   rts

copy_first_arg:
    ldy #$00
copy_first_arg_loop:
    lda (src_ptr),y
    beq copy_first_arg_done
    cmp #' '
    beq copy_first_arg_done
    sta filename_buffer,y
    iny
    cpy #63
    bcc copy_first_arg_loop
copy_first_arg_done:
    lda #$00
    sta filename_buffer,y
    rts

copy_default_arg:
    ldy #$00
copy_default_arg_loop:
    lda default_filename,y
    sta filename_buffer,y
    beq copy_default_arg_done
    iny
    bne copy_default_arg_loop
copy_default_arg_done:
    rts

print_stage_line:
    lda #<line_buffer
    sta write_ptr
    lda #>line_buffer
    sta write_ptr+1
    lda #'S'
    jsr append_char_a
    lda #'='
    jsr append_char_a
    lda file_params+5
    jsr append_hex_a
    lda #' '
    jsr append_char_a
    lda staged_len_lo
    jsr append_hex_a
    lda #' '
    jsr append_char_a
    lda staged_len_hi
    jsr append_hex_a
    lda #' '
    jsr append_char_a
    lda staged_len_bank
    jsr append_hex_a
    lda #$00
    jsr append_char_a
    lda #<line_buffer
    ldy #>line_buffer
    jsr print_ptr
    jmp svc_console_newline

print_prefetch_line:
    lda #<line_buffer
    sta write_ptr
    lda #>line_buffer
    sta write_ptr+1
    lda #'P'
    jsr append_char_a
    lda #'='
    jsr append_char_a
    lda prefetch_status
    jsr append_hex_a
    lda #' '
    jsr append_char_a
    lda prefetch_len_lo
    jsr append_hex_a
    lda #' '
    jsr append_char_a
    lda prefetch_len_hi
    jsr append_hex_a
    lda #' '
    jsr append_char_a
    ldx #$00
print_prefetch_line_loop:
    lda AVMRUN_FILE_BUFFER,x
    jsr append_hex_a
    cpx #LOW_HEADER_LEN-1
    beq print_prefetch_line_done
    lda #' '
    jsr append_char_a
    inx
    bne print_prefetch_line_loop
print_prefetch_line_done:
    lda #$00
    jsr append_char_a
    lda #<line_buffer
    ldy #>line_buffer
    jsr print_ptr
    jmp svc_console_newline

print_exec_line:
    lda #<line_buffer
    sta write_ptr
    lda #>line_buffer
    sta write_ptr+1
    lda #'R'
    jsr append_char_a
    lda #'='
    jsr append_char_a
    lda exec_read_status
    jsr append_hex_a
    lda #' '
    jsr append_char_a
    ldx #$00
print_exec_line_loop:
    lda EXEC_BASE,x
    jsr append_hex_a
    cpx #HEADER_READ_LEN-1
    beq print_exec_line_done
    lda #' '
    jsr append_char_a
    inx
    bne print_exec_line_loop
print_exec_line_done:
    lda #$00
    jsr append_char_a
    lda #<line_buffer
    ldy #>line_buffer
    jsr print_ptr
    jmp svc_console_newline

print_low_line:
    lda #<line_buffer
    sta write_ptr
    lda #>line_buffer
    sta write_ptr+1
    lda #'Q'
    jsr append_char_a
    lda #'='
    jsr append_char_a
    lda low_read_status
    jsr append_hex_a
    lda #' '
    jsr append_char_a
    ldx #$00
print_low_line_loop:
    lda bulk_buffer,x
    jsr append_hex_a
    cpx #LOW_HEADER_LEN-1
    beq print_low_line_done
    lda #' '
    jsr append_char_a
    inx
    bne print_low_line_loop
print_low_line_done:
    lda #$00
    jsr append_char_a
    lda #<line_buffer
    ldy #>line_buffer
    jsr print_ptr
    jmp svc_console_newline

print_head_line:
    lda #<line_buffer
    sta write_ptr
    lda #>line_buffer
    sta write_ptr+1
    lda #'H'
    jsr append_char_a
    lda #'='
    jsr append_char_a
    lda head_read_status
    jsr append_hex_a
    lda #' '
    jsr append_char_a
    ldx #$00
print_head_line_loop:
    lda bulk_buffer,x
    jsr append_hex_a
    cpx #LOW_HEADER_LEN-1
    beq print_head_line_done
    lda #' '
    jsr append_char_a
    inx
    bne print_head_line_loop
print_head_line_done:
    lda #$00
    jsr append_char_a
    lda #<line_buffer
    ldy #>line_buffer
    jsr print_ptr
    jmp svc_console_newline

print_validate_line:
    lda #<line_buffer
    sta write_ptr
    lda #>line_buffer
    sta write_ptr+1
    lda #'V'
    jsr append_char_a
    lda #'='
    jsr append_char_a
    lda exec_validate_ok
    jsr append_hex_a
    lda #$00
    jsr append_char_a
    lda #<line_buffer
    ldy #>line_buffer
    jsr print_ptr
    jmp svc_console_newline

append_hex_a:
    sta tmp_byte
    lsr a
    lsr a
    lsr a
    lsr a
    and #$0F
    jsr append_hex_nibble_a
    lda tmp_byte
    and #$0F
append_hex_nibble_a:
    tay
    lda hex_digits,y
    jmp append_char_a

append_char_a:
    ldy #$00
    sta (write_ptr),y
    inc write_ptr
    bne :+
    inc write_ptr+1
:   rts

print_ptr:
    sta svc_retptr
    sty svc_retptr+1
    ldx #svc_retptr
    jmp svc_console_write_sc0

msg_usage:
    .asciiz "USAGE STAGEINFO <FILE>"
default_filename:
    .asciiz "!AVMRUN_OVL3.BIN"
prefetch_filename:
    .asciiz "BIN/SHELLADD.AVM"
hex_digits:
    .byte "0123456789ABCDEF"
filename_buffer:
    .res 64
line_buffer:
    .res 64
bulk_buffer:
    .res $0101
saved_memcfg_abs:
    .byte 0
staged_len_lo:
    .byte 0
staged_len_hi:
    .byte 0
staged_len_bank:
    .byte 0
exec_read_status:
    .byte 0
exec_validate_ok:
    .byte 0
low_read_status:
    .byte 0
head_read_status:
    .byte 0
prefetch_status:
    .byte 0
prefetch_len_lo:
    .byte 0
prefetch_len_hi:
    .byte 0
