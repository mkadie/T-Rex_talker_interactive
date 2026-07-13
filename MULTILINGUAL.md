# T-Rex Talker — Multi-Lingual Language Pack System

Documentation for the multi-lingual language switching feature, including
sound/menu/image generation pipelines and deployment.

> **Scope.** This document covers the **encoder language picker**
> (`stim_games/multi_lingual.py`): an 8-word runtime picker that swaps the
> device's active language, with 1-bit banner images and per-language menus.
>
> The **T-Rex's Rubber Chicken Challenge** game localizes differently — it
> uses a 14-word game vocabulary, full-colour **per-language screens**
> pre-rendered on the host, and SD-hosted audio, driven by
> `tools/generate_screens.py` and `tools/generate_game_i18n.py`. See the
> repo [README.md](./README.md). Both pipelines share the `LANGUAGES` table
> in `tools/generate_language_sounds.py`.

---

## Overview

The language pack switcher allows the user to change the device's active
language at runtime using the rotary encoder. It supports 13 languages:

| Code | Language   | Script        |
|------|------------|---------------|
| th   | Thai       | Thai (default)|
| ja   | Japanese   | Hiragana      |
| en   | English    | Latin         |
| zh   | Mandarin   | Simplified Chinese |
| hi   | Hindi      | Devanagari    |
| es   | Spanish    | Latin         |
| fr   | French     | Latin         |
| ar   | Arabic     | Arabic        |
| bn   | Bengali    | Bengali       |
| pt   | Portuguese | Latin         |
| ru   | Russian    | Cyrillic      |
| cs   | Czech      | Latin         |
| de   | German     | Latin         |

The encoder scrolls through languages, displaying a full-screen 1-bit BMP
image (320x240) showing the language name in both English and native script.
Press the encoder to select. A 10-second timeout reverts to the previous
language. The selection does not persist across reboots.

---

## How It Works

1. **Language images** are stored on flash under `lang_images/`
   (1-bit BMP, 320x240, ~10KB each for all 13 languages).
2. **Language sounds** (WAV 16kHz 16-bit mono) are stored on the SD card
   under `sd/button_sounds/languages/<lang_code>/` (~3MB for 104 files).
3. **Language menus** (`lang_<code>.menu`) define the button layout and
   sound mappings for each language.
4. When the user selects a language, the device loads the corresponding
   `.menu` file and switches the active sound directory.

### Why WAV, not MP3?

MP3 decoding via `audiomp3.MP3Decoder` + `audiobusio.I2SOut` produces
distorted audio on the Feather RP2350 (direct I2S, no codec). WAV files
play perfectly. This is a known CircuitPython bug on RP2350.

### Configuration

In `hardware_config.py`, the FEATHER_RP2350_V1 variant sets:
```python
language_switcher_enabled = true
```
Currently only supported on this variant.

---

## Sound Generation Pipeline

**Tool:** `tools/generate_language_sounds.py`

**Pipeline:** Text -> gTTS (Google Text-to-Speech) -> MP3 -> ffmpeg -> WAV

1. For each language and each vocabulary word, gTTS generates an MP3.
2. ffmpeg converts to WAV 16kHz 16-bit mono with clean headers (no LIST
   chunks or metadata that confuses CircuitPython's WAV parser).
3. Output goes to `out/button_sounds/languages/<lang_code>/`.

**ffmpeg command used:**
```bash
ffmpeg -i input.mp3 -ar 16000 -ac 1 -sample_fmt s16 -fflags +bitexact -flags:a +bitexact output.wav
```

The `-fflags +bitexact -flags:a +bitexact` flags ensure clean WAV headers
without LIST chunks.

**Dependencies:** `pip install gTTS`, plus `ffmpeg` on the system PATH.

---

## Menu Generation Pipeline

**Tool:** `tools/generate_language_menus.py`

Generates one `lang_<code>.menu` file per language. Each menu maps button
positions to the corresponding language sound files on the SD card. The
menu format is the standard INI-style `.menu` used by the AAC software.

Output goes to `out/menus/`.

---

## Image Generation

**Tool:** `tools/generate_language_images.py`

Language selection banners are generated using PIL/Pillow with Google Noto
Sans fonts to support all writing systems. The generator reads the same
`LANGUAGES` table as the sound generator, and **skips images that already
exist** (pass `--force` to regenerate). It picks a font per writing system:

- **NotoSans-Bold** for Latin, Cyrillic scripts (English, Spanish, French,
  Portuguese, Czech, German, Russian)
- **NotoSansThai-Bold** for Thai
- **NotoSansCJK-Bold** for Japanese and Simplified Chinese
- **NotoSansArabic-Bold** for Arabic
- **NotoSansDevanagari-Bold** for Hindi
- **NotoSansBengali-Bold** for Bengali

Each image is 320x240, 1-bit (black and white), showing the language name
in English on one line and the native script name below it. The generator
auto-fits text size to avoid overflow (relevant for longer names like
Portuguese).

Output goes to `out/lang_images/`.

---

## How to Add a New Language

1. Add the language code, gTTS code, English name, native name, and word
   table to the `LANGUAGES` list in `tools/generate_language_sounds.py`.
   The menu and image generators both import this table, so they need no
   separate edit — unless the native script needs a new font, in which
   case add it to `SCRIPT_FONTS` in `tools/generate_language_images.py`.
2. Add the same entry to the `LANGUAGES` tuple in the device picker,
   `stim_games/multi_lingual.py`, so the encoder can scroll to it.
3. Run all three generators:
   ```bash
   python tools/generate_language_sounds.py
   python tools/generate_language_menus.py
   python tools/generate_language_images.py
   ```
4. Convert the generated MP3s to WAV (see the ffmpeg command above) and
   deploy the new files to the device (see below).

---

## How to Regenerate All Files

From the `T-Rex_talker_interactive` directory:

```bash
# Generate all language sounds (requires internet for gTTS)
python tools/generate_language_sounds.py

# Generate all language menus
python tools/generate_language_menus.py

# Generate language selection banner images
python tools/generate_language_images.py
```

Output lands in `out/button_sounds/languages/`, `out/menus/`, and
`out/lang_images/` respectively.

---

## Deployment to Device via move_to_sd

Language WAV files (~3MB) are too large for the flash filesystem. Use the
`move_to_sd` staging mechanism:

1. Connect the device via USB (CIRCUITPY drive appears).
2. Copy a batch of language WAV directories to:
   `CIRCUITPY/move_to_sd/button_sounds/languages/`
3. Safely eject and reboot. The device auto-copies files from
   `move_to_sd/` to `/sd/` on boot, preserving directory structure.
4. Reconnect and delete the `move_to_sd/` directory from flash.
5. If all languages don't fit in one batch (limited flash space), repeat
   steps 2-4 with additional batches.

Language images (~156KB total for 13 banners) fit directly on flash:
- Copy `lang_*.bmp` to `CIRCUITPY/lang_images/`

Language menu files go directly on flash:
- Copy `lang_*.menu` files to `CIRCUITPY/menus/`

---

## Subprogram Installation Strategy

The multi-lingual feature highlights a broader challenge: not all content
fits on every device. The current deployment copies everything, but devices
with limited flash need selective installation. See the "Subprogram
marketplace/selector" item in `T-Rex_Talker_Subprogram.md` section 12 for
the planned approach to manifest-based selective installation.

---

## Known Issues and Fixes

- **Thai font**: Must use NotoSansThai-Bold specifically (not the generic
  NotoSans which lacks Thai glyphs).
- **Portuguese text overflow**: The image generator auto-fits font size to
  prevent long language names from overflowing the 320px width.
- **Language image flashing after selection**: Fixed by resetting
  `_lang_timeout` and encoder position immediately on selection, preventing
  the display loop from briefly re-showing the language picker.
- **WAV LIST chunks**: gTTS + default ffmpeg output includes LIST metadata
  chunks that crash CircuitPython's WAV parser. Use `-fflags +bitexact`
  flags to produce clean headers.
