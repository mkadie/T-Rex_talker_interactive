# Arduino 720p Port — Plan

**Status:** draft, not started.
**Goal:** rebuild the `fruit_jam_dvi` demo as an Arduino sketch that drives a true **1280×720 60 Hz** HDMI signal on the Fruit Jam, with **pixel tripling** as the default scaling and PSRAM-aware larger framebuffers as opt-in modes.
**Scope:** parity with the working CircuitPython demo at `fruit_jam_dvi/code.py` — 8-button grid, multilingual sub-program, Moana icons, USB HID keyboard, audio (TLV320DAC3100 with speaker/headphone auto-route), F1 help, Tab/Space hotkeys.
**Reversion:** the CircuitPython demo stays untouched throughout. The Arduino build lives in a sibling `fruit_jam_dvi_arduino/` tree. If the port stalls, we keep the working CP path; nothing on the device gets bricked because the Arduino UF2 and CP UF2 are interchangeable via BOOTSEL.

---

## 1 — Findings that shape the plan

Researched 2026-05-09. Three things are non-obvious and steered the design:

1. **Adafruit's `Adafruit-DVI-HSTX` Arduino library does NOT expose a 1280×720 framebuffer.** Its enum tops out at logical 720×400 / 640×480, automatically doubled into a 720×400 / 640×480 raster. The "1280×720 HSTX" announced on the Adafruit blog is the *unbuffered text mode only* (scanlines generated on the fly, no pixels you can write).
2. **The real 1280×720 with arbitrary integer scaling** lives in [fruitjam-doom/Framebuffer_RP2350.c](https://github.com/adafruit/fruitjam-doom/blob/adafruit-fruitjam/Framebuffer_RP2350.c). Adafruit bypassed their own library to do it. That file already implements an `output_scaling` parameter for pixel doubling/tripling, and supports RGB888 / RGB565 / RGB332. **It is the reference HSTX driver for this port.**
3. **Mike Bell's `dvhstx`** is Pimoroni-PicoGraphics-flavored, Pico-SDK / MicroPython-oriented — not Arduino-ready. Porting it would be at least as much work as adopting `Framebuffer_RP2350.c`. Going with the Doom driver.

Other confirmed facts:

- Arduino core: **earlephilhower's `arduino-pico`** (board: "Adafruit Fruit Jam"). Not Adafruit's TinyUSB fork.
- Audio: **Adafruit_TLV320DAC3100** (I²C control + I²S out) coexists with HSTX in the factory test sketch.
- USB host: **Adafruit TinyUSB** + **sekigon-gonnoc Pico PIO-USB**. Documented pattern is pin USB host work to **core1** while HSTX DMA runs on **core0**.
- Auto-overclock: HSTX libraries push the RP2350 to 264 MHz on init; expected and supported.
- PSRAM: 8 MB QSPI on the Fruit Jam (we've seen ~8 MB free in CP). Plenty for any framebuffer config.

## 2 — Display mode design

**Default:** **320×240 logical → ×3 pixel triple → 960×720** drawn into a 1280×720 raster, **horizontally centered with 160 px black pillarbox on each side**. 320 × 240 × 16 bpp = **154 KB framebuffer** — comfortably in internal SRAM.

We chose 320×240 over 426×240 because it lets us **reuse every existing asset from the CircuitPython demo unchanged** — same 320×240 background, 80×100 cell icons, 320×40 language banners, 320×240 help screen — just rendered 3× larger on a much bigger screen. The pillarbox is a small visual cost; the asset reuse is huge.

| Mode | Logical fb | Scale | On-screen pixels | bpp | RAM | Where |
|---|---|---|---|---|---|---|
| **default (DEMO_MODE_TRIPLED_320)** | 320 × 240 | 3× | 960×720 (160 px pillarbox L+R) | 16 | 154 KB | SRAM-OK |
| balanced | 640 × 360 | 2× | 1280×720 | 16 | 460 KB | SRAM-OK |
| native | 1280 × 720 | 1× | 1280×720 | 8 (paletted) | 921 KB | PSRAM |
| native | 1280 × 720 | 1× | 1280×720 | 16 | 1.84 MB | PSRAM |

PSRAM detection happens at `setup()` time. If PSRAM init succeeds and a config flag picks a larger mode, allocate from PSRAM; otherwise stay at default 3× from SRAM.

User-facing config (compile-time `#define` initially, runtime `config.txt` later):

```cpp
// fruit_jam_dvi.ino
#define DEMO_MODE_TRIPLED_426    1   // default
// #define DEMO_MODE_DOUBLED_640   1
// #define DEMO_MODE_NATIVE_8BPP   1
// #define DEMO_MODE_NATIVE_16BPP  1
```

## 3 — Project layout

A new sibling tree, kept entirely separate from the CP demo:

```
fruit_jam_hstx/
    README.md                 deploy + build instructions
    fruit_jam_hstx.ino        main sketch
    platformio.ini            PlatformIO config (preferred over Arduino IDE)
    src/
        hstx_fb/              vendored fruitjam-doom HSTX driver (GPL-2)
            LICENSE.txt       fruitjam-doom's GPL-2 license, preserved
            Framebuffer_RP2350.cpp/.h
            (any deps it pulls in, e.g. dvi.h, dvi_serialiser, etc.)
        audio.cpp/.h          TLV320DAC3100 wrapper + WAV player
        kbd.cpp/.h            USB host HID boot keyboard polling (core1)
        ui.cpp/.h             grid rendering, language banner, help screen
        lang.cpp/.h           LANGUAGES table + asset-path resolution
        bmp.cpp/.h            BMP loader (file -> RGB565 buffer)
        fs.cpp/.h             LittleFS-first / SD-fallback path resolver
    data/                     content shipped with the sketch (LittleFS image)
        lang/lang_<code>.bmp
        images/moana/icon_<n>.bmp
        images/moana_full/icon_<n>.bmp
        sounds/<code>/<word>.wav   (only the languages that fit in flash)
        help.bmp
    tools/
        gen_assets.py         emits scaled assets from sources (no-op for
                              default 320×240 mode, real work for 1280×720)
        build_littlefs.sh     pack data/ into a LittleFS image; sized to
                              the platformio.ini partition layout
```

`src/hstx_fb/` keeps its own `LICENSE.txt` (GPL-2) so the vendored Doom code's terms are clearly preserved without polluting the rest of the project.

### Attribution requirements (applies to every vendored file)

Every file copied or adapted from another project must carry attribution. This is a hard rule, not a "best effort":

1. **In each source file's header comment**, include:
   - Original project name
   - Upstream URL (GitHub repo / specific file path on the default branch)
   - Original copyright + license identifier (SPDX, e.g. `SPDX-License-Identifier: GPL-2.0-only`)
   - Note any modifications we made

   Example header for `src/hstx_fb/Framebuffer_RP2350.cpp`:
   ```cpp
   // Vendored from: https://github.com/adafruit/fruitjam-doom
   //   blob: adafruit-fruitjam/Framebuffer_RP2350.c
   // Original copyright: (c) 2024 Adafruit / contributors
   // SPDX-License-Identifier: GPL-2.0-only
   //
   // Modifications in this copy:
   //   - 2026-05-09: ported from .c -> .cpp for Arduino sketch use
   //   - 2026-05-09: added DEMO_MODE_TRIPLED_320 path with explicit
   //                 horizontal pillarbox at output_scaling=3
   ```
2. **In `fruit_jam_hstx/README.md`** under a "Third-party code" / "Attributions" section, list every vendored library with the same fields plus a one-line description of what we use it for.
3. **In each LittleFS-shipped asset that's derived from a third-party source** (e.g. the Moana icons), the README also notes the source.

If a phase-N commit adds vendored code without these comments, that's a defect — fix it in the same phase before moving on.

PlatformIO over Arduino IDE: command-line build, reproducible env, cleaner library version pinning. Board: `adafruit_fruitjam`, framework: `arduino`, platform: `https://github.com/maxgerhardt/platform-raspberrypi.git` (earlephilhower core).

**Filesystem strategy: LittleFS first, SD fallback.**

`src/fs.cpp` resolves an asset path by trying LittleFS (`/littlefs/<path>`) first, then falling back to SD (`/sd/<path>`). Core assets ship in the LittleFS image baked into the UF2 (or post-flashed via PlatformIO's `uploadfs` target):

- `lang/lang_<code>.bmp` (~456 KB total)
- `images/moana/icon_<n>.bmp` (~192 KB total)
- `images/moana_full/icon_<n>.bmp` (~1.8 MB total)
- `help.bmp` (230 KB)
- `sounds/th/*.wav` + `sounds/en/*.wav` (~600 KB)

That's ~3.3 MB; we'll allocate a 4 MB LittleFS partition. Remaining 10 languages (~2.4 MB) go on SD when present. If no SD: only Thai+English work; other languages show "sound missing" and gracefully skip playback.

## 4 — Phased rollout

Each phase is its own commit. Test on hardware before the next phase. If a phase blocks for >2 hours of debug, **stop and reassess** rather than push through.

| Phase | Deliverable | Acceptance test |
|---|---|---|
| **P0** | Toolchain set up + blank sketch builds + flashes + boots | Serial prints "hello" |
| **P1** | HSTX 720p with the Doom framebuffer driver, 426×240 ×3, fills with one solid color | Monitor shows 1280×720 single-color screen |
| **P2** | BMP loader + show one Moana icon centered | Monitor shows the icon at the correct on-screen size |
| **P3** | Static 4×2 grid: cell rectangles + icons + numbers | Grid matches CP demo's layout, just bigger |
| **P4** | TLV320DAC3100 init + play one WAV from flash | Test sound plays through speaker |
| **P5** | USB HID keyboard on core1 + map keys 1–8 to grid actions | Press 1, hear sound 1; full-screen icon overlay |
| **P6** | Bottom 40-px language banner load (then 60 px scaled to ≥720p? math TBD) | Banner BMP shows correctly at the bottom |
| **P7** | Tab cycles language, F1 shows help screen, Space toggles speaker/headphone | Same UX as CP demo |
| **P8** | Headphone-jack auto-route (poll dac headset_status, debounce, swap with level restore) | Plug/unplug → route swaps |
| **P9** | Optional: PSRAM-aware mode selector (compile-time first, then config-driven) | Recompile with different `DEMO_MODE_*` flag → different framebuffer; visual differs predictably |

P0–P5 is the riskiest stretch. P6–P9 is mostly applying the CP demo's logic to a working Arduino harness.

## 5 — Asset compatibility

Default mode (320×240 ×3) **reuses all existing CP-demo assets unchanged**. The framebuffer is the same 320×240 logical canvas; only the on-screen pixel size is 3× bigger. No re-rendering work for default mode.

Re-rendering is only needed if/when we enable the larger-framebuffer modes:

| Asset | Default (320×240) | Balanced (640×360) | Native (1280×720) |
|---|---|---|---|
| Cell icon | 80×100 (reuse) | 160×160 | 320×320 |
| Full-screen icon | 320×240 (reuse) | 640×360 | 1280×720 |
| Language banner | 320×40 (reuse) | 640×60 | 1280×120 |
| Help screen | 320×240 (reuse) | 640×360 | 1280×720 |

Sounds (WAV, 12 languages × 8 words) reusable as-is from `out/button_sounds/languages/<code>/`.

`tools/gen_assets.py` will be a no-op for default mode and emit the larger sizes when invoked with `--mode balanced` / `--mode native_720p`. Sources stay in NeedsBoard's `original_icons/moana/` (8_Icons-01..08, 131×172 RGB).

## 6 — Risks & open questions

| Risk | Mitigation |
|---|---|
| HSTX + USB-host PIO + I²S DMA all contend for the same DMA channels | Use the Doom code's DMA layout as known-good; pin USB host to core1, HSTX to core0 |
| 264 MHz overclock + audio at the same time may cause jitter | Test early in P4; fall back to a lower HSTX rate if needed |
| Arduino-side text rendering for the bottom band English label | Adafruit_GFX is fine for Latin; for Thai/Chinese/etc. we keep the **pre-rendered banner BMPs** as in the CP demo |
| Build environment fragility (Arduino-pico version pinning) | Capture exact versions in `platformio.ini`; commit a `.tool-versions` |
| LittleFS partition collision with sketch flash | Pick the partition layout in `platformio.ini` early (P0); document it in README |
| Forgetting attribution on vendored code | Per-phase checklist item: any new vendored file must have the header in §3.x AND a `README.md` Attributions row in the same commit |
| SD-not-present at boot | `fs.cpp` falls back gracefully; non-flash languages just show "sound missing" without crashing |
| Bricking risk during P0 firmware flash | None — RP2350 has BOOTSEL; worst case re-flash CircuitPython UF2 |

## 7 — Decisions locked

All four pre-P0 questions resolved 2026-05-09:

- **Default framebuffer:** 320×240 logical → ×3 pixel triple → 960×720 on-screen with 160 px pillarbox each side. Reuses every existing CP-demo asset unchanged.
- **Filesystem:** LittleFS first (4 MB partition for core assets + Thai/English sounds), SD fallback for the other 10 languages. Resolver in `src/fs.cpp`.
- **License:** vendor `fruitjam-doom`'s HSTX driver into `src/hstx_fb/` with its GPL-2 `LICENSE.txt` preserved alongside it. The rest of the sketch keeps T-Rex_talker_interactive's license.
- **Directory name:** `fruit_jam_hstx/` (sibling of the CircuitPython `fruit_jam_dvi/`).

## 8 — Reversion strategy

The Arduino port is **purely additive** to both repos until it's working:

- NeedsBoard: untouched. The CP audio/display infrastructure stays where it is.
- T-Rex_talker_interactive: new `fruit_jam_hstx/` directory. The existing `fruit_jam_dvi/` (CircuitPython) keeps running.

To revert mid-port: stop committing to `fruit_jam_hstx/`; the CP demo on the device still works. To revert post-flash: drag the CircuitPython UF2 onto BOOTSEL, the device is back to the CP demo (assets persist on CIRCUITPY).

---

**Recommended next step:** start at P0 — set up PlatformIO, board target `adafruit_fruitjam`, blank sketch builds and flashes.
