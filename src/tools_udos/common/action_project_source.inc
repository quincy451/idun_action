load_source_file:
    lda #$00
    sta truncated_flag
    lda #<target_path
    sta file_params+0
    lda #>target_path
    sta file_params+1
load_source_file_after_path_setup:
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
    tsx
    stx file_params+8
    lda #$00
    ldx #$00
load_source_file_scrub_stack_loop:
    cpx file_params+8
    bcs load_source_file_scrub_stack_done
    sta $0100,x
    inx
    bne load_source_file_scrub_stack_loop
load_source_file_scrub_stack_done:
    ldx #file_params
    jsr svc_file_load_sc0
    lda file_params+6
    cmp #tool_file_status_ok
    beq load_source_file_ok
    cmp #tool_file_status_too_large
    bne load_source_file_fail
    lda #$01
    sta truncated_flag
load_source_file_ok:
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
    sec
    rts
