.include "avmrun_overlay_abi.inc"
.include "avmrun_overlay_resident.inc"

.export avmrun_overlay_header
.export avmrun_overlay_entry
.export avmrun_overlay_end

.segment "CODE"

avmrun_overlay_header:
    .byte 'A','V','O','V'
    .byte AVMRUN_OVERLAY_ABI_VERSION
    .word AVMRUN_OVERLAY_EXEC_BASE
    .word avmrun_overlay_entry
    .word avmrun_overlay_end - avmrun_overlay_header
    .word $0000

word_tmp = AVMRUN_RES_word_tmp
real_lhs_lo = AVMRUN_RES_real_lhs_lo
real_lhs_hi = AVMRUN_RES_real_lhs_hi
real_rhs_lo = AVMRUN_RES_real_rhs_lo
real_rhs_hi = AVMRUN_RES_real_rhs_hi
real_result_lo = AVMRUN_RES_real_result_lo
real_result_hi = AVMRUN_RES_real_result_hi
real_lhs_mant = AVMRUN_RES_real_lhs_mant
real_rhs_mant = AVMRUN_RES_real_rhs_mant
real_lhs_exp = AVMRUN_RES_real_lhs_exp
real_rhs_exp = AVMRUN_RES_real_rhs_exp
real_lhs_sign = AVMRUN_RES_real_lhs_sign
real_rhs_sign = AVMRUN_RES_real_rhs_sign
real_align_shift = AVMRUN_RES_real_align_shift
real_flip_rhs_sign = AVMRUN_RES_real_flip_rhs_sign
real_work_shift = AVMRUN_RES_real_work_shift
real_exp_work = AVMRUN_RES_real_exp_work
real_work_a = AVMRUN_RES_real_work_a
real_work_b = AVMRUN_RES_real_work_b
real_work_c = AVMRUN_RES_real_work_c
avmrun_overlay_requested_cmd = AVMRUN_RES_avmrun_overlay_requested_cmd

avmrun_overlay_entry:
    lda avmrun_overlay_requested_cmd
    cmp #AVMRUN_OVERLAY_CMD_REAL_ADD_SUB
    beq avmrun_overlay_real_addsub
    cmp #AVMRUN_OVERLAY_CMD_REAL_MUL
    beq avmrun_overlay_real_mul
    cmp #AVMRUN_OVERLAY_CMD_REAL_DIV
    beq avmrun_overlay_real_div
    cmp #AVMRUN_OVERLAY_CMD_REAL_FTOI
    beq avmrun_overlay_real_ftoi
    cmp #AVMRUN_OVERLAY_CMD_REAL_ITOF
    beq avmrun_overlay_real_itof
    sec
    rts

avmrun_overlay_real_addsub:
    lda real_flip_rhs_sign
    beq :+
    lda real_rhs_hi+1
    eor #$80
    sta real_rhs_hi+1
:
    jsr real_unpack_lhs
    jsr real_unpack_rhs
    jmp real_addsub_binary32

avmrun_overlay_real_mul:
    jsr real_unpack_lhs
    jsr real_unpack_rhs
    jmp real_mul_binary32

avmrun_overlay_real_div:
    jsr real_unpack_lhs
    jsr real_unpack_rhs
    jmp real_div_binary32

avmrun_overlay_real_ftoi:
    jsr real_unpack_lhs
    jmp real_trunc_lhs_to_int_word

avmrun_overlay_real_itof:
    lda real_lhs_lo
    ora real_lhs_lo+1
    bne :+
    jsr real_return_zero
    clc
    rts
:   lda real_lhs_lo
    sta real_work_a
    lda real_lhs_lo+1
    sta real_work_a+1
    lda #$00
    sta real_work_a+2
    sta real_work_a+3
    sta real_lhs_sign
    sta real_work_shift
avmrun_overlay_real_itof_normalize_loop:
    lda real_work_a+1
    bmi avmrun_overlay_real_itof_normalized
    asl real_work_a
    rol real_work_a+1
    inc real_work_shift
    jmp avmrun_overlay_real_itof_normalize_loop
avmrun_overlay_real_itof_normalized:
    lda #142
    sec
    sbc real_work_shift
    sta real_lhs_exp
    lda #$00
    sta real_lhs_mant
    lda real_work_a
    sta real_lhs_mant+1
    lda real_work_a+1
    sta real_lhs_mant+2
    lda #$00
    sta real_lhs_mant+3
    jsr real_pack_lhs_to_result
    clc
    rts

real_unpack_lhs:
    lda real_lhs_lo
    ora real_lhs_lo+1
    ora real_lhs_hi
    ora real_lhs_hi+1
    bne :+
    lda #$00
    sta real_lhs_exp
    sta real_lhs_sign
    sta real_lhs_mant
    sta real_lhs_mant+1
    sta real_lhs_mant+2
    sta real_lhs_mant+3
    rts
:   lda real_lhs_hi+1
    and #$80
    sta real_lhs_sign
    lda real_lhs_hi+1
    and #$7F
    asl a
    sta real_lhs_exp
    lda real_lhs_hi
    and #$80
    beq :+
    inc real_lhs_exp
:   lda real_lhs_lo
    sta real_lhs_mant
    lda real_lhs_lo+1
    sta real_lhs_mant+1
    lda real_lhs_hi
    and #$7F
    ora #$80
    sta real_lhs_mant+2
    lda #$00
    sta real_lhs_mant+3
    rts

real_unpack_rhs:
    lda real_rhs_lo
    ora real_rhs_lo+1
    ora real_rhs_hi
    ora real_rhs_hi+1
    bne :+
    lda #$00
    sta real_rhs_exp
    sta real_rhs_sign
    sta real_rhs_mant
    sta real_rhs_mant+1
    sta real_rhs_mant+2
    sta real_rhs_mant+3
    rts
:   lda real_rhs_hi+1
    and #$80
    sta real_rhs_sign
    lda real_rhs_hi+1
    and #$7F
    asl a
    sta real_rhs_exp
    lda real_rhs_hi
    and #$80
    beq :+
    inc real_rhs_exp
:   lda real_rhs_lo
    sta real_rhs_mant
    lda real_rhs_lo+1
    sta real_rhs_mant+1
    lda real_rhs_hi
    and #$7F
    ora #$80
    sta real_rhs_mant+2
    lda #$00
    sta real_rhs_mant+3
    rts

real_addsub_binary32:
    lda real_lhs_exp
    bne :+
    jmp real_return_rhs_packed
:   lda real_rhs_exp
    bne :+
    jmp real_return_lhs_packed
:
    lda real_rhs_exp
    cmp real_lhs_exp
    bcc :+
    bne real_swap_operands
    lda real_lhs_sign
    cmp real_rhs_sign
    beq :+
    jsr real_compare_mantissas
    bcs :+
real_swap_operands:
    jsr real_swap_unpacked_operands
:
    lda real_lhs_exp
    sec
    sbc real_rhs_exp
    sta real_align_shift
    cmp #40
    bcc :+
    ldx #$00
:   lda #$00
    sta real_work_a,x
    sta real_work_b,x
    inx
    cpx #$06
    bne :-

    lda real_lhs_mant
    sta real_work_a+1
    lda real_lhs_mant+1
    sta real_work_a+2
    lda real_lhs_mant+2
    sta real_work_a+3

    lda real_align_shift
    cmp #40
    bcs real_addsub_after_align

    lda real_rhs_mant
    sta real_work_b+1
    lda real_rhs_mant+1
    sta real_work_b+2
    lda real_rhs_mant+2
    sta real_work_b+3

    ldy real_align_shift
    beq real_addsub_after_align
real_align_rhs_loop:
    jsr real_shift_work_b_right
    bcc :+
    lda real_work_b
    ora #$01
    sta real_work_b
:
    dey
    bne real_align_rhs_loop
real_addsub_after_align:
    lda real_lhs_sign
    cmp real_rhs_sign
    bne real_addsub_subtract

    jsr real_add_work_b_to_work_a
    lda real_work_a+5
    ora real_work_a+4
    beq real_addsub_round_pack
    jsr real_shift_work_a_right
    bcc :+
    lda real_work_a
    ora #$01
    sta real_work_a
:
    inc real_lhs_exp
    bne :+
    jmp real_return_zero
:
    jmp real_addsub_round_pack

real_addsub_subtract:
    jsr real_sub_work_b_from_a
    lda real_work_a
    ora real_work_a+1
    ora real_work_a+2
    ora real_work_a+3
    ora real_work_a+4
    ora real_work_a+5
    bne :+
    jmp real_return_zero
:   lda real_work_a+3
    and #$80
    bne real_addsub_round_pack
real_normalize_lhs_loop:
    jsr real_shift_work_a_left
    dec real_lhs_exp
    bne :+
    jmp real_return_zero
:
    lda real_work_a+3
    and #$80
    beq real_normalize_lhs_loop

real_addsub_round_pack:
    lda real_work_a
    cmp #$80
    bcc real_addsub_store_pack
    bne real_addsub_round_up
    lda real_work_a+1
    and #$01
    beq real_addsub_store_pack
real_addsub_round_up:
    inc real_work_a+1
    bne real_addsub_store_pack
    inc real_work_a+2
    bne real_addsub_store_pack
    inc real_work_a+3
    bne real_addsub_store_pack
    inc real_work_a+4
    bne real_addsub_store_pack
    inc real_work_a+5
real_addsub_store_pack:
    lda real_work_a+5
    ora real_work_a+4
    beq real_addsub_post_pack_no_shift
    jsr real_shift_work_a_right
    bcc :+
    lda real_work_a
    ora #$01
    sta real_work_a
:   inc real_lhs_exp
    bne :+
    jmp real_return_zero
:   lda real_lhs_exp
    cmp #$FF
    bne :+
    jmp real_return_zero
:
    jmp real_addsub_store_result

real_addsub_post_pack_no_shift:
    lda real_lhs_exp
    cmp #$FF
    bne :+
    jmp real_return_zero
:
real_addsub_store_result:
    lda real_work_a+1
    sta real_lhs_mant
    lda real_work_a+2
    sta real_lhs_mant+1
    lda real_work_a+3
    sta real_lhs_mant+2
    lda #$00
    sta real_lhs_mant+3
    jmp real_pack_lhs_to_result
real_pack_lhs_to_result:
    lda real_lhs_exp
    beq real_return_zero
    lda real_lhs_mant
    sta real_result_lo
    lda real_lhs_mant+1
    sta real_result_lo+1
    lda real_lhs_mant+2
    and #$7F
    sta real_result_hi
    lda real_lhs_exp
    and #$01
    beq :+
    lda real_result_hi
    ora #$80
    sta real_result_hi
:   lda real_lhs_exp
    lsr a
    ora real_lhs_sign
    sta real_result_hi+1
    clc
    rts

real_return_lhs_packed:
    lda real_lhs_lo
    sta real_result_lo
    lda real_lhs_lo+1
    sta real_result_lo+1
    lda real_lhs_hi
    sta real_result_hi
    lda real_lhs_hi+1
    sta real_result_hi+1
    clc
    rts

real_return_rhs_packed:
    lda real_rhs_lo
    sta real_result_lo
    lda real_rhs_lo+1
    sta real_result_lo+1
    lda real_rhs_hi
    sta real_result_hi
    lda real_rhs_hi+1
    sta real_result_hi+1
    clc
    rts

real_return_zero:
    lda #$00
    sta real_result_lo
    sta real_result_lo+1
    sta real_result_hi
    sta real_result_hi+1
    clc
    rts

real_mul_binary32:
    lda real_lhs_exp
    beq real_return_zero
    lda real_rhs_exp
    beq real_return_zero
    lda real_lhs_sign
    eor real_rhs_sign
    sta real_lhs_sign

    lda real_lhs_exp
    clc
    adc real_rhs_exp
    sta real_exp_work
    lda #$00
    adc #$00
    sta real_exp_work+1
    lda real_exp_work
    sec
    sbc #127
    sta real_exp_work
    lda real_exp_work+1
    sbc #$00
    sta real_exp_work+1

    ldx #$00
real_mul_clear_loop:
    lda #$00
    sta real_work_a,x
    sta real_work_b,x
    inx
    cpx #$06
    bne real_mul_clear_loop

    lda real_lhs_mant
    sta real_work_b
    lda real_lhs_mant+1
    sta real_work_b+1
    lda real_lhs_mant+2
    sta real_work_b+2

    lda #24
    sta real_work_shift
real_mul_loop:
    lda real_rhs_mant
    and #$01
    beq real_mul_noadd
    jsr real_add_work_b_to_work_a
real_mul_noadd:
    lsr real_rhs_mant+2
    ror real_rhs_mant+1
    ror real_rhs_mant
    jsr real_shift_work_b_left
    dec real_work_shift
    bne real_mul_loop

    lda real_work_a+5
    and #$80
    beq real_mul_shift23
    inc real_exp_work
    bne :+
    inc real_exp_work+1
:   lda #24
    sta real_work_shift
    lda #$00
    sta real_work_c
    lda real_work_a+2
    and #$80
    beq real_mul_shift_store
    lda real_work_a
    ora real_work_a+1
    bne real_mul_round_shift24
    lda real_work_a+2
    and #$7F
    bne real_mul_round_shift24
    lda real_work_a+3
    and #$01
    beq real_mul_shift_store
real_mul_round_shift24:
    lda #$01
    sta real_work_c
    bne real_mul_shift_store
real_mul_shift23:
    lda #23
    sta real_work_shift
    lda #$00
    sta real_work_c
    lda real_work_a+2
    and #$40
    beq real_mul_shift_store
    lda real_work_a
    ora real_work_a+1
    bne real_mul_round_shift23
    lda real_work_a+2
    and #$3F
    bne real_mul_round_shift23
    lda real_work_a+2
    and #$80
    beq real_mul_shift_store
real_mul_round_shift23:
    lda #$01
    sta real_work_c
real_mul_shift_store:
real_mul_shift_loop:
    jsr real_shift_work_a_right
    dec real_work_shift
    bne real_mul_shift_loop

    lda real_work_c
    beq real_mul_pack_check
    inc real_work_a
    bne real_mul_pack_check
    inc real_work_a+1
    bne real_mul_pack_check
    inc real_work_a+2
    bne real_mul_pack_check
    lda #$00
    sta real_work_a
    sta real_work_a+1
    lda #$80
    sta real_work_a+2
    inc real_exp_work
    bne real_mul_pack_check
    inc real_exp_work+1

real_mul_pack_check:
    lda real_exp_work+1
    bne real_mul_return_zero
    lda real_exp_work
    beq real_mul_return_zero
    cmp #$FF
    beq real_mul_return_zero
    sta real_lhs_exp
    lda real_work_a
    sta real_lhs_mant
    lda real_work_a+1
    sta real_lhs_mant+1
    lda real_work_a+2
    sta real_lhs_mant+2
    lda #$00
    sta real_lhs_mant+3
    lda real_lhs_mant+2
    and #$80
    beq real_mul_return_zero
    jmp real_pack_lhs_to_result
real_mul_return_zero:
    jmp real_return_zero

real_div_binary32:
    lda real_lhs_exp
    beq :+
    lda real_rhs_exp
    beq :+
    jmp real_div_entry_ok
:   jmp real_div_return_zero
real_div_entry_ok:
    lda real_lhs_sign
    eor real_rhs_sign
    sta real_lhs_sign

    jsr real_compare_mantissas
    bcs real_div_ge

    lda real_lhs_exp
    sec
    sbc real_rhs_exp
    sta real_exp_work
    lda #$00
    sbc #$00
    sta real_exp_work+1
    clc
    lda real_exp_work
    adc #126
    sta real_exp_work
    lda real_exp_work+1
    adc #$00
    sta real_exp_work+1
    lda #24
    sta real_work_shift
    jmp real_div_setup

real_div_ge:
    lda real_lhs_exp
    sec
    sbc real_rhs_exp
    sta real_exp_work
    lda #$00
    sbc #$00
    sta real_exp_work+1
    clc
    lda real_exp_work
    adc #127
    sta real_exp_work
    lda real_exp_work+1
    adc #$00
    sta real_exp_work+1
    lda #23
    sta real_work_shift

real_div_setup:
    ldx #$00
real_div_clear_loop:
    lda #$00
    sta real_work_a,x
    sta real_work_b,x
    inx
    cpx #$06
    bne real_div_clear_loop
    ldx #$00
real_div_clear_q_loop:
    lda #$00
    sta real_work_c,x
    inx
    cpx #$03
    bne real_div_clear_q_loop

    lda real_lhs_mant
    sta real_work_a
    lda real_lhs_mant+1
    sta real_work_a+1
    lda real_lhs_mant+2
    sta real_work_a+2
real_div_num_shift_loop:
    jsr real_shift_work_a_left
    dec real_work_shift
    bne real_div_num_shift_loop

    lda real_rhs_mant
    sta real_work_b
    lda real_rhs_mant+1
    sta real_work_b+1
    lda real_rhs_mant+2
    sta real_work_b+2
    lda #23
    sta real_work_shift
real_div_den_shift_loop:
    jsr real_shift_work_b_left
    dec real_work_shift
    bne real_div_den_shift_loop

    lda #24
    sta real_work_shift
real_div_loop:
    asl real_work_c
    rol real_work_c+1
    rol real_work_c+2
    jsr real_compare_work_a_ge_b
    bcc real_div_skip_sub
    jsr real_sub_work_b_from_a
    inc real_work_c
real_div_skip_sub:
    jsr real_shift_work_b_right
    dec real_work_shift
    bne real_div_loop

    lda real_work_c
    ora real_work_c+1
    ora real_work_c+2
    bne :+
    jmp real_div_return_zero
:   jsr real_compare_work_a_ge_b
    bcc real_div_check_normalize
    lda real_work_a+5
    cmp real_work_b+5
    bne real_div_round_up
    lda real_work_a+4
    cmp real_work_b+4
    bne real_div_round_up
    lda real_work_a+3
    cmp real_work_b+3
    bne real_div_round_up
    lda real_work_a+2
    cmp real_work_b+2
    bne real_div_round_up
    lda real_work_a+1
    cmp real_work_b+1
    bne real_div_round_up
    lda real_work_a
    cmp real_work_b
    bne real_div_round_up
    lda real_work_c
    and #$01
    beq real_div_check_normalize
real_div_round_up:
    inc real_work_c
    bne real_div_check_normalize
    inc real_work_c+1
    bne real_div_check_normalize
    inc real_work_c+2
    bne real_div_check_normalize
    lda #$00
    sta real_work_c
    sta real_work_c+1
    lda #$80
    sta real_work_c+2
    inc real_exp_work
    bne real_div_check_normalize
    inc real_exp_work+1
real_div_check_normalize:
    lda real_work_c+2
    and #$80
    bne real_div_pack
real_div_normalize_loop:
    asl real_work_c
    rol real_work_c+1
    rol real_work_c+2
    lda real_exp_work
    bne :+
    dec real_exp_work+1
:   dec real_exp_work
    lda real_exp_work+1
    bne real_div_return_zero
    lda real_exp_work
    beq real_div_return_zero
    lda real_work_c+2
    and #$80
    beq real_div_normalize_loop
real_div_pack:
    lda real_exp_work+1
    bne real_div_return_zero
    lda real_exp_work
    beq real_div_return_zero
    cmp #$FF
    beq real_div_return_zero
    sta real_lhs_exp
    lda real_work_c
    sta real_lhs_mant
    lda real_work_c+1
    sta real_lhs_mant+1
    lda real_work_c+2
    sta real_lhs_mant+2
    lda #$00
    sta real_lhs_mant+3
    jmp real_pack_lhs_to_result
real_div_return_zero:
    jmp real_return_zero

real_trunc_lhs_to_int_word:
    lda real_lhs_exp
    bne :+
    lda #$00
    sta word_tmp
    sta word_tmp+1
    clc
    rts
:   cmp #127
    bcs :+
    lda #$00
    sta word_tmp
    sta word_tmp+1
    clc
    rts
:   sec
    sbc #127
    cmp #24
    bcc :+
    sec
    rts
:   sta real_work_shift
    lda real_lhs_mant
    sta real_work_a
    lda real_lhs_mant+1
    sta real_work_a+1
    lda real_lhs_mant+2
    sta real_work_a+2
    lda #$00
    sta real_work_a+3
    lda #23
    sec
    sbc real_work_shift
    sta real_work_shift
real_trunc_lhs_shift_loop:
    lda real_work_shift
    beq real_trunc_lhs_shift_done
    lsr real_work_a+3
    ror real_work_a+2
    ror real_work_a+1
    ror real_work_a
    dec real_work_shift
    jmp real_trunc_lhs_shift_loop
real_trunc_lhs_shift_done:
    lda real_work_a+2
    ora real_work_a+3
    beq :+
    sec
    rts
:   lda real_lhs_sign
    beq real_trunc_lhs_positive
    lda real_work_a+1
    cmp #$80
    bcc real_trunc_lhs_negative_ok
    bne real_trunc_lhs_fail
    lda real_work_a
    bne real_trunc_lhs_fail
real_trunc_lhs_negative_ok:
    lda #$00
    sec
    sbc real_work_a
    sta word_tmp
    lda #$00
    sbc real_work_a+1
    sta word_tmp+1
    clc
    rts
real_trunc_lhs_positive:
    lda real_work_a+1
    bmi real_trunc_lhs_fail
    lda real_work_a
    sta word_tmp
    lda real_work_a+1
    sta word_tmp+1
    clc
    rts
real_trunc_lhs_fail:
    sec
    rts

real_add_work_b_to_work_a:
    clc
    lda real_work_a
    adc real_work_b
    sta real_work_a
    lda real_work_a+1
    adc real_work_b+1
    sta real_work_a+1
    lda real_work_a+2
    adc real_work_b+2
    sta real_work_a+2
    lda real_work_a+3
    adc real_work_b+3
    sta real_work_a+3
    lda real_work_a+4
    adc real_work_b+4
    sta real_work_a+4
    lda real_work_a+5
    adc real_work_b+5
    sta real_work_a+5
    rts

real_sub_work_b_from_a:
    sec
    lda real_work_a
    sbc real_work_b
    sta real_work_a
    lda real_work_a+1
    sbc real_work_b+1
    sta real_work_a+1
    lda real_work_a+2
    sbc real_work_b+2
    sta real_work_a+2
    lda real_work_a+3
    sbc real_work_b+3
    sta real_work_a+3
    lda real_work_a+4
    sbc real_work_b+4
    sta real_work_a+4
    lda real_work_a+5
    sbc real_work_b+5
    sta real_work_a+5
    rts

real_compare_work_a_ge_b:
    lda real_work_a+5
    cmp real_work_b+5
    bne :+
    lda real_work_a+4
    cmp real_work_b+4
    bne :+
    lda real_work_a+3
    cmp real_work_b+3
    bne :+
    lda real_work_a+2
    cmp real_work_b+2
    bne :+
    lda real_work_a+1
    cmp real_work_b+1
    bne :+
    lda real_work_a
    cmp real_work_b
:   rts

real_shift_work_a_left:
    asl real_work_a
    rol real_work_a+1
    rol real_work_a+2
    rol real_work_a+3
    rol real_work_a+4
    rol real_work_a+5
    rts

real_shift_work_a_right:
    lsr real_work_a+5
    ror real_work_a+4
    ror real_work_a+3
    ror real_work_a+2
    ror real_work_a+1
    ror real_work_a
    rts

real_shift_work_b_left:
    asl real_work_b
    rol real_work_b+1
    rol real_work_b+2
    rol real_work_b+3
    rol real_work_b+4
    rol real_work_b+5
    rts

real_shift_work_b_right:
    lsr real_work_b+5
    ror real_work_b+4
    ror real_work_b+3
    ror real_work_b+2
    ror real_work_b+1
    ror real_work_b
    rts

real_compare_mantissas:
    lda real_lhs_mant+3
    cmp real_rhs_mant+3
    bne :+
    lda real_lhs_mant+2
    cmp real_rhs_mant+2
    bne :+
    lda real_lhs_mant+1
    cmp real_rhs_mant+1
    bne :+
    lda real_lhs_mant
    cmp real_rhs_mant
:   rts

real_swap_unpacked_operands:
    lda real_lhs_sign
    pha
    lda real_rhs_sign
    sta real_lhs_sign
    pla
    sta real_rhs_sign

    lda real_lhs_exp
    pha
    lda real_rhs_exp
    sta real_lhs_exp
    pla
    sta real_rhs_exp

    ldx #$00
:   lda real_lhs_mant,x
    pha
    lda real_rhs_mant,x
    sta real_lhs_mant,x
    pla
    sta real_rhs_mant,x
    inx
    cpx #$04
    bne :-

    lda real_lhs_lo
    pha
    lda real_rhs_lo
    sta real_lhs_lo
    pla
    sta real_rhs_lo
    lda real_lhs_lo+1
    pha
    lda real_rhs_lo+1
    sta real_lhs_lo+1
    pla
    sta real_rhs_lo+1
    lda real_lhs_hi
    pha
    lda real_rhs_hi
    sta real_lhs_hi
    pla
    sta real_rhs_hi
    lda real_lhs_hi+1
    pha
    lda real_rhs_hi+1
    sta real_lhs_hi+1
    pla
    sta real_rhs_hi+1
    rts


avmrun_overlay_end:
