.include "avmrun_native_helper_abi.inc"
.export avmrun_native_helper_gfx_header
.export avmrun_native_helper_gfx_end

.segment "CODE"

gfx_gap = $f7
gfx_gap_hi = $f8
gfx_src = $f9
gfx_ptr = $fb
gfx_value = $fd
gfx_flags = $fe
gfx_width = $ff

GFX_FLAG_MULTICOLOR = $01
GFX_FLAG_BITMAP_DATA = $02
GFX_FLAG_SCREEN_DATA = $04
GFX_FLAG_COLOR_DATA = $08
GFX_FLAG_COPY_ONLY = $80

avmrun_native_helper_gfx_header:
    .byte AVMRUN_NATIVE_HELPER_MAGIC_0
    .byte AVMRUN_NATIVE_HELPER_MAGIC_1
    .byte AVMRUN_NATIVE_HELPER_MAGIC_2
    .byte AVMRUN_NATIVE_HELPER_MAGIC_3
    .byte AVMRUN_NATIVE_HELPER_ABI_VERSION
    .byte AVMRUN_NATIVE_HELPER_KIND_GFX
    .word avmrun_native_helper_gfx_entry_table - avmrun_native_helper_gfx_header
    .word avmrun_native_helper_gfx_end - avmrun_native_helper_gfx_header
    .byte 23
    .byte 0

avmrun_native_helper_gfx_entry_table:
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_ON
    .word avmrun_native_helper_gfx_bitmap_on - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_OFF
    .word avmrun_native_helper_gfx_bitmap_off - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_MBITMAP_ON
    .word avmrun_native_helper_gfx_mbitmap_on - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BG_COLOR
    .word avmrun_native_helper_gfx_bg_color - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BORDER_COLOR
    .word avmrun_native_helper_gfx_border_color - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_VIC_BANK
    .word avmrun_native_helper_gfx_vic_bank - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_SCREEN_BASE
    .word avmrun_native_helper_gfx_screen_base - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_BASE
    .word avmrun_native_helper_gfx_bitmap_base - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_FILL
    .word avmrun_native_helper_gfx_bitmap_fill - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_SCREEN_CELL
    .word avmrun_native_helper_gfx_screen_cell - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_COLOR_CELL
    .word avmrun_native_helper_gfx_color_cell - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_SHOW
    .word avmrun_native_helper_gfx_bitmap_show - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_HIDE
    .word avmrun_native_helper_gfx_bitmap_off - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_COPY
    .word avmrun_native_helper_gfx_bitmap_copy - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_SCREEN_COPY
    .word avmrun_native_helper_gfx_screen_copy - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_COLOR_COPY
    .word avmrun_native_helper_gfx_color_copy - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_CELL_COLORS
    .word avmrun_native_helper_gfx_bitmap_cell_colors - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_CELL_DATA
    .word avmrun_native_helper_gfx_bitmap_cell_data - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_BLIT
    .word avmrun_native_helper_gfx_bitmap_blit - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_TILE_DRAW
    .word avmrun_native_helper_gfx_tile_draw - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_TILE_RECT_FILL
    .word avmrun_native_helper_gfx_tile_rect_fill - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_BITMAP_MASK_BLIT
    .word avmrun_native_helper_gfx_bitmap_mask_blit - avmrun_native_helper_gfx_header
    .byte AVMRUN_NATIVE_HELPER_ENTRY_GFX_TILE_MASK_DRAW
    .word avmrun_native_helper_gfx_tile_mask_draw - avmrun_native_helper_gfx_header

avmrun_native_helper_gfx_bitmap_on:
    lda #$00
    beq avmrun_native_helper_gfx_bitmap_mode_common

avmrun_native_helper_gfx_mbitmap_on:
    lda #$10
avmrun_native_helper_gfx_bitmap_mode_common:
    sta gfx_value
    lda $D011
    ora #$20
    sta $D011
    lda $D016
    and #$EF
    ora gfx_value
    sta $D016
    rts

avmrun_native_helper_gfx_bitmap_off:
    lda $D011
    and #$DF
    sta $D011
    lda $D016
    and #$EF
    sta $D016
    rts

avmrun_native_helper_gfx_bg_color:
    lda 0,x
    and #$0F
    sta gfx_value
    lda $D021
    and #$F0
    ora gfx_value
    sta $D021
    rts

avmrun_native_helper_gfx_border_color:
    lda 0,x
    and #$0F
    sta gfx_value
    lda $D020
    and #$F0
    ora gfx_value
    sta $D020
    rts

avmrun_native_helper_gfx_vic_bank:
    lda 0,x
    and #$03
    eor #$03
    sta gfx_value
    lda $DD00
    and #$FC
    ora gfx_value
    sta $DD00
    rts

avmrun_native_helper_gfx_screen_base:
    lda 0,x
    and #$0F
    asl a
    asl a
    asl a
    asl a
    sta gfx_value
    lda $D018
    and #$0F
    ora gfx_value
    sta $D018
    rts

avmrun_native_helper_gfx_bitmap_base:
    lda $D018
    and #$F7
    sta gfx_value
    lda 0,x
    and #$01
    beq :+
    lda gfx_value
    ora #$08
    sta $D018
    rts
:   lda gfx_value
    sta $D018
    rts

avmrun_native_helper_gfx_bitmap_fill:
    sei
    lda 0,x
    sta gfx_value
    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    lda $D018
    and #$08
    beq :+
    clc
    lda gfx_ptr+1
    adc #$20
    sta gfx_ptr+1
:   ldx #$1F
    ldy #$00
@page_loop:
    lda gfx_value
@byte_loop:
    sta (gfx_ptr),y
    iny
    bne @byte_loop
    inc gfx_ptr+1
    dex
    bne @page_loop
    ldy #$40
    lda gfx_value
@tail_loop:
    dey
    sta (gfx_ptr),y
    bne @tail_loop
    cli
    rts

avmrun_native_helper_gfx_screen_cell:
    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda $D018
    and #$F0
    lsr a
    lsr a
    clc
    adc gfx_ptr+1
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    clc
    lda gfx_ptr
    adc 2,x
    sta gfx_ptr
    lda gfx_ptr+1
    adc 3,x
    sta gfx_ptr+1
    ldy #$00
    lda 0,x
    sta (gfx_ptr),y
    rts

avmrun_native_helper_gfx_color_cell:
    lda #$00
    sta gfx_ptr
    lda #$D8
    sta gfx_ptr+1
    clc
    lda gfx_ptr
    adc 2,x
    sta gfx_ptr
    lda gfx_ptr+1
    adc 3,x
    sta gfx_ptr+1
    ldy #$00
    lda 0,x
    and #$0F
    sta (gfx_ptr),y
    rts

avmrun_native_helper_gfx_bitmap_show:
    lda #$00
    beq avmrun_native_helper_gfx_bitmap_descriptor_common

avmrun_native_helper_gfx_bitmap_copy:
    lda #GFX_FLAG_COPY_ONLY
avmrun_native_helper_gfx_bitmap_descriptor_common:
    sta gfx_value
    lda 0,x
    sta gfx_ptr
    lda 1,x
    sta gfx_ptr+1

    ldy #$00
    lda (gfx_ptr),y
    ora gfx_value
    sta gfx_flags
    bmi @show_save_state

    iny
    lda (gfx_ptr),y
    and #$03
    eor #$03
    sta gfx_value
    lda $DD00
    and #$FC
    ora gfx_value
    sta $DD00

    iny
    lda (gfx_ptr),y
    and #$0F
    asl a
    asl a
    asl a
    asl a
    sta gfx_value
    lda $D018
    and #$0F
    ora gfx_value
    sta $D018

    iny
    lda $D018
    and #$F7
    sta gfx_value
    lda (gfx_ptr),y
    and #$01
    beq @show_bitmap_base_clear
    lda gfx_value
    ora #$08
    sta $D018
    bne @show_bg_color
@show_bitmap_base_clear:
    lda gfx_value
    sta $D018
@show_bg_color:
    iny
    lda (gfx_ptr),y
    and #$0F
    sta gfx_value
    lda $D021
    and #$F0
    ora gfx_value
    sta $D021

    iny
    lda (gfx_ptr),y
    and #$0F
    sta gfx_value
    lda $D020
    and #$F0
    ora gfx_value
    sta $D020
    clc
    bcc @show_copy_check_bitmap

@show_save_state:
    lda $DD00
    pha
    lda $D018
    pha
    lda $D021
    pha
    lda $D020
    pha

    iny
    lda (gfx_ptr),y
    and #$03
    eor #$03
    sta gfx_value
    lda $DD00
    and #$FC
    ora gfx_value
    sta $DD00

    iny
    lda (gfx_ptr),y
    and #$0F
    asl a
    asl a
    asl a
    asl a
    sta gfx_value
    lda $D018
    and #$0F
    ora gfx_value
    sta $D018

    iny
    lda $D018
    and #$F7
    sta gfx_value
    lda (gfx_ptr),y
    and #$01
    beq @show_copy_bitmap_base_clear
    lda gfx_value
    ora #$08
    sta $D018
    bne @show_copy_bg_color
@show_copy_bitmap_base_clear:
    lda gfx_value
    sta $D018
@show_copy_bg_color:
    iny
    lda (gfx_ptr),y
    and #$0F
    sta gfx_value
    lda $D021
    and #$F0
    ora gfx_value
    sta $D021

    iny
    lda (gfx_ptr),y
    and #$0F
    sta gfx_value
    lda $D020
    and #$F0
    ora gfx_value
    sta $D020

@show_copy_check_bitmap:

    lda gfx_flags
    and #GFX_FLAG_BITMAP_DATA
    beq @show_screen_copy_check
    iny
    lda (gfx_ptr),y
    sta gfx_src
    iny
    lda (gfx_ptr),y
    sta gfx_src+1

    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    lda $D018
    and #$08
    beq @copy_loop_init
    clc
    lda gfx_ptr+1
    adc #$20
    sta gfx_ptr+1
@copy_loop_init:
    lda #$20
    sta gfx_value
    ldy #$00
@bitmap_copy_page:
    lda (gfx_src),y
    sta (gfx_ptr),y
    iny
    bne @bitmap_copy_page
    inc gfx_src+1
    inc gfx_ptr+1
    dec gfx_value
    bne @bitmap_copy_page

@show_screen_copy_check:
    lda gfx_flags
    and #GFX_FLAG_SCREEN_DATA
    beq @show_color_copy_check
    lda 0,x
    sta gfx_ptr
    lda 1,x
    sta gfx_ptr+1
    ldy #$08
    lda (gfx_ptr),y
    sta gfx_src
    iny
    lda (gfx_ptr),y
    sta gfx_src+1

    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda $D018
    and #$F0
    lsr a
    lsr a
    clc
    adc gfx_ptr+1
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr

    lda #$03
    sta gfx_value
    ldy #$00
@screen_copy_page:
    lda (gfx_src),y
    sta (gfx_ptr),y
    iny
    bne @screen_copy_page
    inc gfx_src+1
    inc gfx_ptr+1
    dec gfx_value
    bne @screen_copy_page
    ldy #$E8
@screen_copy_tail:
    dey
    lda (gfx_src),y
    sta (gfx_ptr),y
    bne @screen_copy_tail

@show_color_copy_check:
    lda gfx_flags
    and #GFX_FLAG_COLOR_DATA
    beq @show_mode_apply
    lda 0,x
    sta gfx_ptr
    lda 1,x
    sta gfx_ptr+1
    ldy #$0A
    lda (gfx_ptr),y
    sta gfx_src
    iny
    lda (gfx_ptr),y
    sta gfx_src+1

    lda #$00
    sta gfx_ptr
    lda #$D8
    sta gfx_ptr+1

    lda #$03
    sta gfx_value
    ldy #$00
@color_copy_page:
    lda (gfx_src),y
    and #$0F
    sta (gfx_ptr),y
    iny
    bne @color_copy_page
    inc gfx_src+1
    inc gfx_ptr+1
    dec gfx_value
    bne @color_copy_page
    ldy #$E8
@color_copy_tail:
    dey
    lda (gfx_src),y
    and #$0F
    sta (gfx_ptr),y
    bne @color_copy_tail

@show_mode_apply:
    lda gfx_flags
    bmi @show_copy_done
    and #GFX_FLAG_MULTICOLOR
    beq @show_bitmap_on
    lda $D011
    ora #$20
    sta $D011
    lda $D016
    ora #$10
    sta $D016
    rts
@show_bitmap_on:
    lda $D011
    ora #$20
    sta $D011
    lda $D016
    and #$EF
    sta $D016
    rts
@show_copy_done:
    pla
    sta $D020
    pla
    sta $D021
    pla
    sta $D018
    pla
    sta $DD00
    rts

avmrun_native_helper_gfx_screen_copy:
    lda 0,x
    sta gfx_src
    lda 1,x
    sta gfx_src+1

    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda $D018
    and #$F0
    lsr a
    lsr a
    clc
    adc gfx_ptr+1
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr

    lda #$03
    sta gfx_value
    ldy #$00
@screen_copy_page_direct:
    lda (gfx_src),y
    sta (gfx_ptr),y
    iny
    bne @screen_copy_page_direct
    inc gfx_src+1
    inc gfx_ptr+1
    dec gfx_value
    bne @screen_copy_page_direct
    ldy #$E8
@screen_copy_tail_direct:
    dey
    lda (gfx_src),y
    sta (gfx_ptr),y
    bne @screen_copy_tail_direct
    rts

avmrun_native_helper_gfx_color_copy:
    lda 0,x
    sta gfx_src
    lda 1,x
    sta gfx_src+1

    lda #$00
    sta gfx_ptr
    lda #$D8
    sta gfx_ptr+1

    lda #$03
    sta gfx_value
    ldy #$00
@color_copy_page_direct:
    lda (gfx_src),y
    and #$0F
    sta (gfx_ptr),y
    iny
    bne @color_copy_page_direct
    inc gfx_src+1
    inc gfx_ptr+1
    dec gfx_value
    bne @color_copy_page_direct
    ldy #$E8
@color_copy_tail_direct:
    dey
    lda (gfx_src),y
    and #$0F
    sta (gfx_ptr),y
    bne @color_copy_tail_direct
    rts

avmrun_native_helper_gfx_bitmap_cell_colors:
    lda 2,x
    sta gfx_ptr
    lda #$00
    sta gfx_ptr+1
    lda 3,x
    sta gfx_flags
@bitmap_cell_colors_offset_loop:
    lda gfx_flags
    beq @bitmap_cell_colors_offset_done
    clc
    lda gfx_ptr
    adc #40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_flags
    bne @bitmap_cell_colors_offset_loop
@bitmap_cell_colors_offset_done:
    lda gfx_ptr
    sta gfx_src
    lda gfx_ptr+1
    sta gfx_src+1

    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda $D018
    and #$F0
    lsr a
    lsr a
    clc
    adc gfx_ptr+1
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    clc
    lda gfx_ptr
    adc gfx_src
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_src+1
    sta gfx_ptr+1
    ldy #$00
    lda 0,x
    sta (gfx_ptr),y

    lda #$00
    clc
    adc gfx_src
    sta gfx_ptr
    lda #$D8
    adc gfx_src+1
    sta gfx_ptr+1
    lda 1,x
    and #$0F
    sta (gfx_ptr),y
    rts

avmrun_native_helper_gfx_bitmap_cell_data:
    lda 0,x
    sta gfx_src
    lda 1,x
    sta gfx_src+1

    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    lda $D018
    and #$08
    beq :+
    clc
    lda gfx_ptr+1
    adc #$20
    sta gfx_ptr+1
:   lda 3,x
    sta gfx_flags
@bitmap_cell_data_row_loop:
    lda gfx_flags
    beq @bitmap_cell_data_col_init
    clc
    lda gfx_ptr
    adc #$40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$01
    sta gfx_ptr+1
    dec gfx_flags
    bne @bitmap_cell_data_row_loop
@bitmap_cell_data_col_init:
    lda 2,x
    sta gfx_flags
@bitmap_cell_data_col_loop:
    lda gfx_flags
    beq @bitmap_cell_data_copy
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_flags
    bne @bitmap_cell_data_col_loop
@bitmap_cell_data_copy:
    ldy #$00
@bitmap_cell_data_copy_loop:
    lda (gfx_src),y
    sta (gfx_ptr),y
    iny
    cpy #$08
    bcc @bitmap_cell_data_copy_loop
    rts

avmrun_native_helper_gfx_bitmap_blit:
    lda 0,x
    sta gfx_gap
    lda 1,x
    sta gfx_gap_hi
    ldy #$00
    lda (gfx_gap),y
    sta gfx_width
    bne :+
    jmp @bitmap_blit_done
: 
    iny
    lda (gfx_gap),y
    sta gfx_flags
    bne :+
    jmp @bitmap_blit_done
: 

    ldy #$04
    lda (gfx_gap),y
    sta gfx_src
    iny
    lda (gfx_gap),y
    sta gfx_src+1
    lda gfx_src
    ora gfx_src+1
    bne :+
    jmp @bitmap_blit_screen_plane
: 

    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    lda $D018
    and #$08
    beq :+
    clc
    lda gfx_ptr+1
    adc #$20
    sta gfx_ptr+1
:   ldy #$03
    lda (gfx_gap),y
    sta gfx_value
@bitmap_blit_bitmap_row_offset:
    lda gfx_value
    beq @bitmap_blit_bitmap_col_offset_init
    clc
    lda gfx_ptr
    adc #$40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$01
    sta gfx_ptr+1
    dec gfx_value
    bne @bitmap_blit_bitmap_row_offset
@bitmap_blit_bitmap_col_offset_init:
    ldy #$02
    lda (gfx_gap),y
    sta gfx_value
@bitmap_blit_bitmap_col_offset:
    lda gfx_value
    beq @bitmap_blit_bitmap_gap_ready
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @bitmap_blit_bitmap_col_offset
@bitmap_blit_bitmap_gap_ready:
    lda #$00
    sta gfx_gap_hi
    lda gfx_width
    asl a
    rol gfx_gap_hi
    asl a
    rol gfx_gap_hi
    asl a
    rol gfx_gap_hi
    sta gfx_gap
    sec
    lda #$40
    sbc gfx_gap
    sta gfx_gap
    lda #$01
    sbc gfx_gap_hi
    sta gfx_gap_hi
@bitmap_blit_bitmap_row_loop:
    lda gfx_flags
    beq @bitmap_blit_screen_plane
    lda gfx_width
    sta gfx_value
@bitmap_blit_bitmap_col_loop:
    lda gfx_value
    beq @bitmap_blit_bitmap_row_next
    ldy #$00
@bitmap_blit_bitmap_copy8:
    lda (gfx_src),y
    sta (gfx_ptr),y
    iny
    cpy #$08
    bcc @bitmap_blit_bitmap_copy8
    clc
    lda gfx_src
    adc #$08
    sta gfx_src
    lda gfx_src+1
    adc #$00
    sta gfx_src+1
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @bitmap_blit_bitmap_col_loop
@bitmap_blit_bitmap_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @bitmap_blit_bitmap_row_loop

@bitmap_blit_screen_plane:
    lda 0,x
    sta gfx_gap
    lda 1,x
    sta gfx_gap_hi
    ldy #$00
    lda (gfx_gap),y
    sta gfx_width
    bne :+
    jmp @bitmap_blit_done
: 
    iny
    lda (gfx_gap),y
    sta gfx_flags
    bne :+
    jmp @bitmap_blit_done
: 
    ldy #$06
    lda (gfx_gap),y
    sta gfx_src
    iny
    lda (gfx_gap),y
    sta gfx_src+1
    lda gfx_src
    ora gfx_src+1
    bne :+
    jmp @bitmap_blit_color_plane
: 

    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda $D018
    and #$F0
    lsr a
    lsr a
    clc
    adc gfx_ptr+1
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    ldy #$03
    lda (gfx_gap),y
    sta gfx_value
@bitmap_blit_screen_row_offset:
    lda gfx_value
    beq @bitmap_blit_screen_col_offset
    clc
    lda gfx_ptr
    adc #40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @bitmap_blit_screen_row_offset
@bitmap_blit_screen_col_offset:
    ldy #$02
    lda (gfx_gap),y
    clc
    adc gfx_ptr
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    sec
    lda #40
    sbc gfx_width
    sta gfx_gap
    lda #$00
    sta gfx_gap_hi
@bitmap_blit_screen_row_loop:
    lda gfx_flags
    beq @bitmap_blit_color_plane
    lda gfx_width
    sta gfx_value
    ldy #$00
@bitmap_blit_screen_col_loop:
    lda gfx_value
    beq @bitmap_blit_screen_row_next
    lda (gfx_src),y
    sta (gfx_ptr),y
    inc gfx_src
    bne :+
    inc gfx_src+1
:   inc gfx_ptr
    bne :+
    inc gfx_ptr+1
:   dec gfx_value
    bne @bitmap_blit_screen_col_loop
@bitmap_blit_screen_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @bitmap_blit_screen_row_loop

@bitmap_blit_color_plane:
    lda 0,x
    sta gfx_gap
    lda 1,x
    sta gfx_gap_hi
    ldy #$00
    lda (gfx_gap),y
    sta gfx_width
    bne :+
    jmp @bitmap_blit_done
: 
    iny
    lda (gfx_gap),y
    sta gfx_flags
    bne :+
    jmp @bitmap_blit_done
: 
    ldy #$08
    lda (gfx_gap),y
    sta gfx_src
    iny
    lda (gfx_gap),y
    sta gfx_src+1
    lda gfx_src
    ora gfx_src+1
    beq @bitmap_blit_done

    lda #$00
    sta gfx_ptr
    lda #$D8
    sta gfx_ptr+1
    ldy #$03
    lda (gfx_gap),y
    sta gfx_value
@bitmap_blit_color_row_offset:
    lda gfx_value
    beq @bitmap_blit_color_col_offset
    clc
    lda gfx_ptr
    adc #40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @bitmap_blit_color_row_offset
@bitmap_blit_color_col_offset:
    ldy #$02
    lda (gfx_gap),y
    clc
    adc gfx_ptr
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    sec
    lda #40
    sbc gfx_width
    sta gfx_gap
    lda #$00
    sta gfx_gap_hi
@bitmap_blit_color_row_loop:
    lda gfx_flags
    beq @bitmap_blit_done
    lda gfx_width
    sta gfx_value
    ldy #$00
@bitmap_blit_color_col_loop:
    lda gfx_value
    beq @bitmap_blit_color_row_next
    lda (gfx_src),y
    and #$0F
    sta (gfx_ptr),y
    inc gfx_src
    bne :+
    inc gfx_src+1
:   inc gfx_ptr
    bne :+
    inc gfx_ptr+1
:   dec gfx_value
    bne @bitmap_blit_color_col_loop
@bitmap_blit_color_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @bitmap_blit_color_row_loop

@bitmap_blit_done:
    rts

avmrun_native_helper_gfx_tile_draw:
    lda 0,x
    sta gfx_src
    lda 1,x
    sta gfx_src+1
    ldy #$00
    lda (gfx_src),y
    sta gfx_width
    bne :+
    rts
:   iny
    lda (gfx_src),y
    sta gfx_flags
    bne :+
    rts
:   clc
    lda gfx_src
    adc #$02
    sta gfx_src
    bcc :+
    inc gfx_src+1
:   lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    lda $D018
    and #$08
    beq :+
    clc
    lda gfx_ptr+1
    adc #$20
    sta gfx_ptr+1
:   lda 3,x
    sta gfx_value
@tile_draw_bitmap_row_offset:
    lda gfx_value
    beq @tile_draw_bitmap_col_offset_init
    clc
    lda gfx_ptr
    adc #$40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$01
    sta gfx_ptr+1
    dec gfx_value
    bne @tile_draw_bitmap_row_offset
@tile_draw_bitmap_col_offset_init:
    lda 2,x
    sta gfx_value
@tile_draw_bitmap_col_offset:
    lda gfx_value
    beq @tile_draw_bitmap_gap_ready
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @tile_draw_bitmap_col_offset
@tile_draw_bitmap_gap_ready:
    lda #$00
    sta gfx_gap_hi
    lda gfx_width
    asl a
    rol gfx_gap_hi
    asl a
    rol gfx_gap_hi
    asl a
    rol gfx_gap_hi
    sta gfx_gap
    sec
    lda #$40
    sbc gfx_gap
    sta gfx_gap
    lda #$01
    sbc gfx_gap_hi
    sta gfx_gap_hi
@tile_draw_bitmap_row_loop:
    lda gfx_flags
    beq @tile_draw_screen_plane
    lda gfx_width
    sta gfx_value
@tile_draw_bitmap_col_loop:
    lda gfx_value
    beq @tile_draw_bitmap_row_next
    ldy #$00
@tile_draw_bitmap_copy8:
    lda (gfx_src),y
    sta (gfx_ptr),y
    iny
    cpy #$08
    bcc @tile_draw_bitmap_copy8
    clc
    lda gfx_src
    adc #$08
    sta gfx_src
    lda gfx_src+1
    adc #$00
    sta gfx_src+1
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @tile_draw_bitmap_col_loop
@tile_draw_bitmap_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_draw_bitmap_row_loop

@tile_draw_screen_plane:
    lda 0,x
    sta gfx_gap
    lda 1,x
    sta gfx_gap_hi
    ldy #$01
    lda (gfx_gap),y
    sta gfx_flags
    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda $D018
    and #$F0
    lsr a
    lsr a
    clc
    adc gfx_ptr+1
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    lda 3,x
    sta gfx_value
@tile_draw_screen_row_offset:
    lda gfx_value
    beq @tile_draw_screen_col_offset
    clc
    lda gfx_ptr
    adc #40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @tile_draw_screen_row_offset
@tile_draw_screen_col_offset:
    lda 2,x
    clc
    adc gfx_ptr
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    sec
    lda #40
    sbc gfx_width
    sta gfx_gap
    lda #$00
    sta gfx_gap_hi
@tile_draw_screen_row_loop:
    lda gfx_flags
    beq @tile_draw_color_plane
    lda gfx_width
    sta gfx_value
    ldy #$00
@tile_draw_screen_col_loop:
    lda gfx_value
    beq @tile_draw_screen_row_next
    lda (gfx_src),y
    sta (gfx_ptr),y
    inc gfx_src
    bne :+
    inc gfx_src+1
:   inc gfx_ptr
    bne :+
    inc gfx_ptr+1
:   dec gfx_value
    bne @tile_draw_screen_col_loop
@tile_draw_screen_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_draw_screen_row_loop

@tile_draw_color_plane:
    lda 0,x
    sta gfx_gap
    lda 1,x
    sta gfx_gap_hi
    ldy #$01
    lda (gfx_gap),y
    sta gfx_flags
    lda #$00
    sta gfx_ptr
    lda #$D8
    sta gfx_ptr+1
    lda 3,x
    sta gfx_value
@tile_draw_color_row_offset:
    lda gfx_value
    beq @tile_draw_color_col_offset
    clc
    lda gfx_ptr
    adc #40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @tile_draw_color_row_offset
@tile_draw_color_col_offset:
    lda 2,x
    clc
    adc gfx_ptr
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    sec
    lda #40
    sbc gfx_width
    sta gfx_gap
    lda #$00
    sta gfx_gap_hi
@tile_draw_color_row_loop:
    lda gfx_flags
    beq @tile_draw_done
    lda gfx_width
    sta gfx_value
    ldy #$00
@tile_draw_color_col_loop:
    lda gfx_value
    beq @tile_draw_color_row_next
    lda (gfx_src),y
    and #$0F
    sta (gfx_ptr),y
    inc gfx_src
    bne :+
    inc gfx_src+1
:   inc gfx_ptr
    bne :+
    inc gfx_ptr+1
:   dec gfx_value
    bne @tile_draw_color_col_loop
@tile_draw_color_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_draw_color_row_loop

@tile_draw_done:
    rts

avmrun_native_helper_gfx_tile_rect_fill:
    lda 0,x
    ora 1,x
    bne :+
    rts
:   lda 4,x
    bne :+
    rts
:   lda 5,x
    bne :+
    rts
:   lda 0,x
    sta gfx_src
    lda 1,x
    sta gfx_src+1

    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    lda $D018
    and #$08
    beq :+
    clc
    lda gfx_ptr+1
    adc #$20
    sta gfx_ptr+1
:   lda 3,x
    sta gfx_value
@tile_rect_fill_bitmap_row_offset:
    lda gfx_value
    beq @tile_rect_fill_bitmap_col_offset
    clc
    lda gfx_ptr
    adc #$40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$01
    sta gfx_ptr+1
    dec gfx_value
    bne @tile_rect_fill_bitmap_row_offset
@tile_rect_fill_bitmap_col_offset:
    lda 2,x
    sta gfx_value
@tile_rect_fill_bitmap_col_offset_loop:
    lda gfx_value
    beq @tile_rect_fill_bitmap_gap_ready
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @tile_rect_fill_bitmap_col_offset_loop
@tile_rect_fill_bitmap_gap_ready:
    lda #$00
    sta gfx_gap_hi
    lda 4,x
    asl a
    rol gfx_gap_hi
    asl a
    rol gfx_gap_hi
    asl a
    rol gfx_gap_hi
    sta gfx_gap
    sec
    lda #$40
    sbc gfx_gap
    sta gfx_gap
    lda #$01
    sbc gfx_gap_hi
    sta gfx_gap_hi
    lda 5,x
    sta gfx_flags
@tile_rect_fill_bitmap_row_loop:
    lda gfx_flags
    beq @tile_rect_fill_screen_plane
    lda 4,x
    sta gfx_width
@tile_rect_fill_bitmap_col_loop:
    lda gfx_width
    beq @tile_rect_fill_bitmap_row_next
    ldy #$00
@tile_rect_fill_bitmap_copy8:
    lda (gfx_src),y
    sta (gfx_ptr),y
    iny
    cpy #$08
    bcc @tile_rect_fill_bitmap_copy8
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_width
    bne @tile_rect_fill_bitmap_col_loop
@tile_rect_fill_bitmap_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_rect_fill_bitmap_row_loop

@tile_rect_fill_screen_plane:
    lda 0,x
    sta gfx_src
    lda 1,x
    sta gfx_src+1
    ldy #$08
    lda (gfx_src),y
    sta gfx_value
    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda $D018
    and #$F0
    lsr a
    lsr a
    clc
    adc gfx_ptr+1
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    lda 3,x
    sta gfx_flags
@tile_rect_fill_screen_row_offset:
    lda gfx_flags
    beq @tile_rect_fill_screen_col_offset
    clc
    lda gfx_ptr
    adc #40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_rect_fill_screen_row_offset
@tile_rect_fill_screen_col_offset:
    lda 2,x
    clc
    adc gfx_ptr
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    sec
    lda #40
    sbc 4,x
    sta gfx_gap
    lda #$00
    sta gfx_gap_hi
    lda 5,x
    sta gfx_flags
@tile_rect_fill_screen_row_loop:
    lda gfx_flags
    beq @tile_rect_fill_color_plane
    lda 4,x
    sta gfx_width
    ldy #$00
@tile_rect_fill_screen_col_loop:
    lda gfx_width
    beq @tile_rect_fill_screen_row_next
    lda gfx_value
    sta (gfx_ptr),y
    inc gfx_ptr
    bne :+
    inc gfx_ptr+1
:   dec gfx_width
    bne @tile_rect_fill_screen_col_loop
@tile_rect_fill_screen_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_rect_fill_screen_row_loop

@tile_rect_fill_color_plane:
    lda 0,x
    sta gfx_src
    lda 1,x
    sta gfx_src+1
    ldy #$09
    lda (gfx_src),y
    and #$0F
    sta gfx_value
    lda #$00
    sta gfx_ptr
    lda #$D8
    sta gfx_ptr+1
    lda 3,x
    sta gfx_flags
@tile_rect_fill_color_row_offset:
    lda gfx_flags
    beq @tile_rect_fill_color_col_offset
    clc
    lda gfx_ptr
    adc #40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_rect_fill_color_row_offset
@tile_rect_fill_color_col_offset:
    lda 2,x
    clc
    adc gfx_ptr
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    sec
    lda #40
    sbc 4,x
    sta gfx_gap
    lda #$00
    sta gfx_gap_hi
    lda 5,x
    sta gfx_flags
@tile_rect_fill_color_row_loop:
    lda gfx_flags
    beq @tile_rect_fill_done
    lda 4,x
    sta gfx_width
    ldy #$00
@tile_rect_fill_color_col_loop:
    lda gfx_width
    beq @tile_rect_fill_color_row_next
    lda gfx_value
    sta (gfx_ptr),y
    inc gfx_ptr
    bne :+
    inc gfx_ptr+1
:   dec gfx_width
    bne @tile_rect_fill_color_col_loop
@tile_rect_fill_color_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_rect_fill_color_row_loop

@tile_rect_fill_done:
    rts

avmrun_native_helper_gfx_bitmap_mask_blit:
    lda 0,x
    sta gfx_ptr
    lda 1,x
    sta gfx_ptr+1
    ldy #$00
    lda (gfx_ptr),y
    sta 0,x
    bne :+
    jmp @bitmap_mask_blit_done
:   iny
    lda (gfx_ptr),y
    sta gfx_width
    bne :+
    jmp @bitmap_mask_blit_done
:
    iny
    lda (gfx_ptr),y
    sta 1,x
    iny
    lda (gfx_ptr),y
    sta 2,x
    ldy #$04
    lda (gfx_ptr),y
    sta gfx_src
    iny
    lda (gfx_ptr),y
    sta gfx_src+1
    lda gfx_src
    ora gfx_src+1
    bne :+
    jmp @bitmap_mask_blit_done
:

    ldy #$06
    lda (gfx_ptr),y
    sta gfx_gap
    iny
    lda (gfx_ptr),y
    sta gfx_gap_hi
    lda gfx_gap
    ora gfx_gap_hi
    bne :+
    jmp @bitmap_mask_blit_done
:

    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    lda $D018
    and #$08
    beq :+
    clc
    lda gfx_ptr+1
    adc #$20
    sta gfx_ptr+1
:   lda 2,x
    sta gfx_value
@bitmap_mask_blit_row_offset:
    lda gfx_value
    beq @bitmap_mask_blit_col_offset_init
    clc
    lda gfx_ptr
    adc #$40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$01
    sta gfx_ptr+1
    dec gfx_value
    bne @bitmap_mask_blit_row_offset
@bitmap_mask_blit_col_offset_init:
    lda 1,x
    sta gfx_value
@bitmap_mask_blit_col_offset:
    lda gfx_value
    beq @bitmap_mask_blit_gap_ready
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @bitmap_mask_blit_col_offset
@bitmap_mask_blit_gap_ready:
    lda #$00
    sta gfx_flags
    lda 0,x
    asl a
    rol gfx_flags
    asl a
    rol gfx_flags
    asl a
    rol gfx_flags
    sta 8,x
    lda #$40
    sec
    sbc 8,x
    sta gfx_value
    lda #$01
    sbc gfx_flags
    sta gfx_flags
@bitmap_mask_blit_row_loop:
    lda gfx_width
    beq @bitmap_mask_blit_done
    lda 0,x
    sta 8,x
@bitmap_mask_blit_col_loop:
    lda 8,x
    beq @bitmap_mask_blit_row_next
    ldy #$00
@bitmap_mask_blit_copy8:
    lda (gfx_ptr),y
    eor (gfx_src),y
    and (gfx_gap),y
    eor (gfx_ptr),y
    sta (gfx_ptr),y
    iny
    cpy #$08
    bcc @bitmap_mask_blit_copy8
    clc
    lda gfx_src
    adc #$08
    sta gfx_src
    lda gfx_src+1
    adc #$00
    sta gfx_src+1
    clc
    lda gfx_gap
    adc #$08
    sta gfx_gap
    lda gfx_gap_hi
    adc #$00
    sta gfx_gap_hi
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec 8,x
    bne @bitmap_mask_blit_col_loop
@bitmap_mask_blit_row_next:
    clc
    lda gfx_ptr
    adc gfx_value
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_flags
    sta gfx_ptr+1
    dec gfx_width
    bne @bitmap_mask_blit_row_loop

@bitmap_mask_blit_done:
    rts

avmrun_native_helper_gfx_tile_mask_draw:
    lda 0,x
    sta gfx_src
    lda 1,x
    sta gfx_src+1
    ldy #$00
    lda (gfx_src),y
    sta gfx_width
    bne :+
    rts
:   iny
    lda (gfx_src),y
    sta 4,x
    bne :+
    rts
:   clc
    lda gfx_src
    adc #$02
    sta gfx_src
    bcc :+
    inc gfx_src+1
:   lda gfx_src
    sta gfx_gap
    lda gfx_src+1
    sta gfx_gap_hi
    lda #$00
    sta 6,x
    lda gfx_width
    asl a
    rol 6,x
    asl a
    rol 6,x
    asl a
    rol 6,x
    sta 5,x
    lda 4,x
    sta gfx_flags
@tile_mask_draw_mask_ptr_loop:
    lda gfx_flags
    beq @tile_mask_draw_bitmap_plane
    clc
    lda gfx_gap
    adc 5,x
    sta gfx_gap
    lda gfx_gap_hi
    adc 6,x
    sta gfx_gap_hi
    dec gfx_flags
    bne @tile_mask_draw_mask_ptr_loop

@tile_mask_draw_bitmap_plane:
    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda #$00
    sta gfx_ptr
    lda $D018
    and #$08
    beq :+
    clc
    lda gfx_ptr+1
    adc #$20
    sta gfx_ptr+1
:   lda 3,x
    sta gfx_value
@tile_mask_draw_bitmap_row_offset:
    lda gfx_value
    beq @tile_mask_draw_bitmap_col_offset
    clc
    lda gfx_ptr
    adc #$40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$01
    sta gfx_ptr+1
    dec gfx_value
    bne @tile_mask_draw_bitmap_row_offset
@tile_mask_draw_bitmap_col_offset:
    lda 2,x
    sta gfx_value
@tile_mask_draw_bitmap_col_offset_loop:
    lda gfx_value
    beq @tile_mask_draw_bitmap_gap_ready
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_value
    bne @tile_mask_draw_bitmap_col_offset_loop
@tile_mask_draw_bitmap_gap_ready:
    lda #$40
    sec
    sbc 5,x
    sta gfx_value
    lda #$01
    sbc 6,x
    sta gfx_flags
    lda 4,x
    sta 7,x
@tile_mask_draw_bitmap_row_loop:
    lda 7,x
    beq @tile_mask_draw_screen_plane
    lda gfx_width
    sta 8,x
@tile_mask_draw_bitmap_col_loop:
    lda 8,x
    beq @tile_mask_draw_bitmap_row_next
    ldy #$00
@tile_mask_draw_bitmap_copy8:
    lda (gfx_ptr),y
    eor (gfx_src),y
    and (gfx_gap),y
    eor (gfx_ptr),y
    sta (gfx_ptr),y
    iny
    cpy #$08
    bcc @tile_mask_draw_bitmap_copy8
    clc
    lda gfx_src
    adc #$08
    sta gfx_src
    lda gfx_src+1
    adc #$00
    sta gfx_src+1
    clc
    lda gfx_gap
    adc #$08
    sta gfx_gap
    lda gfx_gap_hi
    adc #$00
    sta gfx_gap_hi
    clc
    lda gfx_ptr
    adc #$08
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec 8,x
    bne @tile_mask_draw_bitmap_col_loop
@tile_mask_draw_bitmap_row_next:
    clc
    lda gfx_ptr
    adc gfx_value
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_flags
    sta gfx_ptr+1
    dec 7,x
    bne @tile_mask_draw_bitmap_row_loop

@tile_mask_draw_screen_plane:
    lda gfx_gap
    sta gfx_src
    lda gfx_gap_hi
    sta gfx_src+1
    lda #$00
    sta gfx_ptr
    lda $DD00
    eor #$03
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta gfx_ptr+1
    lda $D018
    and #$F0
    lsr a
    lsr a
    clc
    adc gfx_ptr+1
    sta gfx_ptr+1
    lda 3,x
    sta gfx_flags
@tile_mask_draw_screen_row_offset:
    lda gfx_flags
    beq @tile_mask_draw_screen_col_offset
    clc
    lda gfx_ptr
    adc #40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_mask_draw_screen_row_offset
@tile_mask_draw_screen_col_offset:
    lda 2,x
    clc
    adc gfx_ptr
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    sec
    lda #40
    sbc gfx_width
    sta gfx_gap
    lda #$00
    sta gfx_gap_hi
    lda 4,x
    sta gfx_flags
@tile_mask_draw_screen_row_loop:
    lda gfx_flags
    beq @tile_mask_draw_color_plane
    lda gfx_width
    sta gfx_value
    ldy #$00
@tile_mask_draw_screen_col_loop:
    lda gfx_value
    beq @tile_mask_draw_screen_row_next
    lda (gfx_src),y
    sta (gfx_ptr),y
    inc gfx_src
    bne :+
    inc gfx_src+1
:   inc gfx_ptr
    bne :+
    inc gfx_ptr+1
:   dec gfx_value
    bne @tile_mask_draw_screen_col_loop
@tile_mask_draw_screen_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_mask_draw_screen_row_loop

@tile_mask_draw_color_plane:
    lda #$00
    sta gfx_ptr
    lda #$D8
    sta gfx_ptr+1
    lda 3,x
    sta gfx_flags
@tile_mask_draw_color_row_offset:
    lda gfx_flags
    beq @tile_mask_draw_color_col_offset
    clc
    lda gfx_ptr
    adc #40
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_mask_draw_color_row_offset
@tile_mask_draw_color_col_offset:
    lda 2,x
    clc
    adc gfx_ptr
    sta gfx_ptr
    lda gfx_ptr+1
    adc #$00
    sta gfx_ptr+1
    sec
    lda #40
    sbc gfx_width
    sta gfx_gap
    lda #$00
    sta gfx_gap_hi
    lda 4,x
    sta gfx_flags
@tile_mask_draw_color_row_loop:
    lda gfx_flags
    beq @tile_mask_draw_done
    lda gfx_width
    sta gfx_value
    ldy #$00
@tile_mask_draw_color_col_loop:
    lda gfx_value
    beq @tile_mask_draw_color_row_next
    lda (gfx_src),y
    and #$0F
    sta (gfx_ptr),y
    inc gfx_src
    bne :+
    inc gfx_src+1
:   inc gfx_ptr
    bne :+
    inc gfx_ptr+1
:   dec gfx_value
    bne @tile_mask_draw_color_col_loop
@tile_mask_draw_color_row_next:
    clc
    lda gfx_ptr
    adc gfx_gap
    sta gfx_ptr
    lda gfx_ptr+1
    adc gfx_gap_hi
    sta gfx_ptr+1
    dec gfx_flags
    bne @tile_mask_draw_color_row_loop

@tile_mask_draw_done:
    rts

avmrun_native_helper_gfx_end:
