"""AAC Trainer — the "Chicken Challenge" game.

Runs on top of the base AAC software. The game loads a menu of
AAC items (by default the current start_menu), plays an audio
prompt, and asks the player to navigate to and select the correct
AAC category. Ten questions form a round; score is total time with
a 30-second penalty per wrong answer.

See:
  Version3/SipAndPuff/T-Rex_Sip_N_Puff.md §3 "Maker Faire Engagement:
  The Chicken Challenge Game".

Input modes
-----------
The game supports three input sources simultaneously — whichever is
first to emit an event wins:

1. Rotary encoder (normal AAC behaviour):
     rotate  -> advance / retreat highlight
     press   -> select

2. Single button / Sip-N-Puff puff (emulated rotary+click):
     tap           -> advance +1
     hold          -> continuous advance at an accelerating rate
     double-tap    -> select current
     long-press >= exit_hold_sec  -> exit trainer

3. Sip-N-Puff sip (optional, if the device differentiates):
     sip tap    -> advance -1
     sip hold   -> continuous retreat

Voice prompts replace on-screen prompts. Each question is an MP3
spoken by the device; feedback ("correct", "try again", and the
selected AAC item's own sound) is also spoken.

Sidecar config (stim_games/aac_trainer.cfg) — see that file for
the concrete shape. Each [question] section has:
    prompt = path/to/question.mp3
    answer = <menu_item_id>         # must match an id in the menu file
"""

import time

from stim_games.subprogram import Subprogram


# Defaults — overrideable from aac_trainer.cfg [header] ------------------
DEFAULT_ROUND_COUNT = 10
DEFAULT_PENALTY_SEC = 30
DEFAULT_EXIT_HOLD_SEC = 3.0
DEFAULT_DOUBLE_TAP_SEC = 0.45
DEFAULT_HOLD_FIRST_MS = 450    # delay before hold-repeat begins
DEFAULT_HOLD_MIN_MS = 60       # fastest repeat rate while held
DEFAULT_HOLD_DECAY = 0.85      # multiplier per step toward HOLD_MIN_MS


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

        # 2. Load the answer menu ----------------------------------------
        self._answer_menu_file = hdr.get("answer_menu",
                                         self.machine._start_menu)
        from menu_parser import parse_menu_file
        menus_dir = getattr(self.machine, "_menus_dir", "/menus")
        menu_path = menus_dir + "/" + self._answer_menu_file
        if self.storage:
            menu_path = self.storage.resolve_path(menu_path)
        print("AAC Trainer: loading answer menu:", menu_path)
        _header, items = parse_menu_file(menu_path)
        self._items = items
        self._id_to_index = {
            str(it.get("id", "")): i for i, it in enumerate(items)
        }

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
        self._sel_index = 0
        self._encoder_last = self._encoder_pos()

        # 5. Play intro then the first question ---------------------------
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
        # Detect a rising edge on encoder_button_held (if available)
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

    # ----- question/answer flow ----------------------------------------

    def _ask(self, idx):
        q = self._questions[idx]
        prompt = q.get("prompt")
        print("AAC Trainer: Q{}/{} prompt={} answer={}".format(
            idx + 1, self._round_count, prompt, q.get("answer")))
        if prompt:
            self._say(prompt)

    def _commit_selection(self):
        if self._round_index >= self._round_count:
            return
        if not self._items:
            return

        selected = self._items[self._sel_index]
        expected = str(self._questions[self._round_index].get("answer", ""))
        print("AAC Trainer: selected {} (expected {})".format(
            selected.get("id"), expected))

        # Speak whichever sound is attached to the chosen AAC item first.
        item_sound = selected.get("sound")
        if item_sound:
            self._say(self._resolve(item_sound))

        correct = str(selected.get("id", "")) == expected
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
        prev = getattr(self, "_prev_enc_click", False)
        self._prev_enc_click = bool(held)
        return bool(held) and not prev

    # ----- audio --------------------------------------------------------

    def _say(self, path):
        """Play a sound file and pause the round timer while it plays."""
        if not path:
            return
        speak_start = time.monotonic()
        try:
            self.audio.play(self._resolve(path))
        except Exception as e:  # noqa: BLE001
            print("AAC Trainer: sound error:", e)
        # Compensate the timer for speech duration — cheap version:
        # we already measure round time from _run_start, so subtract
        # the speaking time by inflating _run_start.
        dur = time.monotonic() - speak_start
        self._run_start += dur

    def _resolve(self, path):
        """Route relative paths through the storage manager like Action does."""
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

    Uses InputManager's raw digital pin reads when available. Falls back
    to treating any poll() press as a tap.
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
        """Best-effort read of a "single button" or puff pin.

        Order of preference:
            input_manager.puff_pressed        (Sip-N-Puff driver)
            input_manager.single_button_pressed
            input_manager.encoder_button_held (fallback)
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
            dur = now - self._press_started
            self._prev_pressed = False
            if self._hold_fired_any:
                # Hold was active; no terminal tap/select on release
                self._hold_fired_any = False
                return None
            # Short press — decide tap vs. double-tap
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
                # Exit gesture takes priority
                self._prev_pressed = False
                self._hold_fired_any = False
                return "exit"
            if now >= self._next_repeat:
                self._hold_fired_any = True
                # Accelerate
                self._current_interval = max(
                    self.min_interval,
                    self._current_interval * self.decay,
                )
                self._next_repeat = now + self._current_interval
                return "tick_fwd"

        return None


GAME = AacTrainer
