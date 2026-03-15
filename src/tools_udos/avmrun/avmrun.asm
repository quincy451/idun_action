.include "udos_services.inc"

.import acheron
.import clear_rstack

.export start

.segment "STARTUP"
    jmp start

AVM_HEADER_SIZE = 10
AVM_FLAG_ACHERON = 1
FILE_BUFFER_SIZE = 2048

OPCODE_NATIVE = $2D
OPCODE_CALLN = $49
OPCODE_SETP16 = $61

INTRINSIC_PRINT = $FF00
INTRINSIC_PRINTE = $FF10
INTRINSIC_EXIT = $FF20

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

.code

start:
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
    bne fail_with_ptr

show_no_file:
    lda #<msg_no_file
    ldy #>msg_no_file
    bne fail_with_ptr

show_too_large:
    lda #<msg_too_large
    ldy #>msg_too_large
    bne fail_with_ptr

file_loaded:
    jsr validate_header
    bcc header_ok
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    bne fail_with_ptr

header_ok:
    jsr patch_payload
    bcc payload_ready
    lda #<msg_unsupported
    ldy #>msg_unsupported
    bne fail_with_ptr

payload_ready:
    jsr clear_rstack
    sec
    lda entry_ptr
    sbc #$01
    sta word_tmp
    lda entry_ptr+1
    sbc #$00
    sta word_tmp+1
    lda word_tmp+1
    pha
    lda word_tmp
    pha
    jmp acheron

fail_with_ptr:
    jsr print_ptr
    jsr svc_console_newline
    lda #$01
    sta svc_retptr
    lda #$00
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

validate_header:
    lda file_buffer+0
    cmp #'A'
    bne validate_header_fail
    lda file_buffer+1
    cmp #'V'
    bne validate_header_fail
    lda file_buffer+2
    cmp #'M'
    bne validate_header_fail
    lda file_buffer+3
    cmp #'1'
    bne validate_header_fail
    lda file_buffer+4
    cmp #$01
    bne validate_header_fail
    lda file_buffer+9
    cmp #AVM_FLAG_ACHERON
    bne validate_header_fail
    lda file_buffer+7
    sta word_tmp
    lda file_buffer+8
    sta word_tmp+1
    lda file_buffer+5
    sta scan_end
    lda file_buffer+6
    sta scan_end+1
    lda word_tmp+1
    cmp scan_end+1
    bcc :+
    bne validate_header_fail
    lda word_tmp
    cmp scan_end
    bcs validate_header_fail
:
    lda #<(file_buffer + AVM_HEADER_SIZE)
    sta payload_ptr
    lda #>(file_buffer + AVM_HEADER_SIZE)
    sta payload_ptr+1
    clc
    lda payload_ptr
    adc file_buffer+5
    sta scan_end
    lda payload_ptr+1
    adc file_buffer+6
    sta scan_end+1
    sec
    lda payload_ptr
    adc word_tmp
    sta entry_ptr
    lda payload_ptr+1
    adc word_tmp+1
    sta entry_ptr+1
    sec
    lda entry_ptr
    sbc #$01
    sta entry_ptr
    lda entry_ptr+1
    sbc #$00
    sta entry_ptr+1
    clc
    rts

validate_header_fail:
    sec
    rts

patch_payload:
    lda payload_ptr
    sta scan_ptr
    lda payload_ptr+1
    sta scan_ptr+1
patch_payload_loop:
    jsr scan_ptr_before_end
    bcc :+
    jmp patch_payload_fail
:
    ldy #$00
    lda (scan_ptr),y
    cmp #OPCODE_NATIVE
    bne :+
    jmp patch_payload_done
:
    cmp #OPCODE_SETP16
    beq patch_setp16
    cmp #OPCODE_CALLN
    beq patch_calln
    sec
    rts

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
    bcs patch_payload_fail
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
    beq patch_calln_print
patch_check_printe:
    lda word_tmp
    cmp #<INTRINSIC_PRINTE
    bne patch_check_exit
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTE
    beq patch_calln_printe
patch_check_exit:
    lda word_tmp
    cmp #<INTRINSIC_EXIT
    bne patch_payload_fail
    lda word_tmp+1
    cmp #>INTRINSIC_EXIT
    bne patch_payload_fail
    lda #<native_exit
    sta word_tmp
    lda #>native_exit
    sta word_tmp+1
    bne patch_calln_store
patch_calln_print:
    lda #<native_print
    sta word_tmp
    lda #>native_print
    sta word_tmp+1
    bne patch_calln_store
patch_calln_printe:
    lda #<native_printe
    sta word_tmp
    lda #>native_printe
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

advance_scan_ptr:
    clc
    adc scan_ptr
    sta scan_ptr
    bcc :+
    inc scan_ptr+1
:
    rts

native_print:
    lda 0,x
    sta svc_retptr
    lda 1,x
    sta svc_retptr+1
    ldx #svc_retptr
    jsr svc_console_write_sc0
    rts

native_printe:
    jsr native_print
    jsr svc_console_newline
    rts

native_exit:
    lda #$00
    sta svc_retptr
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

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

print_ptr:
    sta svc_retptr
    sty svc_retptr+1
    ldx #svc_retptr
    jmp svc_console_write_sc0

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

filename_buffer:
    .res 32
file_buffer:
    .res FILE_BUFFER_SIZE
