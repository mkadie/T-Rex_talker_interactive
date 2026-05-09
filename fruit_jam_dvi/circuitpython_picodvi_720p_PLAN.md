# Custom CircuitPython firmware — add 1280×720 to `picodvi`

**Status:** active plan, replacing the abandoned Arduino approach (see `arduino_720p_PLAN.md` and `arduino_720p_P1_DEBUG.md` for that history; the `fruit_jam_hstx/` directory is archived in place).

**Goal:** the existing CircuitPython multilingual demo at [`../fruit_jam_dvi/`](../fruit_jam_dvi/) should be able to call `request_display_config(1280, 720)` and get a true 1280×720 60 Hz HDMI signal out of the Fruit Jam, with pixel tripling supported (e.g. 320×240 logical → ×3 → 960×720 with horizontal pillarbox; or 426×240 ×3 ≈ 1278×720 to fill the raster).

**Approach:** fork [adafruit/circuitpython](https://github.com/adafruit/circuitpython), extend `shared-module/picodvi/Framebuffer_RP2350.c` with a new `MODE_1280_720_*` timing block and command lists, plumb the new size through `adafruit_fruitjam.peripherals.VALID_DISPLAY_SIZES`, build a custom UF2 for the `adafruit_fruit_jam` board target, flash it. The Python-side demo doesn't change at all — same `request_display_config(W, H)`; we just expand which W/H combos are valid.

**Why not** the Arduino route, the `dvhstx` import, or a brand-new CP module: the file we'd modify is the same code we already vendored into the Arduino attempt. Adding one mode + clock setup is small. A new CP module would require defining `shared-bindings/`, `shared-module/`, board config plumbing, Python class wrappers — for no functionality not already present in `picodvi`.

## What we know about the target

CEA-861 VIC 4 (1280×720@60 Hz):

| | |
|---|---|
| Pixel clock | 74.250 MHz |
| TMDS bit clock | 742.5 MHz (= 10× pixel clock) |
| H total | 1650 |
| H active | 1280 |
| H sync (pulse, polarity) | 40, **positive** |
| H front porch | 110 |
| H back porch | 220 |
| V total | 750 |
| V active | 720 |
| V sync (pulse, polarity) | 5, **positive** |
| V front porch | 5 |
| V back porch | 20 |

Sync polarities differ from the existing 720×400 / 640×480 modes (those are positive H / negative V or vice versa per IBM VGA legacy). We'll need to handle that explicitly.

The HSTX peripheral shifts out 2 bits per HSTX clock, so we want the HSTX clock at half the TMDS bit rate: **HSTX clock = 371.25 MHz**.

The existing CP modes run with HSTX clock ≈ 125 MHz (480p / 350p TMDS at 250 Mbps). Going to 720p means the HSTX peripheral has to run at ~3× that — and `clk_hstx`'s aux source on the Fruit Jam is `clk_sys`. So `clk_sys` needs to be at or above 371 MHz.

**That's an overclock.** Default `clk_sys` on adafruit_fruit_jam in CP is 150 MHz. Per Raspberry Pi's RP2350 datasheet, 150 MHz is guaranteed at the default 1.10 V core voltage; speeds above ~250 MHz are explicitly out of spec and may need 1.30 V core (still within hardware tolerances per a Raspberry Pi blog post on the RP2350 silicon errata). The third-party `fliperama86/pico_hdmi` library uses 372 MHz / 1.30 V for 1280×720 — that's our reference operating point.

So the C-level changes split into three parts:

1. **Mode timing constants and command lists** — straightforward, modeled on the existing 640×480 / 720×400 blocks.
2. **HSTX clock setup** — when 1280×720 is requested, raise `clk_sys` to 372 MHz with vreg at 1.30 V, then configure `clk_hstx` accordingly. Return to the default after a `release_displays()` call so other modes still work.
3. **`construct()` plumbing** — recognize `output_width == 1280` and pick the new mode's H/V totals, command lists, etc.

Plus the Python side:

4. **`adafruit_fruitjam.peripherals.VALID_DISPLAY_SIZES`** — add `(1280, 720)`. Optional: also add intermediate sizes like `(320, 240)` (×3 with pillarbox, no aspect-ratio fit but reuses our assets), `(426, 240)` (×3 fit), `(640, 360)` (×2), `(1280, 720)` native (×1).

## Phased rollout

| Phase | Deliverable | Acceptance test |
|---|---|---|
| **Q0** | CircuitPython source cloned, submodules fetched, **stock** `adafruit_fruit_jam` UF2 builds. | `firmware.uf2` produced. No flash yet. |
| **Q1** | Stock UF2 flashed and verified — same `boot_out.txt` / demo behavior as the cached 10.1.4 release UF2. | Existing CP demo still runs identically. |
| **Q2** | Add `MODE_1280_720_*` timing constants + command lists to `shared-module/picodvi/Framebuffer_RP2350.c`. No clock changes yet — just the static data. | Build succeeds. No flash. |
| **Q3** | Add the `output_width == 1280` branch to `construct()` (sizes, vblank/vactive selection). | Build succeeds. No flash yet. |
| **Q4** | Add HSTX/clk_sys overclock path (`vreg_set_voltage(VREG_VOLTAGE_1_30)`, raise PLL_SYS to 372 MHz, configure `clk_hstx`). Conditional on the mode being 1280×720. | Build succeeds. |
| **Q5** | Update `VALID_DISPLAY_SIZES` and `COLOR_DEPTH_LUT` in `frozen/adafruit_fruitjam/adafruit_fruitjam/peripherals.py` (or however 10.x ships it). | Build succeeds. |
| **Q6** | Flash the custom UF2. Existing CP demo continues to work at 320×240 → 640×480 (sanity check that we didn't break anything). | Demo runs. |
| **Q7** | Smoke-test 1280×720 from a tiny script — `request_display_config(1280, 720)` → solid-color fill. Confirm monitor sees the right resolution. | Monitor info: 1280×720@60 Hz. |
| **Q8** | Update the multilingual demo's display config to one of the pixel-tripled modes. | Same demo, more pixels. |

Q1, Q6, Q7, Q8 each need a BOOTSEL flash. Roll back at any point by re-flashing the stock 10.1.4 UF2 — CIRCUITPY filesystem (assets, demo) survives a firmware-only flash.

## Risks

| | Mitigation |
|---|---|
| 1.30 V overclock on a board not designed for it | Start at 1.30 V, monitor for instability. If unhappy, drop back to 1.20 V and a slightly lower clock (would mean 1280×720@30 instead of @60, still ½ the TMDS rate). |
| Custom UF2 doesn't pass RP2350's signed-image check | RP2350 production silicon allows unsigned UF2s when the `OTP_BOOT_*` fuses are unblown. Fruit Jam ships unfused; standard CP UF2s are unsigned-by-policy. We're within the same envelope. |
| Submodule fetch is multi-GB | Use `--depth=1` shallow clone of the right branch (`10.x`). Then fetch only the submodules the RP2350 port actually needs (NOT the per-board files for other ports). |
| Build environment differs from Adafruit's CI | Document the toolchain versions used (arm-none-eabi-gcc, cmake, picotool). Fix any deltas as they surface. |
| Picodvi shift-out chain at 372 MHz HSTX clock might not actually carry pixels at 8 bpp / 16 bpp at 1280 wide | At 16 bpp / 1280 wide, that's 320 KB just for the framebuffer. Need PSRAM allocation; the existing `picodvi` allocator rejects PSRAM addresses (we've seen the check). May need to extend the allocator OR run at 8 bpp paletted (1280×720×1 = 921 KB, also PSRAM-bound). |
| Going back to default voltage after stopping a 1280×720 framebuffer | The `release_displays()` path needs to drop `clk_sys` back and `vreg` back. Not currently done — small added work. |

## Repo layout

The CircuitPython fork lives outside the T-Rex_talker_interactive repo to keep its bulk out of the project tree. Suggested:

```
~/claude/coder/circuitpython_fork/
    circuitpython/                    upstream adafruit/circuitpython, 10.x branch
        ports/raspberrypi/
            boards/adafruit_fruit_jam/
            ...
        shared-module/picodvi/
            Framebuffer_RP2350.c      <-- our patches go here
        ...
    build_notes.md                    quick-reference for build commands
```

The patches themselves should land as a series of small commits on a topic branch in the CP fork (e.g. `fruit-jam-hstx-720p`). When the user is ready, push the topic branch to a personal fork on GitHub and link the resulting URL from here.

## Where the demo points to the new firmware

When Q7 is green, the multilingual demo at `../fruit_jam_dvi/code.py` only needs one change: `request_display_config(320, 240)` → `request_display_config(426, 240)` (or `(1280, 720)` for native). The grid-layout math, asset paths, USB host, audio — all unchanged.
