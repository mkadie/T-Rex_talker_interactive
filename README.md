# T-Rex Talker Interactive

Stimulation games and pluggable subprograms for the
[T-Rex Talker](https://github.com/mkadie) AAC device — including the
**"Chicken Challenge" AAC Trainer** designed for the Maker Faire
Sip-N-Puff Rubber Chicken demo.

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
│
├── stim_games/                   # the new framework and bundled games
│   ├── __init__.py
│   ├── subprogram.py             # Subprogram base class + loader
│   ├── game_config.py            # sidecar .cfg parser
│   ├── cause_and_effect.py       # press-for-reward stim loop
│   ├── bubble_pop.py             # tap spawns coloured bubbles
│   ├── color_cycle.py            # HSV kaleidoscope with press-boost
│   ├── aac_trainer.py            # "Chicken Challenge" AAC quiz
│   └── aac_trainer.cfg           # 10 question/answer pairs for the trainer
│
├── menus/                        # drop into /menus/ on the device
│   ├── games.menu                # picker for all bundled games
│   ├── trainer.menu              # answer pool the AAC Trainer uses
│   └── base_with_games.menu      # example of wiring Games into base
│
├── tools/
│   ├── fetch_license.sh          # pull the canonical PolyForm text into LICENSE
│   ├── fetch_license.ps1         # same, PowerShell version
│   └── make_trainer_sounds.py    # host-side TTS generator for trainer prompts
│
├── upstream_patches/             # modified T-Rex Talker files (MIT + mods)
│   ├── README.md                 # explains the dual-license boundary
│   ├── action.py                 # adds subprogram dispatch
│   ├── machine.py                # adds _launch_subprogram() and mode= boot
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
5. Overwrite the five files in `upstream_patches/` onto their
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

## The AAC Trainer ("Chicken Challenge")

The headline subprogram. Implements the Maker-Faire demo described in
Michael Kadie's T-Rex Sip-N-Puff Rubber Chicken Edition documentation
(§3, "Maker Faire Engagement: The Chicken Challenge Game").

Gameplay:

1. Ten voice prompts are played in sequence.
2. The player navigates the trainer menu and selects the AAC item that
   answers each prompt.
3. Score is wall-clock time plus a 30-second penalty per wrong answer.
   The round timer pauses during every audio playback.

Input modes, simultaneously:

| Hardware              | Navigate                                 | Select          | Exit            |
|-----------------------|------------------------------------------|-----------------|-----------------|
| Rotary encoder         | rotate                                   | press           | hold 2 s        |
| Single button / puff   | tap (hold = accelerating repeat)         | double-tap      | hold 3 s        |
| Sip-N-Puff sip         | sip events emit −1 ticks (if supported)  | (via puff path) | (via puff path) |

Tune everything via `stim_games/aac_trainer.cfg`. See the file itself
for the list of keys; the full spec is in `T-Rex_Talker_Subprogram.md`.

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
| AAC Trainer — base flow                 | Working             |
| AAC Trainer — Sip-N-Puff integration    | Stubbed; needs driver surface (`input.puff_pressed`) |
| Leaderboard persistence for AAC Trainer | Future              |
| Graphical on-screen trainer feedback    | Future              |
| Simulator / host-side test harness      | Future              |
