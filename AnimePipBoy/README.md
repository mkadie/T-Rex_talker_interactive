# AnimePipBoy

A variation of the Fruit Jam MVP talker (`FRUITJAM_CLONE_18`, 160×128
ST7735R + rotary encoder) with an **English ⇄ Japanese** toggle. Built on
board `62AB3604F4D0B8E6`.

## What's different from the stock MVP

| Cell | Stock | AnimePipBoy |
|------|-------|-------------|
| 4 | Bathroom | **How much for that?** ($ tile) |
| 5 | Play | **Swap Language** (speech-bubble "A あ" tile) |

- **Swap Language** flips the whole board between English
  (`base_fruitjam.menu`) and Japanese (`base_fruitjam_ja.menu`, with its own
  `food_fruitjam_ja.menu`), then announces "English" / "日本語". Same
  tiles in both; only the audio changes. Labels stay English because the
  on-screen font has no Japanese glyphs. The board always boots in English.
- **Screen flipped 180°**: `display_rotation = 270` in `config.txt` (the
  variant default is 90). `config_reader.py` here allows that key.
- **Faster screen** (`display_manager.py`): menu boards are cached in RAM
  after first use (full paint 0.93 s → 0.14 s), and the redundant repaints
  are skipped. Food/Drink in/out went from ~2.3 s to ~0.35 s. Benchmark:
  `BENCHMARK.md`, script `tools/bench_pipboy.py`.
- **Faster wake** (`display_manager.py`, `sleep_manager.py`,
  `machine.py`, `st7735_fast_init = true` in `config.txt`): picture back in
  ~0.62 s (was 1.27 s), presses work in ~0.68 s (was 2.27 s).
- **No delay or hiss between words** (`audio_player.py`,
  `amp_soft_idle = true` in `config.txt`): the speaker is switched off as soon
  as a word ends and back on in ~36 ms, instead of a 0.64 s codec reprogram
  after every quiet spell.
- `action.py` here adds `subprogram = …` menu items (the board's older
  `action.py` couldn't launch a subprogram from a menu).

## Layout

This folder mirrors the CIRCUITPY drive root — copy it over a working MVP
install (keeps everything not listed here):

```
code.py                            auto-reload off; USB-host 5 V held off
config.txt                         per-device settings (rotation 270)
config_reader.py, action.py        patched base files (see above)
display_manager.py                 board backgrounds cached in RAM; no
                                   repaint when nothing changed; fast
                                   ST7735R init (BENCHMARK.md)
sleep_manager.py                   20 ms wake poll; CPU at 24 MHz while asleep
audio_player.py                    soft amp idle: outputs off after each
                                   sound instead of a codec reset
machine.py                         wake: release gate instead of 1 s grace;
                                   no codec reprogram while amp is in reset
stim_games/lang_toggle.py          the toggle subprogram
menus/base_fruitjam.menu           English base (cells 4, 5 changed)
menus/base_fruitjam_ja.menu        Japanese base
menus/food_fruitjam_ja.menu        Japanese food & drink
menus/images/base/                 howmuch.bmp, swaplang.bmp, base_board.bmp
button_sounds/                     how_much_for_that, lang_en, ja/*
```

```
rsync -rt --exclude README.md AnimePipBoy/ /media/$USER/CIRCUITPY/
```

Auto-reload is **off** on this board (`code.py`): a computer writing to
CIRCUITPY, even a metadata touch, used to restart the talker mid-use. Copying
files therefore does nothing until you reset. Hard-reset the board
(`import microcontroller; microcontroller.reset()` from the REPL) — a soft reload leaves `/sd` unreadable on the Fruit Jam.

## Regenerating assets

- Tiles: `python3 tools/make_animepipboy_icons.py <menus/images/base dir>`
  (draws the two tiles and patches them into `base_board.bmp`; run it
  against the *stock* images, since it reads the old cell-4/5 tiles to keep
  the grid lines).
- Audio: `python3 tools/make_animepipboy_sounds.py <drive root>` (gTTS +
  ffmpeg, re-encoded to 44.1 kHz mono 64 kbps MP3 to match the board).

## Firmware

**CircuitPython 11.0.0-alpha.2** (flashed 2026-10-25, was 10.1.4) with the
11.x library bundle (`20261023`). 11.x is the first release with the
`alarm` module on the RP2350, which true sleep needs. The talker,
benchmarks and wake all checked out on it. To go back:
`fruitjam_backups/firmware/uf2/…-10.1.4.uf2` plus the drive backup
`CIRCUITPY_62AB3604_2026-10-25_pre_cp11`. (With 10.x the code falls back to
the polling sleep below on its own.)

## Power and sleep (checked on the device 2026-10-25)

Sleep starts after `sleep_timeout` (120 s) of no input, and **only on
battery**: sleep is suspended while USB is connected, unless `sleep_on_usb`
is set.

**True sleep on battery** (`sleep_true_on_battery = true`): after powering
everything down, the board **light-sleeps** with a pin alarm on each
`sleep_wake_pins` pin (here the encoder press, BUTTON1). The CPU stops until
the press, then carries on in place. Only a *press* wakes it, because pin
alarms cannot see rotation. It is **never used on USB**: with a host attached
the board is externally powered and light sleep would disturb the link, so
it falls back to the 24 MHz poll loop (which rotation can also wake).
`sleep_true_on_usb` forces it on USB for bench tests only.

> **Other versions:** the wake press may not be a direct MCU button. It may
> be a line driven by the **MSPM0 input companion**. Put that pin in
> `sleep_wake_pins` (active low, open drain) and it becomes a pin alarm the
> same way (RP2350: at most 4 pin alarms). Keep the rule that true sleep
> only happens on battery.

| Part | While asleep |
|---|---|
| Screen and its rail (D10) | **off**: rail cut, panel blanked |
| Audio codec + amp | **off**: held in reset (PERIPH_RESET); it drops off I2C |
| CPU | **light sleep** on battery; on USB, polling at **24 MHz** (`sleep_cpu_mhz`) |
| NeoPixels (5) | set to black |
| USB-host 5 V switch | held **off** from boot (`code.py`); it used to float |
| SD card | the talker does not use it (`sd_card: False`), but an inserted card stays powered. Remove it for battery runs |

The clone has no ESP32-C6 fitted. Its board definition names the codec's
reset pin both `ESP_RESET` and `PERIPH_RESET` (one pin), so never hold
"ESP_RESET" low while awake: that silences the audio.

Tested 2026-10-25, with light sleep forced on USB: it light-slept until the
encoder press twice, woke with screen and audio, and the wake press did not
select an item. Polling-sleep wake on 11.0: ~0.64 s to the picture, ~0.69 s
to presses working. **Not yet measured:** current draw in light sleep on
battery.
