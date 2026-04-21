"""AAC Trainer — the "Chicken Challenge" game.

Runs on top of the base AAC software. The game loads a menu of AAC
items (by default the current start_menu), plays an audio prompt,
and asks the player to navigate to and select the correct AAC item.
Ten questions form a round; score is total time with a 30-second
penalty per wrong answer.

See:
  Version3/SipAndPuff/T-Rex_Sip_N_Puff.md §3 "Maker Faire Engagement:
  The Chicken Challenge Game".

Answer paths
------------
An answer in the config can be a single item id (e.g. `bathroom`) or
a slash-separated path that navigates through submenus
(e.g. `more/banana`). For a path answer, the game enters each submenu
when the player selects the matching item; the final step must match
a leaf item to count as correct.

Press evaluation during a path:

  * Correct next step  -> navigate into that step (load its submenu if
                          it has one, or finalize if this was the last
                          step in the path).
  * Back button        -> walk one level up the navigation stack;
                          rolls the path cursor back by one if we were
                          mid-path.
  * Anything else      -> the round is marked wrong immediately.

Input modes
-----------
The game supports three input sources simultaneously:

1. Rotary encoder (normal AAC behaviour):
     rotate  -> advance / retreat highlight
     press   -> select

2. Single button / Sip-N-Puff puff (emulated rotary+click):
     tap                         -> advance +1
     hold                        -> continuous advance at an accelerating rate
     double-tap                  -> select current
     long-press >= exit_hold_sec -> exit trainer

3. Sip-N-Puff sip (optional, if the device differentiates):
     sip tap    -> advance -1
     sip hold   -> continuous retreat

Voice prompts replace on-screen prompts. Each question is an MP3
spoken by the device; feedback ("correct", "try again", and the
selected AAC item's own sound) is also spoken.

Sidecar config (stim_games/aac_trainer.cfg) — see that file for
the concrete shape. Each [question] section has:
    prompt = path/to/question.mp3
    answer = <menu_item_id>          # leaf id in the answer_menu, OR
    answer = more/banana             # slash-separated path through submenus

Extra knobs:
    randomize       = true          # shuffle question order each round (default: true)
    answer_menu     = base.menu     # top-level menu to train against
    rounds          = 10
    penalty_seconds = 30
"""

import time

try:
    import random
except ImportError:  # CircuitPython has `random` but keep the guard
    random = None

from stim_games.subprogram import Subprogram


# Defaults — overrideable from aac_trainer.cfg [header] ------------------
DEFAULT_ROUND_COUNT = 10
DEFAULT_PENALTY_SEC = 30
DEFAULT_EXIT_HOLD_SEC = 3.0
DEFAULT_DOUBLE_TAP_SEC = 0.45
DEFAULT_HOLD_FIRST_MS = 450    # delay before hold-repeat begins
DEFAULT_HOLD_MIN_MS = 60       # fastest repeat rate while held
DEFAULT_HOLD_DECAY = 0.85      # multiplier per step toward HOLD_MIN_MS
DEFAULT_RANDOMIZE = True       # shuffle the question order each round


class AacTrainer(Subprogram):
    name = "AAC Trainer (Chicken Challenge)"

    # ----- lifecycle ----------------------------------------------------

    def setup(self):
        # 1. Resolve configuration ---------------------------------------
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

        self._questions = list(secs.get("question", []))
        if not self._questions:
            print("AAC Trainer: no questions configured; nothing to do")
            self._done = True
            return

        # Clamp round_count to questions available (if not randomizing
        # and we have fewer questions than rounds, we'd otherwise crash)
        if self._round_count > len(self._questions):
            self._round_count = len(self._questions)

        if self._randomize and random is not None:
            random.shuffle(self._questions)

        # 2. Resolve the answer-menu root --------------------------------
        self._answer_menu_file = hdr.get("answer_menu",
                                         self.machine._start_menu)

        # 3. Scorekeeping state ------------------------------------------
        self._score_sec = 0.0
        self._wrong_count = 0
        self._round_index = 0
        self._done = False

        # 4. Input helpers ------------------------------------------------
        self._btn_helper = _SingleButtonHelper(
            self.input,
            first_delay_ms=self._hold_first_ms,
            min_interval_ms=self._hold_min_ms,
            decay=self._hold_decay,
            double_tap_sec=self._double_tap,
            exit_hold_sec=self._exit_hold,
        )
        self._encoder_last = self._encoder_pos()
        self._prev_enc_click = False

        # Navigation stack — top is the currently-loaded menu file name
        self._nav_stack = []
        self._items = []
        self._sel_index = 0
        self._current_path = []
        self._path_pos = 0

        # 5. Play intro, then first question ------------------------------
        self.set_status((0, 128, 255))
        self._say(self._intro_sound)
        self._run_start = time.monotonic()
        self._ask(self._round_index)

    def tick(self):
        if self._done:
            return False

        # --- Rotary encoder (AAC-native) ---------------------------------
        cur = self._encoder_pos()
        if cur is not None and cur != self._encoder_last:
            delta = cur - self._encoder_last
            self._encoder_last = cur
            self._move_selection(delta)

        # --- Single-button / Sip-N-Puff events ---------------------------
        ev = self._btn_helper.poll()
        if ev == "tick_fwd":
            self._move_selection(+1)
        elif ev == "tick_back":
            self._move_selection(-1)
        elif ev == "select":
            self._commit_selection()
        elif ev == "exit":
            print("AAC Trainer: exit gesture")
            return False

        # --- Encoder click = select --------------------------------------
        if self._encoder_click_edge():
            self._commit_selection()

        return True

    def teardown(self):
        if self._round_index >= self._round_count and not self._aborted():
            elapsed = time.monotonic() - self._run_start
            total = elapsed + self._score_sec  # penalty already accumulated
            print("AAC Trainer: run finished in {:.1f}s "
                  "(wrong: {})".format(total, self._wrong_count))
            self._say(self._done_sound)

    # ----- question / answer flow --------------------------------------

    def _ask(self, idx):
        q = self._questions[idx]
        prompt = q.get("prompt")
        raw_answer = str(q.get("answer", ""))
        self._current_path = [
            p for p in raw_answer.replace("\\", "/").split("/") if p
        ]
        self._path_pos = 0

        print("AAC Trainer: Q{}/{} prompt={} path={}".format(
            idx + 1, self._round_count, prompt, self._current_path))

        # Reset the player to the top of the answer menu for every Q
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

        # "Back" navigates up a level without penalty or advancing rounds
        if "back" in selected:
            self._navigate_back()
            # If we just stepped back out of a path-matched submenu,
            # roll the path cursor back so the player can re-attempt.
            if self._path_pos > 0:
                self._path_pos -= 1
            return

        expected = (self._current_path[self._path_pos]
                    if self._path_pos < len(self._current_path) else None)
        print("AAC Trainer: selected {} (expected {} at step {}/{})".format(
            selected_id, expected, self._path_pos + 1,
            len(self._current_path)))

        if expected and selected_id == expected:
            self._path_pos += 1
            if self._path_pos >= len(self._current_path):
                # Final step — evaluate as correct
                self._finalize_answer(selected, correct=True)
            else:
                # Intermediate step — enter the submenu
                submenu = selected.get("submenu")
                if submenu and not str(submenu).endswith(".py"):
                    self._load_menu(str(submenu))
                else:
                    # Config says more steps but the item has no submenu
                    # to dive into. Treat as wrong.
                    print("AAC Trainer: path expects submenu but item "
                          "'{}' has none".format(selected_id))
                    self._finalize_answer(selected, correct=False)
        else:
            self._finalize_answer(selected, correct=False)

    def _finalize_answer(self, selected, correct):
        # Speak whatever sound is attached to the chosen AAC item first.
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
            self.display.set_highlight(self._sel_index)
        except Exception:  # noqa: BLE001
            pass

    # ----- menu navigation --------------------------------------------

    def _load_menu(self, menu_file):
        """Load a .menu file, push it onto the nav stack, render."""
        from menu_parser import parse_menu_file
        menus_dir = getattr(self.machine, "_menus_dir", "/menus")
        menu_path = menus_dir + "/" + menu_file
        if self.storage:
            menu_path = self.storage.resolve_path(menu_path)
        print("AAC Trainer: load menu:", menu_path)
        try:
            _header, items = parse_menu_file(menu_path)
        except Exception as e:  # noqa: BLE001
            print("AAC Trainer: cannot load", menu_path, ":", e)
            items = []
        self._items = items
        self._sel_index = 0
        self._nav_stack.append(menu_file)
        try:
            self.display.set_highlight(0)
        except Exception:  # noqa: BLE001
            pass

    def _navigate_back(self):
        """Pop one level off the nav stack, reload the parent menu."""
        if len(self._nav_stack) <= 1:
            # Already at the answer-menu root — nowhere to go back to.
            return
        self._nav_stack.pop()              # drop current
        prev = self._nav_stack.pop()       # pop parent so _load_menu re-pushes
        self._load_menu(prev)

    # ----- input plumbing ----------------------------------------------

    def _encoder_pos(self):
        enc = getattr(self.input, "_encoder", None)
        if enc is None:
            return None
        try:
            return int(enc.position)
        except Exception:  # noqa: BLE001
            return None

    def _encoder_click_edge(self):
        held = getattr(self.input, "encoder_button_held", False)
        prev = self._prev_enc_click
        self._prev_enc_click = bool(held)
        return bool(held) and not prev

    # ----- audio --------------------------------------------------------

    def _say(self, path):
        """Play a sound and pause the round timer while it plays."""
        if not path:
            return
        speak_start = time.monotonic()
        try:
            self.audio.play(self._resolve(path))
        except Exception as e:  # noqa: BLE001
            print("AAC Trainer: sound error:", e)
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

    # ----- config helpers ----------------------------------------------

    def _header(self):
        return (self.config or {}).get("header", {}) if self.config else {}

    def _sections(self):
        return (self.config or {}).get("sections", {}) if self.config else {}


# ---------------------------------------------------------------------
# Helper: single-button decoder (for Sip-N-Puff puff-only input and
# single external switches). Emits one of:
#     "tick_fwd", "tick_back", "select", "exit", None
# ---------------------------------------------------------------------
class _SingleButtonHelper:
    """Decode a single momentary input into tap / double-tap / hold events.

    Uses InputManager's raw digital pin reads when available. Falls
    back to treating any poll() press as a tap.
    """

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
        """Best-effort read of a single-button or puff pin.

        Preference order:
            input_manager.puff_pressed         (Sip-N-Puff driver)
            input_manager.single_button_pressed
            input_manager.encoder_button_held  (fallback)
        """
        for name in ("puff_pressed", "single_button_pressed",
                     "encoder_button_held"):
            v = getattr(self.im, name, None)
            if isinstance(v, bool):
                return v
        return False

    def poll(self):
        now = time.monotonic()
        pressed = self._raw_pressed()

        # --- Edge: released -----------------------------------------
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

        # --- Edge: newly pressed ------------------------------------
        if pressed and not self._prev_pressed:
            self._prev_pressed = True
            self._press_started = now
            self._current_interval = self.first_delay
            self._next_repeat = now + self._current_interval
            return None

        # --- Continuous hold ----------------------------------------
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
