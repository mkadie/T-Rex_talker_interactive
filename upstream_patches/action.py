# ---------------------------------------------------------------------------
# Modified file — originally from T-Rex Talker (https://github.com/mkadie).
#
# Upstream license: MIT.
#     Copyright (c) T-Rex Talker contributors. All rights reserved under MIT.
#     Permission is hereby granted, free of charge, to any person obtaining
#     a copy of the upstream software and associated documentation files,
#     to deal in the Software without restriction, subject to the conditions
#     in the upstream LICENSE file. See ../NOTICE for the full MIT text.
#
# Modifications in this file were added as part of T-Rex Talker Interactive
# and are licensed under the PolyForm Noncommercial License 1.0.0.
# See ../LICENSE for terms and ../upstream_patches/README.md for what changed.
# ---------------------------------------------------------------------------
"""Action executor for AAC press events.

Each press item in a .menu file can trigger multiple actions.
This class reads the action keys from an item dict and executes
them in order through the device's hardware subsystems.
"""

import time


# Named colors for light actions
COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 128, 0),
    "purple": (128, 0, 255),
    "pink": (255, 105, 180),
    "white": (255, 255, 255),
    "off": (0, 0, 0),
}


def _parse_color(value):
    """Convert a color name or hex string to an (r, g, b) tuple."""
    if isinstance(value, tuple):
        return value
    value = value.strip().lower()
    if value in COLORS:
        return COLORS[value]
    # Try hex: #RRGGBB
    if value.startswith("#") and len(value) == 7:
        r = int(value[1:3], 16)
        g = int(value[3:5], 16)
        b = int(value[5:7], 16)
        return (r, g, b)
    return COLORS.get("white")


class Action:
    """Executes actions for a press event using device hardware.

    Construct with references to the hardware subsystems, then call
    execute(item_dict) for each press.
    """

    def __init__(self, audio=None, display=None, pixel=None,
                 menus_dir="/menus", storage=None, config=None):
        """Set up action executor with hardware references.

        Args:
            audio: AudioPlayer instance (or None if no audio).
            display: DisplayManager instance (or None).
            pixel: NeoPixel object (or None if no status LED).
            menus_dir: Base directory for resolving relative paths.
            storage: StorageManager instance (or None if no SD card).
        """
        self._audio = audio
        self._display = display
        self._pixel = pixel
        self._menus_dir = menus_dir
        self._storage = storage
        self._zoom_enabled = config.get("zoom_image_enabled", False) if config else False

    def execute(self, item):
        """Execute all actions defined in a press item dict.

        Actions are processed in this order:
            1. light / light_pattern (visual feedback — immediate)
            2. vibrate (haptic feedback — immediate)
            3. image (display picture)
            4. text (display text)
            5. sound (play audio — blocks until done)

        Navigation actions (submenu, list, back) are NOT executed here.
        They are returned as a string so the caller can handle navigation.

        Args:
            item: Dict from menu_parser with action keys.

        Returns:
            Navigation action string or None:
                "submenu:filename.menu"      — navigate to submenu
                "list:filename.menu"         — navigate to list
                "subprogram:stim_games/x.py" — launch a Python subprogram
                "back"                       — go back
                None                         — no navigation

            Subprograms can also be triggered by giving a submenu/list
            value that ends in ".py" — see the Subprogram docs.
        """
        if item is None:
            return None

        # Light feedback
        self._do_light(item)

        # Vibration feedback
        self._do_vibrate(item)

        # Display image
        self._do_image(item)

        # Display text
        self._do_text(item)

        # Play sound (blocking)
        self._do_sound(item)

        # Reset light after sound finishes
        if self._pixel and item.get("light"):
            self._pixel[0] = (0, 0, 0)

        # Check for navigation / subprogram actions.
        #
        # Subprogram dispatch: if a submenu/list value ends in .py, the
        # target is a Python subprogram (e.g. a stim game) rather than
        # another .menu file. We emit "subprogram:<path>" so that Machine
        # routes to the subprogram launcher instead of MenuStack.
        # An explicit `subprogram = ...` key is also supported.
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
        if "back" in item:
            return "back"

        return None

    def _resolve_path(self, path):
        """Resolve a menu-relative path to absolute, checking SD card first."""
        if not path:
            return path
        if not path.startswith("/"):
            path = self._menus_dir + "/" + path
        if self._storage:
            return self._storage.resolve_path(path)
        return path

    def _do_sound(self, item):
        """Play a sound file if specified."""
        sound_path = item.get("sound")
        if not sound_path or not self._audio:
            return
        try:
            self._audio.play(self._resolve_path(sound_path))
        except Exception as e:
            print("Action: sound error:", e)

    def _do_vibrate(self, item):
        """Activate vibration if specified.

        Currently prints to console. Actual vibration requires a
        motor driver — this is a placeholder for future hardware.
        """
        pattern = item.get("vibrate")
        if not pattern:
            return
        # Placeholder — real implementation needs motor/haptic hardware
        print("Action: vibrate:", pattern)

    def _do_light(self, item):
        """Set NeoPixel color if specified."""
        color_name = item.get("light")
        if not color_name or not self._pixel:
            return
        color = _parse_color(color_name)
        self._pixel[0] = color

    def _do_image(self, item):
        """Display a zoom image during playback if enabled.

        Skipped for navigation items (submenu/back) and when
        zoom_image_enabled is false in config.
        """
        if not self._zoom_enabled:
            return
        # Don't zoom for navigation items
        if "submenu" in item or "list" in item or "back" in item:
            return
        image_path = item.get("image")
        if not image_path or not self._display:
            return

        resolved = self._resolve_path(image_path)
        print("Action: image:", resolved)
        try:
            self._display.show_image(resolved)
        except Exception as e:
            print("Action: image error:", e)

    def _do_text(self, item):
        """Display text on screen if specified.

        TODO: Implement text rendering overlay on display.
        """
        text = item.get("text")
        if not text:
            return
        # Placeholder — needs DisplayManager text overlay support
        print("Action: text:", text)
