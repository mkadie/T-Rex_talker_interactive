"""Bubble Pop stim game.

Each press spawns a short "pop" event: a colour flash on the
status pixel plus a pop sound. If `displayio` is available,
coloured circles are also drawn on the screen at positions
that match the pressed button (or random positions for encoder/
touch events outside the grid).

Inputs
------
* Any press  -> spawn a bubble (colour flash + pop sound)
* Encoder turn -> slide a bubble across the screen
* Encoder held 2 s -> exit

Configuration (stim_games/bubble_pop.cfg)
-----------------------------------------
    pop_sound = button_sounds/yes.mp3
    max_bubbles = 5
    radius = 20
"""

import time
import random

from stim_games.subprogram import Subprogram


BUBBLE_COLORS = [
    0xFF0044, 0x00FF88, 0x0088FF, 0xFFFF00,
    0xFF00FF, 0x00FFFF, 0xFFAA00, 0xAAFF00,
]


class BubblePop(Subprogram):
    name = "Bubble Pop"

    def setup(self):
        self._group = None
        self._bubbles = []
        self._max = self._get_cfg("max_bubbles", 5)
        self._radius = self._get_cfg("radius", 20)
        self._pop_sound = self._get_cfg("pop_sound", "/button_sounds/more.mp3")

        # Try to attach an overlay group to the display for drawing
        try:
            import displayio
            self._displayio = displayio
            disp = getattr(self.display, "display", None)
            if disp is not None:
                self._group = displayio.Group()
                disp.root_group.append(self._group)
            self._w = getattr(disp, "width", 320) if disp else 320
            self._h = getattr(disp, "height", 240) if disp else 240
        except Exception as e:  # noqa: BLE001
            print("BubblePop: display overlay unavailable:", e)
            self._displayio = None

        try:
            self.display.set_text("Bubble Pop")
        except Exception:  # noqa: BLE001
            pass

    def tick(self):
        pressed = self.input.poll()
        if pressed is not None:
            self._spawn(pressed)
        # Fade oldest bubble if we're at cap
        if len(self._bubbles) > self._max:
            self._pop_oldest()
        return True

    def teardown(self):
        # Remove all drawn bubbles so they don't clutter the menu
        if self._group is not None:
            try:
                parent = self._group.parent if hasattr(self._group, "parent") else None
            except Exception:  # noqa: BLE001
                parent = None
            try:
                if parent is not None:
                    parent.remove(self._group)
            except Exception:  # noqa: BLE001
                pass
        self._bubbles = []

    # --- helpers ---------------------------------------------------------

    def _spawn(self, button_index):
        color = random.choice(BUBBLE_COLORS)
        # Flash status LED
        rgb = ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)
        self.set_status(rgb)
        # Play pop sound
        self.play_sound(self._pop_sound)
        # Draw a circle if we have a display group
        if self._group is not None and self._displayio is not None:
            try:
                from adafruit_display_shapes.circle import Circle
                x = random.randint(self._radius, max(self._w - self._radius, self._radius + 1))
                y = random.randint(self._radius, max(self._h - self._radius, self._radius + 1))
                circle = Circle(x, y, self._radius, fill=color, outline=0xFFFFFF)
                self._group.append(circle)
                self._bubbles.append(circle)
            except Exception as e:  # noqa: BLE001
                print("BubblePop: circle draw error:", e)
        # Fade LED back down
        time.sleep(0.1)
        self.set_status((0, 0, 32))

    def _pop_oldest(self):
        if not self._bubbles:
            return
        victim = self._bubbles.pop(0)
        try:
            self._group.remove(victim)
        except Exception:  # noqa: BLE001
            pass

    def _get_cfg(self, key, default):
        hdr = (self.config or {}).get("header", {}) if self.config else {}
        return hdr.get(key, default)


GAME = BubblePop
