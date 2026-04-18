# T-Rex Talker — Subprograms

*Specification for Python subprograms (stimulation games and other
interactive modules) that run on top of the base AAC software.*

**Status:** Working as of 2026-04-18.
**Scope:** CircuitPython 9 on Pico W / Pico 2 W and Fruit Jam targets.
**Related documents:**
- `menu_system.md` — core menu / config format
- `/stim_games/*.py` — built-in subprograms
- `../../../SipAndPuff/T-Rex_Sip_N_Puff.md` §3 — AAC Trainer gameplay spec

---

## 1. What is a Subprogram?

A **subprogram** is a short-lived Python module that temporarily takes
over the device's input and output, then hands control back to the
menu system. Subprograms are designed to run *on top of* the normal
AAC stack — they do not re-initialize hardware and they do not persist
state across restarts unless they choose to.

Typical subprograms:

- **Stim games** — cause-and-effect, bubble pop, colour cycle.
- **Training tools** — the AAC Trainer "Chicken Challenge".
- **Utilities** — calibration screens, input testers, diagnostics.

A subprogram is expected to:

1. Own the input-poll loop while it is running.
2. Respect the user's configured input hardware (rotary encoder,
   touch grid, physical buttons, Sip-N-Puff).
3. Exit cleanly on a user gesture or completion condition.
4. Leave the display in a state the menu system can redraw from.

It is **not** expected to:

- Deinit or reconfigure shared hardware (I²S, display bus, SD card,
  pressure sensor). The host `Machine` still owns those.
- Know about menu history, storage internals, or hardware variants.
  It only sees the `Machine` reference and whatever sidecar config
  was passed in.

---

## 2. File Layout

```
/code.py                     # existing entry point (unchanged)
/machine.py                  # host — dispatches subprograms
/action.py                   # recognizes submenu="...py"
/config_reader.py            # allows "mode = ...py" in config.txt
/config.txt                  # user settings (mode key optional)
/menus/
    base.menu
    games.menu               # new — menu of installed stim games
    base_with_games.menu     # example integration with base
    trainer.menu             # answer pool for AAC Trainer
    ...
/stim_games/                 # new — the subprograms package
    __init__.py
    subprogram.py            # base class + loader
    game_config.py           # sidecar .cfg parser
    cause_and_effect.py
    bubble_pop.py
    color_cycle.py
    aac_trainer.py
    aac_trainer.cfg
    ...
/sounds/
    trainer/
        welcome.mp3
        correct.mp3
        try_again.mp3
        finished.mp3
        you_are_thirsty.mp3
        ...                  # one per question prompt
```

`stim_games/` is a regular CircuitPython package. Modules in it
should prefer relative imports within the package, and absolute
imports (`from action import Action`) when they need something from
the host.

---

## 3. Launching a Subprogram

There are three ways a subprogram starts.

### 3.1 From a menu item

Any `[item]` in a `.menu` file can launch a subprogram by giving a
`submenu` (or `list` or explicit `subprogram`) value that ends in
`.py`:

```
[bubble_pop]
label = Bubble Pop
image = images/games/bubble_pop.bmp
submenu = stim_games/bubble_pop.py
```

The rule is implemented in `action.py`: when it sees a `submenu` /
`list` / `subprogram` value ending in `.py`, it returns
`"subprogram:<path>"` instead of `"submenu:<path>"`. `machine.py`
then calls `_launch_subprogram(path)` which does the import + run.

When the subprogram returns, the user lands back on the menu that
launched it. The menu navigation stack is not modified.

### 3.2 From `config.txt` (`mode = ...`)

Setting `mode = stim_games/aac_trainer.py` in `/config.txt` causes
the device, after finishing the normal hardware + menu init, to
launch that subprogram immediately instead of idling at the start
menu. When the subprogram exits, the start menu becomes active.

```
# /config.txt
start_menu = base.menu
mode = stim_games/aac_trainer.py
```

This is the intended configuration for kiosk-style setups (Maker
Faire demo table, single-purpose trainer stations).

### 3.3 Programmatically

Any code with a `Machine` reference can call:

```python
machine._launch_subprogram("stim_games/color_cycle.py")
```

This is primarily used by the emergency-mode and scheduled-task
systems; normal subprograms should not call it.

---

## 4. Writing a Subprogram

A subprogram is any Python module that exposes **either**:

- a class named `GAME` that subclasses `Subprogram`, **or**
- a top-level `run(machine, config=None)` function.

### 4.1 Subclass template (preferred)

```python
# /stim_games/my_game.py
from stim_games.subprogram import Subprogram


class MyGame(Subprogram):
    name = "My Stim Game"

    def setup(self):
        # Called once. Display, audio, input, pixel, storage are
        # available as self.display, self.audio, self.input,
        # self.pixel, self.storage.
        ...

    def tick(self):
        # Called in the main loop (~100 Hz). Return False to exit.
        pressed = self.input.poll()
        if pressed is not None:
            self.play_sound("/button_sounds/yes.mp3")
        return True

    def teardown(self):
        # Called on exit, even if tick() raised.
        ...


GAME = MyGame
```

The base class provides:

| Attribute      | Purpose                                           |
|----------------|---------------------------------------------------|
| `self.machine` | The host `Machine` instance                       |
| `self.display` | `DisplayManager`                                   |
| `self.audio`   | `AudioPlayer`                                     |
| `self.input`   | `InputManager` — call `.poll()` in your loop      |
| `self.pixel`   | NeoPixel or `None`                                |
| `self.storage` | `StorageManager` — use `.resolve_path()` for SD   |
| `self.config`  | Parsed sidecar `.cfg` (if one exists), else `{}`  |
| `play_sound(p)`| Plays a sound through the shared audio player     |
| `set_status(rgb)` | Set the status NeoPixel to a (r,g,b) tuple     |
| `exit_requested()` | Default: encoder held for 2 s                  |

The base-class `run()` calls `setup()`, then loops calling `tick()`
and `exit_requested()` until either returns `False`/`True`
respectively. Override `run()` if you need a different lifecycle.

### 4.2 Plain-function template

For micro-subprograms you can skip the class entirely:

```python
# /stim_games/blink.py
import time


def run(machine, config=None):
    pix = machine._pixel
    for _ in range(20):
        if pix is not None:
            pix[0] = (255, 0, 0)
        time.sleep(0.2)
        if pix is not None:
            pix[0] = (0, 0, 0)
        time.sleep(0.2)
```

The loader passes the `Machine` and the parsed sidecar config (if
any) as the first two arguments.

---

## 5. Sidecar Config Files

If a subprogram lives at `stim_games/aac_trainer.py`, the loader
will look for `stim_games/aac_trainer.cfg` next to it and parse it
with `stim_games.game_config.load()`. The parsed result is passed
to the subprogram as:

```python
self.config = {
    "header": {
        # top-level key = value pairs before any [section]
    },
    "sections": {
        # section_name -> list of dicts, one per [section] block
    },
}
```

Format (same INI-ish flavour as `.menu` and `config.txt`):

```
title = AAC Trainer
rounds = 10
penalty_seconds = 30

[question]
prompt = sounds/trainer/thirsty.mp3
answer = water

[question]
prompt = sounds/trainer/hungry.mp3
answer = hungry
```

Values are auto-coerced to `int`, `float`, `True`, or `False`
where appropriate; everything else stays a string. Comments (`#`)
and blank lines are ignored.

---

## 6. Input Handling

The host `InputManager` exposes:

- `poll()` — returns the press index (0..N-1) or `None`
- `selected_index` — the currently-highlighted grid position
  (driven by rotary encoder when `encoder_navigation = true`)
- `encoder_button_held` — bool, raw encoder push state
- optional accessors added by device-specific drivers:
    - `puff_pressed` — true while a Sip-N-Puff puff is over threshold
    - `single_button_pressed` — true while the external 3.5 mm switch is down
    - `_encoder.position` — raw encoder counter

A subprogram is free to read any of these directly. The AAC Trainer
uses a dedicated `_SingleButtonHelper` that decodes
tap / double-tap / hold-to-repeat / long-press-to-exit from a single
momentary input (puff or switch).

### 6.1 Standard exit gestures

For consistency across games, prefer one of:

| Gesture                            | How to implement                            |
|------------------------------------|---------------------------------------------|
| Encoder held 2 s                   | `Subprogram.exit_requested()` default       |
| Single button / puff held 3 s      | `_SingleButtonHelper` emits `"exit"`        |
| Game-over condition (score reached) | Return `False` from `tick()`               |

The Machine's emergency-hold handling (encoder held for
`emergency_hold_seconds`) is **not** active while a subprogram is
running — the subprogram owns the input loop. If you want the same
panic behaviour, call `machine._check_emergency_hold()` yourself.

---

## 7. Display Etiquette

When the subprogram exits, `machine._launch_subprogram()` calls:

```python
machine.display.restore_background()
machine._update_display()
```

which restores the calling menu's background image and redraws the
grid. Anything the subprogram drew on top of the display should
therefore be torn down in `teardown()` — e.g. remove any Groups the
subprogram appended to `display.display.root_group`.

`bubble_pop.py` demonstrates the pattern: it creates its own
overlay Group in `setup()` and removes it from its parent in
`teardown()`.

---

## 8. Audio Etiquette

`self.audio.play(path)` blocks on CircuitPython — the next line
does not run until the sound is complete. For timing-sensitive
games (AAC Trainer tracks per-round elapsed time) compensate by
subtracting the speech duration from your reference timestamp, as
`aac_trainer._say()` does:

```python
t0 = time.monotonic()
self.audio.play(path)
speech_dur = time.monotonic() - t0
self._run_start += speech_dur   # freeze the round timer during speech
```

Do not call `deinit()` on the audio player. It is shared with the
host.

---

## 9. Built-in Subprograms

### 9.1 cause_and_effect.py

Reward-on-any-press stim loop. Every press plays a random sound and
flashes the status pixel a random colour. Includes an idle pulse
after `idle_blink_sec` seconds of inactivity.

Sidecar config keys (`stim_games/cause_and_effect.cfg`):
- `colors = red, green, ...`
- `sounds = path/to/a.mp3, path/to/b.mp3`
- `sound_chance = 70`
- `idle_blink_sec = 5`

### 9.2 bubble_pop.py

Each press spawns a coloured bubble on the screen and plays a pop
sound. Bubbles accumulate up to `max_bubbles` then recycle oldest
first. Falls back to LED-only mode if `displayio` / shape drawing
is unavailable.

Sidecar config keys (`stim_games/bubble_pop.cfg`):
- `pop_sound`
- `max_bubbles`
- `radius`

### 9.3 color_cycle.py

Passive-stim HSV cycle on the status pixel. Any press temporarily
speeds up the cycle, which decays back to the base rate over
`boost_decay_sec`.

Sidecar config keys (`stim_games/color_cycle.cfg`):
- `base_period_ms`
- `boost_period_ms`
- `boost_decay_sec`

### 9.4 aac_trainer.py — Chicken Challenge

Voice-prompt-driven AAC practice game. See the Sip-N-Puff Rubber
Chicken Edition spec for the Maker Faire narrative.

**Flow:**
1. Play the intro sound.
2. For each of N rounds:
   a. Play the question prompt MP3.
   b. Player navigates the trainer menu with encoder / puff / button
      and selects an item.
   c. Play the selected item's own sound.
   d. Play the correct/wrong feedback sound.
   e. Add 30 s penalty to the round time if wrong.
3. Play the "finished" sound.

**Scoring:**
`final_time = wall_clock_time_excluding_speech + wrong_count * 30 s`

The round timer is paused during every audio playback (speech
compensation — see §8) so the user is never penalized for
synthesized speech latency.

**Input modes:**

| Hardware          | Navigate                     | Select          | Exit           |
|-------------------|------------------------------|-----------------|----------------|
| Rotary encoder    | rotate                       | press           | hold 2 s       |
| Single button / puff | tap (1× = +1, hold = repeat, accelerating) | double-tap | hold 3 s |
| Sip-N-Puff sip    | `sip_pressed` if driver emits it — treated as −1 ticks | (uses puff path) | (uses puff path) |

**Config file (`stim_games/aac_trainer.cfg`):**

Top-level keys:
- `answer_menu = trainer.menu`
- `rounds = 10`
- `penalty_seconds = 30`
- `exit_hold_sec = 3.0`
- `double_tap_sec = 0.45`
- `hold_first_ms = 450`
- `hold_min_ms = 60`
- `hold_decay = 0.85`
- `intro_sound`, `correct_sound`, `wrong_sound`, `done_sound`

Each round is a `[question]` section with:
- `prompt = /sounds/trainer/you_are_thirsty.mp3`
- `answer = water`

`answer` must match the `[bracket_id]` of an item in `answer_menu`.

---

## 10. Adding a New Subprogram — Checklist

1. Create `/stim_games/your_game.py` with a `GAME = YourGame`
   class subclassing `Subprogram`.
2. (Optional) Create `/stim_games/your_game.cfg` with any tunables.
3. Add a menu entry under `/menus/games.menu`:
   ```
   [your_game]
   label = Your Game
   submenu = stim_games/your_game.py
   position = N
   ```
4. (Optional) To boot into it directly, set in `/config.txt`:
   ```
   mode = stim_games/your_game.py
   ```
5. Add a row to the table in §9 of this document.
6. If you need new sound assets, list them in the sound-generation
   script (`tools/make_trainer_sounds.py` for the trainer; create a
   new script for other games if appropriate).

---

## 11. Implementation Notes for the Host

### 11.1 `action.py`

```python
# Navigation dispatch — new subprogram branch
if "subprogram" in item:
    return "subprogram:" + str(item["subprogram"])
if "submenu" in item:
    target = str(item["submenu"])
    if target.endswith(".py"):
        return "subprogram:" + target
    return "submenu:" + target
if "list" in item:
    target = str(item["list"])
    if target.endswith(".py"):
        return "subprogram:" + target
    return "list:" + target
```

### 11.2 `machine.py`

```python
elif nav.startswith("subprogram:"):
    target = nav.split(":", 1)[1]
    self._launch_subprogram(target)
    # Redraw the calling menu
    self.display.restore_background()
    self._update_display()
```

And at startup, after init:

```python
mode = self._config.get("mode")
if mode and isinstance(mode, str) and mode.endswith(".py"):
    self._launch_subprogram(mode)
```

### 11.3 `config_reader.py`

The allowlist gains one entry: `"mode"`.

### 11.4 `/stim_games/subprogram.py`

Defines `Subprogram`, `load_subprogram(path, machine, config=None)`,
and `launch_subprogram(machine, path, config=None)`. The latter is
the entry point `Machine._launch_subprogram()` calls into.

---

## 12. Future Work

- **Vibration / haptic feedback** — wire the shared motor driver
  into `Subprogram.set_status()` so games can buzz as well as blink.
- **Leaderboard persistence** — the AAC Trainer currently tracks a
  single run. Adding an on-device leaderboard requires a small
  file-based store (JSON on flash or SD).
- **QR-code game packs** — download a game pack (Python module +
  sidecar config + sound bundle) by scanning a QR code, mirroring
  the planned card-pack workflow in `menu_system.md`.
- **Simulator mode** — a host-side harness that stubs out the
  hardware subsystems so games can be tested on a laptop before
  flashing.

---

## 13. Change Log

| Date       | Change                                                                 |
|------------|------------------------------------------------------------------------|
| 2026-04-18 | Document created. Subprogram framework + stim games + AAC Trainer.     |
