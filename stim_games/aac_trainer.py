"""AAC Communication Game.

Runs on top of the base AAC software. The game loads a menu of AAC
items (by default the current start_menu), plays an audio prompt,
and asks the player to navigate to and select the correct AAC item.
Questions form a round; score is total time with a 30-second
penalty per wrong answer.

Features a high-score leaderboard (top 3 lowest times) with name
entry via encoder. Names are filtered for profanity.
"""

import time

try:
    import random
except ImportError:
    random = None

from stim_games.subprogram import Subprogram


# Defaults — overrideable from aac_trainer.cfg [header] ------------------
DEFAULT_ROUND_COUNT = 10
DEFAULT_PENALTY_SEC = 30
DEFAULT_EXIT_HOLD_SEC = 3.0
DEFAULT_DOUBLE_TAP_SEC = 0.45
DEFAULT_HOLD_FIRST_MS = 450
DEFAULT_HOLD_MIN_MS = 60
DEFAULT_HOLD_DECAY = 0.85
DEFAULT_RANDOMIZE = True
HISCORE_FILE = "/sd/hiscores.txt"
MAX_HISCORES = 3
NAME_LENGTH = 5

# Characters for name entry — space first, then A-Z, then 0-9
NAME_CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Profanity filter — common words and fragments to catch
_BAD_WORDS = {
    "FUCK", "SHIT", "DICK", "COCK", "CUNT", "BITCH", "ASS",
    "DAMN", "HELL", "PISS", "SLUT", "WHORE", "NIGGA", "NIGGE",
    "FAGGO", "FAG", "TWAT", "TITS", "BOOB", "PENIS", "VAGIN",
    "ANUS", "DILDO", "PORN", "RAPE", "NAZI", "KIKE", "SPIC",
    "CHINK", "GOOK", "WETBA",
}


def _is_profane(name):
    """Check if name contains profanity (substring match)."""
    upper = name.upper().replace(" ", "")
    for word in _BAD_WORDS:
        if word in upper:
            return True
    return False


class AacTrainer(Subprogram):
    name = "Communication Game"

    # ----- lifecycle ----------------------------------------------------

    def setup(self):
        hdr = self._header()
        secs = self._sections()

        self._round_count = int(hdr.get("rounds", DEFAULT_ROUND_COUNT))
        self._penalty = int(hdr.get("penalty_seconds", DEFAULT_PENALTY_SEC))
        self._exit_hold = float(hdr.get("exit_hold_sec", DEFAULT_EXIT_HOLD_SEC))
        self._double_tap = float(hdr.get("double_tap_sec", DEFAULT_DOUBLE_TAP_SEC))
        self._hold_first_ms = int(hdr.get("hold_first_ms", DEFAULT_HOLD_FIRST_MS))
        self._hold_min_ms = int(hdr.get("hold_min_ms", DEFAULT_HOLD_MIN_MS))
        self._hold_decay = float(hdr.get("hold_decay", DEFAULT_HOLD_DECAY))
        self._randomize = bool(hdr.get("randomize", DEFAULT_RANDOMIZE))

        self._intro_sound = hdr.get("intro_sound",
                                    "/sounds/trainer/welcome.mp3")
        self._correct_sound = hdr.get("correct_sound",
                                      "/sounds/trainer/correct.mp3")
        self._wrong_sound = hdr.get("wrong_sound",
                                    "/sounds/trainer/try_again.mp3")
        self._done_sound = hdr.get("done_sound",
                                   "/sounds/trainer/finished.mp3")

        self._round_index = 0
        self._questions = list(secs.get("question", []))
        if not self._questions:
            print("Communication Game: no questions configured; nothing to do")
            self._done = True
            return

        if self._round_count > len(self._questions):
            self._round_count = len(self._questions)

        if self._randomize and random is not None:
            try:
                random.shuffle(self._questions)
            except AttributeError:
                for i in range(len(self._questions) - 1, 0, -1):
                    j = random.randint(0, i)
                    self._questions[i], self._questions[j] = self._questions[j], self._questions[i]

        self._answer_menu_file = hdr.get("answer_menu",
                                         self.machine._start_menu)

        self._score_sec = 0.0
        self._wrong_count = 0
        self._round_index = 0
        self._done = False
        self._showing_score = False
        self._prev_enc_click = False

        self._btn_helper = _SingleButtonHelper(
            self.input,
            first_delay_ms=self._hold_first_ms,
            min_interval_ms=self._hold_min_ms,
            decay=self._hold_decay,
            double_tap_sec=self._double_tap,
            exit_hold_sec=self._exit_hold,
        )
        self._last_sel = getattr(self.input, '_selected_index', 0)

        self._nav_stack = []
        self._items = []
        self._sel_index = 0
        self._current_path = []
        self._path_pos = 0

        # Load high scores and show start screen
        self._hiscores = self._load_hiscores()
        self._run_start = time.monotonic()
        self._show_start_screen()
        self.set_status((0, 128, 255))
        self._say(self._intro_sound)
        self._wait_for_button()
        self._run_start = time.monotonic()
        self._ask(self._round_index)

    def tick(self):
        if self._done:
            # Round finished — handle end-of-round, then restart
            self._end_round()
            self._restart_round()
            return True

        press = self.input.poll()

        cur_sel = getattr(self.input, '_selected_index', 0)
        if cur_sel != self._last_sel:
            self._last_sel = cur_sel
            if self._items:
                self._sel_index = cur_sel % len(self._items)
                try:
                    self.display.set_highlight(self._sel_index)
                except Exception:
                    pass
                self._update_item_text()

        if press is not None:
            self._commit_selection()

        ev = self._btn_helper.poll()
        if ev == "tick_fwd":
            self._move_selection(+1)
        elif ev == "tick_back":
            self._move_selection(-1)
        elif ev == "select":
            self._commit_selection()
        elif ev == "exit":
            print("Communication Game: exit gesture")
            return False

        return True

    def _end_round(self):
        """Handle scoring, name entry, and hiscore save after a round."""
        elapsed = time.monotonic() - self._run_start
        total = elapsed + self._score_sec
        print("Communication Game: run finished in {:.1f}s "
              "(wrong: {})".format(total, self._wrong_count))
        self._say(self._done_sound)

        rank = self._get_rank(total)
        if rank is not None:
            player_name = self._name_entry_screen(total)
            self._insert_hiscore(total, player_name, rank)
            self._save_hiscores()

    def _restart_round(self):
        """Reset state and show start screen for a new round."""
        self._hiscores = self._load_hiscores()
        self._show_start_screen()
        self._say(self._intro_sound)
        self._wait_for_button()

        # Re-shuffle questions
        if self._randomize and random is not None:
            try:
                random.shuffle(self._questions)
            except AttributeError:
                for i in range(len(self._questions) - 1, 0, -1):
                    j = random.randint(0, i)
                    self._questions[i], self._questions[j] = self._questions[j], self._questions[i]

        self._score_sec = 0.0
        self._wrong_count = 0
        self._round_index = 0
        self._done = False
        self._run_start = time.monotonic()
        self._ask(self._round_index)

    def teardown(self):
        pass

    # ----- high scores ---------------------------------------------------

    def _load_hiscores(self):
        """Load high scores from file. Returns list of (seconds, name)."""
        scores = []
        try:
            with open(HISCORE_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(None, 1)
                    if len(parts) >= 2:
                        scores.append((float(parts[0]), parts[1]))
                    elif len(parts) == 1:
                        scores.append((float(parts[0]), "???"))
        except Exception:
            pass
        scores.sort(key=lambda x: x[0])
        return scores[:MAX_HISCORES]

    def _save_hiscores(self):
        """Write high scores to file."""
        try:
            with open(HISCORE_FILE, "w") as f:
                for secs, name in self._hiscores:
                    f.write("{:.1f} {}\n".format(secs, name))
            print("Communication Game: saved hiscores")
        except Exception as e:
            print("Communication Game: could not save hiscores:", e)

    def _get_rank(self, total_seconds):
        """Return rank (0-2) if this time beats a top-3 score, else None."""
        for i, (s, _n) in enumerate(self._hiscores):
            if total_seconds < s:
                return i
        if len(self._hiscores) < MAX_HISCORES:
            return len(self._hiscores)
        return None

    def _insert_hiscore(self, total_seconds, name, rank):
        """Insert a new score at the given rank."""
        self._hiscores.insert(rank, (total_seconds, name))
        self._hiscores = self._hiscores[:MAX_HISCORES]

    def _format_time(self, seconds):
        m = int(seconds) // 60
        s = int(seconds) % 60
        return "{}:{:02d}".format(m, s)

    # ----- start screen with high scores ---------------------------------

    def _show_start_screen(self):
        """Show title screen with top 3 high scores. Minimal objects."""
        import gc
        gc.collect()
        import displayio
        try:
            from adafruit_display_text import label
            import terminalio
        except ImportError:
            return

        w = self.display._width
        h = self.display._height

        group = displayio.Group()

        # Black background
        bg = displayio.Bitmap(w, h, 1)
        pal = displayio.Palette(1)
        pal[0] = 0x000000
        group.append(displayio.TileGrid(bg, pixel_shader=pal))

        # Title — single label
        title_lbl = label.Label(
            terminalio.FONT,
            text="Communication Game",
            color=0xFFFF00,
            scale=2,
            anchor_point=(0.5, 0.0),
            anchored_position=(w // 2, 12),
        )
        group.append(title_lbl)

        # Build scores as single text block
        if self._hiscores:
            lines = ["-- BEST TIMES --"]
            for i, (secs, name) in enumerate(self._hiscores):
                lines.append("{}. {} {}".format(
                    i + 1, self._format_time(secs), name))
            scores_lbl = label.Label(
                terminalio.FONT,
                text="\n".join(lines),
                color=0x00FF00,
                scale=2,
                anchor_point=(0.5, 0.5),
                anchored_position=(w // 2, h // 2 + 10),
            )
            group.append(scores_lbl)

        # Hint
        hint_lbl = label.Label(
            terminalio.FONT,
            text="Press button to start",
            color=0xAAAAAA,
            scale=2,
            anchor_point=(0.5, 1.0),
            anchored_position=(w // 2, h - 10),
        )
        group.append(hint_lbl)

        self.display._display.root_group = group
        self._showing_score = True

    def _dismiss_score_screen(self):
        if self._showing_score:
            self.display._display.root_group = self.display._splash
            self._showing_score = False

    def _wait_for_button(self):
        while True:
            press = self.input.poll()
            if press is not None:
                break
            time.sleep(0.05)

    # ----- name entry screen ---------------------------------------------

    def _name_entry_screen(self, total_seconds):
        """Let the player enter a 5-letter name using the encoder.

        Encoder rotates through characters, button advances to next slot.
        After 5 characters, returns the name string.
        Uses a single persistent display group with updatable labels to
        minimize memory allocation.
        """
        import gc
        gc.collect()
        import displayio
        try:
            from adafruit_display_text import label
            import terminalio
        except ImportError:
            return "ANON"

        w = self.display._width
        h = self.display._height
        chars = NAME_CHARS
        name = [0] * NAME_LENGTH  # indices into chars

        # Build display group once — update labels in place
        group = displayio.Group()

        bg = displayio.Bitmap(w, h, 1)
        pal = displayio.Palette(1)
        pal[0] = 0x000000
        group.append(displayio.TileGrid(bg, pixel_shader=pal))

        hs_lbl = label.Label(
            terminalio.FONT, text="NEW HIGH SCORE!",
            color=0x00FF00, scale=2,
            anchor_point=(0.5, 0.0),
            anchored_position=(w // 2, 10),
        )
        group.append(hs_lbl)

        time_lbl = label.Label(
            terminalio.FONT, text=self._format_time(total_seconds),
            color=0xFFFF00, scale=3,
            anchor_point=(0.5, 0.0),
            anchored_position=(w // 2, 45),
        )
        group.append(time_lbl)

        prompt_lbl = label.Label(
            terminalio.FONT, text="Enter name:",
            color=0xAAAAAA, scale=2,
            anchor_point=(0.5, 0.0),
            anchored_position=(w // 2, 85),
        )
        group.append(prompt_lbl)

        # Single label shows the full name string with cursor indicator
        name_lbl = label.Label(
            terminalio.FONT, text="_ _ _ _ _",
            color=0xFFFF00, scale=3,
            anchor_point=(0.5, 0.5),
            anchored_position=(w // 2, 145),
        )
        group.append(name_lbl)

        hint_lbl = label.Label(
            terminalio.FONT, text="Rotate=letter Press=next",
            color=0x888888, scale=1,
            anchor_point=(0.5, 1.0),
            anchored_position=(w // 2, h - 5),
        )
        group.append(hint_lbl)

        self.display._display.root_group = group

        # Take over encoder
        saved_max = getattr(self.input, '_max_index', 8)
        self.input._max_index = len(chars)
        self.input._selected_index = 0
        if hasattr(self.input, '_encoder') and self.input._encoder:
            self.input._last_encoder_pos = self.input._encoder.position

        def _render_name():
            """Update name label text showing cursor position."""
            parts = []
            for i in range(NAME_LENGTH):
                ch = chars[name[i]]
                if ch == " ":
                    ch = "_"
                parts.append(ch)
            name_lbl.text = " ".join(parts)

        _render_name()

        slot = 0
        while slot < NAME_LENGTH:
            press = self.input.poll()
            cur = getattr(self.input, '_selected_index', 0)
            cur = cur % len(chars)
            if cur != name[slot]:
                name[slot] = cur
                _render_name()
            if press is not None:
                slot += 1
                if slot < NAME_LENGTH:
                    self.input._selected_index = 0
                    self.input._max_index = len(chars)
                    if hasattr(self.input, '_encoder') and self.input._encoder:
                        self.input._last_encoder_pos = self.input._encoder.position
                    name[slot] = 0
                    _render_name()
            time.sleep(0.03)

        # Restore encoder
        self.input._max_index = saved_max

        result = "".join(chars[c] for c in name).strip()
        if not result:
            result = "ANON"

        if _is_profane(result):
            result = "Rude!"
            print("Communication Game: profanity filtered")

        print("Communication Game: name entered:", result)
        return result

    # ----- question / answer flow ----------------------------------------

    def _ask(self, idx):
        if self._showing_score:
            self._dismiss_score_screen()

        q = self._questions[idx]
        prompt = q.get("prompt")
        raw_answer = str(q.get("answer", ""))
        self._current_path = [
            p for p in raw_answer.replace("\\", "/").split("/") if p
        ]
        self._path_pos = 0

        print("Communication Game: Q{}/{} prompt={} path={}".format(
            idx + 1, self._round_count, prompt, self._current_path))

        self._nav_stack = []
        self._load_menu(self._answer_menu_file)

        if prompt:
            self._say(prompt)

    def _commit_selection(self):
        if self._round_index >= self._round_count:
            return
        if not self._items:
            return

        selected = self._items[self._sel_index]
        selected_id = str(selected.get("id", ""))

        if "back" in selected:
            self._navigate_back()
            if self._path_pos > 0:
                self._path_pos -= 1
            return

        expected = (self._current_path[self._path_pos]
                    if self._path_pos < len(self._current_path) else None)
        print("Communication Game: selected {} (expected {} at step {}/{})".format(
            selected_id, expected, self._path_pos + 1,
            len(self._current_path)))

        if expected and selected_id == expected:
            self._path_pos += 1
            if self._path_pos >= len(self._current_path):
                self._finalize_answer(selected, correct=True)
            else:
                submenu = selected.get("submenu")
                if submenu and not str(submenu).endswith(".py"):
                    self._load_menu(str(submenu))
                else:
                    print("Communication Game: path expects submenu but item "
                          "'{}' has none".format(selected_id))
                    self._finalize_answer(selected, correct=False)
        else:
            self._finalize_answer(selected, correct=False)

    def _finalize_answer(self, selected, correct):
        item_sound = selected.get("sound")
        if item_sound:
            self._say(self._resolve(item_sound))

        if correct:
            self.set_status((0, 255, 0))
            self._say(self._correct_sound)
        else:
            self.set_status((255, 0, 0))
            self._say(self._wrong_sound)
            self._wrong_count += 1
            self._score_sec += self._penalty

        self._round_index += 1
        if self._round_index >= self._round_count:
            self._done = True
        else:
            self._ask(self._round_index)

    def _move_selection(self, delta):
        if not self._items:
            return
        self._sel_index = (self._sel_index + delta) % len(self._items)
        try:
            self.input._selected_index = self._sel_index
        except Exception:
            pass
        self._last_sel = self._sel_index
        try:
            self.display.set_highlight(self._sel_index)
        except Exception:
            pass
        self._update_item_text()

    def _update_item_text(self):
        """Update the display text overlay with the selected item's description."""
        if not self._items or self._sel_index >= len(self._items):
            return
        item = self._items[self._sel_index]
        text = item.get("text_description", item.get("label", ""))
        try:
            self.display.set_text(text)
        except Exception:
            pass

    # ----- menu navigation ------------------------------------------------

    def _load_menu(self, menu_file):
        from menu_parser import parse_menu_file
        menus_dir = getattr(self.machine, "_menus_dir", "/menus")
        menu_path = menus_dir + "/" + menu_file
        if self.storage:
            menu_path = self.storage.resolve_path(menu_path)
        print("Communication Game: load menu:", menu_path)
        try:
            header, items = parse_menu_file(menu_path)
        except Exception as e:
            print("Communication Game: cannot load", menu_path, ":", e)
            header = {}
            items = []
        self._items = items
        self._sel_index = 0
        self._nav_stack.append(menu_file)

        menu_cols = header.get("columns",
                               self.machine._config.get("button_cols", 4))
        menu_rows = header.get("rows",
                               self.machine._config.get("button_rows", 2))
        try:
            self.display._cols = menu_cols
            self.display._rows = menu_rows
            self.display._zone_width = self.display._width // menu_cols
            self.display._zone_height = self.display._height // menu_rows
        except Exception:
            pass

        try:
            self.input._max_index = len(items)
            self.input._selected_index = 0
            self.input._last_encoder_pos = getattr(
                self.input, '_encoder', None) and self.input._encoder.position or 0
            self._last_sel = 0
        except Exception:
            pass

        bg = header.get("background")
        if bg:
            if bg.startswith("/"):
                bg_path = bg
            else:
                bg_path = menus_dir + "/" + bg
            if self.storage:
                bg_path = self.storage.resolve_path(bg_path)
            try:
                self.display.set_background(bg_path)
            except Exception:
                pass

        try:
            self.display._highlight_index = -1
            self.display.set_highlight(0)
        except Exception:
            pass
        self._sel_index = 0
        self._update_item_text()

    def _navigate_back(self):
        if len(self._nav_stack) <= 1:
            return
        self._nav_stack.pop()
        prev = self._nav_stack.pop()
        self._load_menu(prev)

    # ----- audio ----------------------------------------------------------

    def _say(self, path):
        if not path:
            return
        speak_start = time.monotonic()
        try:
            self.audio.play(self._resolve(path))
        except Exception as e:
            print("Communication Game: sound error:", e)
        dur = time.monotonic() - speak_start
        self._run_start += dur

    def _resolve(self, path):
        if not path:
            return path
        if not path.startswith("/"):
            menus_dir = getattr(self.machine, "_menus_dir", "/menus")
            path = menus_dir + "/" + path
        if self.storage:
            return self.storage.resolve_path(path)
        return path

    def _aborted(self):
        return self._round_index < self._round_count

    def _header(self):
        return (self.config or {}).get("header", {}) if self.config else {}

    def _sections(self):
        return (self.config or {}).get("sections", {}) if self.config else {}


# ---------------------------------------------------------------------
class _SingleButtonHelper:
    """Decode a single momentary input into tap / double-tap / hold events."""

    def __init__(self, input_manager, first_delay_ms=450, min_interval_ms=60,
                 decay=0.85, double_tap_sec=0.45, exit_hold_sec=3.0):
        self.im = input_manager
        self.first_delay = first_delay_ms / 1000.0
        self.min_interval = min_interval_ms / 1000.0
        self.decay = decay
        self.double_tap = double_tap_sec
        self.exit_hold = exit_hold_sec

        self._prev_pressed = False
        self._press_started = 0
        self._last_tap_time = 0
        self._hold_fired_any = False
        self._current_interval = first_delay_ms / 1000.0
        self._next_repeat = 0

    def _raw_pressed(self):
        for name in ("puff_pressed", "single_button_pressed",
                     "encoder_button_held"):
            v = getattr(self.im, name, None)
            if isinstance(v, bool):
                return v
        return False

    def poll(self):
        now = time.monotonic()
        pressed = self._raw_pressed()

        if not pressed and self._prev_pressed:
            self._prev_pressed = False
            if self._hold_fired_any:
                self._hold_fired_any = False
                return None
            if now - self._last_tap_time <= self.double_tap:
                self._last_tap_time = 0
                return "select"
            self._last_tap_time = now
            return "tick_fwd"

        if pressed and not self._prev_pressed:
            self._prev_pressed = True
            self._press_started = now
            self._current_interval = self.first_delay
            self._next_repeat = now + self._current_interval
            return None

        if pressed and self._prev_pressed:
            held_for = now - self._press_started
            if held_for >= self.exit_hold:
                self._prev_pressed = False
                self._hold_fired_any = False
                return "exit"
            if now >= self._next_repeat:
                self._hold_fired_any = True
                self._current_interval = max(
                    self.min_interval,
                    self._current_interval * self.decay,
                )
                self._next_repeat = now + self._current_interval
                return "tick_fwd"

        return None


GAME = AacTrainer
