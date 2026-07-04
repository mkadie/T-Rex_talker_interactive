"""Multi-Lingual language picker.

Runs as a subprogram (typically as the boot-time `mode` in config.txt).
The encoder scrolls through supported languages, showing a full-screen
banner image for each. Pressing the encoder commits the choice: the
Machine's active menu_stack is swapped to the corresponding
`lang_<code>.menu` and the subprogram exits, dropping the user into
the talker with that language loaded.

If the user does nothing for AUTO_COMMIT_SEC seconds, the currently-
highlighted language is auto-committed (boot defaults to English unless
the user scrolled).

Assets expected on flash:
  /lang_images/lang_<code>.bmp   (320x240, used as full-screen banner)
  /menus/lang_<code>.menu        (loaded on commit)
"""

import time

from stim_games.subprogram import Subprogram


# (lang_code, english_name, native_name, menu_filename)
# Schema matches repo machine.py's LANGUAGES so a future shared picker
# can swap between them without re-authoring.
LANGUAGES = (
    ("th", "Thai",       "ไทย",                     "lang_th.menu"),
    ("ja", "Japanese",   "日本語",                     "lang_ja.menu"),
    ("en", "English",    "English",                                 "lang_en.menu"),
    ("zh", "Mandarin",   "中文",                           "lang_zh.menu"),
    ("hi", "Hindi",      "हिन्दी",   "lang_hi.menu"),
    ("es", "Spanish",    "Español",                            "lang_es.menu"),
    ("fr", "French",     "Français",                           "lang_fr.menu"),
    ("ar", "Arabic",     "العربية", "lang_ar.menu"),
    ("bn", "Bengali",    "বাংলা",         "lang_bn.menu"),
    ("pt", "Portuguese", "Português",                          "lang_pt.menu"),
    ("ru", "Russian",    "Русский", "lang_ru.menu"),
    ("cs", "Czech",      "Čeština",                       "lang_cs.menu"),
    ("de", "German",     "Deutsch",                            "lang_de.menu"),
)

DEFAULT_CODE = "en"
AUTO_COMMIT_SEC = 10.0


class MultiLingual(Subprogram):
    name = "Multi-Lingual"

    def setup(self):
        self._index = 0
        for i, lang in enumerate(LANGUAGES):
            if lang[0] == DEFAULT_CODE:
                self._index = i
                break

        # Pre-resolve image paths so each scroll detent skips storage lookup.
        self._image_paths = tuple(
            self.storage.resolve_path("/lang_images/lang_{}.bmp".format(lang[0]))
            if self.storage is not None
            else "/lang_images/lang_{}.bmp".format(lang[0])
            for lang in LANGUAGES
        )

        enc = self.input._encoder
        self._last_pos = enc.position if enc is not None else 0
        self._flip = getattr(self.input, "_encoder_flip", 1)

        self._press_was_down = False
        self._deadline = time.monotonic() + AUTO_COMMIT_SEC

        self._show_current()
        # Boot-mode users haven't seen the talker yet — pulse the LED so
        # it's visibly clear the device is alive and waiting for a pick.
        self.set_status((0, 0, 255))

    def tick(self):
        enc = self.input._encoder
        if enc is not None:
            pos = enc.position
            delta = pos - self._last_pos
            if delta != 0:
                self._last_pos = pos
                self._index = (self._index - delta * self._flip) % len(LANGUAGES)
                self._show_current()
                self.machine.sleep.activity()
                self._deadline = time.monotonic() + AUTO_COMMIT_SEC

        pressed = bool(getattr(self.input, "encoder_button_held", False))
        if pressed and not self._press_was_down:
            self._press_was_down = True
            self._deadline = time.monotonic() + AUTO_COMMIT_SEC
        elif not pressed and self._press_was_down:
            self._press_was_down = False
            self._commit()
            return False

        if time.monotonic() >= self._deadline:
            print("Multi-Lingual: auto-commit after {}s".format(AUTO_COMMIT_SEC))
            self._commit()
            return False

        return True

    def teardown(self):
        # Drop the latched press from input_manager so the talker doesn't
        # immediately re-trigger from the same click on resume.
        if hasattr(self.input, "reset_button_latch"):
            self.input.reset_button_latch()

    # ---- internal helpers ------------------------------------------------

    def _show_current(self):
        _code, en_name, native_name, _menu = LANGUAGES[self._index]
        path = self._image_paths[self._index]
        try:
            self.display.show_image(path)
        except Exception as e:
            print("Multi-Lingual: image load error ({}):".format(e), path)
            self.display.set_text("{} / {}".format(en_name, native_name))
        print("Multi-Lingual: highlight", en_name)

    def _commit(self):
        _code, en_name, _native, menu_file = LANGUAGES[self._index]
        print("Multi-Lingual: commit", en_name, "->", menu_file)

        # Repaint background BEFORE the MenuStack swap so the big banner
        # goes away cleanly even if the menu load raises.
        self.display.restore_background()

        from menu_parser import MenuStack
        m = self.machine
        # Retry the MenuStack load — the ESP32-S3 N16R8 flash-read race
        # that bit code.py imports also catches first-time .menu reads.
        for attempt in range(3):
            try:
                m._menu_stack = MenuStack(
                    m._menus_dir, menu_file, storage=m.storage)
                m._build_grid()
                m._update_display()
                if hasattr(m, "_reset_selection"):
                    m._reset_selection()
                print("Multi-Lingual: loaded", menu_file)
                return
            except Exception as e:
                print("Multi-Lingual: menu load attempt {} failed: {}".format(
                    attempt + 1, e))
                time.sleep(0.1)
        print("Multi-Lingual: gave up loading", menu_file)


GAME = MultiLingual
