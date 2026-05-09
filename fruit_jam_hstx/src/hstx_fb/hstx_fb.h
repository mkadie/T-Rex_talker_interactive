// hstx_fb.h — C API declarations for the vendored picodvi/HSTX framebuffer.
//
// The actual implementation is in Framebuffer_RP2350.c (see that file's
// header for vendoring + license info). This header lets the .cpp
// Arduino sketch call into it through extern "C".

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  uint32_t *framebuffer;
  size_t framebuffer_len;     // in 32-bit words
  uint32_t *dma_commands;
  size_t dma_commands_len;    // in 32-bit words
  uint32_t width;
  uint32_t height;
  uint32_t output_width;      // 640 or 720 — set by construct()
  uint16_t pitch;             // 32-bit words per scanline
  uint8_t color_depth;        // bits per pixel: 1, 2, 4, 8, 16, or 32
  int dma_pixel_channel;
  int dma_command_channel;
  int frameno;
} picodvi_framebuffer_obj_t;

// Bring up the HSTX DVI peripheral with a software framebuffer.
//
// On success returns true and `self` is populated. The pixel framebuffer
// at `self->framebuffer` is `pitch * height` 32-bit words; you can write
// to it as `(uint16_t *)self->framebuffer` for color_depth=16 (RGB565),
// `(uint8_t *)self->framebuffer` for color_depth=8 (RGB332), etc.
//
// `width` is the logical pixel width. `output_width` (set internally to
// 640 or 720) is the actual HDMI raster width; pixel doubling is
// automatic when width is half the output.
//
// `clk_dp / red_dp / green_dp / blue_dp` are HSTX-eligible GPIO numbers
// (12..19 on RP2350). For Adafruit Fruit Jam, the upstream Doom code
// passes 13/15/17/19 (the P-side of each HSTX differential pair).
bool common_hal_picodvi_framebuffer_construct(picodvi_framebuffer_obj_t *self,
    uint32_t width, uint32_t height,
    int clk_dp, int red_dp, int green_dp, int blue_dp,
    uint32_t color_depth);

#ifdef __cplusplus
}
#endif
