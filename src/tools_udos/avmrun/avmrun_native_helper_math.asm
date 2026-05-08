.include "avmrun_native_helper_abi.inc"

.export avmrun_native_helper_math_header
.export avmrun_native_helper_math_end

; MATH1 currently executes only on the compat/interpreter path.
; Its long-lived FSqrt working set uses a fixed compat scratch block below the
; tileset adapter scratch instead of the shared ZPTEMP area.
MATH_RAW_HI = $3C59
MATH_RES_EXP = $3C5A
MATH_RAD0 = $3C5B
MATH_RAD1 = $3C5C
MATH_RAD2 = $3C5D
MATH_RAD3 = $3C5E
MATH_RAD4 = $3C5F
MATH_RAD5 = $3C60
MATH_ROOT0 = $3C61
MATH_ROOT1 = $3C62
MATH_ROOT2 = $3C63
MATH_REM0 = $3C64
MATH_REM1 = $3C65
MATH_REM2 = $3C66
MATH_REM3 = $3C67
MATH_TRIAL0 = $3C68
MATH_TRIAL1 = $3C69
MATH_TRIAL2 = $3C6A
MATH_TRIAL3 = $3C6B
MATH_COUNT = $3C6C
MATH_EXP = $3C6D

.segment "CODE"

avmrun_native_helper_math_header:
    .byte AVMRUN_NATIVE_HELPER_MAGIC_0
    .byte AVMRUN_NATIVE_HELPER_MAGIC_1
    .byte AVMRUN_NATIVE_HELPER_MAGIC_2
    .byte AVMRUN_NATIVE_HELPER_MAGIC_3
    .byte AVMRUN_NATIVE_HELPER_ABI_VERSION
    .byte AVMRUN_NATIVE_HELPER_KIND_MATH
    .word avmrun_native_helper_math_entry_table - avmrun_native_helper_math_header
    .word avmrun_native_helper_math_end - avmrun_native_helper_math_header
    .byte 2
    .byte 0

avmrun_native_helper_math_entry_table:
    .byte AVMRUN_NATIVE_HELPER_ENTRY_MATH_FABS
    .word avmrun_native_helper_math_fabs - avmrun_native_helper_math_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_MATH_FSQRT
    .word avmrun_native_helper_math_fsqrt - avmrun_native_helper_math_header

; x points at a packed REAL value:
;   0..1 = high word
;   2..3 = low word
; FAbs is sign-bit clear on the high word.
avmrun_native_helper_math_fabs:
    lda 1,x
    and #$7F
    sta 1,x
    rts

; FSqrt is a narrow first implementation over the existing packed REAL format.
; It handles nonnegative values directly by:
;   1. unpacking exponent and 24-bit mantissa
;   2. building a 48-bit scaled radicand
;   3. running a restoring integer square root for 24 result bits
;   4. packing the normalized result back into place
; Negative inputs currently return zero.
avmrun_native_helper_math_fsqrt:
    lda 0,x
    sta MATH_RAW_HI
    ora 1,x
    ora 2,x
    ora 3,x
    bne :+
    jmp avmrun_native_helper_math_return_zero
:   lda 1,x
    bpl :+
    jmp avmrun_native_helper_math_return_zero
:   
    and #$7F
    asl a
    sta MATH_EXP
    lda MATH_RAW_HI
    and #$80
    beq :+
    inc MATH_EXP
:   lda MATH_EXP
    clc
    adc #127
    ror a
    sta MATH_RES_EXP
    lda MATH_EXP
    and #$01
    bne :+
    lda #24
    bne avmrun_native_helper_math_store_shift
:   lda #23
avmrun_native_helper_math_store_shift:
    sta MATH_COUNT

    lda 2,x
    sta MATH_RAD0
    lda 3,x
    sta MATH_RAD1
    lda MATH_RAW_HI
    and #$7F
    ora #$80
    sta MATH_RAD2
    lda #$00
    sta MATH_RAD3
    sta MATH_RAD4
    sta MATH_RAD5
    sta MATH_ROOT0
    sta MATH_ROOT1
    sta MATH_ROOT2
    sta MATH_REM0
    sta MATH_REM1
    sta MATH_REM2
    sta MATH_REM3

avmrun_native_helper_math_shift_radicand_loop:
    lda MATH_COUNT
    beq avmrun_native_helper_math_shift_radicand_done
    asl MATH_RAD0
    rol MATH_RAD1
    rol MATH_RAD2
    rol MATH_RAD3
    rol MATH_RAD4
    rol MATH_RAD5
    dec MATH_COUNT
    jmp avmrun_native_helper_math_shift_radicand_loop
avmrun_native_helper_math_shift_radicand_done:

    lda #24
    sta MATH_COUNT
avmrun_native_helper_math_sqrt_loop:
    jsr avmrun_native_helper_math_shift_rad_bit_into_rem
    jsr avmrun_native_helper_math_shift_rad_bit_into_rem
    jsr avmrun_native_helper_math_build_trial
    jsr avmrun_native_helper_math_compare_rem_trial
    bcc avmrun_native_helper_math_root_shift_only
    jsr avmrun_native_helper_math_subtract_trial_from_rem
    asl MATH_ROOT0
    rol MATH_ROOT1
    rol MATH_ROOT2
    lda MATH_ROOT0
    ora #$01
    sta MATH_ROOT0
    jmp avmrun_native_helper_math_sqrt_next
avmrun_native_helper_math_root_shift_only:
    asl MATH_ROOT0
    rol MATH_ROOT1
    rol MATH_ROOT2
avmrun_native_helper_math_sqrt_next:
    dec MATH_COUNT
    bne avmrun_native_helper_math_sqrt_loop

    lda MATH_ROOT0
    ora MATH_ROOT1
    ora MATH_ROOT2
    bne avmrun_native_helper_math_pack_result
    jmp avmrun_native_helper_math_return_zero

avmrun_native_helper_math_pack_result:
    lda MATH_ROOT0
    sta 2,x
    lda MATH_ROOT1
    sta 3,x
    lda MATH_ROOT2
    and #$7F
    ldy MATH_RES_EXP
    tya
    and #$01
    beq :+
    lda MATH_ROOT2
    and #$7F
    ora #$80
:   sta 0,x
    lda MATH_RES_EXP
    lsr a
    sta 1,x
    rts

avmrun_native_helper_math_return_zero:
    lda #$00
    sta 0,x
    sta 1,x
    sta 2,x
    sta 3,x
    rts

avmrun_native_helper_math_shift_rad_bit_into_rem:
    asl MATH_RAD0
    rol MATH_RAD1
    rol MATH_RAD2
    rol MATH_RAD3
    rol MATH_RAD4
    rol MATH_RAD5
    rol MATH_REM0
    rol MATH_REM1
    rol MATH_REM2
    rol MATH_REM3
    rts

avmrun_native_helper_math_build_trial:
    lda MATH_ROOT0
    asl a
    sta MATH_TRIAL0
    lda MATH_ROOT1
    rol a
    sta MATH_TRIAL1
    lda MATH_ROOT2
    rol a
    sta MATH_TRIAL2
    lda #$00
    rol a
    sta MATH_TRIAL3
    asl MATH_TRIAL0
    rol MATH_TRIAL1
    rol MATH_TRIAL2
    rol MATH_TRIAL3
    inc MATH_TRIAL0
    bne :+
    inc MATH_TRIAL1
    bne :+
    inc MATH_TRIAL2
    bne :+
    inc MATH_TRIAL3
:   rts

avmrun_native_helper_math_compare_rem_trial:
    lda MATH_REM3
    cmp MATH_TRIAL3
    bne :+
    lda MATH_REM2
    cmp MATH_TRIAL2
    bne :+
    lda MATH_REM1
    cmp MATH_TRIAL1
    bne :+
    lda MATH_REM0
    cmp MATH_TRIAL0
:   rts

avmrun_native_helper_math_subtract_trial_from_rem:
    sec
    lda MATH_REM0
    sbc MATH_TRIAL0
    sta MATH_REM0
    lda MATH_REM1
    sbc MATH_TRIAL1
    sta MATH_REM1
    lda MATH_REM2
    sbc MATH_TRIAL2
    sta MATH_REM2
    lda MATH_REM3
    sbc MATH_TRIAL3
    sta MATH_REM3
    rts

avmrun_native_helper_math_end:
