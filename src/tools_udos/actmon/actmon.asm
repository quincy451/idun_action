.include "udos_services.inc"

.export start

MANIFEST_LIMIT = 191
SOURCE_LIMIT = 191

FLAG_PROJECT = $01
FLAG_SRC = $02
FLAG_BIN = $04
FLAG_OBJ = $08
FLAG_TRUNCATED = $10
ACTION_PROJECT_FLAG_TRUNCATED = FLAG_TRUNCATED

.segment "ZPTEMP": zeropage
svc_retptr:
    .res 2
file_params:
    .res 9
entry_ptr:
    .res 2
const_ptr:
    .res 2
scan_ptr:
    .res 2
status_flags:
    .res 1
module_count:
    .res 1
count_work:
    .res 1
compare_char:
    .res 1
src_ptr:
    .res 2
line_len:
    .res 1

save_params = file_params

.code

start:
    ldx #svc_retptr
    jsr svc_program_get_cmdline_len
    lda svc_retptr
    ora svc_retptr+1
    bne have_args
    jsr print_help
    jmp report_ok

have_args:
    ldx #svc_retptr
    jsr svc_program_get_cmdline_ptr
    lda svc_retptr
    sta src_ptr
    lda svc_retptr+1
    sta src_ptr+1
    jsr skip_cmd_spaces
    jsr copy_command_token
    lda command_buffer
    bne dispatch_command
    jsr print_help
    jmp report_ok

dispatch_command:
    jsr skip_cmd_spaces

    lda #<cmd_help
    ldy #>cmd_help
    jsr token_equals_const
    bcs check_work
    jsr print_help
    jmp report_ok

check_work:
    lda #<cmd_work
    ldy #>cmd_work
    jsr token_equals_const
    bcs check_check
    jsr do_work
    jmp report_ok

check_check:
    lda #<cmd_check
    ldy #>cmd_check
    jsr token_equals_const
    bcs check_src
    jsr do_check
    jmp report_ok

check_src:
    lda #<cmd_src
    ldy #>cmd_src
    jsr token_equals_const
    bcs check_file
    jsr do_src
    jmp report_ok

check_file:
    lda #<cmd_file
    ldy #>cmd_file
    jsr token_equals_const
    bcs check_add
    jsr do_file
    jmp report_ok

check_add:
    lda #<cmd_add
    ldy #>cmd_add
    jsr token_equals_const
    bcs check_del
    jsr do_add
    jmp report_ok

check_del:
    lda #<cmd_del
    ldy #>cmd_del
    jsr token_equals_const
    bcs check_ren
    jsr do_del
    jmp report_ok

check_ren:
    lda #<cmd_ren
    ldy #>cmd_ren
    jsr token_equals_const
    bcs check_copy
    jsr do_ren
    jmp report_ok

check_copy:
    lda #<cmd_copy
    ldy #>cmd_copy
    jsr token_equals_const
    bcs check_save
    jsr do_copy
    jmp report_ok

check_save:
    lda #<cmd_save
    ldy #>cmd_save
    jsr token_equals_const
    bcs unknown_command
    jsr do_save
    jmp report_ok

unknown_command:
    lda #<msg_unknown
    ldy #>msg_unknown
    jmp fail_with_ptr

do_work:
    lda #$00
    sta status_flags
    sta module_count
    jsr load_project_manifest
    bcc do_work_manifest_ready
    lda file_params+6
    cmp #tool_file_status_nofile
    beq do_work_no_manifest
    lda #<msg_load_fail
    ldy #>msg_load_fail
    jmp fail_with_ptr

do_work_manifest_ready:
    lda status_flags
    ora #FLAG_PROJECT
    sta status_flags
    jsr count_manifest_entries

do_work_no_manifest:
    jsr scan_current_dir
    jsr print_work_summary
    rts

do_check:
    lda #$00
    sta status_flags
    sta module_count
    sta missing_count
    sta save_mode
    jsr require_loaded_project
    lda status_flags
    ora #FLAG_PROJECT
    sta status_flags
    jsr count_manifest_entries
    jsr scan_current_dir
    jsr count_missing_entries
    jsr print_work_summary
    jsr print_missing_count_line

    lda status_flags
    and #FLAG_SRC|FLAG_BIN|FLAG_OBJ
    cmp #FLAG_SRC|FLAG_BIN|FLAG_OBJ
    beq :+
    lda #$01
    sta save_mode
:   lda missing_count
    beq :+
    lda #$01
    sta save_mode
    jsr print_missing_entries
:   lda save_mode
    beq do_check_done
    lda #<msg_broken
    ldy #>msg_broken
    jmp fail_with_ptr

do_check_done:
    rts

do_src:
    lda #$00
    sta status_flags
    jsr require_loaded_project
    jsr begin_manifest_scan
    jsr manifest_scan_has_entry
    bcc do_src_have_entries
    lda #<msg_empty
    ldy #>msg_empty
    jsr print_line_ptr
    rts

do_src_have_entries:
do_src_print_loop:
    jsr copy_manifest_line_to_buffer
    bcc do_src_print_line
    rts

do_src_print_line:
    lda #<line_buffer
    ldy #>line_buffer
    jsr print_line_ptr
    jsr skip_line_breaks
    ldy #$00
    lda (scan_ptr),y
    bne do_src_print_loop
    rts

do_file:
    lda #$00
    sta status_flags
    jsr require_module_arg
    jsr build_manifest_entry
    jsr require_loaded_project
    jsr require_manifest_entry_tracked
    jsr build_target_path
    jsr load_source_file
    bcc do_file_source_ready
    lda file_params+6
    cmp #tool_file_status_nofile
    beq do_file_missing_source
    lda #<msg_load_fail
    ldy #>msg_load_fail
    jmp fail_with_ptr

do_file_missing_source:
    lda #<msg_no_file
    ldy #>msg_no_file
    jmp fail_with_ptr

do_file_source_ready:
    lda #<source_buffer
    ldy #>source_buffer
    jsr print_line_ptr
    lda truncated_flag
    beq do_file_done
    lda #<msg_truncated
    ldy #>msg_truncated
    jsr print_line_ptr
do_file_done:
    rts

do_add:
    lda #$00
    sta status_flags
    jsr require_module_arg
    jsr build_manifest_entry
    jsr require_loaded_project
    jsr require_manifest_entry_missing
    jsr build_target_path
    jsr require_target_missing

do_add_create:
    jsr save_stub_content_to_target_or_fail

do_add_saved:
    jsr append_manifest_entry_and_save
    bcc do_add_done
    lda #<msg_save_fail
    ldy #>msg_save_fail
    jmp fail_with_ptr

do_add_done:
    lda #<msg_created
    ldy #>msg_created
    jsr print_line_ptr
    rts

do_del:
    lda #$00
    sta status_flags
    jsr require_module_arg
    jsr build_manifest_entry
    jsr require_loaded_project
    jsr require_manifest_entry_tracked
    jsr remove_manifest_entry_and_save
    bcc do_del_manifest_saved
    lda #<msg_save_fail
    ldy #>msg_save_fail
    jmp fail_with_ptr

do_del_manifest_saved:
    jsr build_target_path
    jsr delete_target_path
    lda file_params+2
    cmp #tool_file_status_ok
    beq do_del_done
    cmp #tool_file_status_nofile
    beq do_del_done
    lda #<msg_del_fail
    ldy #>msg_del_fail
    jmp fail_with_ptr

do_del_done:
    lda #<msg_removed
    ldy #>msg_removed
    jsr print_line_ptr
    rts

do_ren:
    lda #$00
    sta status_flags
    jsr require_module_arg
    jsr build_manifest_entry
    jsr require_loaded_project
    jsr require_manifest_entry_tracked
    jsr build_target_path
    jsr copy_manifest_entry_to_old_manifest
    jsr copy_target_path_to_old_target
    jsr skip_module_arg_token
    jsr skip_cmd_spaces
    jsr require_module_arg
    jsr build_manifest_entry
    jsr require_manifest_entry_missing
    jsr build_target_path
    jsr require_target_missing
    jsr rename_old_target_or_fail
    jsr replace_old_manifest_entry_and_save_or_rollback

do_ren_done:
    lda #<msg_renamed
    ldy #>msg_renamed
    jsr print_line_ptr
    rts

do_copy:
    lda #$00
    sta status_flags
    jsr require_module_arg
    jsr build_manifest_entry
    jsr require_loaded_project
    jsr require_manifest_entry_tracked
    jsr build_target_path
    jsr copy_target_path_to_old_target
    jsr skip_module_arg_token
    jsr skip_cmd_spaces
    jsr require_module_arg
    jsr build_manifest_entry
    jsr require_manifest_entry_missing
    jsr build_target_path
    jsr require_target_missing
    jsr copy_old_target_or_fail
    jsr append_manifest_entry_and_save_or_delete_target

do_copy_done:
    lda #<msg_copied
    ldy #>msg_copied
    jsr print_line_ptr
    rts

do_save:
    lda #$00
    sta status_flags
    jsr require_module_arg
    jsr build_manifest_entry
    jsr require_loaded_project
    jsr require_manifest_entry_tracked
    jsr build_target_path
    jsr probe_target_save_mode_or_fail
    jsr save_stub_content_to_target_or_fail
    jsr report_save_mode_result
    rts

require_module_arg:
    ldy #$00
    lda (src_ptr),y
    beq require_module_arg_missing
    jsr copy_module_arg
    bcc require_module_arg_done
    lda #<msg_bad_name
    ldy #>msg_bad_name
    jmp fail_with_ptr
require_module_arg_missing:
    lda #<msg_no_name
    ldy #>msg_no_name
    jmp fail_with_ptr
require_module_arg_done:
    rts

skip_module_arg_token:
    ldy #$00
skip_module_arg_token_loop:
    lda (src_ptr),y
    beq skip_module_arg_token_done
    cmp #' '
    beq skip_module_arg_token_done
    jsr advance_src_ptr
    jmp skip_module_arg_token_loop
skip_module_arg_token_done:
    rts

skip_cmd_spaces:
    ldy #$00
skip_cmd_spaces_loop:
    lda (src_ptr),y
    cmp #' '
    bne skip_cmd_spaces_done
    jsr advance_src_ptr
    jmp skip_cmd_spaces_loop
skip_cmd_spaces_done:
    rts

copy_command_token:
    ldx #$00
copy_command_token_loop:
    ldy #$00
    lda (src_ptr),y
    beq copy_command_token_done
    cmp #' '
    beq copy_command_token_done
    cpx #7
    bcs copy_command_token_overflow
    jsr normalize_module_arg_char
    sta command_buffer,x
    inx
    jsr advance_src_ptr
    jmp copy_command_token_loop
copy_command_token_overflow:
    lda #$00
    sta command_buffer
    rts
copy_command_token_done:
    lda #$00
    sta command_buffer,x
    rts

token_equals_const:
    sta const_ptr
    sty const_ptr+1
    ldy #$00
token_equals_const_loop:
    lda command_buffer,y
    cmp (const_ptr),y
    bne token_equals_const_fail
    cmp #$00
    beq token_equals_const_ok
    iny
    cpy #8
    bcc token_equals_const_loop
token_equals_const_fail:
    sec
    rts
token_equals_const_ok:
    clc
    rts

.include "../common/action_project_module_arg.inc"
.include "../common/action_project_load.inc"
.include "../common/action_project_load_guard.inc"
.include "../common/action_project_count.inc"
.include "../common/action_project_entry.inc"
.include "../common/action_project_entry_guard.inc"
.include "../common/action_project_create_guard.inc"
.include "../common/action_project_manifest_commit.inc"
.include "../common/action_project_manifest_replace.inc"
.include "../common/action_project_manifest_rollback.inc"
.include "../common/action_project_path.inc"
.include "../common/action_project_save_mode.inc"
.include "../common/action_project_save_write.inc"
.include "../common/action_project_source.inc"
.include "../common/action_project_stub_source.inc"
.include "../common/action_project_mutate.inc"
.include "../common/action_project_work_summary.inc"
.include "../common/action_project_manifest_scan.inc"
.include "../common/action_project_check.inc"
.include "../common/action_project_transfer.inc"
.include "../common/action_project_transfer_guard.inc"

advance_src_ptr:
    inc src_ptr
    bne :+
    inc src_ptr+1
:
    rts

advance_entry_ptr:
    inc entry_ptr
    bne :+
    inc entry_ptr+1
:
    rts

print_help:
    lda #<msg_help_text
    ldy #>msg_help_text
    jmp print_ptr

report_ok:
    lda #<msg_ok
    ldy #>msg_ok
    jsr print_line_ptr
    lda #$00
    sta svc_retptr
    sta svc_retptr+1
    ldx #svc_retptr
    jmp svc_program_exit

print_line_ptr:
    jsr print_ptr
    jmp svc_console_newline

fail_with_ptr:
    jsr print_line_ptr
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

cmd_help:
    .asciiz "HELP"
cmd_work:
    .asciiz "WORK"
cmd_check:
    .asciiz "CHECK"
cmd_src:
    .asciiz "SRC"
cmd_file:
    .asciiz "FILE"
cmd_add:
    .asciiz "ADD"
cmd_del:
    .asciiz "DEL"
cmd_ren:
    .asciiz "REN"
cmd_copy:
    .asciiz "COPY"
cmd_save:
    .asciiz "SAVE"

msg_unknown:
    .asciiz "UNKNOWN"
msg_no_name:
    .asciiz "NO NAME"
msg_bad_name:
    .asciiz "BAD NAME"
msg_no_project:
    .asciiz "NO PROJECT"
msg_not_in_project:
    .asciiz "NOT IN PROJECT"
msg_no_file:
    .asciiz "NO FILE"
msg_load_fail:
    .asciiz "LOAD FAIL"
msg_probe_fail:
    .asciiz "PROBE FAIL"
msg_missing_prefix:
    .asciiz "MISSING "
msg_del_fail:
    .asciiz "DEL FAIL"
msg_ren_fail:
    .asciiz "REN FAIL"
msg_copy_fail:
    .asciiz "COPY FAIL"
msg_save_fail:
    .asciiz "SAVE FAIL"
msg_broken:
    .asciiz "ACTMON BROKEN"
msg_exists:
    .asciiz "EXISTS"
msg_empty:
    .asciiz "EMPTY"
msg_truncated:
    .asciiz "TRUNCATED"
msg_created:
    .asciiz "CREATED"
msg_removed:
    .asciiz "REMOVED"
msg_renamed:
    .asciiz "RENAMED"
msg_copied:
    .asciiz "COPIED"
msg_updated:
    .asciiz "UPDATED"
msg_project_prefix:
    .asciiz "PROJECT "
msg_src_prefix:
    .asciiz "SRC "
msg_bin_prefix:
    .asciiz "BIN "
msg_obj_prefix:
    .asciiz "OBJ "
msg_modules_prefix:
    .asciiz "MODULES "
msg_yes:
    .asciiz "YES"
msg_no:
    .asciiz "NO"
msg_help_text:
    .byte "WORK",$0D
    .byte "CHECK",$0D
    .byte "SRC",$0D
    .byte "FILE NAME",$0D
    .byte "ADD NAME",$0D
    .byte "DEL NAME",$0D
    .byte "REN OLD NEW",$0D
    .byte "COPY OLD NEW",$0D
    .byte "SAVE NAME",$0D
    .byte "HELP",$0D,$00
msg_ok:
    .asciiz "ACTMON OK"
truncated_flag:
    .byte 0
save_mode:
    .byte 0
missing_count:
    .byte 0
project_marker:
    .asciiz "ACTION.PROJ"
src_dir_name:
    .asciiz "SRC/"
bin_dir_name:
    .asciiz "BIN/"
obj_dir_name:
    .asciiz "OBJ/"
command_buffer:
    .res 8
module_name:
    .res 25
manifest_entry:
    .res 32
old_manifest_entry:
    .res 32
target_path:
    .res 36
old_target_path:
    .res 36
line_buffer:
    .res 29
count_buffer:
    .res 4
content_buffer:
    .res 48
manifest_buffer:
    .res 192
source_buffer:
    .res 192
