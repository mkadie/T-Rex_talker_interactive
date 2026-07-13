# RecrateChicken.md — Maker-Faire Chicken Challenge Setup Runbook (Linux)

> **Historical runbook (rotary-encoder build).** This captures the original
> single-player Maker-Faire setup on rotary-encoder hardware. The project has
> since moved to the **Fruit Jam DVI + USB** variant running the full
> multilingual, **two-player** Rubber Chicken Challenge (sip-n-puff input,
> per-language pre-rendered screens on the SD card). For the current state,
> see the repo [README.md](./README.md), [TWO_PLAYER.md](./TWO_PLAYER.md),
> and [documents/circuitpython_SD_writing.md](./documents/circuitpython_SD_writing.md).
> The bring-up steps below remain useful for the encoder variant.

> **You are reading this as a fresh Claude session on a Linux box.**
> Your job: pick up the *T-Rex Talker Interactive* "Chicken Challenge"
> AAC trainer, get it running on the user's connected CircuitPython
> device with rotary encoder, and tune it for a public demonstration
> at Maker Faire on **Sunday**.
>
> Read this whole file before touching anything. Then work the phases
> in order. Stop at every **CHECK** and report what you saw to the
> user before continuing.

---

## 0. Mission briefing

**Project lineage**

| Repo | Role | License |
|------|------|---------|
| `mkadie/trextalkv3` (or the user's fork) | Upstream T-Rex Talker AAC base software | **MIT** |
| `<user>/T-Rex_talker_interactive` | Subprogram framework + stim games + AAC Trainer ("Chicken Challenge") | **PolyForm Noncommercial 1.0.0** for new code; MIT preserved on patched files |

**Deliverable for Sunday:** a CircuitPython device on rotary-encoder
hardware that boots straight into the AAC Trainer, plays a voice
prompt, and lets a Maker-Faire visitor squeeze a rubber chicken
(or rotate the encoder) to navigate menus and answer ten questions —
finishing with a time score plus 30 s penalties for wrong answers.

The "Chicken Challenge" gameplay spec lives in the upstream design doc
(`Version3/SipAndPuff/T-Rex_Sip_N_Puff.md` §3 in the user's local
working tree, if available). You don't need it — the cfg + py already
implement it.

---

## 1. Standing rules (NEVER violate these without explicit consent)

1. **Hardware config is per-device.** `hardware_config.py` reflects the
   physical wiring of the specific board that's plugged in. **Do NOT
   overwrite, modify, push, or "reset" `hardware_config.py` on a
   connected device.** If the upstream `deploy.sh` would copy it,
   skip that file. The user's deploy script *does* include it; you
   must explicitly omit it.

2. **Active GitHub is sacred.** The user may have a working clone of
   T-Rex Talker on disk that is also their active git remote. Treat
   that clone as read-only by default. Stage all overlay work into a
   separate working directory and only push patched files onto it via
   the documented installer (`install.sh`), which makes
   `*.pre_interactive.bak` backups of every file it changes.

3. **License boundaries.** New code in `T-Rex_talker_interactive` is
   PolyForm Noncommercial 1.0.0. Files under `upstream_patches/` carry
   an MIT attribution header at the top — **preserve it on every edit**.
   The PolyForm verbatim text must live in `LICENSE` before any push;
   a `tools/fetch_license.sh` helper is provided to drop it in.

4. **Ask before doing anything destructive.** This includes wiping the
   CIRCUITPY drive, force-pushing to git, force-rebooting the device,
   or installing system packages with sudo.

5. **Stop at every CHECK.** If a check fails, do not advance. Report
   the failure and ask the user how to proceed.

---

## 2. Hardware assumed for this run

The user said "**CYD with rotary encoder**". The default rotary-
encoder variant in upstream is `FRUITJAM_V2`, which sets
`rotary_encoder = True` and `start_menu = base_fruitjam.menu`.
The Trainer is keyed to `base_fruitjam.menu` and `food_fruitjam.menu`.

If the connected board's `hardware_config.py` says it's something
*other* than a rotary-encoder variant pointing at `base_fruitjam.menu`,
**STOP** and ask the user before continuing. Do NOT change the
device's hardware_config to "fix" the mismatch — instead, ask whether
to change the Trainer's `answer_menu` to match what the device boots.

---

## 3. Linux prerequisites

Tested on Ubuntu 22.04+ and Debian 12. Adapt `apt` to your distro
(`dnf`, `pacman`, `zypper` etc.) but the package names map cleanly.

```bash
# Core toolchain
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv ffmpeg \
                    udisks2 usbutils
```

For text-to-speech (pick ONE; gTTS is recommended for natural voices):

```bash
# Option A — gTTS (online, free, very natural)
python3 -m pip install --user gTTS

# Option B — pyttsx3 (fully offline, uses host voices via espeak)
sudo apt install -y espeak espeak-ng
python3 -m pip install --user pyttsx3

# Option C — piper (offline neural TTS, best quality)
#   See https://github.com/rhasspy/piper for the install steps and a
#   voice .onnx file. Skip unless A or B aren't acceptable.
```

**CHECK 3.1** — confirm:
```bash
git --version
python3 --version
ffmpeg -version | head -1
python3 -c "import gtts; print('gTTS', gtts.__version__)" 2>/dev/null \
  || python3 -c "import pyttsx3; print('pyttsx3 OK')" 2>/dev/null \
  || echo "no TTS backend installed"
```
All four commands should print a version string. Report results.

---

## 4. Clone the repos

Pick a workspace directory (the user's existing local layout uses
`~/aac/` style paths; if not specified, default to `~/trex/`):

```bash
mkdir -p ~/trex && cd ~/trex
```

### 4.1 Upstream T-Rex Talker (MIT base software)

The user owns / forked this. Ask them for the URL if it's not in
their `~/.gitconfig` or shell history. Common candidates:

```bash
# Replace <user> with the actual GitHub user / org you confirm with them.
git clone https://github.com/<user>/trextalkv3.git
```

### 4.2 T-Rex Talker Interactive (this repo)

```bash
git clone https://github.com/<user>/T-Rex_talker_interactive.git
cd T-Rex_talker_interactive
```

**CHECK 4.1** — both directories exist and contain the expected
top-level files:

```bash
ls ~/trex/trextalkv3/code.py ~/trex/trextalkv3/machine.py \
   ~/trex/trextalkv3/menus/base_fruitjam.menu \
   ~/trex/T-Rex_talker_interactive/install.sh \
   ~/trex/T-Rex_talker_interactive/stim_games/aac_trainer.py \
   ~/trex/T-Rex_talker_interactive/stim_games/aac_trainer.cfg \
   ~/trex/T-Rex_talker_interactive/tools/make_trainer_sounds.py
```
If any path is missing, stop and ask the user.

---

## 5. Bring in the verbatim PolyForm license

The repo ships with a placeholder `LICENSE`. Replace it with the
canonical text once:

```bash
cd ~/trex/T-Rex_talker_interactive
./tools/fetch_license.sh
head -3 LICENSE
```

The first line should be `SPDX-License-Identifier:
PolyForm-Noncommercial-1.0.0` and the third should be
`# PolyForm Noncommercial License 1.0.0`.

**CHECK 5.1** — `wc -l LICENSE` should report ≥ 70 lines (the full
canonical text). If not, the fetch failed; rerun, or check the
network egress.

---

## 6. Generate the trainer audio

The Trainer references 14 MP3s under `/sounds/trainer/`: 4 framing
sounds + 10 question prompts. The corpus is hard-coded in
`tools/make_trainer_sounds.py` and must stay in sync with
`stim_games/aac_trainer.cfg`.

```bash
cd ~/trex/T-Rex_talker_interactive
python3 tools/make_trainer_sounds.py --out out/sounds/trainer
ls out/sounds/trainer/ | sort
```

You should see exactly 14 `.mp3` files. The current set (as of this
runbook) is:

```
welcome.mp3                       (framing)
correct.mp3                       (framing)
try_again.mp3                     (framing)
finished.mp3                      (framing)
someone_held_the_door.mp3         -> thankyou
bad_smell_making_me_angry.mp3     -> stinky
i_need_to_number_one.mp3          -> bathroom
want_to_go_to_the_park.mp3        -> yes
want_to_eat_broccoli.mp3          -> no
im_thirsty_want_water.mp3         -> more/water
want_a_crunchy_red_apple.mp3      -> more/apple
want_a_cold_glass_of_milk.mp3     -> more/milk
want_a_banana_only_a_banana.mp3   -> more/banana
a_little_hungry_just_a_cracker.mp3 -> more/cracker
```

**CHECK 6.1** — every cfg-referenced prompt resolved on disk. Run
this verifier:

```bash
cd ~/trex/T-Rex_talker_interactive
python3 - <<'PY'
import sys, os, importlib.util
sys.path.insert(0, '.')
spec = importlib.util.spec_from_file_location("mts", "tools/make_trainer_sounds.py")
mts = importlib.util.module_from_spec(spec); spec.loader.exec_module(mts)
corpus = {n for n,_ in mts.PROMPTS}
from stim_games.game_config import load
_, secs = load("stim_games/aac_trainer.cfg")
miss = [os.path.basename(q.get("prompt","")) for q in secs.get("question",[])
        if os.path.basename(q.get("prompt","")) not in corpus]
print("MISSING in corpus:", miss) if miss else print("All cfg prompts in corpus")
disk = set(os.listdir("out/sounds/trainer"))
miss_disk = [n for n in corpus if n not in disk]
print("MISSING on disk:", miss_disk) if miss_disk else print("All corpus MP3s on disk")
PY
```

Report both lines. If either prints "MISSING…", stop and investigate.

---

## 7. Find the connected device

Plug in the rotary-encoder device. CircuitPython exposes it as a USB
mass-storage volume labelled `CIRCUITPY`. On Linux it auto-mounts
under `/media/$USER/CIRCUITPY` (or `/run/media/$USER/CIRCUITPY` on
Fedora/Arch).

```bash
lsblk -o NAME,LABEL,MOUNTPOINT | grep -i CIRCUITPY
# OR
findmnt -no SOURCE,TARGET -t vfat | grep -i CIRCUITPY
```

If it's not mounted, mount it manually:

```bash
udisksctl mount -b /dev/disk/by-label/CIRCUITPY
```

Set a shell variable for the rest of this runbook:

```bash
export DEV="/media/$USER/CIRCUITPY"   # adjust to whatever mountpoint you saw
ls "$DEV"
```

**CHECK 7.1** — `ls "$DEV"` should show at minimum `code.py`,
`machine.py`, `menus/`, and a `config.txt`. If it's a brand-new
CircuitPython install with only `boot_out.txt` and `lib/`, the user
hasn't run the upstream installer yet — STOP and ask whether to do so
first.

**CHECK 7.2** — confirm it's a rotary-encoder variant. Read its
`hardware_config.py` and report what `DEFAULT_VARIANT` is, but **do
NOT modify it**:

```bash
grep -E '^DEFAULT_VARIANT' "$DEV/hardware_config.py"
grep -E '^\s+"start_menu"' "$DEV/hardware_config.py" | head -5
```

If `DEFAULT_VARIANT` is not a rotary variant (e.g. it's a touch-only
CYD with no encoder configured), STOP and ask the user how to proceed.
Do not change `hardware_config.py`.

---

## 8. Deploy the overlay

The repo ships an installer that copies new files into a target
trextalkv3 checkout AND patches the five upstream files (action.py,
machine.py, config_reader.py, config.txt, menu_system.md) with
backups. The installer is for a *checkout*, not the device itself —
on Linux you can pipe it straight into the device too because
CIRCUITPY is just a filesystem.

### 8.1 First, overlay onto your local trextalkv3 checkout (canonical)

```bash
cd ~/trex/T-Rex_talker_interactive
./install.sh ~/trex/trextalkv3
```

Verify backups were made:

```bash
ls ~/trex/trextalkv3/*.pre_interactive.bak
```

You should see `action.py.pre_interactive.bak`,
`machine.py.pre_interactive.bak`,
`config_reader.py.pre_interactive.bak`,
`config.txt.pre_interactive.bak`, and
`menu_system.md.pre_interactive.bak`.

### 8.2 Then deploy to the device — without touching hardware_config.py

The upstream `deploy.sh` includes `hardware_config.py` in its file
list. **Do NOT use it as-is.** Use this Linux equivalent that
explicitly excludes that file:

```bash
TREX=~/trex/trextalkv3

# 1. Python files (hardware_config.py intentionally OMITTED)
for f in code.py machine.py display_manager.py audio_player.py \
         input_manager.py sleep_manager.py menu_parser.py action.py \
         storage_manager.py config_reader.py; do
    [ -f "$TREX/$f" ] && cp "$TREX/$f" "$DEV/$f"
done

# 2. Subprograms package + new menus
mkdir -p "$DEV/stim_games"
cp -r "$TREX/stim_games/." "$DEV/stim_games/"
mkdir -p "$DEV/menus"
cp "$TREX"/menus/*.menu "$DEV/menus/"

# 3. Trainer audio prompts (from the generated corpus)
mkdir -p "$DEV/sounds/trainer"
cp ~/trex/T-Rex_talker_interactive/out/sounds/trainer/*.mp3 \
   "$DEV/sounds/trainer/"

# 4. Force a config.txt overwrite (to pick up the new mode key etc.)
#    — this is the ONE config file we DO replace because it is per-deploy,
#      not per-board.
cp "$TREX/config.txt" "$DEV/config.txt"

sync
```

**CHECK 8.1** — the device now has the new files:

```bash
ls "$DEV/stim_games/"     # expect aac_trainer.py, aac_trainer.cfg, ...
ls "$DEV/sounds/trainer/" # expect 14 mp3s
grep -E '^mode|^start_menu' "$DEV/config.txt"
```

`grep mode` may show `#mode =` (commented out); we'll set it next.

---

## 9. Configure for the Maker-Faire kiosk demo

Edit the device's `config.txt` so the unit boots straight into the
AAC Trainer instead of idling at the menu. Two ways:

### Option A — pure kiosk (recommended for the demo)

```bash
sed -i 's|^#\?mode\s*=.*|mode = stim_games/aac_trainer.py|' "$DEV/config.txt"
grep ^mode "$DEV/config.txt"
```

When the device boots, it does normal hardware init, then immediately
launches the Trainer. Exit gesture (encoder-hold ≥ 3 s) drops back to
the start menu.

### Option B — menu-first with Trainer on a button

If you want the visitor to pick "Games → AAC Trainer" themselves, do
NOT set `mode`. Instead replace the start menu with the bundled
example:

```bash
sed -i 's|^start_menu\s*=.*|start_menu = base_with_games.menu|' "$DEV/config.txt"
```

Ask the user which mode they prefer for the booth. Default to A.

---

## 10. End-to-end smoke test on the device

Reload the device. CircuitPython auto-reloads when files change, but
to be sure, press **Ctrl-D** in the serial console or unplug/replug.

Open the serial console:

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
# pick the right one (usually /dev/ttyACM0 for Pico-class boards)
sudo usermod -aG dialout $USER   # one-time so you can read the port w/o sudo
                                  # (log out/in for it to take effect)
screen /dev/ttyACM0 115200       # or: minicom, picocom, tio
```

You should see the device print something like:

```
AAC Device — variant: FRUITJAM_V2
User config loaded (N settings)
...
Config mode: launching subprogram stim_games/aac_trainer.py
Subprogram launch: stim_games/aac_trainer.py
Loaded subprogram config: /menus/stim_games/aac_trainer.cfg
AAC Trainer: Q1/10 prompt=/sounds/trainer/<random>.mp3 path=[...]
```

Then a voice prompt should play.

### Test scenarios (all REQUIRED for green-light Sunday)

For each scenario, drive the encoder, observe the device's behaviour,
and capture both the serial log and what the visitor would experience:

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 1 | Boot, listen to first prompt, navigate to correct answer with encoder, click. | Item sound plays, "Yes, that's right!" plays, next prompt starts. | |
| 2 | Get a prompt that needs `more/X`, press `more`, navigate to wrong food, click. | Wrong item's sound plays, "Not quite, try again." plays, +30 s penalty, next prompt starts. | |
| 3 | Get a `more/X` prompt, press `more`, then press `back_button`. | Returns to base menu, path cursor rolls back, you can re-attempt. | |
| 4 | Run all 10 questions to completion. | "Great job, you finished the round." plays. Total time printed in serial log. | |
| 5 | Hold the encoder button for ≥ 3 s mid-game. | Game exits cleanly, device returns to menu. | |
| 6 | Reset the device and run the game a second time. | Question order is **different** from the first run (proves randomize works). | |
| 7 | Disconnect, reconnect, observe boot. | Boots back into the Trainer (mode= still set). | |

**CHECK 10.1** — fill in the Pass column above and report to the user.
Any FAIL is a blocker — diagnose with the troubleshooting section
before iterating prompts/parameters.

---

## 11. Iterating with the user (until Sunday)

The user will tweak prompt wording, add/remove questions, adjust
penalties, etc. Standard loop:

1. Edit `~/trex/T-Rex_talker_interactive/stim_games/aac_trainer.cfg`
   (and the matching `(filename, text)` entry in
   `tools/make_trainer_sounds.py` if you change a prompt or rename
   one).
2. Regenerate audio:
   ```bash
   python3 tools/make_trainer_sounds.py --out out/sounds/trainer
   ```
3. Push to the device:
   ```bash
   cp stim_games/aac_trainer.cfg "$DEV/stim_games/aac_trainer.cfg"
   cp stim_games/aac_trainer.py  "$DEV/stim_games/aac_trainer.py"
   cp out/sounds/trainer/*.mp3   "$DEV/sounds/trainer/"
   sync
   ```
4. Ctrl-D in the serial console (or unplug/replug) to soft-reboot.
5. Re-run scenario 1 above to verify.
6. Once happy, commit:
   ```bash
   cd ~/trex/T-Rex_talker_interactive
   git add -A
   git commit -m "Trainer: <what changed>"
   git push
   ```

When asked to rename a prompt MP3, change THREE places to keep
everything in sync:
- `aac_trainer.cfg` — `prompt = ...` line
- `tools/make_trainer_sounds.py` — `PROMPTS` list entry
- `tools/make_trainer_sounds.py` — file listing in the docstring

The file `T-Rex_Talker_Subprogram.md` (in this repo) is the spec for
how subprograms work; consult it if extending.

---

## 12. Maker-Faire day hardening

48 hours before the event, do these once. Ask the user to confirm each.

- [ ] Confirm `mode = stim_games/aac_trainer.py` is set in
      `$DEV/config.txt`.
- [ ] Confirm `randomize = true` in
      `$DEV/stim_games/aac_trainer.cfg` (the default).
- [ ] Run the device on battery for 30 min to validate power /
      sleep behaviour. Sleep should NOT trigger mid-round; if it
      does, ask user to set `sleep_enabled = false` in `config.txt`
      for the demo.
- [ ] Test with the actual rubber-chicken Sip-N-Puff if the user
      brings one. The single-button helper in `aac_trainer.py` reads
      `input.puff_pressed` first, falling back to encoder. Verify
      the `puff_pressed` attribute exists on the device's
      InputManager — if not, the chicken will be treated as a plain
      button (still works, just no separate sip path).
- [ ] Make a backup of the device's working `\sounds\trainer\`
      folder onto a USB stick in case files corrupt during the show.
- [ ] Print a tiny laminated card with the exit gesture
      ("hold encoder 3 seconds to exit"). Visitors will get stuck
      otherwise.
- [ ] Have the upstream `deploy.sh` MINUS hardware_config.py ready
      as a one-liner script in case a full re-deploy is needed
      mid-event.

---

## 13. Troubleshooting

**Symptom:** Device boots into the menu, not the Trainer.
**Likely cause:** `mode = ...` not set in the *device's* config.txt
(you may have edited the source-tree config.txt instead).
**Fix:** Re-grep `$DEV/config.txt`. Set the line. Soft-reboot.

**Symptom:** Trainer launches but exits immediately, "no questions
configured".
**Likely cause:** The cfg path didn't get loaded — usually a typo in
the cfg path that `_launch_subprogram` looks up. The cfg must be at
`$DEV/stim_games/aac_trainer.cfg`.
**Fix:** Confirm the file exists at that path. Check serial log for
`Loaded subprogram config: ...`.

**Symptom:** Voice prompts don't play but the game advances.
**Likely cause:** MP3 files missing under `$DEV/sounds/trainer/`.
**Fix:** Re-run §6 (generate) and re-copy in §8.

**Symptom:** Selecting `more` does nothing — game stays on base menu.
**Likely cause:** The submenu file `food_fruitjam.menu` is missing
from the device, or the `more` item's `submenu` value points at a
filename the device doesn't have.
**Fix:** `ls $DEV/menus/food_fruitjam.menu` — should exist. If not,
re-run §8.2.

**Symptom:** Random order is suspiciously not random.
**Likely cause:** CircuitPython's `random` module has a deterministic
seed at boot. The shuffle works but the first sequence is the same
every cold boot.
**Workaround:** Add `import os; random.seed(int.from_bytes(os.urandom(4), "big"))`
at the top of `aac_trainer.py`'s setup(). Ask the user before doing
this — it's a small code change.

**Symptom:** Penalty doesn't seem to apply.
**Likely cause:** Score is computed at end of round only. Check
serial log for the final printout: `AAC Trainer: run finished in
N.Ns (wrong: M)`. Time = wall clock minus speech minutes plus
30 × wrong_count.

**Symptom:** Encoder direction feels backwards.
**Fix:** Set `encoder_direction_flip = true` in `$DEV/config.txt`.
Soft-reboot.

**Symptom:** Display goes blank during the game.
**Likely cause:** Sleep manager firing because the Trainer doesn't
call `machine.sleep.activity()`.
**Workaround:** Set `sleep_enabled = false` in `$DEV/config.txt` for
the demo run. (Future fix: have `aac_trainer.tick()` call
`machine.sleep.activity()` whenever input arrives.)

---

## 14. Success criteria for Sunday

The demo is GO when, on the venue's actual table, with the actual
chicken rigged to the device:

1. Cold-boot the device → AAC Trainer is running within 10 seconds.
2. Squeeze chicken / rotate encoder → highlight moves predictably.
3. A round of 10 questions can be completed by a non-technical
   visitor in under three minutes.
4. The serial log printout shows total time and wrong count.
5. Hold-to-exit works, returning the device to a state where the
   next visitor can simply press the encoder to start a new round.
6. Five consecutive rounds run without a crash, hang, or audio
   glitch.
7. Battery lasts ≥ 4 hours of continuous demo use, OR a USB power
   strategy is in place.

Once 1–7 are green, commit a `v1.0-makerfaire` tag:

```bash
cd ~/trex/T-Rex_talker_interactive
git tag -a v1.0-makerfaire -m "Maker Faire demo build"
git push --tags
```

---

## 15. After the show — debrief artefacts to capture

Tell the user to keep these for post-event analysis:

- Serial console log of the demo session (use `script` to record).
- Total visitor count, average completion time, leaderboard of best
  times if the user chooses to record manually.
- Any prompt that visitors found confusing — those are the next
  iteration target.
- Photos / video of visitors operating the chicken — useful for the
  user's PhD vision documentation in the upstream repo.

---

## Appendix A — File map you'll be touching

In `~/trex/T-Rex_talker_interactive/`:
```
LICENSE                              # PolyForm-NC verbatim (after fetch)
NOTICE                               # MIT credit for upstream
README.md                            # mission, install, usage
T-Rex_Talker_Subprogram.md           # subprogram spec — read for context
RecrateChicken.md                    # this file
install.sh / install.ps1             # overlay installer
stim_games/
    subprogram.py                    # base class + loader (don't edit unless asked)
    game_config.py                   # cfg parser  (don't edit unless asked)
    aac_trainer.py                   # the game engine — edit for behaviour
    aac_trainer.cfg                  # questions, answers, knobs — edit often
    cause_and_effect.py / bubble_pop.py / color_cycle.py
                                     # other stim games — orthogonal to chicken
menus/
    games.menu                       # picker (Option B)
    base_with_games.menu             # base+Games launcher (Option B)
    trainer.menu                     # the OLD trainer pool — unused now
                                     # since we point answer_menu at base_fruitjam.menu
tools/
    fetch_license.sh                 # one-shot license drop-in
    make_trainer_sounds.py           # TTS corpus  -> mp3 files
upstream_patches/
    README.md                        # license boundary
    action.py / machine.py / config_reader.py / config.txt / menu_system.md
                                     # MIT-credited modified upstream files
```

In `~/trex/trextalkv3/` (after install.sh has run):
```
*.pre_interactive.bak                # backups of every patched upstream file
stim_games/                          # symlink-ish overlay of the new package
menus/games.menu, menus/trainer.menu, menus/base_with_games.menu
tools/make_trainer_sounds.py
T-Rex_Talker_Subprogram.md
```

On the device (`$DEV` — typically `/media/$USER/CIRCUITPY`):
```
config.txt                           # mode = stim_games/aac_trainer.py
stim_games/                          # full package
sounds/trainer/*.mp3                 # 14 files
menus/                               # all .menu files INCLUDING base_fruitjam.menu
                                     # and food_fruitjam.menu from upstream
hardware_config.py                   # **DO NOT TOUCH**
```

---

## Appendix B — Quick reference: the 10 rounds

Default cfg (Trainer answer_menu = `base_fruitjam.menu`):

| # | Prompt MP3                              | Spoken text                                                               | Answer path        |
|---|-----------------------------------------|---------------------------------------------------------------------------|--------------------|
| 1 | someone_held_the_door.mp3               | Someone just held the door open for you. What do you want to say?         | `thankyou`         |
| 2 | bad_smell_making_me_angry.mp3           | There is a bad smell making me angry.                                     | `stinky`           |
| 3 | i_need_to_number_one.mp3                | I need to go number one.                                                  | `bathroom`         |
| 4 | want_to_go_to_the_park.mp3              | Your friend asked if you want to go to the park. You want to say?         | `yes`              |
| 5 | want_to_eat_broccoli.mp3                | Mom asked if you want to eat broccoli for dessert. You want to say?       | `no`               |
| 6 | im_thirsty_want_water.mp3               | I'm thirsty and I want a glass of water.                                  | `more` → `water`   |
| 7 | want_a_crunchy_red_apple.mp3            | I want to eat a crunchy red apple.                                        | `more` → `apple`   |
| 8 | want_a_cold_glass_of_milk.mp3           | I want a cold glass of milk.                                              | `more` → `milk`    |
| 9 | want_a_banana_only_a_banana.mp3         | I am hungry and I want a banana, and only a banana.                       | `more` → `banana`  |
| 10| a_little_hungry_just_a_cracker.mp3      | I am a little hungry; I just want a cracker.                              | `more` → `cracker` |

Order is shuffled at start unless `randomize = false` in the cfg.

---

*End of runbook. When in doubt, re-read §1.*
