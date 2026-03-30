.include "udos_services.inc"

.export start

FILE_PROBE_SIZE = 64

.segment "ZPTEMP": zeropage
svc_retptr:
    .res 2
file_params:
    .res 9
query_params:
    .res 9
save_params:
    .res 7
src_ptr:
    .res 2
name_len:
    .res 1

.code

start:
    ldx #svc_retptr
    jsr svc_program_get_cmdline_len
    lda svc_retptr
    ora svc_retptr+1
    bne have_args
    lda #<msg_no_name
    ldy #>msg_no_name
    jmp fail_with_ptr

have_args:
    ldx #svc_retptr
    jsr svc_program_get_cmdline_ptr
    lda svc_retptr
    sta src_ptr
    lda svc_retptr+1
    sta src_ptr+1
    jsr copy_first_arg
    bcc name_ok
    lda #<msg_bad_name
    ldy #>msg_bad_name
    jmp fail_with_ptr

name_ok:
    jsr verify_project_root
    bcc project_ok
    lda #<msg_no_project
    ldy #>msg_no_project
    jmp fail_with_ptr

project_ok:
    jsr build_target_path
    jsr build_content
    jsr probe_target_path
    lda query_params+6
    cmp #tool_file_status_nofile
    beq save_file
    cmp #tool_file_status_fail
    beq target_fail_status
    cmp #tool_file_status_ok
    beq target_exists
    cmp #tool_file_status_too_large
    beq target_exists
    lda #<msg_load_fail
    ldy #>msg_load_fail
    jmp fail_with_ptr

target_exists:
    lda #<msg_exists
    ldy #>msg_exists
    jmp fail_with_ptr

target_fail_status:
    lda #<msg_probe_fail
    ldy #>msg_probe_fail
    jmp fail_with_ptr

save_file:
    lda #<target_path
    sta save_params+0
    lda #>target_path
    sta save_params+1
    lda #<content_buffer
    sta save_params+2
    lda #>content_buffer
    sta save_params+3
    lda #tool_file_status_fail
    sta save_params+4

    ldx #save_params
    jsr svc_file_save_sc0

    lda save_params+4
    cmp #tool_file_status_ok
    beq save_ok
    lda #<msg_save_fail
    ldy #>msg_save_fail
    jmp fail_with_ptr

save_ok:
    lda #<msg_ok
    ldy #>msg_ok
    jsr print_ptr
    jsr svc_console_newline
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
    cpy #24
    bcs copy_first_arg_fail
    jsr normalize_name_char
    sta module_name,y
    iny
    bne copy_first_arg_loop
copy_first_arg_done:
    cpy #$00
    beq copy_first_arg_fail
    sty name_len
    lda #$00
    sta module_name,y
    clc
    rts
copy_first_arg_fail:
    sec
    rts

normalize_name_char:
    cmp #$01
    bcc normalize_name_ascii
    cmp #$1B
    bcs normalize_name_ascii
    clc
    adc #$40
    rts
normalize_name_ascii:
    cmp #'a'
    bcc :+
    cmp #'z'+1
    bcs :+
    and #$DF
:    
    rts

verify_project_root:
    lda #<project_marker
    sta file_params+0
    lda #>project_marker
    sta file_params+1
    lda #<probe_buffer
    sta file_params+2
    lda #>probe_buffer
    sta file_params+3
    lda #<FILE_PROBE_SIZE
    sta file_params+4
    lda #>FILE_PROBE_SIZE
    sta file_params+5
    lda #$00
    sta file_params+6
    sta file_params+7
    sta file_params+8
    ldx #file_params
    jsr svc_file_load_sc0
    lda file_params+6
    cmp #tool_file_status_ok
    beq :+
    cmp #tool_file_status_too_large
    bne verify_project_root_fail
:    
    clc
    rts
verify_project_root_fail:
    sec
    rts

probe_target_path:
    lda #<target_path
    sta query_params+0
    lda #>target_path
    sta query_params+1
    lda #$00
    sta query_params+2
    sta query_params+3
    sta query_params+4
    sta query_params+5
    sta query_params+6
    sta query_params+7
    sta query_params+8
    ldx #query_params
    jmp svc_file_load_sc0

build_target_path:
    lda #'S'
    sta target_path+0
    lda #'R'
    sta target_path+1
    lda #'C'
    sta target_path+2
    lda #'/'
    sta target_path+3
    ldy #$00
build_target_copy_name:
    lda module_name,y
    beq build_target_suffix
    sta target_path+4,y
    iny
    bne build_target_copy_name
build_target_suffix:
    lda #'.'
    sta target_path+4,y
    iny
    lda #'A'
    sta target_path+4,y
    iny
    lda #'C'
    sta target_path+4,y
    iny
    lda #'T'
    sta target_path+4,y
    iny
    lda #$00
    sta target_path+4,y
    rts

build_content:
    lda #'P'
    sta content_buffer+0
    lda #'R'
    sta content_buffer+1
    lda #'O'
    sta content_buffer+2
    lda #'C'
    sta content_buffer+3
    lda #' '
    sta content_buffer+4
    ldy #$00
build_content_copy_name:
    lda module_name,y
    beq build_content_suffix
    sta content_buffer+5,y
    iny
    bne build_content_copy_name
build_content_suffix:
    lda #'('
    sta content_buffer+5,y
    iny
    lda #')'
    sta content_buffer+5,y
    iny
    lda #13
    sta content_buffer+5,y
    iny
    lda #'E'
    sta content_buffer+5,y
    iny
    lda #'N'
    sta content_buffer+5,y
    iny
    lda #'D'
    sta content_buffer+5,y
    iny
    lda #'P'
    sta content_buffer+5,y
    iny
    lda #'R'
    sta content_buffer+5,y
    iny
    lda #'O'
    sta content_buffer+5,y
    iny
    lda #'C'
    sta content_buffer+5,y
    iny
    lda #13
    sta content_buffer+5,y
    iny
    lda #$00
    sta content_buffer+5,y
    rts

fail_with_ptr:
    jsr print_ptr
    jsr svc_console_newline
    lda #$01
    sta svc_retptr
    lda #$00
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

print_ptr:
    sta svc_retptr
    sty svc_retptr+1
    ldx #svc_retptr
    jmp svc_console_write_sc0

msg_no_name:
    .asciiz "NO NAME"
msg_bad_name:
    .asciiz "BAD NAME"
msg_no_project:
    .asciiz "NO PROJECT"
msg_exists:
    .asciiz "EXISTS"
msg_probe_fail:
    .asciiz "PROBE FAIL"
msg_load_fail:
    .asciiz "LOAD FAIL"
msg_save_fail:
    .asciiz "SAVE FAIL"
msg_ok:
    .asciiz "ACTADD OK"
project_marker:
    .asciiz "ACTION.PROJ"
module_name:
    .res 25
target_path:
    .res 40
content_buffer:
    .res 64
probe_buffer:
    .res FILE_PROBE_SIZE
