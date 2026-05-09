# `src/hstx_fb/` — vendored HSTX DVI framebuffer driver

`Framebuffer_RP2350.c` drives the RP2350's HSTX peripheral to produce a
DVI/HDMI signal with a software framebuffer.

## Vendored from

| | |
|---|---|
| **Project** | [adafruit/fruitjam-doom](https://github.com/adafruit/fruitjam-doom) |
| **Original file** | [`Framebuffer_RP2350.c`](https://github.com/adafruit/fruitjam-doom/blob/adafruit-fruitjam/Framebuffer_RP2350.c) on the `adafruit-fruitjam` branch |
| **License (this file)** | MIT — see `LICENSE.txt` and the file's own header |
| **Origin chain** | MicroPython port → Adafruit's fruitjam-doom → here |
| **Pulled in** | 2026-05-09 (P1' of the Arduino 720p port) |

## Modes supported

| Output raster | Logical sizes (with output_scaling) |
|---|---|
| 640×480 | 320×240 ×2 (used by P1'), 640×480 ×1 |
| 720×400 | 360×200 ×2, 720×400 ×1 |

Note: this file does **not** include 1280×720@60. Adding it is part of
P1.5 in the project plan (`fruit_jam_dvi/arduino_720p_PLAN.md` §4).

## Local modifications

Two changes from the upstream copy, both flagged with
`// MODIFIED 2026-05-09:` comments in the source:

1. `self->height = 200;` → `self->height = height;` — the upstream copy
   hardcoded the framebuffer height to 200 for Doom (320×200). We want
   320×240, so the height parameter is now actually used.
2. `row = row * 200 / 480;` → `row = row * self->height /
   mode_v_active_lines;` — same Doom hardcode in the row-scaling math.
   With the active-line count of the chosen output mode now stored in a
   `mode_v_active_lines` local, the formula generalizes to any input
   height ≤ output raster.

No other behavior changes.

## API

See `hstx_fb.h` for the declarations the Arduino `.cpp` sketch uses:

```c
bool common_hal_picodvi_framebuffer_construct(picodvi_framebuffer_obj_t *self,
    uint32_t width, uint32_t height,
    int clk_dp, int red_dp, int green_dp, int blue_dp,
    uint32_t color_depth);
```

The Adafruit Fruit Jam wires HSTX to GPIO 12–19. Upstream Doom uses
`13, 15, 17, 19` — i.e. the P-side of each differential pair (CKP, D0P,
D1P, D2P). Same here.
