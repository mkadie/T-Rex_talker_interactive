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
- `action.py` here adds `subprogram = …` menu items (the board's older
  `action.py` couldn't launch a subprogram from a menu).

## Layout

This folder mirrors the CIRCUITPY drive root — copy it over a working MVP
install (keeps everything not listed here):

```
config.txt                         per-device settings (rotation 270)
config_reader.py, action.py        patched base files (see above)
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

Then hard-reset the board (`import microcontroller; microcontroller.reset()`
from the REPL) — a soft reload leaves `/sd` unreadable on the Fruit Jam.

## Regenerating assets

- Tiles: `python3 tools/make_animepipboy_icons.py <menus/images/base dir>`
  (draws the two tiles and patches them into `base_board.bmp`; run it
  against the *stock* images, since it reads the old cell-4/5 tiles to keep
  the grid lines).
- Audio: `python3 tools/make_animepipboy_sounds.py <drive root>` (gTTS +
  ffmpeg, re-encoded to 44.1 kHz mono 64 kbps MP3 to match the board).
