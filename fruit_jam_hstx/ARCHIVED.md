# `fruit_jam_hstx/` — archived

**Status:** archived 2026-05-10. **Do not build or flash from this directory.**

This directory was an Arduino port attempt for HDMI/HSTX output on the Adafruit Fruit Jam. The goal was a true 1280×720 60 Hz signal with pixel tripling. The attempt ran into a hard wall in P1' — vendoring the Pico-SDK picodvi framebuffer driver into an Arduino sketch (earlephilhower's arduino-pico core) reproducibly broke USB enumeration on the device, and three rounds of host-side analysis + 5 hardware flash cycles didn't find the cause.

The full debug write-up is at [`../fruit_jam_dvi/arduino_720p_P1_DEBUG.md`](../fruit_jam_dvi/arduino_720p_P1_DEBUG.md). It captures: the bisect that proved merely linking `construct()` into the binary breaks USB even when the function never runs; the symbol-diff analysis showing TinyUSB hardware-endpoint veneers shifting between working and failing builds; the three failed fix attempts (`const`-ing the static command-list arrays, dropping `__not_in_flash_func`, removing the explicit `clock_configure` call); and the working theory that USB on arduino-pico's TinyUSB is sensitive to *something* about the picodvi vendor's compiled presence — possibly RAM-bank conflict or PicoTool UF2-packaging shifts.

## Why the project pivoted

The actual goal was always **a 720p HSTX library callable from CircuitPython**, not a from-scratch Arduino rewrite of the multilingual talker. The Arduino path would have meant porting the working CircuitPython demo to C++ — display, USB host, audio, language switcher, the whole thing — for no benefit beyond resolution. The cleaner path is to fork CircuitPython itself, extend the existing `shared-module/picodvi/Framebuffer_RP2350.c` (which is the same source we vendored here) with a 1280×720 mode + the needed HSTX clock setup, build a custom UF2, and let the existing Python demo just call `request_display_config(1280, 720)`.

That work lives at [`../circuitpython_picodvi_720p_PLAN.md`](../circuitpython_picodvi_720p_PLAN.md) (or wherever the new plan ends up).

## What's preserved here for future reference

- `src/hstx_fb/Framebuffer_RP2350.c` — the vendored picodvi driver with our four documented modifications (parameterized height, `const`-ified arrays, `<stdio.h>`/`<string.h>` adds, dropped `__not_in_flash_func`). Same content as CircuitPython's `shared-module/picodvi/Framebuffer_RP2350.c`. Useful comparison point if the CP fork hits similar issues.
- `src/hstx_fb/LICENSE.txt` — preserved MIT terms from the file's own header.
- `src/main.cpp` — minimal Arduino sketch that constructed the framebuffer and filled it with a solid color. Useful demonstration of the API call shape.
- `platformio.ini` — earlephilhower arduino-pico target for `adafruit_fruitjam`. If anyone else wants to retry the Arduino path with `Adafruit-DVI-HSTX` instead, this is the working PlatformIO scaffold.
- `README.md` — original project layout, hardware list, build/flash commands.

## How to come back to this

If the CircuitPython fork hits an unfixable wall and we genuinely need to retry Arduino, start at the debug notes (`../fruit_jam_dvi/arduino_720p_P1_DEBUG.md` §"Recommendation for next session") and try `Adafruit-DVI-HSTX` as the reference driver instead of the picodvi vendor. Coexistence with TinyUSB device + host is documented in Adafruit's `Fruit_Jam_Factory_Test.ino`.
