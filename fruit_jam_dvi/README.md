# Fruit Jam DVI — Multi-Lingual AAC Demo (legacy standalone)

> **Legacy.** This is the original self-contained 8-button language-cycling
> demo (a single `code.py`). It has been **superseded** by the full game:
> the base T-Rex Talker machine booting **T-Rex's Rubber Chicken Challenge**
> (`stim_games/aac_trainer.py`) on the `FRUITJAM_DVI_KBD` variant, which adds
> the timed quiz, per-language pre-rendered screens, sip-n-puff support, and
> SD-hosted content. See the repo **[README.md](../README.md)** ("T-Rex's
> Rubber Chicken Challenge"). This doc is kept for the simple demo, which is
> parked on-device as `code.py.trucc_bak`.

An 8-button AAC board running on the Adafruit Fruit Jam, using the
onboard DVI/HDMI output, USB host keyboard, and TLV320DAC3100 audio.
Cycles through 13 languages (Thai, Japanese, English, Mandarin, Hindi,
Spanish, French, Arabic, Bengali, Portuguese, Russian, Czech, German)
using the language packs already shipped in this repo.

## Hardware

- **Board:** Adafruit Fruit Jam (RP2350B, dual M33 + RISC-V, CircuitPython 10.0+)
- **Display:** any monitor that accepts a 640×480 HDMI signal
- **Input:** USB keyboard plugged into the Fruit Jam's host USB-A port,
  plus the three onboard tactile buttons (BUTTON1, BUTTON2, BUTTON3)
- **Audio:** built-in TLV320DAC3100 + speaker (no external amp needed)

## Layout

```
+--------------------------------------------------+
|                                                  |
|     4 × 2 button grid (cells 80×100)             |   200 px
|     each cell shows an 80×100 Moana icon + 1..8  |
|                                                  |
+--------------------------------------------------+
|  bottom band: native + English language label    |    40 px
+--------------------------------------------------+
```

Total framebuffer: 320×240, auto-doubled to 640×480 HDMI by the firmware.

## Controls

| Input | Action |
|---|---|
| Keyboard 1–8 | Activate cell — full-screen Moana icon + sound in current language; held ≥1.5 s |
| BUTTON1 | Advance the on-screen selection (yellow highlight) to the next cell |
| BUTTON2 | Activate the selected cell (same as pressing its number) |
| BUTTON3 | Next language |
| Tab | Next language |
| Shift-Tab | Previous language |
| F1 | Show 5 s help screen with all 13 languages numbered in their native scripts; current language highlighted |

> **USB keyboard must be plugged in before boot.** The PIO-USB host port
> is brought up once by `boot.py`, which runs only on power-on / hard
> reset — never on a soft reboot (Ctrl-D, auto-reload). A keyboard
> hot-plugged into an already-running board is never enumerated
> (`usb.core.find()` returns 0 devices, the demo logs `kbd=False`
> forever). Plug the keyboard in **first**, then hard-reset. See "Deploying".

## Files

```
fruit_jam_dvi/
    README.md
    code.py                       Demo entry point (auto-runs as code.py)
    boot.py                       USB host port setup (PIO-USB)
    images/moana/icon_<n>.bmp     8 × 80×100 cell icons (cell view)
    images/moana_full/icon_<n>.bmp  8 × 320×240 full-screen icons (press)
```

These icons are scaled-down / scaled-up derivatives of the original
Moana 8-button set (`8_Icons-01.bmp` … `8_Icons-08.bmp`, 131×172 RGB,
licensed under NeedsBoard's terms).

## Deploying

The demo needs the language banners + help screen + 13 language sound
packs that already live in this repo's `out/` directory. Copy everything
to the Fruit Jam's CIRCUITPY drive in this layout:

```
/CIRCUITPY/
    boot.py                       <- fruit_jam_dvi/boot.py
    code.py                       <- fruit_jam_dvi/code.py
    help.bmp                      <- out/help_screen_320x240.bmp
    images/moana/                 <- fruit_jam_dvi/images/moana/
    images/moana_full/            <- fruit_jam_dvi/images/moana_full/
    lang/                         <- out/lang_banners_320x40/
    sounds/<code>/<word>.wav      <- one per (language, word) cell
```

Per-language sound files in this repo live at
`out/button_sounds/languages/<code>/<word>_<native_suffix>.wav`. Strip
the `_<native_suffix>` part of the filename (or the English-only `.wav`
for `en`) so the device sees plain `<word>.wav` paths. The demo expects:

- `<word>` ∈ {`milk`, `water`, `snack`, `play`, `mum`, `yes`, `no`, `thankyou`}
- `<code>` ∈ {`th`, `ja`, `en`, `zh`, `hi`, `es`, `fr`, `ar`, `bn`, `pt`, `ru`, `cs`, `de`}

(One-shot deploy script is left as an exercise — the existing `install.sh`
in this repo can serve as a template.)

After first install, **hard-reset** the Fruit Jam (unplug/replug USB or
press the reset button) so `boot.py` runs and the USB host port comes
up. Subsequent edits to `code.py` auto-reload normally.

Because the USB host port only initializes in `boot.py` at hard reset,
**connect the USB keyboard before that reset** (or press the reset button
after plugging it in). Hot-plugging a keyboard onto a running board does
nothing — the host stack enumerates devices only at startup. From the
REPL, `import microcontroller; microcontroller.reset()` is a full reset
that re-runs `boot.py` (the serial port drops and re-appears within a few
seconds).

## Validation

Hardware-tested 2026-05-09 on Fruit Jam CFC632F82988649F (CircuitPython
10.0.3, `adafruit_fruitjam` 10.x). All 12 language banners render in
their native scripts, all 96 sound files play cleanly through the
TLV320DAC3100 (no MP3-on-direct-I2S distortion the Feather RP2350 path
exhibits — that's a different audio chip story).

Re-deployed 2026-07-04 on the same board (CircuitPython 10.1.4) with the
13th language (German) added: DVI comes up 320x240 -> 640x480, the DAC
initializes, and all 13 languages enumerate at boot. The help-screen line
height dropped 17 -> 16 px so 13 entries fit the 240 px screen. German
verified end-to-end: banner loads and all 8 German WAVs play through the
DAC. USB keyboard confirmed working (number keys play words, Tab cycles
languages) — but only after a hard reset with the keyboard already
attached (see "Deploying").

## Why this is a sub-program

Multi-lingual support is gated by licensing terms on the language packs;
it cannot live in the upstream NeedsBoard repository. The device-side
infrastructure (Fruit Jam DVI variant, USB keyboard input,
TLV320DAC3100 audio, 8-button menu format) lives in NeedsBoard; this
demo composes that infrastructure with the language packs from this
repository to produce a working multi-lingual board.
