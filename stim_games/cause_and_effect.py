"""Cause-and-Effect stim game.

The simplest possible interactive loop: every press lights the
status pixel a new colour and plays a short sound. Designed for
pre-verbal / early-cause-and-effect learners.

Inputs
------
* Any button  -> trigger a reward event (colour + sound)
* Rotary encoder turn -> trigger a reward event
* Encoder held 2 s -> exit back to the menu

Configuration (stim_games/cause_and_effect.cfg)
-----------------------------------------------
    colors = red, green, blue, yellow, purple, orange, white, pink
    sounds = button_sounds/yes.mp3, button_sounds/more.mp3
    sound_chance = 70         # % chance each press plays a sound
    idle_blink_sec = 5        # inactivity before pixel blinks softly
"""

import time
import random

from stim_games.subprogram import Subprogram


COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
    (128, 0, 255),
    (255, 128, 0),
    (255, 255, 255),
    (255, 105, 180),
]


class CauseAndEffect(Subprogram):
    name = "Cause and Effect"

    def setup(self):
        self._last_event = time.monotonic()
        self._idle_blink = self._get_cfg("idle_blink_sec", 5)
        self._sounds = self._get_cfg_list(
            "sounds",
            ["/button_sounds/yes.mp3"],
        )
        self._sound_chance = self._get_cfg("sound_chance", 70)
        # Visually mark we're in stim mode
        try:
            self.display.set_text("Cause & Effect")
        except Exception:  # noqa: BLE001
            pass
        self.set_status((0, 0, 64))  # dim blue "ready"

    def tick(self):
        # Any press (touch grid, button, or encoder click) triggers a reward
        pressed = self.input.poll()
        if pressed is not None:
            self._reward()
            return True

        # Idle blink
        if time.monotonic() - self._last_event > self._idle_blink:
            self._idle_pulse()
            self._last_event = time.monotonic()

        return True

    # --- helpers ---------------------------------------------------------

    def _reward(self):
        color = random.choice(COLORS)
        self.set_status(color)
        self._last_event = time.monotonic()
        # Probabilistic sound so it doesn't become overwhelming
        if random.randint(0, 99) < self._sound_chance and self._sounds:
            self.play_sound(random.choice(self._sounds))
        # Fade back to a dim "ready" colour
        time.sleep(0.25)
        self.set_status((0, 0, 32))

    def _idle_pulse(self):
        for level in (8, 16, 32, 16, 8):
            self.set_status((level, level, level))
            time.sleep(0.05)

    def _get_cfg(self, key, default):
        hdr = (self.config or {}).get("header", {}) if self.config else {}
        return hdr.get(key, default)

    def _get_cfg_list(self, key, default):
        raw = self._get_cfg(key, None)
        if raw is None:
            return list(default)
        if isinstance(raw, (list, tuple)):
            return list(raw)
        return [x.strip() for x in str(raw).split(",") if x.strip()]


# The module-level hook the subprogram loader uses
GAME = CauseAndEffect
