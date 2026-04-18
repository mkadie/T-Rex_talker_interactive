"""Color Cycle / Kaleidoscope stim game.

A passive-stim animated colour cycle on the status pixel and (if the
display supports it) a tinted rectangle overlay. Any input nudges the
cycle speed faster, then it eases back. Encoder rotation changes the
colour family.

Inputs
------
* Any button / touch -> bump speed
* Encoder rotate     -> shift hue
* Encoder hold 2 s   -> exit

Configuration (stim_games/color_cycle.cfg)
------------------------------------------
    base_period_ms = 80
    boost_period_ms = 30
    boost_decay_sec = 4
"""

import time

from stim_games.subprogram import Subprogram


def _hsv_to_rgb(h, s, v):
    """h in [0,360), s and v in [0,1]. Returns (r,g,b) 0..255."""
    if s <= 0:
        x = int(v * 255)
        return (x, x, x)
    h6 = (h % 360) / 60.0
    i = int(h6)
    f = h6 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))


class ColorCycle(Subprogram):
    name = "Color Cycle"

    def setup(self):
        self._hue = 0
        self._period = self._get_cfg("base_period_ms", 80) / 1000.0
        self._base = self._period
        self._boost = self._get_cfg("boost_period_ms", 30) / 1000.0
        self._decay = self._get_cfg("boost_decay_sec", 4)
        self._last_step = time.monotonic()
        self._last_boost = 0
        try:
            self.display.set_text("Color Cycle")
        except Exception:  # noqa: BLE001
            pass

    def tick(self):
        now = time.monotonic()

        pressed = self.input.poll()
        if pressed is not None:
            # Bump speed: shorter period, then decay back
            self._period = self._boost
            self._last_boost = now

        # Decay boost back toward base period
        if self._period < self._base:
            elapsed = now - self._last_boost
            if elapsed >= self._decay:
                self._period = self._base
            else:
                ratio = elapsed / self._decay
                self._period = self._boost + (self._base - self._boost) * ratio

        # Step hue
        if now - self._last_step >= self._period:
            self._hue = (self._hue + 5) % 360
            self.set_status(_hsv_to_rgb(self._hue, 1.0, 0.5))
            self._last_step = now

        return True

    def _get_cfg(self, key, default):
        hdr = (self.config or {}).get("header", {}) if self.config else {}
        return hdr.get(key, default)


GAME = ColorCycle
