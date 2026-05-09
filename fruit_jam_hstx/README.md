# Fruit Jam HSTX 720p Demo (Arduino)

Arduino C++ port of the multi-lingual AAC demo, targeting **true 1280×720 60 Hz HDMI** output via the RP2350's HSTX peripheral. Replaces the CircuitPython demo at [`../fruit_jam_dvi/`](../fruit_jam_dvi/), which is capped at 720×400 by CircuitPython's built-in `picodvi` module.

See [`../fruit_jam_dvi/arduino_720p_PLAN.md`](../fruit_jam_dvi/arduino_720p_PLAN.md) for the full design and phased rollout (P0..P9). The CircuitPython demo stays available throughout; this Arduino sketch is purely additive.

## Status

| Phase | Done? | Description |
|---|---|---|
| **P0** | ✅ | PlatformIO toolchain + blank sketch builds + flashes + boots with serial heartbeat |
| **P1'** | ✅ (build) | HSTX framebuffer at 320×240 ×2 (640×480 raster — vendored driver's ceiling). Solid color test. Hardware-validated: pending. |
| P1.5 |  | Add 1280×720@60 (CEA VIC 4) timing constants + command lists to `src/hstx_fb/Framebuffer_RP2350.c`. Switches the default to 320×240 ×3 = 960×720 with 160 px pillarbox each side. |
| P2 |  | BMP loader + show one Moana icon centered |
| P3 |  | Static 4×2 grid (cells + icons + numbers) |
| P4 |  | TLV320DAC3100 init + WAV playback |
| P5 |  | USB HID keyboard on core1, keys 1–8 → cell actions |
| P6 |  | Bottom 40-px language banner |
| P7 |  | Tab cycle, F1 help screen, Space speaker/headphone toggle |
| P8 |  | 3.5 mm jack auto-route with debounce + level restore |
| P9 |  | Optional PSRAM-aware larger framebuffer modes |

## Hardware

- Adafruit Fruit Jam (RP2350B, 8 MB QSPI PSRAM, HSTX DVI, TLV320DAC3100 audio)
- HDMI display that accepts 1280×720 60 Hz
- USB keyboard plugged into the host USB-A port (P5+)
- Optional 3.5 mm headphone or amplified speaker on the jack (P8)

## Build

Requires [PlatformIO Core](https://platformio.org/install/cli) ≥ 6.1.

```sh
cd fruit_jam_hstx
pio run
```

Build output: `.pio/build/adafruit_fruitjam/firmware.uf2`.

## Flash

1. Hold the **BOOTSEL** button on the Fruit Jam, then press reset (or unplug/replug USB).
2. The device mounts as `RPI-RP2` on the host.
3. Drag `firmware.uf2` onto that drive — the Fruit Jam reboots into Arduino.

> **Reverting to CircuitPython:** download the matching CircuitPython UF2 for the Fruit Jam from circuitpython.org and flash it the same way. The CIRCUITPY drive contents are stored in a separate region; back up `/code.py`, `/boot.py`, `/lang/`, `/images/`, `/sounds/`, `/help.bmp` before flashing Arduino if you want a no-redeploy rollback.

## Monitor

```sh
pio device monitor
```

Should print `[fruit_jam_hstx] P0 hello, t=N s` once per second.

## Layout (post-P0)

```
fruit_jam_hstx/
    README.md             this file
    platformio.ini        PlatformIO config (board: adafruit_fruitjam)
    src/
        main.cpp          P0: heartbeat. P1+: pulls in modules below.
        hstx_fb/          P1: vendored HSTX framebuffer driver (P1+)
            LICENSE.txt   GPL-2 (preserved from upstream)
            ...
        audio.cpp/.h      P4: TLV320DAC3100 wrapper
        kbd.cpp/.h        P5: USB host HID polling
        ui.cpp/.h         P3+: grid, banner, help screen
        lang.cpp/.h       P6+: LANGUAGES table
        bmp.cpp/.h        P2+: BMP loader
        fs.cpp/.h         P6+: LittleFS-first / SD-fallback
    data/                 LittleFS image (P6+)
    tools/                asset generators (P6+)
```

## Third-party code

| Component | Upstream | License | Used for |
|---|---|---|---|
| `src/hstx_fb/Framebuffer_RP2350.c` | [adafruit/fruitjam-doom @ adafruit-fruitjam](https://github.com/adafruit/fruitjam-doom/blob/adafruit-fruitjam/Framebuffer_RP2350.c) (originally from MicroPython) | MIT (per the file's own header — not GPL-2 like the rest of fruitjam-doom). Full text in `src/hstx_fb/LICENSE.txt`. | HSTX DVI/HDMI framebuffer driver — drives the RP2350's HSTX peripheral with a software framebuffer. Two local modifications, all flagged with `// MODIFIED 2026-05-09:` in the source. See `src/hstx_fb/README.md` for the diff summary. |

Per the project's attribution rule (see `../fruit_jam_dvi/arduino_720p_PLAN.md` §3 "Attribution requirements"), every vendored file gets a header comment with its upstream URL and license **and** a row in this table describing what it's used for.
