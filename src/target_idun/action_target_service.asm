; ActionC64U Idun target service
; Copyright 2026 ActionC64U contributors. MIT License.
;
; This is an Idun shell tool, not a Commodore PRG. It opens the type-8
; local Unix-socket device, relocates to $c000-$cfff, and then no longer
; depends on the Idun kernel. The Linux ACTDBG/ACTPROF client uploads the
; target PRG through the IDBG protocol before asking it to run.
;
; The low-level Idun I/O sequence follows the MIT-licensed Idun kernel
; implementation in cbm/idun-io.asm and cbm/sys/acepid.asm.

!source "idun_ace_api.inc"

SERVICE_BASE = $c000
SERVICE_LIMIT = $d000
SOCKET_CHANNEL = 27

MSG_HELLO       = 1
MSG_TARGET_INFO = 2
MSG_READ_MEMORY = 3
MSG_WRITE_MEMORY = 4
MSG_READ_REGISTERS = 5
MSG_WRITE_REGISTERS = 6
MSG_HALT        = 7
MSG_RUN         = 8
MSG_STEP        = 9
MSG_BREAK_SET   = 10
MSG_BREAK_CLEAR = 11
MSG_BREAK_LIST  = 12
MSG_SAMPLE_CONFIG = 13
MSG_SAMPLE_READ = 14
MSG_PING        = 15
MSG_RESET       = 16

EVENT_STOPPED   = 64
EVENT_BREAKPOINT = 65
EVENT_TARGET_EXIT = 66
EVENT_TARGET_FAULT = 67

FLAG_RESPONSE = 1
FLAG_EVENT = 2
FLAG_ERROR = 4

STATUS_OK = 0
STATUS_BAD_PACKET = 1
STATUS_UNSUPPORTED = 2
STATUS_BAD_ARGUMENT = 3
STATUS_UNSAFE_ADDRESS = 4
STATUS_BAD_STATE = 5
STATUS_NO_BREAKPOINT = 6
STATUS_NOT_FOUND = 7

CAPABILITIES = $005f ; memory, registers, run/halt, breakpoints, sampling, step
MAX_PAYLOAD = 240
MAX_BREAKPOINTS = 8
MAX_SAMPLES = 100

!macro jne .target {
    beq +
    jmp .target
+
}

!macro jeq .target {
    bne +
    jmp .target
+
}

!macro jcs .target {
    bcc +
    jmp .target
+
}

!macro jcc .target {
    bcs +
    jmp .target
+
}

* = aceToolAddress

    jmp loader_main
    !byte aceID1, aceID2, aceID3
    !byte 64, 0

loader_main:
    lda aceArgc+1
    bne loader_have_arg
    lda aceArgc
    cmp #2
    bcs loader_have_arg
    jmp loader_fail
loader_have_arg:
    lda #1
    ldy #0
    jsr loader_getarg
    lda zp
    ora zp+1
    beq loader_fail
    jsr loader_open_socket
    bcs loader_fail
    sta loader_socket_lfn

    lda #<resident_source
    sta zp
    lda #>resident_source
    sta zp+1
    lda #<SERVICE_BASE
    sta zw
    lda #>SERVICE_BASE
    sta zw+1
    lda #<RESIDENT_SIZE
    sta mp
    lda #>RESIDENT_SIZE
    sta mp+1
    ldy #0
loader_copy:
    lda (zp),y
    sta (zw),y
    inc zp
    bne loader_copy_src_ok
    inc zp+1
loader_copy_src_ok:
    inc zw
    bne loader_copy_dst_ok
    inc zw+1
loader_copy_dst_ok:
    lda mp
    bne loader_copy_low
    dec mp+1
loader_copy_low:
    dec mp
    lda mp
    ora mp+1
    bne loader_copy
    lda loader_socket_lfn
    jmp SERVICE_BASE

loader_fail:
    lda #1
    ldx #0
    jmp aceProcExit

; Return argv[A] in (zp), matching the public ACE argv representation.
loader_getarg:
    sty zp+1
    asl
    sta zp
    rol zp+1
    clc
    lda aceArgv
    adc zp
    sta zp
    lda aceArgv+1
    adc zp+1
    sta zp+1
    ldy #0
    lda (zp),y
    tax
    iny
    lda (zp),y
    stx zp
    sta zp+1
    ora zp
    rts

; Open "[:<pid>" through the public Idun API so device parsing and logical-file
; allocation remain kernel-version compatible. (zp) points at the decimal PID
; argument. Return the allocated logical file number in A.
loader_open_socket:
    ldy #0
    ldx #2
loader_open_name:
    lda (zp),y
    sta loader_socket_name,x
    beq loader_open_call
    iny
    inx
    bne loader_open_name
    sec
    rts
loader_open_call:
    lda #<loader_socket_name
    sta zp
    lda #>loader_socket_name
    sta zp+1
    lda #"+"
    jsr open
    bcs loader_open_done
    tax
    lda lftable,x
    clc
loader_open_done:
    rts

loader_socket_name:
    !pet "[:"
    !fill 12, 0
loader_socket_lfn:
    !byte 0

resident_source = *
!pseudopc SERVICE_BASE {

resident_entry:
    sei
    sta socket_lfn
    ldx #7
resident_save_initial_zp:
    lda $02,x
    sta saved_zp,x
    dex
    bpl resident_save_initial_zp
    lda #0
    sta target_a
    sta target_x
    sta target_y
    sta target_pc
    sta target_pc+1
    sta target_state
    sta sample_enabled
    sta sample_count
    sta rx_selected
    sta resume_after_reply
    sta event_pending
    sta step_active
    sta step_temp_armed
    sta step_auto_continue
    lda #$ff
    sta step_rearm_index
    lda #0
    lda #$fd
    sta target_sp
    lda #$20
    sta target_status
    lda #$01
    sta next_breakpoint_id
    ldx #MAX_BREAKPOINTS-1
resident_clear_breakpoints:
    lda #0
    sta breakpoint_id,x
    sta breakpoint_armed,x
    dex
    bpl resident_clear_breakpoints
    lda #<(target_exit_stub-1)
    sta $01fe
    lda #>(target_exit_stub-1)
    sta $01ff
    jmp command_loop

command_loop:
    sei
    lda event_pending
    beq command_receive
    jsr send_pending_event
command_receive:
    jsr receive_packet
    bcc command_dispatch
    lda #0
    sta response_data_len
    lda #STATUS_BAD_PACKET
    jmp reply_status

command_dispatch:
    lda packet+6
    sec
    sbc #1
    cmp #16
    bcs command_unsupported
    asl
    tax
    lda command_table+1,x
    pha
    lda command_table,x
    pha
    rts
command_table:
    !word command_hello-1
    !word command_target_info-1
    !word command_read_memory-1
    !word command_write_memory-1
    !word command_read_registers-1
    !word command_write_registers-1
    !word command_halt-1
    !word command_run-1
    !word command_step-1
    !word command_break_set-1
    !word command_break_clear-1
    !word command_break_list-1
    !word command_sample_config-1
    !word command_sample_read-1
    !word command_ping-1
    !word command_reset-1
command_unsupported:
    lda #0
    sta response_data_len
    lda #STATUS_UNSUPPORTED
    jmp reply_status

command_require_empty:
    lda packet+10
    ora packet+11
    rts

command_hello:
    jsr command_require_empty
    +jne command_bad_argument
    lda #MAX_PAYLOAD
    sta packet+15
    lda #0
    sta packet+16
    lda #<CAPABILITIES
    sta packet+17
    lda #>CAPABILITIES
    sta packet+18
    lda #<SERVICE_BASE
    sta packet+19
    lda #>SERVICE_BASE
    sta packet+20
    lda #<(SERVICE_LIMIT-1)
    sta packet+21
    lda #>(SERVICE_LIMIT-1)
    sta packet+22
    lda #8
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_target_info:
    jsr command_require_empty
    +jne command_bad_argument
    lda target_state
    sta packet+15
    lda target_pc
    sta packet+16
    lda target_pc+1
    sta packet+17
    lda #<SERVICE_BASE
    sta packet+18
    lda #>SERVICE_BASE
    sta packet+19
    lda #<(SERVICE_LIMIT-1)
    sta packet+20
    lda #>(SERVICE_LIMIT-1)
    sta packet+21
    lda #7
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_read_memory:
    lda packet+10
    cmp #3
    +jne command_bad_argument
    lda packet+11
    +jne command_bad_argument
    lda packet+16
    +jeq command_bad_argument
    cmp #MAX_PAYLOAD
    +jcs command_bad_argument
    sta transfer_count
    lda packet+14
    sta $02
    lda packet+15
    sta $03
    clc
    lda $02
    adc transfer_count
    lda $03
    adc #0
    +jcs command_unsafe_address
    ldy #0
    ldx #0
command_read_memory_loop:
    lda ($02),y
    sta packet+15,x
    iny
    inx
    cpx transfer_count
    bne command_read_memory_loop
    lda transfer_count
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_write_memory:
    lda packet+11
    +jne command_bad_argument
    lda packet+10
    cmp #4
    +jcc command_bad_argument
    lda packet+16
    +jeq command_bad_argument
    sta transfer_count
    clc
    adc #3
    cmp packet+10
    +jne command_bad_argument
    lda packet+14
    sta $02
    sta transfer_begin
    lda packet+15
    sta $03
    sta transfer_begin+1
    clc
    lda $02
    adc transfer_count
    sta transfer_end
    lda $03
    adc #0
    sta transfer_end+1
    +jcs command_unsafe_address
    jsr transfer_overlaps_service
    +jcs command_unsafe_address
    lda transfer_end+1
    cmp #$d0
    bcc command_write_memory_safe
    +jne command_unsafe_address
    lda transfer_end
    +jne command_unsafe_address
command_write_memory_safe:
    ldy #0
    ldx #0
command_write_memory_loop:
    lda packet+17,x
    sta ($02),y
    iny
    inx
    cpx transfer_count
    bne command_write_memory_loop
    lda #0
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

; Carry set when [transfer_begin, transfer_end) intersects the service.
transfer_overlaps_service:
    lda transfer_begin+1
    cmp #>SERVICE_LIMIT
    bcs transfer_no_overlap
    lda transfer_end+1
    cmp #>SERVICE_BASE
    bcc transfer_no_overlap
    bne transfer_overlap
    lda transfer_end
    cmp #<SERVICE_BASE
    beq transfer_no_overlap
transfer_overlap:
    sec
    rts
transfer_no_overlap:
    clc
    rts

command_read_registers:
    jsr command_require_empty
    +jne command_bad_argument
    lda target_a
    sta packet+15
    lda target_x
    sta packet+16
    lda target_y
    sta packet+17
    lda target_sp
    sta packet+18
    lda target_status
    sta packet+19
    lda target_pc
    sta packet+20
    lda target_pc+1
    sta packet+21
    lda target_state
    sta packet+22
    lda #8
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_write_registers:
    lda packet+10
    cmp #7
    +jne command_bad_argument
    lda packet+11
    +jne command_bad_argument
    lda target_state
    cmp #1
    +jeq command_bad_state
    lda packet+14
    sta target_a
    lda packet+15
    sta target_x
    lda packet+16
    sta target_y
    lda packet+17
    sta target_sp
    lda packet+18
    sta target_status
    lda packet+19
    sta target_pc
    lda packet+20
    sta target_pc+1
    jsr rearm_unarmed_except_pc
    lda #0
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_halt:
    jsr command_require_empty
    +jne command_bad_argument
    lda #0
    sta target_state
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_run:
    jsr command_require_empty
    +jne command_bad_argument
    lda target_state
    cmp #2
    +jeq command_bad_state
    jsr find_unarmed_breakpoint_at_pc
    bcc command_run_rearm_stale
    stx step_rearm_index
    lda #1
    sta step_auto_continue
    jsr prepare_step
    bcs command_step_failed
    jmp command_run_ready
command_run_rearm_stale:
    jsr rearm_unarmed_except_pc
command_run_ready:
    lda #1
    sta resume_after_reply
    lda #0
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_step:
    jsr command_require_empty
    +jne command_bad_argument
    lda target_state
    +jne command_bad_state
    lda #$ff
    sta step_rearm_index
    jsr find_unarmed_breakpoint_at_pc
    bcc command_step_no_rearm
    stx step_rearm_index
command_step_no_rearm:
    lda #0
    sta step_auto_continue
    jsr prepare_step
    bcs command_step_failed
    lda #1
    sta resume_after_reply
    lda #0
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status
command_step_failed:
    pha
    lda #$ff
    sta step_rearm_index
    lda #0
    sta step_auto_continue
    sta response_data_len
    pla
    jmp reply_status

command_break_set:
    lda packet+10
    cmp #2
    +jne command_bad_argument
    lda packet+11
    +jne command_bad_argument
    lda packet+14
    sta transfer_begin
    lda packet+15
    sta transfer_begin+1
    cmp #>SERVICE_BASE
    bcc command_break_search
    cmp #>SERVICE_LIMIT
    +jcc command_unsafe_address
command_break_search:
    lda transfer_begin+1
    cmp #$a0
    bcc command_break_memory_ok
    cmp #$c0
    bcs command_break_memory_ok
    lda $01
    and #$03
    cmp #$03
    +jeq command_unsafe_address
command_break_memory_ok:
    lda transfer_begin+1
    cmp #$02
    +jcc command_unsafe_address
    cmp #$d0
    +jcs command_unsafe_address
    ldx #0
    ldy #$ff
command_break_search_loop:
    lda breakpoint_id,x
    beq command_break_free
    lda breakpoint_lo,x
    cmp transfer_begin
    bne command_break_next
    lda breakpoint_hi,x
    cmp transfer_begin+1
    beq command_break_duplicate
command_break_next:
    inx
    cpx #MAX_BREAKPOINTS
    bne command_break_search_loop
    cpy #$ff
    +jeq command_no_breakpoint
    tya
    tax
    jmp command_break_install
command_break_free:
    cpy #$ff
    bne command_break_next
    txa
    tay
    jmp command_break_next
command_break_duplicate:
    lda breakpoint_id,x
    sta packet+15
    lda #1
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status
command_break_install:
    lda next_breakpoint_id
    bne command_break_id_ok
    inc next_breakpoint_id
command_break_id_ok:
    lda next_breakpoint_id
    sta breakpoint_id,x
    inc next_breakpoint_id
    lda transfer_begin
    sta breakpoint_lo,x
    sta $02
    lda transfer_begin+1
    sta breakpoint_hi,x
    sta $03
    ldy #0
    lda ($02),y
    sta breakpoint_original,x
    lda #0
    sta ($02),y
    lda #1
    sta breakpoint_armed,x
    lda breakpoint_id,x
    sta packet+15
    lda #1
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_break_clear:
    lda packet+10
    cmp #1
    +jne command_bad_argument
    lda packet+11
    +jne command_bad_argument
    ldx #0
command_break_clear_search:
    lda breakpoint_id,x
    cmp packet+14
    beq command_break_clear_found
    inx
    cpx #MAX_BREAKPOINTS
    bne command_break_clear_search
    lda #0
    sta response_data_len
    lda #STATUS_NOT_FOUND
    jmp reply_status
command_break_clear_found:
    jsr restore_breakpoint_x
    lda #0
    sta breakpoint_id,x
    sta breakpoint_armed,x
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_break_list:
    jsr command_require_empty
    +jne command_bad_argument
    lda #0
    sta packet+15
    sta transfer_count
    ldx #0
    ldy #0
command_break_list_loop:
    lda breakpoint_id,x
    beq command_break_list_next
    inc packet+15
    iny
    sta packet+15,y
    iny
    lda breakpoint_lo,x
    sta packet+15,y
    iny
    lda breakpoint_hi,x
    sta packet+15,y
    iny
    lda breakpoint_original,x
    sta packet+15,y
command_break_list_next:
    inx
    cpx #MAX_BREAKPOINTS
    bne command_break_list_loop
    iny
    sty response_data_len
    lda #STATUS_OK
    jmp reply_status

command_sample_config:
    lda packet+10
    cmp #1
    +jne command_bad_argument
    lda packet+11
    +jne command_bad_argument
    lda packet+14
    cmp #2
    +jcs command_bad_argument
    sta sample_enabled
    lda #0
    sta sample_count
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_sample_read:
    jsr command_require_empty
    +jne command_bad_argument
    lda sample_count
    sta packet+15
    lda $02a6
    beq command_sample_ntsc
    ldx #$20
    lda #$4e
    bne command_sample_interval
command_sample_ntsc:
    ldx #$1b
    lda #$41
command_sample_interval:
    stx packet+16
    sta packet+17
    lda #0
    sta packet+18
    sta packet+19
    ldx #0
    ldy #0
command_sample_copy:
    cpx sample_count
    beq command_sample_done
    lda samples,y
    sta packet+20,y
    iny
    lda samples,y
    sta packet+20,y
    iny
    inx
    jmp command_sample_copy
command_sample_done:
    lda #0
    sta sample_count
    tya
    clc
    adc #5
    sta response_data_len
    lda #STATUS_OK
    jmp reply_status

command_ping:
    lda packet+11
    +jne command_bad_argument
    lda packet+10
    cmp #MAX_PAYLOAD
    +jcs command_bad_argument
    sta response_data_len
    tax
    beq command_ping_done
    dex
command_ping_copy:
    lda packet+14,x
    sta packet+15,x
    dex
    bpl command_ping_copy
command_ping_done:
    lda #STATUS_OK
    jmp reply_status

command_reset:
    jsr command_require_empty
    +jne command_bad_argument
    jsr cancel_step
    ldx #0
command_reset_breakpoints:
    lda breakpoint_id,x
    beq command_reset_next
    jsr restore_breakpoint_x
    lda #0
    sta breakpoint_id,x
    sta breakpoint_armed,x
command_reset_next:
    inx
    cpx #MAX_BREAKPOINTS
    bne command_reset_breakpoints
    lda #0
    sta step_active
    sta step_temp_armed
    sta step_auto_continue
    sta sample_enabled
    sta sample_count
    sta target_state
    sta response_data_len
    lda #$ff
    sta step_rearm_index
    lda #STATUS_OK
    jmp reply_status

command_bad_argument:
    lda #0
    sta response_data_len
    lda #STATUS_BAD_ARGUMENT
    jmp reply_status
command_unsafe_address:
    lda #0
    sta response_data_len
    lda #STATUS_UNSAFE_ADDRESS
    jmp reply_status
command_bad_state:
    lda #0
    sta response_data_len
    lda #STATUS_BAD_STATE
    jmp reply_status
command_no_breakpoint:
    lda #0
    sta response_data_len
    lda #STATUS_NO_BREAKPOINT
    jmp reply_status

restore_breakpoint_x:
    lda breakpoint_armed,x
    beq restore_breakpoint_done
    lda breakpoint_lo,x
    sta $02
    lda breakpoint_hi,x
    sta $03
    lda breakpoint_original,x
    ldy #0
    sta ($02),y
    lda #0
    sta breakpoint_armed,x
restore_breakpoint_done:
    rts

arm_breakpoint_x:
    lda breakpoint_lo,x
    sta $02
    lda breakpoint_hi,x
    sta $03
    lda #0
    ldy #0
    sta ($02),y
    lda #1
    sta breakpoint_armed,x
    rts

find_unarmed_breakpoint_at_pc:
    ldx #0
find_unarmed_breakpoint_loop:
    lda breakpoint_id,x
    beq find_unarmed_breakpoint_next
    lda breakpoint_armed,x
    bne find_unarmed_breakpoint_next
    lda breakpoint_lo,x
    cmp target_pc
    bne find_unarmed_breakpoint_next
    lda breakpoint_hi,x
    cmp target_pc+1
    beq find_unarmed_breakpoint_found
find_unarmed_breakpoint_next:
    inx
    cpx #MAX_BREAKPOINTS
    bne find_unarmed_breakpoint_loop
    clc
    rts
find_unarmed_breakpoint_found:
    sec
    rts

rearm_unarmed_except_pc:
    ldx #0
rearm_unarmed_loop:
    lda breakpoint_id,x
    beq rearm_unarmed_next
    lda breakpoint_armed,x
    bne rearm_unarmed_next
    lda breakpoint_lo,x
    cmp target_pc
    bne rearm_unarmed_arm
    lda breakpoint_hi,x
    cmp target_pc+1
    beq rearm_unarmed_next
rearm_unarmed_arm:
    jsr arm_breakpoint_x
rearm_unarmed_next:
    inx
    cpx #MAX_BREAKPOINTS
    bne rearm_unarmed_loop
    rts

find_armed_breakpoint_at_pc:
    ldx #0
find_armed_pc_loop:
    lda breakpoint_id,x
    beq find_armed_pc_next
    lda breakpoint_armed,x
    beq find_armed_pc_next
    lda breakpoint_lo,x
    cmp target_pc
    bne find_armed_pc_next
    lda breakpoint_hi,x
    cmp target_pc+1
    beq find_armed_pc_found
find_armed_pc_next:
    inx
    cpx #MAX_BREAKPOINTS
    bne find_armed_pc_loop
    clc
    rts
find_armed_pc_found:
    sec
    rts

find_armed_breakpoint_at_step_target:
    ldx #0
find_armed_step_loop:
    lda breakpoint_id,x
    beq find_armed_step_next
    lda breakpoint_armed,x
    beq find_armed_step_next
    lda breakpoint_lo,x
    cmp step_target
    bne find_armed_step_next
    lda breakpoint_hi,x
    cmp step_target+1
    beq find_armed_step_found
find_armed_step_next:
    inx
    cpx #MAX_BREAKPOINTS
    bne find_armed_step_loop
    clc
    rts
find_armed_step_found:
    sec
    rts

prepare_step:
    lda #0
    sta step_active
    sta step_temp_armed
    jsr compute_step_target
    bcs prepare_step_done
    lda step_target
    cmp target_pc
    bne prepare_step_not_self
    lda step_target+1
    cmp target_pc+1
    bne prepare_step_not_self
    lda #STATUS_UNSUPPORTED
    sec
    rts
prepare_step_not_self:
    lda step_target
    cmp #<target_exit_stub
    bne prepare_step_patch
    lda step_target+1
    cmp #>target_exit_stub
    beq prepare_step_ready
prepare_step_patch:
    jsr step_target_is_safe
    bcs prepare_step_unsafe
    jsr find_armed_breakpoint_at_step_target
    bcs prepare_step_ready
    lda step_target
    sta $02
    lda step_target+1
    sta $03
    ldy #0
    lda ($02),y
    sta step_original
    lda #0
    sta ($02),y
    lda #1
    sta step_temp_armed
prepare_step_ready:
    lda #1
    sta step_active
    clc
prepare_step_done:
    rts
prepare_step_unsafe:
    lda #STATUS_UNSAFE_ADDRESS
    sec
    rts

step_target_is_safe:
    lda step_target+1
    cmp #$02
    bcc step_target_unsafe
    cmp #>SERVICE_BASE
    bcs step_target_unsafe
    cmp #$a0
    bcc step_target_safe
    lda $01
    and #$03
    cmp #$03
    beq step_target_unsafe
step_target_safe:
    clc
    rts
step_target_unsafe:
    sec
    rts

finish_step:
    lda step_temp_armed
    beq finish_step_rearm
    lda step_target
    sta $02
    lda step_target+1
    sta $03
    lda step_original
    ldy #0
    sta ($02),y
    lda #0
    sta step_temp_armed
finish_step_rearm:
    ldx step_rearm_index
    cpx #$ff
    beq finish_step_state
    lda breakpoint_id,x
    beq finish_step_clear_rearm
    jsr arm_breakpoint_x
finish_step_clear_rearm:
    lda #$ff
    sta step_rearm_index
finish_step_state:
    lda #0
    sta step_active
    rts

cancel_step:
    jsr finish_step
    lda #0
    sta step_auto_continue
    rts

compute_step_target:
    ldy #0
    jsr step_read_pc_y
    sta step_opcode
    +jeq compute_step_unsupported
    cmp #$20
    beq compute_step_absolute
    cmp #$4c
    beq compute_step_absolute
    cmp #$6c
    beq compute_step_indirect
    cmp #$60
    beq compute_step_return
    cmp #$40
    beq compute_step_rti
    and #$1f
    cmp #$10
    +jeq compute_step_branch
    ldx step_opcode
    lda step_opcode_lengths,x
    +jeq compute_step_unsupported
    clc
    adc target_pc
    sta step_target
    lda target_pc+1
    adc #0
    sta step_target+1
    clc
    rts

compute_step_absolute:
    ldy #1
    jsr step_read_pc_y
    sta step_target
    iny
    jsr step_read_pc_y
    sta step_target+1
    clc
    rts

compute_step_indirect:
    ldy #1
    jsr step_read_pc_y
    sta $04
    iny
    jsr step_read_pc_y
    sta $05
    ldy #0
    lda ($04),y
    sta step_target
    inc $04
    lda ($04),y
    sta step_target+1
    clc
    rts

compute_step_return:
    ldx target_sp
    cpx #$fe
    +jcs compute_step_unsupported
    lda $0101,x
    sta step_target
    lda $0102,x
    sta step_target+1
    inc step_target
    bne compute_step_return_done
    inc step_target+1
compute_step_return_done:
    clc
    rts

compute_step_rti:
    ldx target_sp
    cpx #$fd
    +jcs compute_step_unsupported
    lda $0102,x
    sta step_target
    lda $0103,x
    sta step_target+1
    clc
    rts

compute_step_branch:
    jsr step_branch_is_taken
    bcs compute_step_branch_taken
    clc
    lda target_pc
    adc #2
    sta step_target
    lda target_pc+1
    adc #0
    sta step_target+1
    clc
    rts
compute_step_branch_taken:
    ldy #1
    jsr step_read_pc_y
    sta step_branch_offset
    clc
    lda target_pc
    adc #2
    sta step_target
    lda target_pc+1
    adc #0
    sta step_target+1
    lda step_branch_offset
    bpl compute_step_branch_add
    dec step_target+1
compute_step_branch_add:
    clc
    adc step_target
    sta step_target
    bcc compute_step_branch_done
    inc step_target+1
compute_step_branch_done:
    clc
    rts

step_branch_is_taken:
    lda step_opcode
    cmp #$10
    beq step_branch_bpl
    cmp #$30
    beq step_branch_bmi
    cmp #$50
    beq step_branch_bvc
    cmp #$70
    beq step_branch_bvs
    cmp #$90
    beq step_branch_bcc
    cmp #$b0
    beq step_branch_bcs
    cmp #$d0
    beq step_branch_bne
    lda target_status
    and #$02
    bne step_branch_yes
    beq step_branch_no
step_branch_bpl:
    lda target_status
    and #$80
    beq step_branch_yes
    bne step_branch_no
step_branch_bmi:
    lda target_status
    and #$80
    bne step_branch_yes
    beq step_branch_no
step_branch_bvc:
    lda target_status
    and #$40
    beq step_branch_yes
    bne step_branch_no
step_branch_bvs:
    lda target_status
    and #$40
    bne step_branch_yes
    beq step_branch_no
step_branch_bcc:
    lda target_status
    and #$01
    beq step_branch_yes
    bne step_branch_no
step_branch_bcs:
    lda target_status
    and #$01
    bne step_branch_yes
    beq step_branch_no
step_branch_bne:
    lda target_status
    and #$02
    beq step_branch_yes
step_branch_no:
    clc
    rts
step_branch_yes:
    sec
    rts

compute_step_unsupported:
    lda #STATUS_UNSUPPORTED
    sec
    rts

step_read_pc_y:
    lda target_pc
    sta $02
    lda target_pc+1
    sta $03
    lda ($02),y
    rts

reply_status:
    sta packet+14
    cmp #0
    beq reply_ok_flag
    lda #FLAG_RESPONSE | FLAG_ERROR
    bne reply_set_flag
reply_ok_flag:
    lda #FLAG_RESPONSE
reply_set_flag:
    sta packet+7
    lda response_data_len
    clc
    adc #1
    sta packet+10
    lda #0
    sta packet+11
    jsr finalize_and_send
    lda resume_after_reply
    beq reply_done
    lda #0
    sta resume_after_reply
    jsr raw_begin_read
    lda #1
    sta rx_selected
    jmp resume_target
reply_done:
    jmp command_loop

receive_packet:
    lda rx_selected
    beq receive_select
    lda #0
    sta rx_selected
    jmp receive_header
receive_select:
    jsr raw_begin_read
receive_header:
    ldy #0
receive_header_loop:
    jsr raw_get_block
    sta packet,y
    iny
    cpy #14
    bne receive_header_loop
    lda packet
    cmp #"I"
    bne receive_bad
    lda packet+1
    cmp #"D"
    bne receive_bad
    lda packet+2
    cmp #"B"
    bne receive_bad
    lda packet+3
    cmp #"G"
    bne receive_bad
    lda packet+4
    cmp #1
    bne receive_bad
    lda packet+11
    bne receive_bad
    lda packet+10
    cmp #MAX_PAYLOAD+1
    bcs receive_bad
    tax
    ldy #14
receive_payload_loop:
    cpx #0
    beq receive_checksum
    jsr raw_get_block
    sta packet,y
    iny
    dex
    jmp receive_payload_loop
receive_checksum:
    jsr calculate_checksum
    lda checksum_lo
    cmp packet+12
    bne receive_bad
    lda checksum_hi
    cmp packet+13
    bne receive_bad
    clc
    rts
receive_bad:
    sec
    rts

calculate_checksum:
    lda #0
    sta checksum_lo
    sta checksum_hi
    ldy #0
checksum_header_loop:
    lda packet,y
    jsr checksum_add
    iny
    cpy #12
    bne checksum_header_loop
    ldy #14
    ldx packet+10
checksum_payload_loop:
    cpx #0
    beq checksum_done
    lda packet,y
    jsr checksum_add
    iny
    dex
    jmp checksum_payload_loop
checksum_done:
    rts
checksum_add:
    clc
    adc checksum_lo
    sta checksum_lo
    bcc checksum_add_done
    inc checksum_hi
checksum_add_done:
    rts

finalize_and_send:
    lda #"I"
    sta packet
    lda #"D"
    sta packet+1
    lda #"B"
    sta packet+2
    lda #"G"
    sta packet+3
    lda #1
    sta packet+4
    lda #0
    sta packet+5
    jsr calculate_checksum
    lda checksum_lo
    sta packet+12
    lda checksum_hi
    sta packet+13
    lda packet+10
    clc
    adc #14
    sta packet_total
    jmp raw_send_packet

send_pending_event:
    lda event_type
    sta packet+6
    lda #FLAG_EVENT
    sta packet+7
    lda #0
    sta packet+8
    sta packet+9
    lda event_payload_len
    sta packet+10
    lda #0
    sta packet+11
    lda event_data
    sta packet+14
    lda event_data+1
    sta packet+15
    lda event_data+2
    sta packet+16
    jsr finalize_and_send
    lda #0
    sta event_pending
    sta rx_selected
    rts

raw_begin_read:
    lda #$40 + SOCKET_CHANNEL
    jsr raw_put
    lda socket_lfn
    ora #$60
    jmp raw_put

raw_send_packet:
    lda #$5f
    jsr raw_put
    lda #$20 + SOCKET_CHANNEL
    jsr raw_put
    lda socket_lfn
    ora #$60
    jsr raw_put
    ldx #0
raw_send_loop:
    lda packet,x
    jsr raw_put
    inx
    cpx packet_total
    bne raw_send_loop
    lda #$fa
    jsr raw_put
    lda #0
    jsr raw_put
    lda #$3f
    jmp raw_put

raw_put:
    sta turboOff
    sta idDataport
    sta turboOn
    rts

raw_get_block:
    sta turboOff
raw_get_wait:
    lda idRxBufLen
    beq raw_get_wait
    nop
    lda idDataport
    sta turboOn
    rts

resume_target:
    sei
    lda #<(target_exit_stub-1)
    sta $01fe
    lda #>(target_exit_stub-1)
    sta $01ff
    lda #<service_irq
    sta $0314
    lda #>service_irq
    sta $0315
    lda #<service_brk
    sta $0316
    lda #>service_brk
    sta $0317
    ldx #7
resume_restore_zp:
    lda saved_zp,x
    sta $02,x
    dex
    bpl resume_restore_zp
    lda #1
    sta target_state
    ldx target_sp
    txs
    lda target_pc+1
    pha
    lda target_pc
    pha
    lda target_status
    pha
    lda target_a
    ldx target_x
    ldy target_y
    rti

; Called by the C64 KERNAL IRQ dispatcher after it has stacked A/X/Y.
service_irq:
    lda $dc0d
    lda $d019
    sta $d019
    tsx
    stx interrupt_sp
    lda sample_enabled
    beq service_irq_check_input
    lda sample_count
    cmp #MAX_SAMPLES
    bcs service_irq_check_input
    asl
    tay
    lda $0105,x
    sta samples,y
    iny
    lda $0106,x
    sta samples,y
    inc sample_count
service_irq_check_input:
    sta turboOff
    lda idRxBufLen
    beq service_irq_continue
    sta turboOn
    lda #EVENT_STOPPED
    sta event_type
    lda #2
    sta event_payload_len
    jsr capture_interrupt
    ldx #$ff
    txs
    sei
    lda step_active
    beq service_irq_step_done
    jsr cancel_step
service_irq_step_done:
    lda #0
    sta target_state
    sta rx_selected
    lda target_pc
    sta event_data
    lda target_pc+1
    sta event_data+1
    lda #1
    sta event_pending
    jmp command_loop
service_irq_continue:
    sta turboOn
    pla
    tay
    pla
    tax
    pla
    rti

service_brk:
    lda $dc0d
    lda $d019
    sta $d019
    tsx
    stx interrupt_sp
    jsr capture_interrupt
    ldx #$ff
    txs
    sei
    lda #0
    sta target_state
    sta rx_selected
    sec
    lda target_pc
    sbc #2
    sta target_pc
    lda target_pc+1
    sbc #0
    sta target_pc+1
    lda target_pc
    cmp #<target_exit_stub
    bne service_brk_not_exit
    lda target_pc+1
    cmp #>target_exit_stub
    bne service_brk_not_exit
    lda step_active
    beq service_brk_exit_ready
    jsr finish_step
service_brk_exit_ready:
    lda #0
    sta step_auto_continue
    lda #2
    sta target_state
    lda #EVENT_TARGET_EXIT
    sta event_type
    lda #2
    sta event_payload_len
    lda target_pc
    sta event_data
    lda target_pc+1
    sta event_data+1
    lda #1
    sta event_pending
    jmp command_loop
service_brk_not_exit:
    lda step_active
    beq service_brk_find_user
    lda target_pc
    cmp step_target
    bne service_brk_fault_cleanup
    lda target_pc+1
    cmp step_target+1
    bne service_brk_fault_cleanup
    jsr finish_step
    jsr find_armed_breakpoint_at_pc
    bcs service_brk_found
    lda step_auto_continue
    beq service_brk_step_stopped
    lda #0
    sta step_auto_continue
    jmp resume_target
service_brk_step_stopped:
    lda #0
    sta step_auto_continue
    lda #EVENT_STOPPED
    sta event_type
    lda #2
    sta event_payload_len
    lda target_pc
    sta event_data
    lda target_pc+1
    sta event_data+1
    lda #1
    sta event_pending
    jmp command_loop
service_brk_find_user:
    jsr find_armed_breakpoint_at_pc
    bcs service_brk_found
service_brk_fault_cleanup:
    lda step_active
    beq service_brk_fault
    jsr cancel_step
service_brk_fault:
    lda #EVENT_TARGET_FAULT
    sta event_type
    lda #2
    sta event_payload_len
    lda target_pc
    sta event_data
    lda target_pc+1
    sta event_data+1
    lda #1
    sta event_pending
    jmp command_loop
service_brk_found:
    lda breakpoint_id,x
    sta event_data
    lda breakpoint_lo,x
    sta event_data+1
    lda breakpoint_hi,x
    sta event_data+2
    jsr restore_breakpoint_x
    lda #0
    sta step_auto_continue
    lda #EVENT_BREAKPOINT
    sta event_type
    lda #3
    sta event_payload_len
    lda #1
    sta event_pending
    jmp command_loop

capture_interrupt:
    ldx interrupt_sp
    lda $0101,x
    sta target_y
    lda $0102,x
    sta target_x
    lda $0103,x
    sta target_a
    lda $0104,x
    sta target_status
    lda $0105,x
    sta target_pc
    lda $0106,x
    sta target_pc+1
    txa
    clc
    adc #6
    sta target_sp
    ldx #7
capture_zp:
    lda $02,x
    sta saved_zp,x
    dex
    bpl capture_zp
    rts

target_exit_stub:
    brk
    !byte $42

; NMOS 6510 instruction lengths, including stable lengths for undocumented
; opcodes. BRK is handled separately because it cannot be single-stepped with
; a software breakpoint.
step_opcode_lengths:
    !byte 1,2,0,2,2,2,2,2,1,2,1,2,3,3,3,3
    !byte 2,2,0,2,2,2,2,2,1,3,1,3,3,3,3,3
    !byte 3,2,0,2,2,2,2,2,1,2,1,2,3,3,3,3
    !byte 2,2,0,2,2,2,2,2,1,3,1,3,3,3,3,3
    !byte 1,2,0,2,2,2,2,2,1,2,1,2,3,3,3,3
    !byte 2,2,0,2,2,2,2,2,1,3,1,3,3,3,3,3
    !byte 1,2,0,2,2,2,2,2,1,2,1,2,3,3,3,3
    !byte 2,2,0,2,2,2,2,2,1,3,1,3,3,3,3,3
    !byte 2,2,2,2,2,2,2,2,1,2,1,2,3,3,3,3
    !byte 2,2,0,2,2,2,2,2,1,3,1,3,3,3,3,3
    !byte 2,2,2,2,2,2,2,2,1,2,1,2,3,3,3,3
    !byte 2,2,0,2,2,2,2,2,1,3,1,3,3,3,3,3
    !byte 2,2,2,2,2,2,2,2,1,2,1,2,3,3,3,3
    !byte 2,2,0,2,2,2,2,2,1,3,1,3,3,3,3,3
    !byte 2,2,2,2,2,2,2,2,1,2,1,2,3,3,3,3
    !byte 2,2,0,2,2,2,2,2,1,3,1,3,3,3,3,3

; Service state and bounded buffers. Keep all of this below SERVICE_LIMIT.
target_a: !byte 0
target_x: !byte 0
target_y: !byte 0
target_sp: !byte 0
target_status: !byte 0
target_pc: !word 0
target_state: !byte 0
socket_lfn: !byte 0
saved_zp: !fill 8, 0
interrupt_sp: !byte 0
rx_selected: !byte 0
resume_after_reply: !byte 0
response_data_len: !byte 0
transfer_count: !byte 0
transfer_begin: !word 0
transfer_end: !word 0
checksum_lo: !byte 0
checksum_hi: !byte 0
packet_total: !byte 0
event_pending: !byte 0
event_type: !byte 0
event_payload_len: !byte 0
event_data: !fill 3, 0
step_active: !byte 0
step_temp_armed: !byte 0
step_auto_continue: !byte 0
step_rearm_index: !byte $ff
step_target: !word 0
step_original: !byte 0
step_opcode: !byte 0
step_branch_offset: !byte 0
sample_enabled: !byte 0
sample_count: !byte 0
next_breakpoint_id: !byte 1
breakpoint_id: !fill MAX_BREAKPOINTS, 0
breakpoint_armed: !fill MAX_BREAKPOINTS, 0
breakpoint_lo: !fill MAX_BREAKPOINTS, 0
breakpoint_hi: !fill MAX_BREAKPOINTS, 0
breakpoint_original: !fill MAX_BREAKPOINTS, 0
samples: !fill MAX_SAMPLES*2, 0
packet: !fill 14+MAX_PAYLOAD, 0

resident_end_virtual = *
}
resident_end = *
RESIDENT_SIZE = resident_end - resident_source

!if RESIDENT_SIZE > SERVICE_LIMIT-SERVICE_BASE {
    !error "Action target service exceeds $c000-$cfff"
}
