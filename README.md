# T-Rex Talker Interactive

Stimulation games and pluggable subprograms for the
[T-Rex Talker](https://github.com/mkadie) AAC device — including
**T-Rex's Rubber Chicken Challenge**, a timed, **13-language** AAC quiz
built for the Maker Faire Sip-N-Puff Rubber Chicken demo.

This is an **extension-only overlay**. It adds a subprogram framework
to the base T-Rex Talker software so that:

- Any menu item can launch a Python subprogram by giving a `.py` path:
  `submenu = stim_games/bubble_pop.py`
- `config.txt` can boot the device straight into a subprogram:
  `mode = stim_games/aac_trainer.py`
- New stim games are drop-in modules under `/stim_games/`.

Licensed under **PolyForm Noncommercial 1.0.0**
([LICENSE](./LICENSE), see caveat below about fetching the verbatim
text on first clone).

---

## Mission

Our primary goal is simple: get free or low-cost assistive devices to
people whose needs are going unmet.

Stepping back into AAC work, we hit a problem we hadn't anticipated —
you can't just *explain* how a device works to a user you can't yet
talk with. Teaching a pre-verbal or non-verbal user a new
communication tool is its own challenge, and working around that
challenge led us to some very creative interactive features.
Features that, when we looked at them sideways, seemed like they
could be **AMAZING** for a set of autistic children.

As we brought this stim-interactive work into our ecosystem, we
realized something else: it might also be genuinely useful for
neurotypical children, and we might be able to sell or license a
version of it to help pay for everything else. That is why the
stim-interactive work in this repository is released under a
**noncommercial** license — to leave the door open to bringing in
funds that help us reach more people.

I will freely admit that I would love for it to bring in enough
funding that I could quit my day job and work on this full time.
I also think that is a fair use of those funds, as long as the math
balances out to *more* people getting a voice than we could reach
otherwise.

---

## What's in here

```
T-Rex_talker_interactive/
├── LICENSE                       # PolyForm Noncommercial 1.0.0 — see "Before publishing"
├── NOTICE                        # upstream credits + MIT text for T-Rex Talker
├── README.md                     # this file
├── T-Rex_Talker_Subprogram.md    # full specification of the subprogram framework
├── TWO_PLAYER.md                 # two-player race mode — controls, scoring
├── MULTILINGUAL.md               # encoder language-picker pipeline
├── documents/
│   └── circuitpython_SD_writing.md   # host<->SD write access via boot.py remount
│
├── stim_games/                   # the new framework and bundled games
│   ├── __init__.py
│   ├── subprogram.py             # Subprogram base class + loader
│   ├── game_config.py            # sidecar .cfg parser
│   ├── cause_and_effect.py       # press-for-reward stim loop
│   ├── bubble_pop.py             # tap spawns coloured bubbles
│   ├── color_cycle.py            # HSV kaleidoscope with press-boost
│   ├── aac_trainer.py            # "Rubber Chicken Challenge" quiz (1- & 2-player)
│   └── aac_trainer.cfg           # 14 question/answer pairs + two_player toggle
│
├── menus/                        # drop into /menus/ on the device
│   ├── games.menu                # picker for all bundled games
│   ├── trainer.menu              # answer pool the AAC Trainer uses
│   └── base_with_games.menu      # example of wiring Games into base
│
├── tools/
│   ├── fetch_license.sh          # pull the canonical PolyForm text into LICENSE
│   ├── fetch_license.ps1         # same, PowerShell version
│   ├── make_trainer_sounds.py    # English trainer prompt/feedback TTS
│   ├── generate_game_i18n.py     # 13-language word + prompt WAVs (translate + TTS)
│   ├── generate_screens.py       # 13-language pre-rendered screen BMPs
│   ├── generate_board_art.py     # English flash board images (emoji tiles)
│   └── generate_language_*.py    # encoder-picker sounds / menus / banner images
│
├── upstream_patches/             # modified T-Rex Talker files (MIT + mods)
│   ├── README.md                 # explains the dual-license boundary
│   ├── action.py                 # adds subprogram dispatch
│   ├── code.py                   # entry point with subprogram boot support
│   ├── machine.py                # adds _launch_subprogram() and mode= boot
│   ├── input_manager.py          # multi-keyboard polling + generic-HID sip-n-puff
│   ├── audio_player.py           # non-blocking playback (block=False)
│   ├── config_reader.py          # adds "mode" to the allowlist
│   ├── config.txt                # adds commented mode example
│   └── menu_system.md            # doc updates for subprogram syntax
│
└── .github/
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md
    │   └── feature_request.md
    └── pull_request_template.md
```

---

## Before publishing the repo

The `LICENSE` file in this checkout is a **placeholder** that names
the license (SPDX: `PolyForm-Noncommercial-1.0.0`) but does not contain
the verbatim legal text. This is because the initial scaffold was
generated in an environment without access to polyformproject.org.

Before you push the repo to GitHub, run once:

```sh
# macOS / Linux
./tools/fetch_license.sh

# Windows PowerShell
.\tools\fetch_license.ps1
```

Both helpers download the canonical license text from
`polyformproject/polyform-licenses` at tag `1.0.0` and replace the
placeholder in place. After running, inspect the first line of
`LICENSE` and confirm it begins with `SPDX-License-Identifier:` and
the second section begins with `# PolyForm Noncommercial License
1.0.0`.

---

## Installing onto a T-Rex Talker

This repo is an overlay. You also need a working
[T-Rex Talker](https://github.com/mkadie) checkout (or an SD card
flashed with the installer).

### One-step install

From the repo root:

```sh
# macOS / Linux
./install.sh /path/to/your/trextalkv3

# Windows PowerShell
.\install.ps1 -Target C:\path\to\your\trextalkv3
```

The installer will:

1. Copy `stim_games/` into `<target>/stim_games/`.
2. Copy `menus/*.menu` into `<target>/menus/`.
3. Copy `tools/make_trainer_sounds.py` into `<target>/tools/`.
4. Copy `T-Rex_Talker_Subprogram.md` into `<target>/`.
5. Overwrite the eight patched files in `upstream_patches/` onto their
   counterparts in `<target>/`, backing each original up as
   `<file>.pre_interactive.bak`.

### Manual install

If you prefer explicit control, copy the same files yourself. See
`upstream_patches/README.md` for what each patched file does.

---

## Using the extension

### Launch a game from a menu

Add an entry to any `.menu` file:

```
[bubble_pop]
label = Bubble Pop
image = images/games/bubble_pop.bmp
submenu = stim_games/bubble_pop.py
```

When the user presses it, the subprogram loads, takes over the input
loop, and returns to the calling menu on exit.

The included `menus/games.menu` demonstrates this for all four bundled
games. See `menus/base_with_games.menu` for an example of linking
`games.menu` from the home screen.

### Boot straight into a game (kiosk mode)

Add to `/config.txt`:

```
mode = stim_games/aac_trainer.py
```

After hardware and menu init the device launches that subprogram
directly instead of idling at `start_menu`. When the subprogram exits,
the normal menu loop resumes.

### Generate the trainer's voice prompts

Run on your PC (not the device):

```sh
pip install gTTS          # or pyttsx3, or install piper
python tools/make_trainer_sounds.py --out out/sounds/trainer
```

This produces the 14 MP3 prompts referenced by `aac_trainer.cfg`.
Copy the resulting folder into `/sounds/trainer/` on the device's SD
card or flash.

---

## Writing your own subprogram

See **[T-Rex_Talker_Subprogram.md](./T-Rex_Talker_Subprogram.md)** for
the full specification. The short version:

```python
# stim_games/my_game.py
from stim_games.subprogram import Subprogram


class MyGame(Subprogram):
    name = "My Game"

    def setup(self):
        self.play_sound("/button_sounds/yes.mp3")

    def tick(self):
        pressed = self.input.poll()
        if pressed is not None:
            self.set_status((0, 255, 0))
        return True                  # return False to exit


GAME = MyGame
```

Then add a menu entry: `submenu = stim_games/my_game.py`. Done.

---

## T-Rex's Rubber Chicken Challenge (the AAC Trainer)

The headline subprogram (`stim_games/aac_trainer.py`) — a timed AAC quiz
built for the Maker-Faire Sip-N-Puff demo, now **multilingual** and running
on the Fruit Jam DVI + USB variant.

Gameplay:

1. A voice prompt describes a scenario ("Someone held the door for you —
   what do you say?").
2. The player navigates the AAC board and selects the item that answers
   it. Base-page answers are direct; food answers are reached through
   the **More** button.
3. Score is wall-clock time plus a 30 s penalty per wrong answer (the
   timer pauses during audio). A top-3 leaderboard persists to
   `/sd/hiscores.txt` with encoder name entry.

Round shape: **6 questions per round**, drawn from a 14-item pool (one per
board word) with no repeats in a round. Target selection is page-weighted —
**75 %** land on the base page, **25 %** on the food page — so the common
words come up ~3× as often. Configure via `stim_games/aac_trainer.cfg`
(`rounds`, `first_page_bias`, `penalty_seconds`, …).

### Two-player race mode

Set `two_player = true` (the default) for a real-time head-to-head race:
**P1** drives a yellow cursor (Left / Right / **Space**, starts cell 1),
**P2** a blue cursor (Up / Down / **Enter**, starts cell 8). Both hear the
same prompt, then race — the **first buzz-in ends the question**. Time is
shared; a 30 s penalty lands on whoever was too slow (correct) or on the
buzzer (wrong). Two sip-n-puffs are polled at once so both stations are
live. Two-player uses the **base page only** (the food submenu is skipped
because the board is shared). Full rules in
**[TWO_PLAYER.md](./TWO_PLAYER.md)**; set `two_player = false` for the
classic single-player food-navigation game.

**Booth-friendly timeouts.** High-score name entry ends after **15 s** of no
input (keeping whatever's typed), and an abandoned round resets to the
attract / start screen after **60 s** of no gameplay activity — so a walked-
away player never leaves the game stuck.

### Multilingual (13 languages)

Thai, Japanese, Czech, Mandarin, Hindi, Spanish, French, Arabic, Bengali,
Portuguese, Russian, German, and English. **Everything** localizes — the
spoken prompts, per-word audio, feedback, and the full **screens**.

Because CircuitPython's built-in font is ASCII-only, each screen is
**pre-rendered per language into an image** on the host (Pillow + Noto
fonts) so every script renders perfectly on-device — the game is a
"screen-swapper". Content lives on the SD card:

- `/sd/screens/<lang>/{title,board_base,board_food,finished}.bmp`
- `/sd/sounds/game/<lang>/{words,prompts}/*.wav`

On the start and end screens, **BUTTON1 / BUTTON3** cycle the language
(silent while scrolling; after 5 s it speaks the language's name in that
language), and **BUTTON2** starts. The active language is shown in English.

### Input

Runs on the `FRUITJAM_DVI_KBD` variant. Works simultaneously with:

| Hardware | Navigate | Select |
|---|---|---|
| USB keyboard | arrows | Enter / Space |
| Onboard buttons (in game) | BUTTON1/2/3 activate the highlighted cell | — |
| Sip-n-puff adapter(s) | emulated arrows | emulated Enter |

Sip-n-puff adapters are **CircuitPython composite devices** whose HID
interface isn't a "boot keyboard", so the input manager attaches them via a
generic HID-endpoint fallback and polls **multiple keyboards at once** (two
players / stations). Prompts play **non-blocking** so navigation stays
responsive while a clip is still speaking.

### Generating the localized content

Host-side tools (need `gTTS`, `deep-translator`, `Pillow`, `ffmpeg`):

```sh
python tools/make_trainer_sounds.py       # English prompt/feedback MP3s
python tools/generate_game_i18n.py        # 13-language word + prompt WAVs -> out/game_i18n/
python tools/generate_screens.py          # 13-language screen BMPs      -> out/screens/
python tools/generate_board_art.py        # English flash board images
```

Then copy `out/game_i18n/*` and `out/screens/*` onto the SD under
`/sd/sounds/game/` and `/sd/screens/`. The card is host-read-only by
default; see **`documents/circuitpython_SD_writing.md`** for the `boot.py`
`storage.remount` cycle that hands it to the PC.

---

## License summary

| What                                           | License                           |
|------------------------------------------------|-----------------------------------|
| New code (stim_games, menus, tools, docs)      | PolyForm Noncommercial 1.0.0      |
| Unmodified portions of files in `upstream_patches/` | MIT (upstream T-Rex Talker)  |
| Modifications inside `upstream_patches/`       | PolyForm Noncommercial 1.0.0      |
| CircuitPython / Adafruit dependencies          | Their respective upstream licenses |
| AAC symbol artwork (referenced, not bundled)   | See `NOTICE` (mostly CC BY-SA / CC BY-NC-SA / CC BY-NC) |

"Noncommercial" is defined in the PolyForm license itself — generally
it includes personal, hobbyist, academic, charitable, educational, and
government use. If you want to build or sell commercial products
derived from this repository, you need a different license from the
copyright holder.

---

## Contributing

Bug reports and feature requests are welcome — please use the issue
templates in `.github/ISSUE_TEMPLATE/`. Pull requests should follow
`.github/pull_request_template.md` and keep the same dual-license
structure: new code lands under PolyForm-NC; any unavoidable changes
to `upstream_patches/` keep their MIT headers.

---

## Status

| Piece                                   | Status              |
|-----------------------------------------|---------------------|
| Subprogram framework (launch, exit)     | Working             |
| `mode = *.py` boot-into-game            | Working             |
| `submenu = *.py` menu launch            | Working             |
| cause_and_effect / color_cycle / bubble_pop | Working         |
| AAC Trainer — single-player flow        | Working             |
| AAC Trainer — two-player race mode      | Working (P1/P2 buzz-in; see TWO_PLAYER.md) |
| AAC Trainer — 13-language localization  | Working (screen-swapper; audio + screens on SD) |
| AAC Trainer — Sip-N-Puff integration    | Working (generic-HID USB, multiple devices)     |
| Leaderboard persistence for AAC Trainer | Working (`/sd/hiscores.txt`) |
| Graphical on-screen trainer feedback    | Working (per-language pre-rendered screens)     |
| Simulator / host-side test harness      | Future              |
