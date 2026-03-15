.include "udos_services.inc"

.export start

FILE_BUFFER_SIZE = 1024

.segment "ZPTEMP": zeropage
svc_retptr:
    .res 2
file_params:
    .res 9
src_ptr:
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
    jsr print_ptr
    jsr svc_console_newline
    lda #$01
    sta svc_retptr
    lda #$00
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

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
    bne show_error

show_no_file:
    lda #<msg_no_file
    ldy #>msg_no_file
    bne show_error

show_too_large:
    lda #<msg_too_large
    ldy #>msg_too_large

show_error:
    jsr print_ptr
    jsr svc_console_newline
    lda #$01
    sta svc_retptr
    lda #$00
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

file_loaded:
    lda file_buffer+0
    cmp #'A'
    bne bad_avm
    lda file_buffer+1
    cmp #'V'
    bne bad_avm
    lda file_buffer+2
    cmp #'M'
    bne bad_avm
    lda file_buffer+3
    cmp #'1'
    bne bad_avm

    lda #<msg_ok
    ldy #>msg_ok
    jsr print_ptr
    jsr svc_console_newline
    lda #$00
    sta svc_retptr
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

bad_avm:
    lda #<msg_bad_avm
    ldy #>msg_bad_avm
    jsr print_ptr
    jsr svc_console_newline
    lda #$01
    sta svc_retptr
    lda #$00
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

msg_ok:
    .asciiz "AVM OK"
msg_bad_avm:
    .asciiz "BAD AVM"
msg_no_file:
    .asciiz "NO FILE"
msg_too_large:
    .asciiz "TOO LARGE"
msg_load_fail:
    .asciiz "LOAD FAIL"
filename_buffer:
    .res 32
file_buffer:
    .res FILE_BUFFER_SIZE
