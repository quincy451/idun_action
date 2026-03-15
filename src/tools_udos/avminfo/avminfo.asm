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

    lda #<msg_version
    ldy #>msg_version
    jsr print_ptr
    lda file_buffer+4
    sta svc_retptr
    lda #$00
    sta svc_retptr+1
    jsr print_dec16_zp

    lda #<msg_payload
    ldy #>msg_payload
    jsr print_ptr
    lda file_buffer+5
    sta svc_retptr
    lda file_buffer+6
    sta svc_retptr+1
    jsr print_dec16_zp

    lda #<msg_entry
    ldy #>msg_entry
    jsr print_ptr
    lda file_buffer+7
    sta svc_retptr
    lda file_buffer+8
    sta svc_retptr+1
    jsr print_dec16_zp
    jsr svc_console_newline

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

print_dec16_zp:
    lda svc_retptr
    sta value_lo
    lda svc_retptr+1
    sta value_hi
    ldx #$00
thousands_loop:
    lda value_hi
    cmp #>1000
    bcc hundreds_start
    bne thousands_sub
    lda value_lo
    cmp #<1000
    bcc hundreds_start
thousands_sub:
    sec
    lda value_lo
    sbc #<1000
    sta value_lo
    lda value_hi
    sbc #>1000
    sta value_hi
    inx
    bne thousands_loop
hundreds_start:
    txa
    ldy #$00
    jsr emit_digit_if_needed
    ldx #$00
hundreds_loop:
    lda value_hi
    cmp #>100
    bcc tens_start
    bne hundreds_sub
    lda value_lo
    cmp #<100
    bcc tens_start
hundreds_sub:
    sec
    lda value_lo
    sbc #<100
    sta value_lo
    lda value_hi
    sbc #>100
    sta value_hi
    inx
    bne hundreds_loop
tens_start:
    txa
    jsr emit_digit_if_needed
    ldx #$00
tens_loop:
    lda value_hi
    bne tens_sub
    lda value_lo
    cmp #10
    bcc ones_digit
tens_sub:
    sec
    lda value_lo
    sbc #10
    sta value_lo
    lda value_hi
    sbc #0
    sta value_hi
    inx
    bne tens_loop
ones_digit:
    txa
    jsr emit_digit_if_needed
    lda value_lo
    clc
    adc #'0'
    jmp emit_char

emit_digit_if_needed:
    pha
    cpy #$00
    bne emit_digit_now
    pla
    beq emit_digit_skip
    pha
emit_digit_now:
    pla
    clc
    adc #'0'
    jsr emit_char
    ldy #$01
    rts
emit_digit_skip:
    rts

emit_char:
    sta char_buf
    lda #<char_buf
    sta svc_retptr
    lda #>char_buf
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_console_write_sc0

msg_version:
    .asciiz "AVM VERSION "
msg_payload:
    .asciiz " PAYLOAD "
msg_entry:
    .asciiz " ENTRY "
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
char_buf:
    .byte 0, 0
value_lo:
    .byte 0
value_hi:
    .byte 0
filename_buffer:
    .res 32
file_buffer:
    .res FILE_BUFFER_SIZE
