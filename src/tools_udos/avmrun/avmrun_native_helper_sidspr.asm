.include "avmrun_native_helper_abi.inc"
.export avmrun_native_helper_sidspr_header
.export avmrun_native_helper_sidspr_end

.segment "CODE"

sidspr_mask = $fb

avmrun_native_helper_sidspr_header:
    .byte AVMRUN_NATIVE_HELPER_MAGIC_0
    .byte AVMRUN_NATIVE_HELPER_MAGIC_1
    .byte AVMRUN_NATIVE_HELPER_MAGIC_2
    .byte AVMRUN_NATIVE_HELPER_MAGIC_3
    .byte AVMRUN_NATIVE_HELPER_ABI_VERSION
    .byte AVMRUN_NATIVE_HELPER_KIND_SIDSPR
    .word avmrun_native_helper_sidspr_entry_table - avmrun_native_helper_sidspr_header
    .word avmrun_native_helper_sidspr_end - avmrun_native_helper_sidspr_header
    .byte 12
    .byte 0

avmrun_native_helper_sidspr_entry_table:
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SPRITE_ON
    .word avmrun_native_helper_sidspr_sprite_on - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SPRITE_OFF
    .word avmrun_native_helper_sidspr_sprite_off - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SPRITE_POS
    .word avmrun_native_helper_sidspr_sprite_pos - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SPRITE_DATA
    .word avmrun_native_helper_sidspr_sprite_data - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SPRITE_COLOR
    .word avmrun_native_helper_sidspr_sprite_color - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_FREQ
    .word avmrun_native_helper_sidspr_sid_freq - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_WAVE
    .word avmrun_native_helper_sidspr_sid_wave - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_AD
    .word avmrun_native_helper_sidspr_sid_ad - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_SR
    .word avmrun_native_helper_sidspr_sid_sr - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_ON
    .word avmrun_native_helper_sidspr_sid_on - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_OFF
    .word avmrun_native_helper_sidspr_sid_off - avmrun_native_helper_sidspr_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_SIDSPR_SID_VOL
    .word avmrun_native_helper_sidspr_sid_vol - avmrun_native_helper_sidspr_header

avmrun_native_helper_sidspr_sprite_on:
    lda 0,x
    and #$07
    tay
    lda #$01
@mask_loop:
    cpy #$00
    beq @mask_done
    asl a
    dey
    bne @mask_loop
@mask_done:
    ora $D015
    sta $D015
    rts
avmrun_native_helper_sidspr_sprite_off:
    lda 0,x
    and #$07
    tay
    lda #$01
@mask_loop:
    cpy #$00
    beq @mask_done
    asl a
    dey
    bne @mask_loop
@mask_done:
    eor #$FF
    and $D015
    sta $D015
    rts
avmrun_native_helper_sidspr_sprite_pos:
    lda 1,x
    and #$07
    pha
    asl a
    tay
    lda 2,x
    sta $D000,y
    iny
    lda 0,x
    sta $D000,y
    pla
    and #$07
    tay
    lda #$01
@mask_loop:
    cpy #$00
    beq @mask_done
    asl a
    dey
    bne @mask_loop
@mask_done:
    sta sidspr_mask
    lda 3,x
    and #$01
    beq :+
    lda sidspr_mask
    ora $D010
    sta $D010
    rts
:   lda sidspr_mask
    eor #$FF
    and $D010
    sta $D010
    rts
avmrun_native_helper_sidspr_sprite_data:
    lda 3,x
    asl a
    asl a
    sta sidspr_mask
    lda 2,x
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    ora sidspr_mask
    sta sidspr_mask
    lda 0,x
    and #$07
    tay
    lda sidspr_mask
    sta $07F8,y
    rts
avmrun_native_helper_sidspr_sprite_color:
    lda 1,x
    and #$07
    tay
    lda 0,x
    and #$0F
    sta $D027,y
    rts
avmrun_native_helper_sidspr_sid_freq:
    lda 0,x
    and #$03
    sta sidspr_mask
    asl a
    asl a
    clc
    adc sidspr_mask
    adc sidspr_mask
    adc sidspr_mask
    sta sidspr_mask
    lda #$D4
    sta sidspr_mask+1
    ldy #$00
    lda 2,x
    sta (sidspr_mask),y
    iny
    lda 3,x
    sta (sidspr_mask),y
    rts
avmrun_native_helper_sidspr_sid_wave:
    lda 1,x
    and #$03
    sta sidspr_mask
    asl a
    asl a
    clc
    adc sidspr_mask
    adc sidspr_mask
    adc sidspr_mask
    clc
    adc #$04
    sta sidspr_mask
    lda #$D4
    sta sidspr_mask+1
    ldy #$00
    lda 0,x
    sta (sidspr_mask),y
    rts
avmrun_native_helper_sidspr_sid_ad:
    lda 1,x
    and #$03
    sta sidspr_mask
    asl a
    asl a
    clc
    adc sidspr_mask
    adc sidspr_mask
    adc sidspr_mask
    clc
    adc #$05
    sta sidspr_mask
    lda #$D4
    sta sidspr_mask+1
    ldy #$00
    lda 0,x
    sta (sidspr_mask),y
    rts
avmrun_native_helper_sidspr_sid_sr:
    lda 1,x
    and #$03
    sta sidspr_mask
    asl a
    asl a
    clc
    adc sidspr_mask
    adc sidspr_mask
    adc sidspr_mask
    clc
    adc #$06
    sta sidspr_mask
    lda #$D4
    sta sidspr_mask+1
    ldy #$00
    lda 0,x
    sta (sidspr_mask),y
    rts
avmrun_native_helper_sidspr_sid_on:
    lda 0,x
    and #$03
    sta sidspr_mask
    asl a
    asl a
    clc
    adc sidspr_mask
    adc sidspr_mask
    adc sidspr_mask
    clc
    adc #$04
    sta sidspr_mask
    lda #$D4
    sta sidspr_mask+1
    ldy #$00
    lda (sidspr_mask),y
    ora #$01
    sta (sidspr_mask),y
    rts
avmrun_native_helper_sidspr_sid_off:
    lda 0,x
    and #$03
    sta sidspr_mask
    asl a
    asl a
    clc
    adc sidspr_mask
    adc sidspr_mask
    adc sidspr_mask
    clc
    adc #$04
    sta sidspr_mask
    lda #$D4
    sta sidspr_mask+1
    ldy #$00
    lda (sidspr_mask),y
    and #$FE
    sta (sidspr_mask),y
    rts
avmrun_native_helper_sidspr_sid_vol:
    lda 0,x
    and #$0F
    sta sidspr_mask
    lda $D418
    and #$F0
    ora sidspr_mask
    sta $D418
    rts

avmrun_native_helper_sidspr_end:
