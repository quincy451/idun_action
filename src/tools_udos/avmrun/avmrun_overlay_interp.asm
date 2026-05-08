.include "avmrun_overlay_abi.inc"
.include "avmrun_overlay_resident.inc"

.export avmrun_overlay_header
.export avmrun_overlay_entry
.export avmrun_overlay_end

INTERP_STACK_MAX = 16
RESIDENT_LAUNCH_TRACE_STAGE = $03F2

OPCODE_PUSH8 = $10
OPCODE_PUSH16 = $11
OPCODE_STORE = $12
OPCODE_LOAD = $13
OPCODE_ADD = $14
OPCODE_SUB = $15
OPCODE_EQ = $16
OPCODE_NE = $17
OPCODE_JZ = $18
OPCODE_JMP = $19
OPCODE_DUP = $1A
OPCODE_DROP = $1B
OPCODE_LT = $1C
OPCODE_GT = $1D
OPCODE_BAND = $1E
OPCODE_BOR = $1F
OPCODE_BXOR = $20
OPCODE_SHL1 = $21
OPCODE_SHR1 = $22
OPCODE_FADD = $23
OPCODE_FSUB = $24
OPCODE_FMUL = $25
OPCODE_FDIV = $26
OPCODE_FTOI = $27
OPCODE_ITOF = $28
OPCODE_CALL = $45
OPCODE_RET = $48
OPCODE_CALLN = $49
OPCODE_SETP16 = $61

INTRINSIC_PRINT = $FF00
INTRINSIC_PRINTE = $FF10
INTRINSIC_EXIT = $FF20
INTRINSIC_PRINTI = $FF30
INTRINSIC_PRINTIE = $FF31
INTRINSIC_PRINTREAL = $FF32
INTRINSIC_LINKED_PRINT = $FE00
INTRINSIC_LINKED_PRINTE = $FE10
INTRINSIC_LINKED_PRINTI = $FE30
INTRINSIC_LINKED_PRINTIE = $FE31
INTRINSIC_LINKED_PRINTREAL = $FE32
INTRINSIC_LINKED_MATH_FABS = $FA01
INTRINSIC_LINKED_MATH_FSQRT = $FA02
INTRINSIC_LINKED_DBF_CREATE = $FB01
INTRINSIC_LINKED_DBF_CURRRECNO = $FB02
INTRINSIC_LINKED_DBF_TOTALRECS = $FB03
INTRINSIC_LINKED_DBF_CLOSE = $FB04
INTRINSIC_LINKED_DBF_OPEN = $FB05
INTRINSIC_LINKED_DBF_APPENDBLANK = $FB06
INTRINSIC_LINKED_DBF_GO = $FB07
INTRINSIC_LINKED_DBF_READFIELD = $FB08
INTRINSIC_LINKED_DBF_WRITEFIELD = $FB09
INTRINSIC_LINKED_GFX_BITMAP_ON = $FC01
INTRINSIC_LINKED_GFX_BITMAP_OFF = $FC02
INTRINSIC_LINKED_GFX_MBITMAP_ON = $FC03
INTRINSIC_LINKED_GFX_BG_COLOR = $FC04
INTRINSIC_LINKED_GFX_BORDER_COLOR = $FC05
INTRINSIC_LINKED_GFX_VIC_BANK = $FC06
INTRINSIC_LINKED_GFX_SCREEN_BASE = $FC07
INTRINSIC_LINKED_GFX_BITMAP_BASE = $FC08
INTRINSIC_LINKED_GFX_BITMAP_FILL = $FC09
INTRINSIC_LINKED_GFX_SCREEN_CELL = $FC0A
INTRINSIC_LINKED_GFX_COLOR_CELL = $FC0B
INTRINSIC_LINKED_GFX_BITMAP_SHOW = $FC0C
INTRINSIC_LINKED_GFX_BITMAP_HIDE = $FC0D
INTRINSIC_LINKED_GFX_BITMAP_COPY = $FC0E
INTRINSIC_LINKED_GFX_SCREEN_COPY = $FC0F
INTRINSIC_LINKED_GFX_COLOR_COPY = $FC10
INTRINSIC_LINKED_GFX_BITMAP_CELL_COLORS = $FC11
INTRINSIC_LINKED_GFX_BITMAP_CELL_DATA = $FC12
INTRINSIC_LINKED_GFX_BITMAP_BLIT = $FC13
INTRINSIC_LINKED_GFX_TILE_DRAW = $FC14
INTRINSIC_LINKED_GFX_TILE_RECT_FILL = $FC15
INTRINSIC_LINKED_GFX_BITMAP_MASK_BLIT = $FC16
INTRINSIC_LINKED_GFX_TILE_MASK_DRAW = $FC17
INTRINSIC_LINKED_GFX_TILESET_DRAW = $FC18
INTRINSIC_LINKED_GFX_TILESET_RECT_FILL = $FC19
INTRINSIC_LINKED_GFX_TILESET_MASK_DRAW = $FC1A
INTRINSIC_LINKED_GFX_TILESET_MASK_RECT_FILL = $FC1B
INTRINSIC_LINKED_SIDSPR_SPRITE_ON = $FD01
INTRINSIC_LINKED_SIDSPR_SPRITE_OFF = $FD02
INTRINSIC_LINKED_SIDSPR_SPRITE_POS = $FD03
INTRINSIC_LINKED_SIDSPR_SPRITE_DATA = $FD04
INTRINSIC_LINKED_SIDSPR_SPRITE_COLOR = $FD05
INTRINSIC_LINKED_SIDSPR_SID_FREQ = $FD10
INTRINSIC_LINKED_SIDSPR_SID_WAVE = $FD11
INTRINSIC_LINKED_SIDSPR_SID_AD = $FD12
INTRINSIC_LINKED_SIDSPR_SID_SR = $FD13
INTRINSIC_LINKED_SIDSPR_SID_ON = $FD14
INTRINSIC_LINKED_SIDSPR_SID_OFF = $FD15
INTRINSIC_LINKED_SIDSPR_SID_VOL = $FD16

AVMRUN_INTERP_RESUME_NONE = $00
AVMRUN_INTERP_RESUME_AFTER_REAL_PUSH = $01
AVMRUN_INTERP_RESUME_AFTER_FTOI = $02
AVMRUN_INTERP_RESUME_AFTER_ADVANCE3 = $03

.segment "CODE"

avmrun_overlay_header:
    .byte 'A','V','O','V'
    .byte AVMRUN_OVERLAY_ABI_VERSION
    .word AVMRUN_OVERLAY_EXEC_BASE
    .word avmrun_overlay_entry
    .word avmrun_overlay_end - avmrun_overlay_header
    .word $0000

svc_retptr = AVMRUN_RES_svc_retptr
file_params = AVMRUN_RES_file_params
pptr = AVMRUN_RES_pptr
payload_ptr = AVMRUN_RES_payload_ptr
entry_ptr = AVMRUN_RES_entry_ptr
scan_ptr = AVMRUN_RES_scan_ptr
scan_end = AVMRUN_RES_scan_end
word_tmp = AVMRUN_RES_word_tmp
real_print_low = AVMRUN_RES_real_print_low
real_print_high = AVMRUN_RES_real_print_high
real_print_flag = AVMRUN_RES_real_print_flag
real_lhs_lo = AVMRUN_RES_real_lhs_lo
real_lhs_hi = AVMRUN_RES_real_lhs_hi
real_rhs_lo = AVMRUN_RES_real_rhs_lo
real_rhs_hi = AVMRUN_RES_real_rhs_hi
real_result_lo = AVMRUN_RES_real_result_lo
real_result_hi = AVMRUN_RES_real_result_hi
real_flip_rhs_sign = AVMRUN_RES_real_flip_rhs_sign
interp_error_ptr = AVMRUN_RES_interp_error_ptr
interp_sp = AVMRUN_RES_interp_sp
interp_rsp = AVMRUN_RES_interp_rsp
interp_string_ptr = AVMRUN_RES_interp_string_ptr
interp_stack_lo = AVMRUN_RES_interp_stack_lo
interp_stack_hi = AVMRUN_RES_interp_stack_hi
interp_rstack_lo = AVMRUN_RES_interp_rstack_lo
interp_rstack_hi = AVMRUN_RES_interp_rstack_hi
avmrun_overlay_requested_cmd = AVMRUN_RES_avmrun_overlay_requested_cmd
avmrun_interp_result = AVMRUN_RES_avmrun_interp_result
avmrun_interp_service_kind = AVMRUN_RES_avmrun_interp_service_kind
avmrun_interp_service_cmd = AVMRUN_RES_avmrun_interp_service_cmd
avmrun_interp_resume_state = AVMRUN_RES_avmrun_interp_resume_state
avmrun_interp_service_failed = AVMRUN_RES_avmrun_interp_service_failed
scan_ptr_before_end = AVMRUN_RES_scan_ptr_before_end
ensure_scan_room_2 = AVMRUN_RES_ensure_scan_room_2
ensure_scan_room_3 = AVMRUN_RES_ensure_scan_room_3
advance_scan_ptr = AVMRUN_RES_advance_scan_ptr
msg_real_to_int_range = AVMRUN_RES_msg_real_to_int_range
native_print = AVMRUN_RES_native_print
native_printe = AVMRUN_RES_native_printe
native_linked_print = AVMRUN_RES_native_linked_print
native_linked_printe = AVMRUN_RES_native_linked_printe
native_printi = AVMRUN_RES_native_printi
native_printie = AVMRUN_RES_native_printie
native_printreal = AVMRUN_RES_native_printreal
native_math_fabs = AVMRUN_RES_native_math_fabs
native_math_fsqrt = AVMRUN_RES_native_math_fsqrt
native_dbf_create = AVMRUN_RES_native_dbf_create
native_dbf_open = AVMRUN_RES_native_dbf_open
native_dbf_currrecno = AVMRUN_RES_native_dbf_currrecno
native_dbf_totalrecs = AVMRUN_RES_native_dbf_totalrecs
native_dbf_close = AVMRUN_RES_native_dbf_close
native_dbf_appendblank = AVMRUN_RES_native_dbf_appendblank
native_dbf_go = AVMRUN_RES_native_dbf_go
native_dbf_readfield = AVMRUN_RES_native_dbf_readfield
native_dbf_writefield = AVMRUN_RES_native_dbf_writefield
native_gfx_bitmap_on = AVMRUN_RES_native_gfx_bitmap_on
native_gfx_bitmap_off = AVMRUN_RES_native_gfx_bitmap_off
native_gfx_mbitmap_on = AVMRUN_RES_native_gfx_mbitmap_on
native_gfx_bg_color = AVMRUN_RES_native_gfx_bg_color
native_gfx_border_color = AVMRUN_RES_native_gfx_border_color
native_gfx_vic_bank = AVMRUN_RES_native_gfx_vic_bank
native_gfx_screen_base = AVMRUN_RES_native_gfx_screen_base
native_gfx_bitmap_base = AVMRUN_RES_native_gfx_bitmap_base
native_gfx_bitmap_fill = AVMRUN_RES_native_gfx_bitmap_fill
native_gfx_screen_cell = AVMRUN_RES_native_gfx_screen_cell
native_gfx_color_cell = AVMRUN_RES_native_gfx_color_cell
native_gfx_bitmap_show = AVMRUN_RES_native_gfx_bitmap_show
native_gfx_bitmap_hide = AVMRUN_RES_native_gfx_bitmap_hide
native_gfx_bitmap_copy = AVMRUN_RES_native_gfx_bitmap_copy
native_gfx_screen_copy = AVMRUN_RES_native_gfx_screen_copy
native_gfx_color_copy = AVMRUN_RES_native_gfx_color_copy
native_gfx_bitmap_cell_colors = AVMRUN_RES_native_gfx_bitmap_cell_colors
native_gfx_bitmap_cell_data = AVMRUN_RES_native_gfx_bitmap_cell_data
native_gfx_bitmap_blit = AVMRUN_RES_native_gfx_bitmap_blit
native_gfx_tile_draw = AVMRUN_RES_native_gfx_tile_draw
native_gfx_tile_rect_fill = AVMRUN_RES_native_gfx_tile_rect_fill
native_gfx_bitmap_mask_blit = AVMRUN_RES_native_gfx_bitmap_mask_blit
native_gfx_tile_mask_draw = AVMRUN_RES_native_gfx_tile_mask_draw
native_gfx_tileset_draw = AVMRUN_RES_native_gfx_tileset_draw
native_gfx_tileset_rect_fill = AVMRUN_RES_native_gfx_tileset_rect_fill
native_gfx_tileset_mask_draw = AVMRUN_RES_native_gfx_tileset_mask_draw
native_gfx_tileset_mask_rect_fill = AVMRUN_RES_native_gfx_tileset_mask_rect_fill
native_sidspr_sprite_on = AVMRUN_RES_native_sidspr_sprite_on
native_sidspr_sprite_off = AVMRUN_RES_native_sidspr_sprite_off
native_sidspr_sprite_pos = AVMRUN_RES_native_sidspr_sprite_pos
native_sidspr_sprite_data = AVMRUN_RES_native_sidspr_sprite_data
native_sidspr_sprite_color = AVMRUN_RES_native_sidspr_sprite_color
native_sidspr_sid_freq = AVMRUN_RES_native_sidspr_sid_freq
native_sidspr_sid_wave = AVMRUN_RES_native_sidspr_sid_wave
native_sidspr_sid_ad = AVMRUN_RES_native_sidspr_sid_ad
native_sidspr_sid_sr = AVMRUN_RES_native_sidspr_sid_sr
native_sidspr_sid_on = AVMRUN_RES_native_sidspr_sid_on
native_sidspr_sid_off = AVMRUN_RES_native_sidspr_sid_off
native_sidspr_sid_vol = AVMRUN_RES_native_sidspr_sid_vol
native_exit = AVMRUN_RES_native_exit

math_fsqrt_raw_hi = $3C59
math_fsqrt_res_exp = $3C5A
math_fsqrt_rad0 = $3C5B
math_fsqrt_rad1 = $3C5C
math_fsqrt_rad2 = $3C5D
math_fsqrt_rad3 = $3C5E
math_fsqrt_rad4 = $3C5F
math_fsqrt_rad5 = $3C60
math_fsqrt_root0 = $3C61
math_fsqrt_root1 = $3C62
math_fsqrt_root2 = $3C63
math_fsqrt_rem0 = $3C64
math_fsqrt_rem1 = $3C65
math_fsqrt_rem2 = $3C66
math_fsqrt_rem3 = $3C67
math_fsqrt_trial0 = $3C68
math_fsqrt_trial1 = $3C69
math_fsqrt_trial2 = $3C6A
math_fsqrt_trial3 = $3C6B
math_fsqrt_count = $3C6C
math_fsqrt_exp = $3C6D

avmrun_overlay_entry:
    lda avmrun_overlay_requested_cmd
    cmp #AVMRUN_OVERLAY_CMD_INTERP_START
    beq interpret_payload_start
    cmp #AVMRUN_OVERLAY_CMD_INTERP_RESUME
    beq interpret_payload_resume
    jmp interpret_payload_fail

interpret_payload_start:
    lda #$00
    sta interp_sp
    sta interp_rsp
    sta interp_error_ptr
    sta interp_error_ptr+1
    sta avmrun_interp_resume_state
    sta avmrun_interp_service_failed
    lda #$B0
    sta RESIDENT_LAUNCH_TRACE_STAGE
    lda entry_ptr
    sta scan_ptr
    lda entry_ptr+1
    sta scan_ptr+1
    lda payload_ptr
    sta interp_string_ptr
    lda payload_ptr+1
    sta interp_string_ptr+1
    jmp interpret_payload_loop

interpret_payload_resume:
    lda avmrun_interp_resume_state
    beq interpret_payload_loop
    cmp #AVMRUN_INTERP_RESUME_AFTER_REAL_PUSH
    beq interpret_resume_after_real_push
    cmp #AVMRUN_INTERP_RESUME_AFTER_FTOI
    beq interpret_resume_after_ftoi
    cmp #AVMRUN_INTERP_RESUME_AFTER_ADVANCE3
    beq interpret_resume_after_advance3
    jmp interpret_payload_fail

interpret_resume_after_real_push:
    lda avmrun_interp_service_failed
    beq :+
    jmp interpret_payload_fail
:   
    jsr interpret_real_push_result
    bcc :+
    jmp interpret_payload_fail
:   lda #$00
    sta avmrun_interp_resume_state
    lda #$01
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_resume_after_ftoi:
    lda avmrun_interp_service_failed
    beq :+
    lda #<msg_real_to_int_range
    sta interp_error_ptr
    lda #>msg_real_to_int_range
    sta interp_error_ptr+1
    jmp interpret_payload_fail
:   jsr interp_push_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda #$00
    sta avmrun_interp_resume_state
    lda #$01
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_resume_after_advance3:
    lda avmrun_interp_service_failed
    beq :+
    jmp interpret_payload_fail
:   
    lda #$00
    sta avmrun_interp_resume_state
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_payload_loop:
    lda scan_ptr
    cmp scan_end
    bne :+
    lda scan_ptr+1
    cmp scan_end+1
    bne :+
    jmp interpret_payload_done
:   jsr scan_ptr_before_end
    bcc :+
    jmp interpret_payload_fail
:   ldy #$00
    lda (scan_ptr),y
    cmp #OPCODE_PUSH8
    bne :+
    jmp interpret_push8
:   cmp #OPCODE_PUSH16
    bne :+
    jmp interpret_push16
:   cmp #OPCODE_STORE
    bne :+
    jmp interpret_store
:   cmp #OPCODE_LOAD
    bne :+
    jmp interpret_load
:   cmp #OPCODE_ADD
    bne :+
    jmp interpret_add
:   cmp #OPCODE_SUB
    bne :+
    jmp interpret_sub
:   cmp #OPCODE_EQ
    bne :+
    jmp interpret_eq
:   cmp #OPCODE_NE
    bne :+
    jmp interpret_ne
:   cmp #OPCODE_LT
    bne :+
    jmp interpret_lt
:   cmp #OPCODE_GT
    bne :+
    jmp interpret_gt
:   cmp #OPCODE_BAND
    bne :+
    jmp interpret_band
:   cmp #OPCODE_BOR
    bne :+
    jmp interpret_bor
:   cmp #OPCODE_BXOR
    bne :+
    jmp interpret_bxor
:   cmp #OPCODE_SHL1
    bne :+
    jmp interpret_shl1
:   cmp #OPCODE_SHR1
    bne :+
    jmp interpret_shr1
:   cmp #OPCODE_FADD
    bne :+
    jmp interpret_fadd
:   cmp #OPCODE_FSUB
    bne :+
    jmp interpret_fsub
:   cmp #OPCODE_FMUL
    bne :+
    jmp interpret_fmul
:   cmp #OPCODE_FDIV
    bne :+
    jmp interpret_fdiv
:   cmp #OPCODE_FTOI
    bne :+
    jmp interpret_ftoi
:   cmp #OPCODE_ITOF
    bne :+
    jmp interpret_itof
:   cmp #OPCODE_JZ
    bne :+
    jmp interpret_jz
:   cmp #OPCODE_JMP
    bne :+
    jmp interpret_jmp
:   cmp #OPCODE_DUP
    bne :+
    jmp interpret_dup
:   cmp #OPCODE_DROP
    bne :+
    jmp interpret_drop
:   cmp #OPCODE_SETP16
    bne :+
    jmp interpret_setp16
:   cmp #OPCODE_CALL
    bne :+
    jmp interpret_call
:   cmp #OPCODE_RET
    bne :+
    jmp interpret_ret
:   cmp #OPCODE_CALLN
    bne :+
    jmp interpret_calln
:   jmp interpret_payload_fail

interpret_push8:
    jsr ensure_scan_room_2
    bcc :+
    jmp interpret_payload_fail
:   ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    lda #$00
    sta word_tmp+1
    jsr interp_push_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda #$02
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_push16:
    jsr ensure_scan_room_3
    bcc :+
    jmp interpret_payload_fail
:   ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    jsr interp_push_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_store:
    jsr ensure_scan_room_3
    bcc :+
    jmp interpret_payload_fail
:   ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    jsr interpret_resolve_word_tmp_to_absolute
    bcc :+
    jmp interpret_payload_fail
:   jsr interp_pop_to_svc_retptr
    bcc :+
    jmp interpret_payload_fail
:   ldy #$00
    lda svc_retptr
    sta (word_tmp),y
    iny
    lda svc_retptr+1
    sta (word_tmp),y
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_load:
    jsr ensure_scan_room_3
    bcc :+
    jmp interpret_payload_fail
:   ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    jsr interpret_resolve_word_tmp_to_absolute
    bcc :+
    jmp interpret_payload_fail
:   lda word_tmp
    sta svc_retptr
    lda word_tmp+1
    sta svc_retptr+1
    ldy #$00
    lda (svc_retptr),y
    sta word_tmp
    iny
    lda (svc_retptr),y
    sta word_tmp+1
    jsr interp_push_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_add:
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   jsr interp_pop_to_svc_retptr
    bcc :+
    jmp interpret_payload_fail
:   clc
    lda svc_retptr
    adc word_tmp
    sta word_tmp
    lda svc_retptr+1
    adc word_tmp+1
    sta word_tmp+1
    jsr interp_push_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda #$01
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_sub:
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   jsr interp_pop_to_svc_retptr
    bcc :+
    jmp interpret_payload_fail
:   sec
    lda svc_retptr
    sbc word_tmp
    sta word_tmp
    lda svc_retptr+1
    sbc word_tmp+1
    sta word_tmp+1
    jsr interp_push_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda #$01
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_eq:
    jsr interp_compare_to_bool_eq
    jmp interpret_compare_common

interpret_ne:
    jsr interp_compare_to_bool_ne
    jmp interpret_compare_common

interpret_lt:
    jsr interp_compare_to_bool_lt
    jmp interpret_compare_common

interpret_gt:
    jsr interp_compare_to_bool_gt
interpret_compare_common:
    bcc :+
    jmp interpret_payload_fail
:   jsr interp_push_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda #$01
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_band:
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   jsr interp_pop_to_svc_retptr
    bcc :+
    jmp interpret_payload_fail
:   lda svc_retptr
    and word_tmp
    sta word_tmp
    lda svc_retptr+1
    and word_tmp+1
    sta word_tmp+1
    jmp interpret_bitwise_push_common

interpret_bor:
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   jsr interp_pop_to_svc_retptr
    bcc :+
    jmp interpret_payload_fail
:   lda svc_retptr
    ora word_tmp
    sta word_tmp
    lda svc_retptr+1
    ora word_tmp+1
    sta word_tmp+1
    jmp interpret_bitwise_push_common

interpret_bxor:
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   jsr interp_pop_to_svc_retptr
    bcc :+
    jmp interpret_payload_fail
:   lda svc_retptr
    eor word_tmp
    sta word_tmp
    lda svc_retptr+1
    eor word_tmp+1
    sta word_tmp+1
    jmp interpret_bitwise_push_common

interpret_shl1:
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   asl word_tmp
    rol word_tmp+1
    jmp interpret_bitwise_push_common

interpret_shr1:
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lsr word_tmp+1
    ror word_tmp
interpret_bitwise_push_common:
    jsr interp_push_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda #$01
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_fadd:
    lda #$00
    sta real_flip_rhs_sign
    jsr interpret_real_pop_operands
    bcc :+
    jmp interpret_payload_fail
:   lda #AVMRUN_INTERP_RESUME_AFTER_REAL_PUSH
    sta avmrun_interp_resume_state
    lda #AVMRUN_OVERLAY_CMD_REAL_ADD_SUB
    jmp interpret_request_realops

interpret_fsub:
    lda #$01
    sta real_flip_rhs_sign
    jsr interpret_real_pop_operands
    bcc :+
    jmp interpret_payload_fail
:   lda #AVMRUN_INTERP_RESUME_AFTER_REAL_PUSH
    sta avmrun_interp_resume_state
    lda #AVMRUN_OVERLAY_CMD_REAL_ADD_SUB
    jmp interpret_request_realops

interpret_fmul:
    jsr interpret_real_pop_operands
    bcc :+
    jmp interpret_payload_fail
:   lda #AVMRUN_INTERP_RESUME_AFTER_REAL_PUSH
    sta avmrun_interp_resume_state
    lda #AVMRUN_OVERLAY_CMD_REAL_MUL
    jmp interpret_request_realops

interpret_fdiv:
    jsr interpret_real_pop_operands
    bcc :+
    jmp interpret_payload_fail
:   lda #AVMRUN_INTERP_RESUME_AFTER_REAL_PUSH
    sta avmrun_interp_resume_state
    lda #AVMRUN_OVERLAY_CMD_REAL_DIV
    jmp interpret_request_realops

interpret_ftoi:
    jsr interpret_real_pop_value
    bcc :+
    jmp interpret_payload_fail
:   lda #AVMRUN_INTERP_RESUME_AFTER_FTOI
    sta avmrun_interp_resume_state
    lda #AVMRUN_OVERLAY_CMD_REAL_FTOI
    jmp interpret_request_realops

interpret_itof:
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda #AVMRUN_INTERP_RESUME_AFTER_REAL_PUSH
    sta avmrun_interp_resume_state
    lda #AVMRUN_OVERLAY_CMD_REAL_ITOF
    jmp interpret_request_realops

interpret_real_pop_operands:
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta real_rhs_hi
    lda word_tmp+1
    sta real_rhs_hi+1
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta real_rhs_lo
    lda word_tmp+1
    sta real_rhs_lo+1
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta real_lhs_hi
    lda word_tmp+1
    sta real_lhs_hi+1
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta real_lhs_lo
    lda word_tmp+1
    sta real_lhs_lo+1
    clc
    rts

interpret_real_pop_value:
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta real_lhs_hi
    lda word_tmp+1
    sta real_lhs_hi+1
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta real_lhs_lo
    lda word_tmp+1
    sta real_lhs_lo+1
    clc
    rts

interpret_real_push_result:
    lda real_result_lo
    sta word_tmp
    lda real_result_lo+1
    sta word_tmp+1
    jsr interp_push_word_tmp
    bcc :+
    rts
:   lda real_result_hi
    sta word_tmp
    lda real_result_hi+1
    sta word_tmp+1
    jsr interp_push_word_tmp
    rts

interpret_jz:
    jsr ensure_scan_room_3
    bcc :+
    jmp interpret_payload_fail
:   ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    jsr interp_pop_to_svc_retptr
    bcc :+
    jmp interpret_payload_fail
:   lda svc_retptr
    ora svc_retptr+1
    beq interpret_jz_taken
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop
interpret_jz_taken:
    jsr interpret_resolve_word_tmp_to_absolute
    bcc :+
    jmp interpret_payload_fail
:   lda word_tmp
    sta scan_ptr
    lda word_tmp+1
    sta scan_ptr+1
    jmp interpret_payload_loop

interpret_jmp:
    jsr ensure_scan_room_3
    bcc :+
    jmp interpret_payload_fail
:   ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    jsr interpret_resolve_word_tmp_to_absolute
    bcc :+
    jmp interpret_payload_fail
:   lda word_tmp
    sta scan_ptr
    lda word_tmp+1
    sta scan_ptr+1
    jmp interpret_payload_loop

interpret_dup:
    jsr interp_peek_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   jsr interp_push_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda #$01
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_drop:
    lda interp_sp
    bne :+
    jmp interpret_payload_fail
:
    dec interp_sp
    lda #$01
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_setp16:
    jsr ensure_scan_room_3
    bcc :+
    jmp interpret_payload_fail
:   ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    jsr interpret_resolve_word_tmp_to_absolute
    bcc :+
    jmp interpret_payload_fail
:   lda word_tmp
    sta interp_string_ptr
    lda word_tmp+1
    sta interp_string_ptr+1
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_call:
    jsr ensure_scan_room_3
    bcc :+
    jmp interpret_payload_fail
:   lda interp_rsp
    cmp #INTERP_STACK_MAX
    bcc :+
    jmp interpret_payload_fail
:   ldx interp_rsp
    clc
    lda scan_ptr
    adc #$03
    sta interp_rstack_lo,x
    lda scan_ptr+1
    adc #$00
    sta interp_rstack_hi,x
    inc interp_rsp
    ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    jsr interpret_resolve_word_tmp_to_absolute
    bcc :+
    jmp interpret_payload_fail
:   lda word_tmp
    sta scan_ptr
    lda word_tmp+1
    sta scan_ptr+1
    jmp interpret_payload_loop

interpret_ret:
    lda interp_rsp
    bne :+
    jmp interpret_payload_done
:   dec interp_rsp
    ldx interp_rsp
    lda interp_rstack_lo,x
    sta scan_ptr
    lda interp_rstack_hi,x
    sta scan_ptr+1
    jmp interpret_payload_loop

interpret_calln:
    jsr ensure_scan_room_3
    bcc :+
    jmp interpret_payload_fail
:   ldy #$01
    lda (scan_ptr),y
    sta word_tmp
    iny
    lda (scan_ptr),y
    sta word_tmp+1
    lda word_tmp
    cmp #<INTRINSIC_LINKED_PRINT
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_PRINT
    bne :+
    jmp interpret_calln_linked_print
:   lda word_tmp
    cmp #<INTRINSIC_PRINT
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_PRINT
    bne :+
    jmp interpret_calln_print
:   lda word_tmp
    cmp #<native_print
    bne interpret_calln_check_native_linked_print
    lda word_tmp+1
    cmp #>native_print
    bne interpret_calln_check_native_linked_print
    jmp interpret_calln_print
interpret_calln_check_native_linked_print:
    lda word_tmp
    cmp #<native_linked_print
    bne interpret_calln_check_printe
    lda word_tmp+1
    cmp #>native_linked_print
    bne interpret_calln_check_printe
    jmp interpret_calln_linked_print
interpret_calln_check_printe:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_PRINTE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_PRINTE
    bne :+
    jmp interpret_calln_linked_printe
:   lda word_tmp
    cmp #<INTRINSIC_PRINTE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTE
    bne :+
    jmp interpret_calln_printe
:   lda word_tmp
    cmp #<native_printe
    bne interpret_calln_check_native_linked_printe
    lda word_tmp+1
    cmp #>native_printe
    bne interpret_calln_check_native_linked_printe
    jmp interpret_calln_printe
interpret_calln_check_native_linked_printe:
    lda word_tmp
    cmp #<native_linked_printe
    bne interpret_calln_check_printi
    lda word_tmp+1
    cmp #>native_linked_printe
    bne interpret_calln_check_printi
    jmp interpret_calln_linked_printe
interpret_calln_check_printi:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_PRINTI
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_PRINTI
    bne :+
    jmp interpret_calln_printi
:   lda word_tmp
    cmp #<INTRINSIC_PRINTI
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTI
    bne :+
    jmp interpret_calln_printi
:   lda word_tmp
    cmp #<native_printi
    bne interpret_calln_check_printie
    lda word_tmp+1
    cmp #>native_printi
    bne interpret_calln_check_printie
    jmp interpret_calln_printi
interpret_calln_check_printie:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_PRINTIE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_PRINTIE
    bne :+
    jmp interpret_calln_printie
:   lda word_tmp
    cmp #<INTRINSIC_PRINTIE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTIE
    bne :+
    jmp interpret_calln_printie
:   lda word_tmp
    cmp #<native_printie
    bne interpret_calln_check_printreal
    lda word_tmp+1
    cmp #>native_printie
    bne interpret_calln_check_printreal
    jmp interpret_calln_printie
interpret_calln_check_printreal:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_PRINTREAL
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_PRINTREAL
    bne :+
    jmp interpret_calln_printreal
:   lda word_tmp
    cmp #<INTRINSIC_PRINTREAL
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_PRINTREAL
    bne :+
    jmp interpret_calln_printreal
:   lda word_tmp
    cmp #<native_printreal
    bne interpret_calln_check_math_fabs
    lda word_tmp+1
    cmp #>native_printreal
    bne interpret_calln_check_math_fabs
    jmp interpret_calln_printreal
interpret_calln_check_math_fabs:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_MATH_FABS
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_MATH_FABS
    bne :+
    jmp interpret_calln_math_fabs
:   lda word_tmp
    cmp #<native_math_fabs
    bne interpret_calln_check_math_fsqrt
    lda word_tmp+1
    cmp #>native_math_fabs
    bne interpret_calln_check_math_fsqrt
    jmp interpret_calln_math_fabs
interpret_calln_check_math_fsqrt:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_MATH_FSQRT
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_MATH_FSQRT
    bne :+
    jmp interpret_calln_math_fsqrt
:   lda word_tmp
    cmp #<native_math_fsqrt
    bne interpret_calln_check_dbf_create
    lda word_tmp+1
    cmp #>native_math_fsqrt
    bne interpret_calln_check_dbf_create
    jmp interpret_calln_math_fsqrt
interpret_calln_check_dbf_create:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_CREATE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_DBF_CREATE
    bne :+
    jmp interpret_calln_dbf_create
:   lda word_tmp
    cmp #<native_dbf_create
    bne interpret_calln_check_dbf_currrecno
    lda word_tmp+1
    cmp #>native_dbf_create
    bne interpret_calln_check_dbf_currrecno
    jmp interpret_calln_dbf_create
interpret_calln_check_dbf_currrecno:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_CURRRECNO
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_DBF_CURRRECNO
    bne :+
    jmp interpret_calln_dbf_currrecno
:   lda word_tmp
    cmp #<native_dbf_currrecno
    bne interpret_calln_check_dbf_totalrecs
    lda word_tmp+1
    cmp #>native_dbf_currrecno
    bne interpret_calln_check_dbf_totalrecs
    jmp interpret_calln_dbf_currrecno
interpret_calln_check_dbf_totalrecs:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_TOTALRECS
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_DBF_TOTALRECS
    bne :+
    jmp interpret_calln_dbf_totalrecs
:   lda word_tmp
    cmp #<native_dbf_totalrecs
    bne interpret_calln_check_dbf_close
    lda word_tmp+1
    cmp #>native_dbf_totalrecs
    bne interpret_calln_check_dbf_close
    jmp interpret_calln_dbf_totalrecs
interpret_calln_check_dbf_close:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_CLOSE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_DBF_CLOSE
    bne :+
    jmp interpret_calln_dbf_close
:   lda word_tmp
    cmp #<native_dbf_close
    bne interpret_calln_check_dbf_open
    lda word_tmp+1
    cmp #>native_dbf_close
    bne interpret_calln_check_dbf_open
    jmp interpret_calln_dbf_close
interpret_calln_check_dbf_open:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_OPEN
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_DBF_OPEN
    bne :+
    jmp interpret_calln_dbf_open
:   lda word_tmp
    cmp #<native_dbf_open
    bne interpret_calln_check_dbf_appendblank
    lda word_tmp+1
    cmp #>native_dbf_open
    bne interpret_calln_check_dbf_appendblank
    jmp interpret_calln_dbf_open
interpret_calln_check_dbf_appendblank:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_APPENDBLANK
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_DBF_APPENDBLANK
    bne :+
    jmp interpret_calln_dbf_appendblank
:   lda word_tmp
    cmp #<native_dbf_appendblank
    bne interpret_calln_check_dbf_go
    lda word_tmp+1
    cmp #>native_dbf_appendblank
    bne interpret_calln_check_dbf_go
    jmp interpret_calln_dbf_appendblank
interpret_calln_check_dbf_go:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_GO
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_DBF_GO
    bne :+
    jmp interpret_calln_dbf_go
:   lda word_tmp
    cmp #<native_dbf_go
    bne interpret_calln_check_dbf_readfield
    lda word_tmp+1
    cmp #>native_dbf_go
    bne interpret_calln_check_dbf_readfield
    jmp interpret_calln_dbf_go
interpret_calln_check_dbf_readfield:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_READFIELD
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_DBF_READFIELD
    bne :+
    jmp interpret_calln_dbf_readfield
:   lda word_tmp
    cmp #<native_dbf_readfield
    bne interpret_calln_check_dbf_writefield
    lda word_tmp+1
    cmp #>native_dbf_readfield
    bne interpret_calln_check_dbf_writefield
    jmp interpret_calln_dbf_readfield
interpret_calln_check_dbf_writefield:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_DBF_WRITEFIELD
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_DBF_WRITEFIELD
    bne :+
    jmp interpret_calln_dbf_writefield
:   lda word_tmp
    cmp #<native_dbf_writefield
    bne interpret_calln_check_gfx_bitmap_on
    lda word_tmp+1
    cmp #>native_dbf_writefield
    bne interpret_calln_check_gfx_bitmap_on
    jmp interpret_calln_dbf_writefield
interpret_calln_check_gfx_bitmap_on:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_ON
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_ON
    bne :+
    jmp interpret_calln_gfx_bitmap_on
:   lda word_tmp
    cmp #<native_gfx_bitmap_on
    bne interpret_calln_check_gfx_bitmap_off
    lda word_tmp+1
    cmp #>native_gfx_bitmap_on
    bne interpret_calln_check_gfx_bitmap_off
    jmp interpret_calln_gfx_bitmap_on
interpret_calln_check_gfx_bitmap_off:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_OFF
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_OFF
    bne :+
    jmp interpret_calln_gfx_bitmap_off
:   lda word_tmp
    cmp #<native_gfx_bitmap_off
    bne interpret_calln_check_gfx_mbitmap_on
    lda word_tmp+1
    cmp #>native_gfx_bitmap_off
    bne interpret_calln_check_gfx_mbitmap_on
    jmp interpret_calln_gfx_bitmap_off
interpret_calln_check_gfx_mbitmap_on:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_MBITMAP_ON
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_MBITMAP_ON
    bne :+
    jmp interpret_calln_gfx_mbitmap_on
:   lda word_tmp
    cmp #<native_gfx_mbitmap_on
    bne interpret_calln_check_gfx_bg_color
    lda word_tmp+1
    cmp #>native_gfx_mbitmap_on
    bne interpret_calln_check_gfx_bg_color
    jmp interpret_calln_gfx_mbitmap_on
interpret_calln_check_gfx_bg_color:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BG_COLOR
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BG_COLOR
    bne :+
    jmp interpret_calln_gfx_bg_color
:   lda word_tmp
    cmp #<native_gfx_bg_color
    bne interpret_calln_check_gfx_border_color
    lda word_tmp+1
    cmp #>native_gfx_bg_color
    bne interpret_calln_check_gfx_border_color
    jmp interpret_calln_gfx_bg_color
interpret_calln_check_gfx_border_color:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BORDER_COLOR
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BORDER_COLOR
    bne :+
    jmp interpret_calln_gfx_border_color
:   lda word_tmp
    cmp #<native_gfx_border_color
    bne interpret_calln_check_gfx_vic_bank
    lda word_tmp+1
    cmp #>native_gfx_border_color
    bne interpret_calln_check_gfx_vic_bank
    jmp interpret_calln_gfx_border_color
interpret_calln_check_gfx_vic_bank:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_VIC_BANK
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_VIC_BANK
    bne :+
    jmp interpret_calln_gfx_vic_bank
:   lda word_tmp
    cmp #<native_gfx_vic_bank
    bne interpret_calln_check_gfx_screen_base
    lda word_tmp+1
    cmp #>native_gfx_vic_bank
    bne interpret_calln_check_gfx_screen_base
    jmp interpret_calln_gfx_vic_bank
interpret_calln_check_gfx_screen_base:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_SCREEN_BASE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_SCREEN_BASE
    bne :+
    jmp interpret_calln_gfx_screen_base
:   lda word_tmp
    cmp #<native_gfx_screen_base
    bne interpret_calln_check_gfx_bitmap_base
    lda word_tmp+1
    cmp #>native_gfx_screen_base
    bne interpret_calln_check_gfx_bitmap_base
    jmp interpret_calln_gfx_screen_base
interpret_calln_check_gfx_bitmap_base:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_BASE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_BASE
    bne :+
    jmp interpret_calln_gfx_bitmap_base
:   lda word_tmp
    cmp #<native_gfx_bitmap_base
    bne interpret_calln_check_gfx_bitmap_fill
    lda word_tmp+1
    cmp #>native_gfx_bitmap_base
    bne interpret_calln_check_gfx_bitmap_fill
    jmp interpret_calln_gfx_bitmap_base
interpret_calln_check_gfx_bitmap_fill:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_FILL
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_FILL
    bne :+
    jmp interpret_calln_gfx_bitmap_fill
:   lda word_tmp
    cmp #<native_gfx_bitmap_fill
    bne interpret_calln_check_gfx_screen_cell
    lda word_tmp+1
    cmp #>native_gfx_bitmap_fill
    bne interpret_calln_check_gfx_screen_cell
    jmp interpret_calln_gfx_bitmap_fill
interpret_calln_check_gfx_screen_cell:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_SCREEN_CELL
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_SCREEN_CELL
    bne :+
    jmp interpret_calln_gfx_screen_cell
:   lda word_tmp
    cmp #<native_gfx_screen_cell
    bne interpret_calln_check_gfx_color_cell
    lda word_tmp+1
    cmp #>native_gfx_screen_cell
    bne interpret_calln_check_gfx_color_cell
    jmp interpret_calln_gfx_screen_cell
interpret_calln_check_gfx_color_cell:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_COLOR_CELL
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_COLOR_CELL
    bne :+
    jmp interpret_calln_gfx_color_cell
:   lda word_tmp
    cmp #<native_gfx_color_cell
    bne interpret_calln_check_gfx_bitmap_show
    lda word_tmp+1
    cmp #>native_gfx_color_cell
    bne interpret_calln_check_gfx_bitmap_show
    jmp interpret_calln_gfx_color_cell
interpret_calln_check_gfx_bitmap_show:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_SHOW
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_SHOW
    bne :+
    jmp interpret_calln_gfx_bitmap_show
:   lda word_tmp
    cmp #<native_gfx_bitmap_show
    bne interpret_calln_check_gfx_bitmap_hide
    lda word_tmp+1
    cmp #>native_gfx_bitmap_show
    bne interpret_calln_check_gfx_bitmap_hide
    jmp interpret_calln_gfx_bitmap_show
interpret_calln_check_gfx_bitmap_hide:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_HIDE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_HIDE
    bne :+
    jmp interpret_calln_gfx_bitmap_hide
:   lda word_tmp
    cmp #<native_gfx_bitmap_hide
    bne interpret_calln_check_gfx_bitmap_copy
    lda word_tmp+1
    cmp #>native_gfx_bitmap_hide
    bne interpret_calln_check_gfx_bitmap_copy
    jmp interpret_calln_gfx_bitmap_hide
interpret_calln_check_gfx_bitmap_copy:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_COPY
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_COPY
    bne :+
    jmp interpret_calln_gfx_bitmap_copy
:   lda word_tmp
    cmp #<native_gfx_bitmap_copy
    bne interpret_calln_check_gfx_screen_copy
    lda word_tmp+1
    cmp #>native_gfx_bitmap_copy
    bne interpret_calln_check_gfx_screen_copy
    jmp interpret_calln_gfx_bitmap_copy
interpret_calln_check_gfx_screen_copy:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_SCREEN_COPY
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_SCREEN_COPY
    bne :+
    jmp interpret_calln_gfx_screen_copy
:   lda word_tmp
    cmp #<native_gfx_screen_copy
    bne interpret_calln_check_gfx_color_copy
    lda word_tmp+1
    cmp #>native_gfx_screen_copy
    bne interpret_calln_check_gfx_color_copy
    jmp interpret_calln_gfx_screen_copy
interpret_calln_check_gfx_color_copy:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_COLOR_COPY
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_COLOR_COPY
    bne :+
    jmp interpret_calln_gfx_color_copy
:   lda word_tmp
    cmp #<native_gfx_color_copy
    bne interpret_calln_check_gfx_bitmap_cell_colors
    lda word_tmp+1
    cmp #>native_gfx_color_copy
    bne interpret_calln_check_gfx_bitmap_cell_colors
    jmp interpret_calln_gfx_color_copy
interpret_calln_check_gfx_bitmap_cell_colors:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_CELL_COLORS
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_CELL_COLORS
    bne :+
    jmp interpret_calln_gfx_bitmap_cell_colors
:   lda word_tmp
    cmp #<native_gfx_bitmap_cell_colors
    bne interpret_calln_check_gfx_bitmap_cell_data
    lda word_tmp+1
    cmp #>native_gfx_bitmap_cell_colors
    bne interpret_calln_check_gfx_bitmap_cell_data
    jmp interpret_calln_gfx_bitmap_cell_colors
interpret_calln_check_gfx_bitmap_cell_data:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_CELL_DATA
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_CELL_DATA
    bne :+
    jmp interpret_calln_gfx_bitmap_cell_data
:   lda word_tmp
    cmp #<native_gfx_bitmap_cell_data
    bne interpret_calln_check_gfx_bitmap_blit
    lda word_tmp+1
    cmp #>native_gfx_bitmap_cell_data
    bne interpret_calln_check_gfx_bitmap_blit
    jmp interpret_calln_gfx_bitmap_cell_data
interpret_calln_check_gfx_bitmap_blit:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_BLIT
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_BLIT
    bne :+
    jmp interpret_calln_gfx_bitmap_blit
:   lda word_tmp
    cmp #<native_gfx_bitmap_blit
    bne interpret_calln_check_gfx_tile_draw
    lda word_tmp+1
    cmp #>native_gfx_bitmap_blit
    bne interpret_calln_check_gfx_tile_draw
    jmp interpret_calln_gfx_bitmap_blit
interpret_calln_check_gfx_tile_draw:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILE_DRAW
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_TILE_DRAW
    bne :+
    jmp interpret_calln_gfx_tile_draw
:   lda word_tmp
    cmp #<native_gfx_tile_draw
    bne interpret_calln_check_gfx_tile_rect_fill
    lda word_tmp+1
    cmp #>native_gfx_tile_draw
    bne interpret_calln_check_gfx_tile_rect_fill
    jmp interpret_calln_gfx_tile_draw
interpret_calln_check_gfx_tile_rect_fill:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILE_RECT_FILL
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_TILE_RECT_FILL
    bne :+
    jmp interpret_calln_gfx_tile_rect_fill
:   lda word_tmp
    cmp #<native_gfx_tile_rect_fill
    bne interpret_calln_check_gfx_bitmap_mask_blit
    lda word_tmp+1
    cmp #>native_gfx_tile_rect_fill
    bne interpret_calln_check_gfx_bitmap_mask_blit
    jmp interpret_calln_gfx_tile_rect_fill
interpret_calln_check_gfx_bitmap_mask_blit:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_BITMAP_MASK_BLIT
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_BITMAP_MASK_BLIT
    bne :+
    jmp interpret_calln_gfx_bitmap_mask_blit
:   lda word_tmp
    cmp #<native_gfx_bitmap_mask_blit
    bne interpret_calln_check_gfx_tile_mask_draw
    lda word_tmp+1
    cmp #>native_gfx_bitmap_mask_blit
    bne interpret_calln_check_gfx_tile_mask_draw
    jmp interpret_calln_gfx_bitmap_mask_blit
interpret_calln_check_gfx_tile_mask_draw:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILE_MASK_DRAW
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_TILE_MASK_DRAW
    bne :+
    jmp interpret_calln_gfx_tile_mask_draw
:   lda word_tmp
    cmp #<native_gfx_tile_mask_draw
    bne interpret_calln_check_gfx_tileset_draw
    lda word_tmp+1
    cmp #>native_gfx_tile_mask_draw
    bne interpret_calln_check_gfx_tileset_draw
    jmp interpret_calln_gfx_tile_mask_draw
interpret_calln_check_gfx_tileset_draw:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILESET_DRAW
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_TILESET_DRAW
    bne :+
    jmp interpret_calln_gfx_tileset_draw
:   lda word_tmp
    cmp #<native_gfx_tileset_draw
    bne interpret_calln_check_gfx_tileset_rect_fill
    lda word_tmp+1
    cmp #>native_gfx_tileset_draw
    bne interpret_calln_check_gfx_tileset_rect_fill
    jmp interpret_calln_gfx_tileset_draw
interpret_calln_check_gfx_tileset_rect_fill:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILESET_RECT_FILL
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_TILESET_RECT_FILL
    bne :+
    jmp interpret_calln_gfx_tileset_rect_fill
:   lda word_tmp
    cmp #<native_gfx_tileset_rect_fill
    bne interpret_calln_check_gfx_tileset_mask_draw
    lda word_tmp+1
    cmp #>native_gfx_tileset_rect_fill
    bne interpret_calln_check_gfx_tileset_mask_draw
    jmp interpret_calln_gfx_tileset_rect_fill
interpret_calln_check_gfx_tileset_mask_draw:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILESET_MASK_DRAW
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_TILESET_MASK_DRAW
    bne :+
    jmp interpret_calln_gfx_tileset_mask_draw
:   lda word_tmp
    cmp #<native_gfx_tileset_mask_draw
    bne interpret_calln_check_gfx_tileset_mask_rect_fill
    lda word_tmp+1
    cmp #>native_gfx_tileset_mask_draw
    bne interpret_calln_check_gfx_tileset_mask_rect_fill
    jmp interpret_calln_gfx_tileset_mask_draw
interpret_calln_check_gfx_tileset_mask_rect_fill:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_GFX_TILESET_MASK_RECT_FILL
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_GFX_TILESET_MASK_RECT_FILL
    bne :+
    jmp interpret_calln_gfx_tileset_mask_rect_fill
:   lda word_tmp
    cmp #<native_gfx_tileset_mask_rect_fill
    bne interpret_calln_check_sidspr_sprite_on
    lda word_tmp+1
    cmp #>native_gfx_tileset_mask_rect_fill
    bne interpret_calln_check_sidspr_sprite_on
    jmp interpret_calln_gfx_tileset_mask_rect_fill
interpret_calln_check_sidspr_sprite_on:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SPRITE_ON
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SPRITE_ON
    bne :+
    jmp interpret_calln_sidspr_sprite_on
:   lda word_tmp
    cmp #<native_sidspr_sprite_on
    bne interpret_calln_check_sidspr_sprite_off
    lda word_tmp+1
    cmp #>native_sidspr_sprite_on
    bne interpret_calln_check_sidspr_sprite_off
    jmp interpret_calln_sidspr_sprite_on
interpret_calln_check_sidspr_sprite_off:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SPRITE_OFF
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SPRITE_OFF
    bne :+
    jmp interpret_calln_sidspr_sprite_off
:   lda word_tmp
    cmp #<native_sidspr_sprite_off
    bne interpret_calln_check_sidspr_sprite_pos
    lda word_tmp+1
    cmp #>native_sidspr_sprite_off
    bne interpret_calln_check_sidspr_sprite_pos
    jmp interpret_calln_sidspr_sprite_off
interpret_calln_check_sidspr_sprite_pos:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SPRITE_POS
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SPRITE_POS
    bne :+
    jmp interpret_calln_sidspr_sprite_pos
:   lda word_tmp
    cmp #<native_sidspr_sprite_pos
    bne interpret_calln_check_sidspr_sprite_data
    lda word_tmp+1
    cmp #>native_sidspr_sprite_pos
    bne interpret_calln_check_sidspr_sprite_data
    jmp interpret_calln_sidspr_sprite_pos
interpret_calln_check_sidspr_sprite_data:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SPRITE_DATA
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SPRITE_DATA
    bne :+
    jmp interpret_calln_sidspr_sprite_data
:   lda word_tmp
    cmp #<native_sidspr_sprite_data
    bne interpret_calln_check_sidspr_sprite_color
    lda word_tmp+1
    cmp #>native_sidspr_sprite_data
    bne interpret_calln_check_sidspr_sprite_color
    jmp interpret_calln_sidspr_sprite_data
interpret_calln_check_sidspr_sprite_color:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SPRITE_COLOR
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SPRITE_COLOR
    bne :+
    jmp interpret_calln_sidspr_sprite_color
:   lda word_tmp
    cmp #<native_sidspr_sprite_color
    bne interpret_calln_check_sidspr_sid_freq
    lda word_tmp+1
    cmp #>native_sidspr_sprite_color
    bne interpret_calln_check_sidspr_sid_freq
    jmp interpret_calln_sidspr_sprite_color
interpret_calln_check_sidspr_sid_freq:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_FREQ
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SID_FREQ
    bne :+
    jmp interpret_calln_sidspr_sid_freq
:   lda word_tmp
    cmp #<native_sidspr_sid_freq
    bne interpret_calln_check_sidspr_sid_wave
    lda word_tmp+1
    cmp #>native_sidspr_sid_freq
    bne interpret_calln_check_sidspr_sid_wave
    jmp interpret_calln_sidspr_sid_freq
interpret_calln_check_sidspr_sid_wave:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_WAVE
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SID_WAVE
    bne :+
    jmp interpret_calln_sidspr_sid_wave
:   lda word_tmp
    cmp #<native_sidspr_sid_wave
    bne interpret_calln_check_sidspr_sid_ad
    lda word_tmp+1
    cmp #>native_sidspr_sid_wave
    bne interpret_calln_check_sidspr_sid_ad
    jmp interpret_calln_sidspr_sid_wave
interpret_calln_check_sidspr_sid_ad:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_AD
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SID_AD
    bne :+
    jmp interpret_calln_sidspr_sid_ad
:   lda word_tmp
    cmp #<native_sidspr_sid_ad
    bne interpret_calln_check_sidspr_sid_sr
    lda word_tmp+1
    cmp #>native_sidspr_sid_ad
    bne interpret_calln_check_sidspr_sid_sr
    jmp interpret_calln_sidspr_sid_ad
interpret_calln_check_sidspr_sid_sr:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_SR
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SID_SR
    bne :+
    jmp interpret_calln_sidspr_sid_sr
:   lda word_tmp
    cmp #<native_sidspr_sid_sr
    bne interpret_calln_check_sidspr_sid_on
    lda word_tmp+1
    cmp #>native_sidspr_sid_sr
    bne interpret_calln_check_sidspr_sid_on
    jmp interpret_calln_sidspr_sid_sr
interpret_calln_check_sidspr_sid_on:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_ON
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SID_ON
    bne :+
    jmp interpret_calln_sidspr_sid_on
:   lda word_tmp
    cmp #<native_sidspr_sid_on
    bne interpret_calln_check_sidspr_sid_off
    lda word_tmp+1
    cmp #>native_sidspr_sid_on
    bne interpret_calln_check_sidspr_sid_off
    jmp interpret_calln_sidspr_sid_on
interpret_calln_check_sidspr_sid_off:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_OFF
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SID_OFF
    bne :+
    jmp interpret_calln_sidspr_sid_off
:   lda word_tmp
    cmp #<native_sidspr_sid_off
    bne interpret_calln_check_sidspr_sid_vol
    lda word_tmp+1
    cmp #>native_sidspr_sid_off
    bne interpret_calln_check_sidspr_sid_vol
    jmp interpret_calln_sidspr_sid_off
interpret_calln_check_sidspr_sid_vol:
    lda word_tmp
    cmp #<INTRINSIC_LINKED_SIDSPR_SID_VOL
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_LINKED_SIDSPR_SID_VOL
    bne :+
    jmp interpret_calln_sidspr_sid_vol
:   lda word_tmp
    cmp #<native_sidspr_sid_vol
    bne interpret_calln_check_exit
    lda word_tmp+1
    cmp #>native_sidspr_sid_vol
    bne interpret_calln_check_exit
    jmp interpret_calln_sidspr_sid_vol
interpret_calln_check_exit:
    lda word_tmp
    cmp #<INTRINSIC_EXIT
    bne :+
    lda word_tmp+1
    cmp #>INTRINSIC_EXIT
    bne :+
    jmp interpret_calln_exit
:   lda word_tmp
    cmp #<native_exit
    beq :+
    jmp interpret_payload_fail
:   lda word_tmp+1
    cmp #>native_exit
    beq interpret_calln_exit
    jmp interpret_payload_fail
interpret_calln_exit:
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_done

interpret_calln_print:
    jsr interpret_prepare_print_string_arg
    jsr native_print
    jmp interpret_finish_calln_advance3

interpret_calln_linked_print:
    jsr interpret_prepare_print_string_arg
    jsr native_linked_print
    jmp interpret_finish_calln_advance3

interpret_calln_printe:
    jsr interpret_prepare_print_string_arg
    jsr native_printe
    jmp interpret_finish_calln_advance3

interpret_calln_linked_printe:
    jsr interpret_prepare_print_string_arg
    jsr native_linked_printe
    jmp interpret_finish_calln_advance3

interpret_calln_printi:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_printi
    jmp interpret_finish_calln_advance3

interpret_calln_printie:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_printie
    jmp interpret_finish_calln_advance3

interpret_calln_printreal:
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda word_tmp
    sta real_print_flag
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda word_tmp
    sta real_print_high
    lda word_tmp+1
    sta real_print_high+1
    jsr interp_pop_to_word_tmp
    bcc :+
    jmp interpret_payload_fail
:   lda word_tmp
    sta real_print_low
    lda word_tmp+1
    sta real_print_low+1
    lda #AVMRUN_INTERP_RESUME_AFTER_ADVANCE3
    sta avmrun_interp_resume_state
    lda #AVMRUN_OVERLAY_CMD_PRINT_REAL
    jmp interpret_request_print

interpret_calln_math_fabs:
    jsr interpret_real_pop_value
    bcc :+
    jmp interpret_payload_fail
:   lda real_lhs_hi
    sta file_params+0
    lda real_lhs_hi+1
    sta file_params+1
    lda real_lhs_lo
    sta file_params+2
    lda real_lhs_lo+1
    sta file_params+3
    lda #<file_params
    sta pptr
    lda #>file_params
    sta pptr+1
    jsr native_math_fabs
    lda file_params+2
    sta real_result_lo
    lda file_params+3
    sta real_result_lo+1
    lda file_params+0
    sta real_result_hi
    lda file_params+1
    sta real_result_hi+1
    jsr interpret_real_push_result
    bcs :+
    jmp interpret_finish_calln_advance3
:   jmp interpret_payload_fail

interpret_calln_math_fsqrt:
    jsr interpret_real_pop_value
    bcc :+
    jmp interpret_payload_fail
:   lda real_lhs_hi
    sta file_params+0
    lda real_lhs_hi+1
    sta file_params+1
    lda real_lhs_lo
    sta file_params+2
    lda real_lhs_lo+1
    sta file_params+3
    lda #<file_params
    sta pptr
    lda #>file_params
    sta pptr+1
    jsr compat_math_fsqrt_file_params
    lda file_params+2
    sta real_result_lo
    lda file_params+3
    sta real_result_lo+1
    lda file_params+0
    sta real_result_hi
    lda file_params+1
    sta real_result_hi+1
    jsr interpret_real_push_result
    bcs :+
    jmp interpret_finish_calln_advance3
:   jmp interpret_payload_fail

compat_math_fsqrt_file_params:
    php
    cld
    lda file_params+0
    sta math_fsqrt_raw_hi
    ora file_params+1
    ora file_params+2
    ora file_params+3
    bne :+
    jmp compat_math_fsqrt_return_zero
:   lda file_params+1
    bpl :+
    jmp compat_math_fsqrt_return_zero
:   and #$7F
    asl a
    sta math_fsqrt_exp
    lda math_fsqrt_raw_hi
    and #$80
    beq :+
    inc math_fsqrt_exp
:   lda math_fsqrt_exp
    clc
    adc #127
    ror a
    sta math_fsqrt_res_exp
    lda math_fsqrt_exp
    and #$01
    beq compat_math_fsqrt_even_lookup
    lda #23
compat_math_fsqrt_store_shift:
    sta math_fsqrt_count
    jmp compat_math_fsqrt_prepare_radicand

compat_math_fsqrt_even_lookup:
    lda math_fsqrt_raw_hi
    and #$7F
    tay
    lda compat_math_fsqrt_even_hi_table,y
    sta file_params+0
    lda math_fsqrt_res_exp
    and #$01
    beq compat_math_fsqrt_even_store_exp
    lda file_params+0
    ora #$80
    sta file_params+0
compat_math_fsqrt_even_store_exp:
    lda math_fsqrt_res_exp
    lsr a
    sta file_params+1
    lda #$00
    sta file_params+2
    sta file_params+3
    plp
    rts

compat_math_fsqrt_prepare_radicand:
    lda file_params+2
    sta math_fsqrt_rad0
    lda file_params+3
    sta math_fsqrt_rad1
    lda math_fsqrt_raw_hi
    and #$7F
    ora #$80
    sta math_fsqrt_rad2
    lda #$00
    sta math_fsqrt_rad3
    sta math_fsqrt_rad4
    sta math_fsqrt_rad5
    sta math_fsqrt_root0
    sta math_fsqrt_root1
    sta math_fsqrt_root2
    sta math_fsqrt_rem0
    sta math_fsqrt_rem1
    sta math_fsqrt_rem2
    sta math_fsqrt_rem3

compat_math_fsqrt_shift_radicand_loop:
    lda math_fsqrt_count
    beq compat_math_fsqrt_shift_radicand_done
    asl math_fsqrt_rad0
    rol math_fsqrt_rad1
    rol math_fsqrt_rad2
    rol math_fsqrt_rad3
    rol math_fsqrt_rad4
    rol math_fsqrt_rad5
    dec math_fsqrt_count
    jmp compat_math_fsqrt_shift_radicand_loop
compat_math_fsqrt_shift_radicand_done:

    lda #24
    sta math_fsqrt_count
compat_math_fsqrt_loop:
    jsr compat_math_fsqrt_shift_rad_bit_into_rem
    jsr compat_math_fsqrt_shift_rad_bit_into_rem
    jsr compat_math_fsqrt_build_trial
    jsr compat_math_fsqrt_compare_rem_trial
    bcc compat_math_fsqrt_root_shift_only
    jsr compat_math_fsqrt_subtract_trial_from_rem
    asl math_fsqrt_root0
    rol math_fsqrt_root1
    rol math_fsqrt_root2
    lda math_fsqrt_root0
    ora #$01
    sta math_fsqrt_root0
    jmp compat_math_fsqrt_next
compat_math_fsqrt_root_shift_only:
    asl math_fsqrt_root0
    rol math_fsqrt_root1
    rol math_fsqrt_root2
compat_math_fsqrt_next:
    dec math_fsqrt_count
    bne compat_math_fsqrt_loop

    lda math_fsqrt_root0
    ora math_fsqrt_root1
    ora math_fsqrt_root2
    bne compat_math_fsqrt_pack_result
    jmp compat_math_fsqrt_return_zero

compat_math_fsqrt_pack_result:
    lda math_fsqrt_root0
    sta file_params+2
    lda math_fsqrt_root1
    sta file_params+3
    lda math_fsqrt_root2
    and #$7F
    ldy math_fsqrt_res_exp
    tya
    and #$01
    beq :+
    lda math_fsqrt_root2
    and #$7F
    ora #$80
:   sta file_params+0
    lda math_fsqrt_res_exp
    lsr a
    sta file_params+1
    plp
    rts

compat_math_fsqrt_return_zero:
    lda #$00
    sta file_params+0
    sta file_params+1
    sta file_params+2
    sta file_params+3
    plp
    rts

compat_math_fsqrt_shift_rad_bit_into_rem:
    asl math_fsqrt_rad0
    rol math_fsqrt_rad1
    rol math_fsqrt_rad2
    rol math_fsqrt_rad3
    rol math_fsqrt_rad4
    rol math_fsqrt_rad5
    rol math_fsqrt_rem0
    rol math_fsqrt_rem1
    rol math_fsqrt_rem2
    rol math_fsqrt_rem3
    rts

compat_math_fsqrt_build_trial:
    lda math_fsqrt_root0
    asl a
    sta math_fsqrt_trial0
    lda math_fsqrt_root1
    rol a
    sta math_fsqrt_trial1
    lda math_fsqrt_root2
    rol a
    sta math_fsqrt_trial2
    lda #$00
    rol a
    sta math_fsqrt_trial3
    asl math_fsqrt_trial0
    rol math_fsqrt_trial1
    rol math_fsqrt_trial2
    rol math_fsqrt_trial3
    inc math_fsqrt_trial0
    bne :+
    inc math_fsqrt_trial1
    bne :+
    inc math_fsqrt_trial2
    bne :+
    inc math_fsqrt_trial3
:   rts

compat_math_fsqrt_compare_rem_trial:
    lda math_fsqrt_rem3
    cmp math_fsqrt_trial3
    bne :+
    lda math_fsqrt_rem2
    cmp math_fsqrt_trial2
    bne :+
    lda math_fsqrt_rem1
    cmp math_fsqrt_trial1
    bne :+
    lda math_fsqrt_rem0
    cmp math_fsqrt_trial0
:   rts

compat_math_fsqrt_subtract_trial_from_rem:
    sec
    lda math_fsqrt_rem0
    sbc math_fsqrt_trial0
    sta math_fsqrt_rem0
    lda math_fsqrt_rem1
    sbc math_fsqrt_trial1
    sta math_fsqrt_rem1
    lda math_fsqrt_rem2
    sbc math_fsqrt_trial2
    sta math_fsqrt_rem2
    lda math_fsqrt_rem3
    sbc math_fsqrt_trial3
    sta math_fsqrt_rem3
    rts

compat_math_fsqrt_even_hi_table:
    .byte $35, $36, $36, $37, $38, $39, $39, $3A, $3B, $3B, $3C, $3D, $3D, $3E, $3F, $3F
    .byte $40, $41, $41, $42, $43, $43, $44, $45, $45, $46, $47, $47, $48, $48, $49, $4A
    .byte $4A, $4B, $4C, $4C, $4D, $4E, $4E, $4F, $4F, $50, $51, $51, $52, $52, $53, $54
    .byte $54, $55, $55, $56, $57, $57, $58, $58, $59, $5A, $5A, $5B, $5B, $5C, $5D, $5D
    .byte $5E, $5E, $5F, $5F, $60, $61, $61, $62, $62, $63, $63, $64, $65, $65, $66, $66
    .byte $67, $67, $68, $68, $69, $6A, $6A, $6B, $6B, $6C, $6C, $6D, $6D, $6E, $6E, $6F
    .byte $6F, $70, $71, $71, $72, $72, $73, $73, $74, $74, $75, $75, $76, $76, $77, $77
    .byte $78, $78, $79, $79, $7A, $7A, $7B, $7B, $7C, $7C, $7D, $7D, $7E, $7E, $7F, $7F

interpret_calln_dbf_create:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_dbf_create
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_dbf_currrecno:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_dbf_currrecno
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_dbf_totalrecs:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_dbf_totalrecs
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_dbf_close:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_dbf_close
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_dbf_open:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_dbf_open
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_dbf_appendblank:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_dbf_appendblank
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_dbf_go:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_dbf_go
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_dbf_readfield:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_dbf_readfield
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_dbf_writefield:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_dbf_writefield
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sprite_on:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sprite_on
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sprite_off:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sprite_off
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sprite_pos:
    jsr interpret_prepare_sidspr_arg2
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sprite_pos
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sprite_data:
    jsr interpret_prepare_sidspr_arg2
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sprite_data
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sprite_color:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sprite_color
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sid_freq:
    jsr interpret_prepare_sidspr_arg2
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sid_freq
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sid_wave:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sid_wave
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sid_ad:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sid_ad
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sid_sr:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sid_sr
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sid_on:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sid_on
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sid_off:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sid_off
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_sidspr_sid_vol:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_sidspr_sid_vol
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_on:
    jsr native_gfx_bitmap_on
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_off:
    jsr native_gfx_bitmap_off
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_mbitmap_on:
    jsr native_gfx_mbitmap_on
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bg_color:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_bg_color
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_border_color:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_border_color
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_vic_bank:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_vic_bank
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_screen_base:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_screen_base
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_base:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_bitmap_base
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_fill:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_bitmap_fill
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_screen_cell:
    jsr interpret_prepare_sidspr_arg2
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_screen_cell
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_color_cell:
    jsr interpret_prepare_sidspr_arg2
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_color_cell
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_show:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_bitmap_show
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_hide:
    jsr native_gfx_bitmap_hide
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_copy:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_bitmap_copy
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_screen_copy:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_screen_copy
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_color_copy:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_color_copy
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_cell_colors:
    jsr interpret_prepare_sidspr_arg2
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_bitmap_cell_colors
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_cell_data:
    jsr interpret_prepare_sidspr_arg2
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_bitmap_cell_data
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_blit:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_bitmap_blit
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_tile_draw:
    jsr interpret_prepare_sidspr_arg2
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_tile_draw
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_tile_rect_fill:
    jsr interpret_prepare_sidspr_arg3
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_tile_rect_fill
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_bitmap_mask_blit:
    jsr interpret_prepare_sidspr_arg
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_bitmap_mask_blit
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_tile_mask_draw:
    jsr interpret_prepare_sidspr_arg2
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_tile_mask_draw
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_tileset_draw:
    jsr interpret_prepare_sidspr_arg3
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_tileset_draw
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_tileset_rect_fill:
    jsr interpret_prepare_sidspr_arg4
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_tileset_rect_fill
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_tileset_mask_draw:
    jsr interpret_prepare_sidspr_arg3
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_tileset_mask_draw
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_calln_gfx_tileset_mask_rect_fill:
    jsr interpret_prepare_sidspr_arg4
    bcc :+
    jmp interpret_payload_fail
:   jsr native_gfx_tileset_mask_rect_fill
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_request_print:
    sta avmrun_interp_service_cmd
    lda #AVMRUN_OVERLAY_KIND_PRINT
    sta avmrun_interp_service_kind
    lda #AVMRUN_INTERP_RESULT_SERVICE
    sta avmrun_interp_result
    clc
    rts

interpret_request_realops:
    sta avmrun_interp_service_cmd
    lda #AVMRUN_OVERLAY_KIND_REALOPS
    sta avmrun_interp_service_kind
    lda #AVMRUN_INTERP_RESULT_SERVICE
    sta avmrun_interp_result
    clc
    rts

interpret_prepare_sidspr_arg:
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta file_params+0
    lda word_tmp+1
    sta file_params+1
    jmp interpret_prepare_file_params_ptr

interpret_prepare_print_string_arg:
    lda interp_string_ptr
    sta file_params+0
    lda interp_string_ptr+1
    sta file_params+1
interpret_prepare_file_params_ptr:
    lda #<file_params
    sta pptr
    lda #>file_params
    sta pptr+1
    clc
    rts

interpret_finish_calln_advance3:
    lda #$03
    jsr advance_scan_ptr
    jmp interpret_payload_loop

interpret_prepare_sidspr_arg2:
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta file_params+0
    lda word_tmp+1
    sta file_params+1
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta file_params+2
    lda word_tmp+1
    sta file_params+3
    jmp interpret_prepare_file_params_ptr

interpret_prepare_sidspr_arg3:
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta file_params+0
    lda word_tmp+1
    sta file_params+1
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta file_params+2
    lda word_tmp+1
    sta file_params+3
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta file_params+4
    lda word_tmp+1
    sta file_params+5
    jmp interpret_prepare_file_params_ptr

interpret_prepare_sidspr_arg4:
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta file_params+0
    lda word_tmp+1
    sta file_params+1
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta file_params+2
    lda word_tmp+1
    sta file_params+3
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta file_params+4
    lda word_tmp+1
    sta file_params+5
    jsr interp_pop_to_word_tmp
    bcc :+
    rts
:   lda word_tmp
    sta file_params+6
    lda word_tmp+1
    sta file_params+7
    jmp interpret_prepare_file_params_ptr

interpret_payload_done:
    lda #$B1
    sta RESIDENT_LAUNCH_TRACE_STAGE
    lda #AVMRUN_INTERP_RESULT_DONE_OK
    sta avmrun_interp_result
    clc
    rts

interpret_payload_fail:
    lda #AVMRUN_INTERP_RESULT_DONE_FAIL
    sta avmrun_interp_result
    sec
    rts

interp_push_word_tmp:
    ldx interp_sp
    cpx #INTERP_STACK_MAX
    bcc :+
    sec
    rts
:   lda word_tmp
    sta interp_stack_lo,x
    lda word_tmp+1
    sta interp_stack_hi,x
    inc interp_sp
    clc
    rts

interp_pop_to_word_tmp:
    lda interp_sp
    beq interp_pop_fail
    dec interp_sp
    ldx interp_sp
    lda interp_stack_lo,x
    sta word_tmp
    lda interp_stack_hi,x
    sta word_tmp+1
    clc
    rts

interp_pop_to_svc_retptr:
    lda interp_sp
    beq interp_pop_fail
    dec interp_sp
    ldx interp_sp
    lda interp_stack_lo,x
    sta svc_retptr
    lda interp_stack_hi,x
    sta svc_retptr+1
    clc
    rts

interp_peek_to_word_tmp:
    lda interp_sp
    beq interp_pop_fail
    sec
    sbc #$01
    tax
    lda interp_stack_lo,x
    sta word_tmp
    lda interp_stack_hi,x
    sta word_tmp+1
    clc
    rts

interp_pop_fail:
    sec
    rts

interp_compare_to_bool_eq:
    jsr interp_pop_to_word_tmp
    bcc :+
    sec
    rts
:   jsr interp_pop_to_svc_retptr
    bcc :+
    sec
    rts
:   lda svc_retptr
    cmp word_tmp
    bne interp_compare_false
    lda svc_retptr+1
    cmp word_tmp+1
    bne interp_compare_false
    jmp interp_compare_true

interp_compare_to_bool_ne:
    jsr interp_pop_to_word_tmp
    bcc :+
    sec
    rts
:   jsr interp_pop_to_svc_retptr
    bcc :+
    sec
    rts
:   lda svc_retptr
    cmp word_tmp
    bne interp_compare_true
    lda svc_retptr+1
    cmp word_tmp+1
    bne interp_compare_true
    jmp interp_compare_false

interp_compare_to_bool_lt:
    jsr interp_pop_to_word_tmp
    bcc :+
    sec
    rts
:   jsr interp_pop_to_svc_retptr
    bcc :+
    sec
    rts
:   lda svc_retptr+1
    cmp word_tmp+1
    bcc interp_compare_true
    bne interp_compare_false
    lda svc_retptr
    cmp word_tmp
    bcc interp_compare_true
    jmp interp_compare_false

interp_compare_to_bool_gt:
    jsr interp_pop_to_word_tmp
    bcc :+
    sec
    rts
:   jsr interp_pop_to_svc_retptr
    bcc :+
    sec
    rts
:   lda svc_retptr+1
    cmp word_tmp+1
    bcc interp_compare_false
    bne interp_compare_true
    lda svc_retptr
    cmp word_tmp
    bcc interp_compare_false
    beq interp_compare_false
    jmp interp_compare_true

interp_compare_true:
    lda #$01
    sta word_tmp
    lda #$00
    sta word_tmp+1
    clc
    rts

interp_compare_false:
    lda #$00
    sta word_tmp
    sta word_tmp+1
    clc
    rts

interpret_resolve_word_tmp_to_absolute:
    lda word_tmp+1
    cmp payload_ptr+1
    bcc interpret_resolve_relative
    bne interpret_resolve_absolute
    lda word_tmp
    cmp payload_ptr
    bcc interpret_resolve_relative
    bcs interpret_resolve_absolute
interpret_resolve_relative:
    clc
    lda word_tmp
    adc payload_ptr
    sta word_tmp
    lda word_tmp+1
    adc payload_ptr+1
    sta word_tmp+1
interpret_resolve_absolute:
    clc
    rts

avmrun_overlay_end:
