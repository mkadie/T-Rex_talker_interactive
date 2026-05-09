# P1' debug — vendored Doom HSTX framebuffer breaks USB on Arduino

**Status:** open, blocked, paused 2026-05-09.
**Symptom:** with the vendored `src/hstx_fb/Framebuffer_RP2350.c` linked into the Arduino sketch in any way that keeps `common_hal_picodvi_framebuffer_construct` reachable, the Fruit Jam **does not enumerate as a USB device** after flashing the UF2 — no `/dev/ttyACM*`, nothing in `lsusb` for VID `0x2e8a` or `0x239a`.
**Recovery:** BOOTSEL → flash CircuitPython UF2 → CIRCUITPY filesystem persists → CP demo runs again. Verified twice.

## What we tried

| # | Variant | Result |
|---|---|---|
| **A** | Bare P0 sketch, no HSTX. | USB CDC up, heartbeat at 1 Hz. |
| **B** | P1' with construct() called from setup(). | USB never enumerates. |
| **C** | `HSTX_CONSTRUCT_ENABLED 0` — `.c` file linked, but `construct()` is dead-code-eliminated by the linker because nothing references it from main. | USB CDC up, "no HSTX" heartbeat at 1 Hz. |
| **D** | `HSTX_CONSTRUCT_ENABLED 1`, but call deferred to `t ≥ 5 s` (USB has 5 s to fully enumerate before HSTX init). | USB never enumerates. |
| **E** | `HSTX_CONSTRUCT_ENABLED 1` *and* `HSTX_CONSTRUCT_RUN 0` — function reachable via a `volatile auto _keep = &try_init_hstx;` reference but never actually called. | USB never enumerates. |

### What that tells us

- (A) vs (B): something the `construct()` runtime path does kills USB.
- (C) vs (D)/(E): just having the function compiled and present in the binary is enough to break USB — the call doesn't have to actually run. (C) only worked because the linker DCE'd `construct()` away once nothing referenced it.

So the bug is *not* "construct runs and disturbs USB". It's "merely linking a binary that contains construct's compiled code in flash makes the device fail to enumerate."

## Hypotheses ranked by likelihood

1. **`__not_in_flash_func(dma_irq_handler)`** — the file places this function in RAM via an attribute. The earlephilhower arduino-pico boot code copies these from flash to RAM at startup. If that copy region overlaps with something USB needs (USB-stack RAM buffers, .bss for TinyUSB), boot-time corruption could prevent USB init.
2. **Static-initialized arrays in `.data`** — `vblank_line640_*`, `vactive_line640`, `vblank_line720_*`, `vactive_line720` are large static-but-non-const arrays. In RP2350 ARM startup code, these are copied from flash to RAM. Same overlap concern as #1.
3. **Bus-priority register** — `bus_ctrl_hw->priority = BUSCTRL_BUS_PRIORITY_DMA_W_BITS | BUSCTRL_BUS_PRIORITY_DMA_R_BITS;` only runs inside `construct()`, so this wouldn't explain (E). But it's worth noting if we get to a runtime-failure case later.
4. **Section-attribute conflict** — earlephilhower's linker script may not know about the `__not_in_flash_func` attribute used by the Pico SDK. If sections collide silently, the binary could lay out incorrectly.
5. **Boot signature / metadata** — RP2350 boots a signed UF2. If the signed-image generation does anything with the linked code that the vendored file disturbs, the device could refuse to boot the Arduino payload at all and we just don't see the "device boots into BOOTSEL" recovery path because the device IS booting but USB never comes up.

## Next steps to try (host-side first)

These don't need a flash cycle and may pinpoint the issue:

1. **Diff the .map files** of (C) vs (E). What sections / addresses change? Look specifically at `.data`, `.bss`, `.ramfunc`, and any sections related to USB / TinyUSB.
2. **`objdump -h`** on both ELFs — what sections are in the binary, what are their VMAs/LMAs?
3. **Check the linker script** that earlephilhower's arduino-pico uses for `adafruit_fruitjam`. Look for whether `__not_in_flash_func` (which expands to `__attribute__((section(".time_critical")))` or similar in Pico SDK) has a corresponding output section. If not, the linker may silently put it in `.text` (flash), wasting the attribute *or* worse, into `.data` where it shouldn't be.
4. **Try replacing `__not_in_flash_func(name)` with plain `name`** in the vendored file. If that fixes it, hypothesis #1 is correct.
5. **Make the static command-list arrays `const`**. They never get written to (we just take their addresses for DMA). Marking const places them in `.rodata` (flash) — eliminates the .data copy at boot. Tests hypothesis #2.

## Next steps requiring a flash cycle

Only after the host-side analysis, in priority order:

1. **Try (5) above** — `const`-ify the static arrays. Likely the smallest safe change.
2. **Try (4) above** — strip `__not_in_flash_func`. Slightly slower IRQ handler but acceptable for debug.
3. **Replace the construct() body with a one-line stub that calls a single Pico SDK function** (e.g. `clock_get_hz(clk_sys)`). If THAT breaks USB, the issue is broader than this file.
4. **Switch reference driver**: vendor `Adafruit_dvhstx` instead, which is documented to coexist with USB host in Adafruit's factory test sketch. Different API; less control over output_scaling, but a known-good integration baseline.

## Recovery procedure (works)

If a flash leaves the device unenumerable:

1. Unplug USB completely.
2. Hold the **BOOT** button on the Fruit Jam.
3. Plug USB back in while still holding BOOT.
4. Release BOOT once a `RP2350` drive mounts on the host.
5. Drag `adafruit-circuitpython-adafruit_fruit_jam-en_US-10.1.4.uf2` onto it (or a known-good Arduino UF2 like P0's).
6. Device reboots. CIRCUITPY filesystem persists across this; assets (`/code.py`, `/lang/`, `/images/`, `/sounds/`, `/help.bmp`) are intact.

A backup of the CIRCUITPY contents (without `lib/`) lives on the host at
`~/claude/coder/FruitJam/circuitpy_backup_2026-05-09/` for additional safety.

## Where the work is committed

- `0d9d6dc` — P0 toolchain skeleton + heartbeat sketch (works on hardware).
- `3ac3dc2` — P1' attempt: vendored Doom framebuffer + main.cpp call (fails on hardware as documented above).
- (further bisect builds were not committed; main.cpp was rewritten in place between flash attempts.)

When P1' resumes, start from `3ac3dc2` and apply one of the host-side fixes above as a fresh commit.
