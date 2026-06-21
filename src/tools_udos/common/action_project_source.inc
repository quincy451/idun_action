.ifndef ACTC_REU_SOURCE_CACHE
ACTC_REU_SOURCE_CACHE = 0
.endif
.ifndef ACTC_SOURCE_REU_BASE_LO
ACTC_SOURCE_REU_BASE_LO = $00
.endif
.ifndef ACTC_SOURCE_REU_BASE_HI
ACTC_SOURCE_REU_BASE_HI = $00
.endif
.ifndef ACTC_SOURCE_REU_BASE_BANK
ACTC_SOURCE_REU_BASE_BANK = $01
.endif

load_source_file:
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$20
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$00
    sta ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
.endif
    lda #$00
    sta truncated_flag
    lda #<target_path
    sta file_params+0
    lda #>target_path
    sta file_params+1
load_source_file_after_path_setup:
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$21
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
.if ACTC_REU_SOURCE_CACHE
    jmp load_source_file_reu_cache
.endif
    lda #<source_buffer
    sta file_params+2
    lda #>source_buffer
    sta file_params+3
    lda #<SOURCE_LIMIT
    sta file_params+4
    lda #>SOURCE_LIMIT
    sta file_params+5
    lda #$00
    sta file_params+6
    sta file_params+7
    sta file_params+8
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$22
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
    tsx
    stx file_params+8
.ifdef ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
    stx ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
.endif
    lda #$00
    ldx #$00
load_source_file_scrub_stack_loop:
    cpx file_params+8
    bcs load_source_file_scrub_stack_done
    sta $0100,x
    inx
    bne load_source_file_scrub_stack_loop
load_source_file_scrub_stack_done:
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$23
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
    ldx #file_params
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$24
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
.ifdef ALINK_PRESERVE_ZP_SERVICES
    jsr alink_svc_file_load_sc0
.else
    jsr svc_file_load_sc0
.endif
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$25
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
    lda file_params+6
.ifdef ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
    sta ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
.endif
    cmp #tool_file_status_ok
    beq load_source_file_ok
    cmp #tool_file_status_too_large
    bne load_source_file_fail
    lda #$01
    sta truncated_flag
load_source_file_ok:
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$26
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
    lda #<source_buffer
    clc
    adc file_params+7
    sta src_ptr
    lda #>source_buffer
    adc file_params+8
    sta src_ptr+1
    ldy #$00
    lda #$00
    sta (src_ptr),y
    clc
    rts
load_source_file_fail:
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$27
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
    sec
    rts

source_reader_reset_to_start:
.if ACTC_REU_SOURCE_CACHE
    lda source_window_valid
    beq source_reader_reset_to_start_reload
    lda source_window_next_offset+2
    bne source_reader_reset_to_start_reload
    lda source_window_next_offset+1
    cmp source_window_len+1
    bne source_reader_reset_to_start_reload
    lda source_window_next_offset
    cmp source_window_len
    bne source_reader_reset_to_start_reload
    lda #<source_buffer
    sta scan_ptr
    lda #>source_buffer
    sta scan_ptr+1
    clc
    rts
source_reader_reset_to_start_reload:
    lda #$00
    sta source_window_next_offset
    sta source_window_next_offset+1
    sta source_window_next_offset+2
    jmp source_reader_load_next_window
.else
    lda #<source_buffer
    sta scan_ptr
    lda #>source_buffer
    sta scan_ptr+1
    clc
    rts
.endif

source_reader_commit_256_from_scan_ptr:
.if ACTC_REU_SOURCE_CACHE
    lda scan_ptr
    sta src_ptr
    lda scan_ptr+1
    clc
    adc #$01
    sta src_ptr+1
    cmp source_window_end_ptr+1
    bcc source_reader_commit_256_use_target
    bne source_reader_commit_256_cross_window
    lda src_ptr
    cmp source_window_end_ptr
    bcc source_reader_commit_256_use_target
source_reader_commit_256_cross_window:
    sec
    lda src_ptr
    sbc source_window_end_ptr
    sta content_ptr
    lda src_ptr+1
    sbc source_window_end_ptr+1
    sta content_ptr+1
    jsr source_reader_load_next_window
    bcs source_reader_commit_256_done
    clc
    lda scan_ptr
    adc content_ptr
    sta scan_ptr
    lda scan_ptr+1
    adc content_ptr+1
    sta scan_ptr+1
    clc
    rts
source_reader_commit_256_use_target:
    lda src_ptr
    sta scan_ptr
    lda src_ptr+1
    sta scan_ptr+1
    clc
source_reader_commit_256_done:
    rts
.else
    inc scan_ptr+1
    clc
    rts
.endif

.if ACTC_REU_SOURCE_CACHE
load_source_file_reu_cache:
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$30
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
    lda #$00
    sta source_window_valid
.ifdef ALINK_PRESERVE_ZP_SERVICES
    sta alink_source_direct_cached
    jsr alink_try_load_source_direct_window
    bcs :+
    clc
    rts
:
    lda file_params+6
    cmp #tool_file_status_too_large
    beq :+
    sec
    rts
:
.endif
    lda #ACTC_SOURCE_REU_BASE_LO
    sta file_params+2
    lda #ACTC_SOURCE_REU_BASE_HI
    sta file_params+3
    lda #ACTC_SOURCE_REU_BASE_BANK
    sta file_params+4
    lda #$00
    sta file_params+5
    sta file_params+6
    sta file_params+7
    sta file_params+8
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$31
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$C1
    sta debug_phase_zp
.endif
    ldx #file_params
.ifdef ALINK_PRESERVE_ZP_SERVICES
    jsr alink_svc_file_stage_reu_sc0
.else
    jsr svc_file_stage_reu_sc0
.endif
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$C2
    sta debug_phase_zp
    lda #$32
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
    lda file_params+5
.ifdef ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
    sta debug_phase_zp
    sta ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
.endif
    cmp #tool_file_status_ok
    beq load_source_file_reu_stage_ok
    sta file_params+6
    sec
    rts

load_source_file_reu_stage_ok:
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$33
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
    lda file_params+6
    sta source_total_len
    lda file_params+7
    sta source_total_len+1
    lda file_params+8
    sta source_total_len+2
    jsr source_reader_reset_to_start
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$34
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
    bcc load_source_file_reu_read_ok
    lda file_params+7
    sta file_params+6
.ifdef ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
    sta ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
.endif
    sec
    rts

load_source_file_reu_read_ok:
.ifdef ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
    lda #$35
    sta ALINK_SOURCE_LOAD_PHASE_SNAPSHOT
.endif
    lda #tool_file_status_ok
    sta file_params+6
.ifdef ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
    sta ALINK_SOURCE_LOAD_STATUS_SNAPSHOT
.endif
    lda source_window_len
    sta file_params+7
    lda source_window_len+1
    sta file_params+8
.ifdef ALINK_SOURCE_RETURN_SNAPSHOT
    tsx
    stx ALINK_SOURCE_RETURN_SNAPSHOT+0
    lda $0101,x
    sta ALINK_SOURCE_RETURN_SNAPSHOT+1
    lda $0102,x
    sta ALINK_SOURCE_RETURN_SNAPSHOT+2
.endif
    clc
    rts

.ifdef ALINK_PRESERVE_ZP_SERVICES
alink_try_load_source_direct_window:
    lda #<source_buffer
    sta file_params+2
    lda #>source_buffer
    sta file_params+3
    lda #<SOURCE_READ_LIMIT
    sta file_params+4
    lda #>SOURCE_READ_LIMIT
    sta file_params+5
    lda #$00
    sta file_params+6
    sta file_params+7
    sta file_params+8
    ldx #file_params
    jsr alink_svc_file_load_sc0
    lda file_params+6
    cmp #tool_file_status_ok
    beq alink_try_load_source_direct_ok
    sec
    rts

alink_try_load_source_direct_ok:
    lda file_params+7
    sta source_total_len
    sta source_window_len
    sta source_window_read_len
    sta source_window_next_offset
    lda file_params+8
    sta source_total_len+1
    sta source_window_len+1
    sta source_window_read_len+1
    sta source_window_next_offset+1
    lda #$00
    sta source_total_len+2
    sta source_window_next_offset+2
    jsr source_reader_zero_terminate_window
    lda #$01
    sta source_window_valid
    sta alink_source_direct_cached
    lda #<source_buffer
    sta scan_ptr
    lda #>source_buffer
    sta scan_ptr+1
    lda #tool_file_status_ok
    sta file_params+6
    clc
    rts
.endif

source_reader_load_next_window:
    sec
    lda source_total_len
    sbc source_window_next_offset
    sta file_params+5
    lda source_total_len+1
    sbc source_window_next_offset+1
    sta file_params+6
    lda source_total_len+2
    sbc source_window_next_offset+2
    bcs :+
    jmp source_reader_load_eof_window
:
    sta file_params+7
    lda file_params+5
    ora file_params+6
    ora file_params+7
    bne :+
    jmp source_reader_load_eof_window
:

    lda file_params+7
    bne source_reader_load_use_limit
    lda file_params+6
    cmp #>SOURCE_LIMIT
    bcc source_reader_load_use_remaining
    bne source_reader_load_use_limit
    lda file_params+5
    cmp #<SOURCE_LIMIT
    bcc source_reader_load_use_remaining

source_reader_load_use_limit:
    lda #<SOURCE_LIMIT
    sta source_window_len
    lda #>SOURCE_LIMIT
    sta source_window_len+1
    jmp source_reader_set_read_len

source_reader_load_use_remaining:
    lda file_params+5
    sta source_window_len
    lda file_params+6
    sta source_window_len+1

source_reader_set_read_len:
    lda file_params+7
    bne source_reader_read_use_limit
    lda file_params+6
    cmp #>SOURCE_READ_LIMIT
    bcc source_reader_read_use_remaining
    bne source_reader_read_use_limit
    lda file_params+5
    cmp #<SOURCE_READ_LIMIT
    bcc source_reader_read_use_remaining

source_reader_read_use_limit:
    lda #<SOURCE_READ_LIMIT
    sta source_window_read_len
    lda #>SOURCE_READ_LIMIT
    sta source_window_read_len+1
    jmp source_reader_load_window

source_reader_read_use_remaining:
    lda file_params+5
    sta source_window_read_len
    lda file_params+6
    sta source_window_read_len+1

source_reader_load_window:
    lda #ACTC_SOURCE_REU_BASE_LO
    clc
    adc source_window_next_offset
    sta file_params+0
    lda #ACTC_SOURCE_REU_BASE_HI
    adc source_window_next_offset+1
    sta file_params+1
    lda #ACTC_SOURCE_REU_BASE_BANK
    adc source_window_next_offset+2
    sta file_params+2
    lda #<source_buffer
    sta file_params+3
    lda #>source_buffer
    sta file_params+4
    lda source_window_read_len
    sta file_params+5
    lda source_window_read_len+1
    sta file_params+6
    lda #$00
    sta file_params+7
    ldx #file_params
.ifdef ALINK_PRESERVE_ZP_SERVICES
    jsr alink_svc_reu_read_sc0
.else
    jsr svc_reu_read_sc0
.endif
    lda file_params+7
    cmp #tool_file_status_ok
    beq source_reader_load_window_ok
    sec
    rts

source_reader_load_window_ok:
    jsr source_reader_zero_terminate_window
    lda #$01
    sta source_window_valid
    clc
    lda source_window_next_offset
    adc source_window_len
    sta source_window_next_offset
    lda source_window_next_offset+1
    adc source_window_len+1
    sta source_window_next_offset+1
    lda source_window_next_offset+2
    adc #$00
    sta source_window_next_offset+2
    lda #<source_buffer
    sta scan_ptr
    lda #>source_buffer
    sta scan_ptr+1
    clc
    rts

source_reader_load_eof_window:
    lda #$00
    sta source_window_len
    sta source_window_len+1
    sta source_window_read_len
    sta source_window_read_len+1
    jsr source_reader_zero_terminate_window
    lda #$01
    sta source_window_valid
    lda #<source_buffer
    sta scan_ptr
    lda #>source_buffer
    sta scan_ptr+1
    clc
    rts

source_reader_zero_terminate_window:
    lda #<source_buffer
    clc
    adc source_window_read_len
    sta source_window_end_ptr
    sta src_ptr
    lda #>source_buffer
    adc source_window_read_len+1
    sta source_window_end_ptr+1
    sta src_ptr+1
    ldy #$00
    lda #$00
    sta (src_ptr),y
    lda #<source_buffer
    clc
    adc source_window_len
    sta source_window_end_ptr
    lda #>source_buffer
    adc source_window_len+1
    sta source_window_end_ptr+1
    rts

source_reader_refill_if_at_window_end:
    lda scan_ptr
    cmp source_window_end_ptr
    bne source_reader_refill_not_needed
    lda scan_ptr+1
    cmp source_window_end_ptr+1
    bne source_reader_refill_not_needed
.ifdef ALINK_PRESERVE_ZP_SERVICES
    lda alink_source_direct_cached
    beq :+
    clc
    rts
:
.endif
    jmp source_reader_load_next_window
source_reader_refill_not_needed:
    clc
    rts
.endif
