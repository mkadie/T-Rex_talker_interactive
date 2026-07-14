"""T-Rex's Rubber Chicken Challenge (AAC communication game).

Runs on top of the base AAC software on the Fruit Jam DVI + USB variant.
A spoken prompt describes a scenario; the player navigates the AAC board
and selects the item that answers it (base-page answers are direct; food
answers are reached through the "More" button). A round is `rounds`
questions (default 6) drawn from a 14-item pool with no repeats, target
selection page-weighted (first_page_bias). Score is total time plus a
30 s penalty per wrong answer; a top-3 leaderboard persists to
/sd/hiscores.txt with profanity-filtered name entry.

Two modes (toggle with `two_player` in aac_trainer.cfg):

  * Single player — one cursor, base + food navigation.
  * Two player   — P1 (yellow, Left/Right/Space, starts cell 1) vs P2
                   (blue, Up/Down/Enter, starts cell 8) race to buzz in;
                   first selection ends the question. Base page only.
                   See TWO_PLAYER.md.

Fully localizes into 13 languages as a "screen-swapper": each screen is
pre-rendered per language to an image on the SD (built-in font is
ASCII-only), and per-word / prompt audio lives on the SD too. BUTTON1 /
BUTTON3 cycle the language on the start / end screens (BUTTON2 starts).
Prompts play non-blocking so input stays responsive while speaking.
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
LANG_SELECT_TIMEOUT = 5    # seconds of no scrolling before the language is
                           # announced (spoken in that language)
HISCORE_FILE = "/sd/hiscores.txt"
MAX_HISCORES = 3
NAME_LENGTH = 5
NAME_ENTRY_TIMEOUT = 15    # seconds of no activity before name entry ends

# Characters for name entry — space first, then A-Z, then 0-9
# Leading "-" so a name slot shows a dash until a letter is dialed in,
# making the current position obvious. Space is last (rendered as "_").
NAME_CHARS = "-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "

# HID keycodes for routing two-player input:
#   Player 1 -> Left / Right / Space     Player 2 -> Up / Down / Enter
_KC_RIGHT = 0x4F
_KC_LEFT = 0x50
_KC_DOWN = 0x51
_KC_UP = 0x52
_KC_ENTER = 0x28
_KC_SPACE = 0x2C
NUM_CELLS = 8   # answer board is a 4x2 grid

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


# Languages the start / end screens cycle through with BUTTON1. The code
# selects the /sounds/game/<code>/ audio tree; the English name is shown
# on-screen so a non-reader can see which language is active. English uses
# its existing on-flash prompt assets, so the game still runs with no SD.
LANGS = [
    ("en", "English"), ("th", "Thai"), ("cs", "Czech"),
    ("ja", "Japanese"), ("zh", "Mandarin"), ("hi", "Hindi"),
    ("es", "Spanish"), ("fr", "French"), ("ar", "Arabic"),
    ("bn", "Bengali"), ("pt", "Portuguese"), ("ru", "Russian"),
    ("de", "German"),
]


class AacTrainer(Subprogram):
    name = "T-Rex's Rubber Chicken Challenge"

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
            print("Chicken Challenge: no questions configured; nothing to do")
            self._done = True
            return

        # Partition targets into page 1 (base menu, direct answers) and
        # page 2 (food items reached via "more"), by whether the answer
        # path descends through a submenu. Each target is chosen by
        # drawing a page (first_page_bias) then a uniform item on it, so
        # a round may ask more questions than there are sections.
        self._page1 = [q for q in self._questions
                       if "/" not in str(q.get("answer", ""))]
        self._page2 = [q for q in self._questions
                       if "/" in str(q.get("answer", ""))]
        self._first_page_bias = float(hdr.get("first_page_bias", 0.75))
        self._asked = set()   # question ids already asked this round

        # Language state — BUTTON1/BUTTON3 cycle this on the start/end
        # screens; the active code drives which audio tree is played.
        self._lang_idx = 0
        self._lang = LANGS[0][0]
        self._lang_label = None
        self._btn_prev = [True, True, True]  # onboard buttons, active-low

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

        # Audio queue — clips are played one at a time by tick() (non-
        # blocking) so the input loop never freezes on audio and key
        # presses are never dropped. _audio_active_since pauses the round
        # timer for the span audio occupies.
        self._audio_q = []
        self._audio_active_since = None
        # Defer advancing the screen until the answer's audio finishes, so
        # the board never jumps to the next question mid-speech.
        self._pending_ask = False
        self._pending_end = False

        # Live 2-player score bar (bottom of the board).
        self._p1_label = None
        self._p2_label = None
        self._score_bar_sec = -1

        # --- Two-player real-time race -------------------------------------
        # P1 drives Left/Right/Space, P2 drives Up/Down/Enter; both cursors
        # move at once and the first selection ends the question. Multi-step
        # (food) answers can't work on a shared board, so 2P uses single-step
        # base-page questions only.
        _tp = str(hdr.get("two_player", "true")).strip().lower()
        self._two_player = _tp not in ("false", "0", "no", "off")
        if self._two_player:
            self._page2 = []
        self._p1_idx = 0
        self._p2_idx = NUM_CELLS - 1
        self._p1_time = 0.0
        self._p2_time = 0.0
        self._q_start = None       # monotonic time input opened this question
        self._p2_hl = None         # blue P2 highlight TileGrid

        # Load high scores and show start screen
        self._hiscores = self._load_hiscores()
        self._run_start = time.monotonic()
        self._show_start_screen()
        self.set_status((0, 128, 255))
        self._say(self._lang_prompt(self._intro_sound), block=False)
        self._wait_for_button()
        self._run_start = time.monotonic()
        self._ask(self._round_index)

    def tick(self):
        if self._done:
            # Round finished — handle end-of-round, then restart
            self._end_round()
            self._restart_round()
            return True

        # Audio gate: while a clip is playing or queued, do NOT poll input
        # at all — nothing the player presses during the prompt / word /
        # feedback is acted on. When the audio finishes, credit the paused
        # round time, flush the buffered presses, and only then start
        # responding to input again.
        now = time.monotonic()
        if self.audio.playing:
            if self._audio_active_since is None:
                self._audio_active_since = now
            audio_active = True
        elif self._audio_q:
            if self._audio_active_since is None:
                self._audio_active_since = now
            try:
                self.audio.play(self._audio_q.pop(0), block=False)
            except Exception as e:
                print("Chicken Challenge: audio error:", e)
            audio_active = True
        else:
            audio_active = False
            if self._audio_active_since is not None:
                # The answer's word + feedback just finished speaking.
                self._run_start += now - self._audio_active_since
                self._audio_active_since = None
                try:
                    self.input.flush_keyboards()
                except Exception:
                    pass
                # Now (not on the key press) advance the screen: load the
                # next question's board, or end the round.
                if self._pending_ask:
                    self._pending_ask = False
                    self._ask(self._round_index)   # updates board + queues prompt
                    audio_active = True
                elif self._pending_end:
                    self._pending_end = False
                    self._done = True

        if self._done:
            # End-of-round handled at the top of the next tick.
            return True
        if audio_active:
            self._update_score_bar()
            return True

        # Two-player real-time input: both cursors move at once; the first
        # selection (P1 Space or P2 Enter) ends the question.
        if self._two_player:
            if self._q_start is None:
                self._q_start = now
            self.input.poll()          # pump keyboard reads -> fills events
            for code in self.input.drain_key_events():
                if code == _KC_LEFT:
                    self._move_cursor(1, -1)
                elif code == _KC_RIGHT:
                    self._move_cursor(1, 1)
                elif code == _KC_UP:
                    self._move_cursor(2, -1)
                elif code == _KC_DOWN:
                    self._move_cursor(2, 1)
                elif code == _KC_SPACE:
                    self._player_select(1)
                    break
                elif code == _KC_ENTER:
                    self._player_select(2)
                    break
            self._update_score_bar()
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
            print("Chicken Challenge: exit gesture")
            return False

        self._update_score_bar()
        return True

    def _end_round(self):
        """Handle scoring, name entry, and hiscore save after a round."""
        self._show_full_screen("finished")
        self._say(self._lang_prompt(self._done_sound))

        if self._two_player:
            print("2P finished: P1=%.1f  P2=%.1f" %
                  (self._p1_time, self._p2_time))
            # Both players are eligible for the leaderboard, in order.
            for ptime in (self._p1_time, self._p2_time):
                self._hiscores = self._load_hiscores()
                rank = self._get_rank(ptime)
                if rank is not None:
                    name = self._name_entry_screen(ptime)
                    self._insert_hiscore(ptime, name, rank)
                    self._save_hiscores()
            return

        elapsed = time.monotonic() - self._run_start
        total = elapsed + self._score_sec
        print("Chicken Challenge: run finished in {:.1f}s "
              "(wrong: {})".format(total, self._wrong_count))
        rank = self._get_rank(total)
        if rank is not None:
            player_name = self._name_entry_screen(total)
            self._insert_hiscore(total, player_name, rank)
            self._save_hiscores()

    def _restart_round(self):
        """Reset state and show start screen for a new round."""
        self._hiscores = self._load_hiscores()
        self._show_start_screen()
        self._say(self._lang_prompt(self._intro_sound), block=False)
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
        self._p1_time = 0.0
        self._p2_time = 0.0
        self._q_start = None
        self._round_index = 0
        self._asked = set()
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
            print("Chicken Challenge: saved hiscores")
        except Exception as e:
            print("Chicken Challenge: could not save hiscores:", e)

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
        """Put up the active language's pre-rendered title screen
        (/sd/screens/<lang>/title.bmp) with the top-3 times overlaid as
        ASCII digits (the built-in font handles numbers and A-Z names)."""
        import gc
        import displayio

        # Drop the previous screen first so its OnDiskBitmap file handle is
        # freed before we open the next image, then collect.
        try:
            self.display._display.root_group = displayio.Group()
        except Exception:
            pass
        gc.collect()

        w = self.display._width
        h = self.display._height
        group = displayio.Group()

        try:
            import adafruit_imageload
            bmp, shader = adafruit_imageload.load(self._screen_path("title"))
            group.append(displayio.TileGrid(bmp, pixel_shader=shader))
        except Exception as e:
            print("Chicken Challenge: title screen missing:", e)
            bg = displayio.Bitmap(w, h, 1)
            pal = displayio.Palette(1)
            pal[0] = 0x000000
            group.append(displayio.TileGrid(bg, pixel_shader=pal))

        # Dynamic high scores overlaid (ASCII) in the mid gap of the image.
        if self._hiscores:
            try:
                from adafruit_display_text import label
                import terminalio
                lines = []
                for i, (secs, name) in enumerate(self._hiscores):
                    lines.append("{}. {} {}".format(
                        i + 1, self._format_time(secs), name))
                scores_lbl = label.Label(
                    terminalio.FONT, text="\n".join(lines),
                    color=0x00FF00, scale=1,
                    anchor_point=(0.5, 1.0),
                    anchored_position=(w // 2, h - 4),
                )
                group.append(scores_lbl)
            except ImportError:
                pass

        self.display._display.root_group = group
        # Draw the image now, before any audio streams from the SD, so the
        # title can't render blank while a sound is being read.
        try:
            self.display._display.refresh()
        except Exception:
            pass
        self._showing_score = True

    def _dismiss_score_screen(self):
        if self._showing_score:
            self.display._display.root_group = self.display._splash
            self._showing_score = False

    def _wait_for_button(self):
        """Hold on the start/end screen until start. The onboard buttons
        are read directly (so BUTTON1 can't be confused with a keyboard
        select): BUTTON1 -> next language, BUTTON3 -> previous language,
        BUTTON2 -> start. A keyboard/puff/chicken press also starts (only
        counted when no onboard button is held, so a held BUTTON1 press
        surfaced by poll() doesn't trip the start)."""
        self._btn_prev = [self._btn_raw(i) for i in range(3)]
        scroll_at = None       # monotonic time of the last language change
        announced = True       # has the current language been spoken yet?
        while True:
            if self._btn_edge(0):
                self._cycle_language(+1)
                scroll_at = time.monotonic()
                announced = False
                continue
            if self._btn_edge(2):
                self._cycle_language(-1)
                scroll_at = time.monotonic()
                announced = False
                continue
            if self._btn_edge(1):
                break
            # Once scrolling stops for LANG_SELECT_TIMEOUT, announce the
            # chosen language (its name spoken in that language). Nothing is
            # said while the player is still scrolling.
            if (not announced and scroll_at is not None
                    and time.monotonic() - scroll_at >= LANG_SELECT_TIMEOUT):
                self._announce_language()
                announced = True
            press = self.input.poll()
            if press is not None and not any(self._btn_raw(i) for i in range(3)):
                break
            time.sleep(0.01)

    def _announce_language(self):
        """Speak the selected language's name in that language."""
        self._say("/sd/sounds/game/%s/langname.wav" % self._lang)

    # ----- onboard buttons + language cycling ----------------------------

    def _btn_raw(self, i):
        """True if onboard button i is currently pressed (active-low)."""
        db = getattr(self.input, "_direct_buttons", None)
        if not db or i >= len(db):
            return False
        try:
            v = db[i].value
        except Exception:
            return False
        active_low = getattr(self.input, "_direct_active_low", True)
        return (not v) if active_low else v

    def _btn_edge(self, i):
        """True once, on the press (rising) edge of onboard button i."""
        now = self._btn_raw(i)
        prev = self._btn_prev[i] if i < len(self._btn_prev) else False
        if i < len(self._btn_prev):
            self._btn_prev[i] = now
        return now and not prev

    def _lang_name(self):
        return "Lang: " + LANGS[self._lang_idx][1]

    def _cycle_language(self, delta):
        self._lang_idx = (self._lang_idx + delta) % len(LANGS)
        self._lang = LANGS[self._lang_idx][0]
        print("Chicken Challenge: language ->", self._lang)
        # Swap to the new language's pre-rendered title screen. No audio
        # here — the name is announced once scrolling stops so we never
        # read an image and stream a sound off the SD at the same time.
        if self._showing_score:
            self._show_start_screen()

    def _screen_path(self, name):
        """Path to a pre-rendered screen image for the active language."""
        return "/sd/screens/%s/%s.bmp" % (self._lang, name)

    def _show_full_screen(self, name):
        """Put up a pre-rendered full-screen image for the active language."""
        import displayio
        try:
            import adafruit_imageload
            bmp, shader = adafruit_imageload.load(self._screen_path(name))
            g = displayio.Group()
            g.append(displayio.TileGrid(bmp, pixel_shader=shader))
            self.display._display.root_group = g
            try:
                self.display._display.refresh()
            except Exception:
                pass
            self._showing_score = True
        except Exception as e:
            print("Chicken Challenge: screen missing", name, e)

    def _lang_prompt(self, path):
        """Map a trainer prompt/framing path to the active language, read
        from the SD card's /sd/sounds/game tree. English keeps its
        existing on-flash asset so it runs with no SD."""
        if self._lang == "en" or not path:
            return path
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        return "/sd/sounds/game/%s/prompts/%s.wav" % (self._lang, stem)

    def _lang_word(self, item_id, cfg_path):
        """Map a selected item's word audio to the active language's SD
        tree (/sd/sounds/game/<code>/words/<id>.wav) for every language
        including English, whose on-flash word set is incomplete. Falls
        back to cfg_path when the item has no id."""
        if not item_id:
            return cfg_path
        return "/sd/sounds/game/%s/words/%s.wav" % (self._lang, item_id)

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
        last_activity = time.monotonic()
        while slot < NAME_LENGTH:
            press = self.input.poll()
            cur = getattr(self.input, '_selected_index', 0)
            cur = cur % len(chars)
            if cur != name[slot]:
                name[slot] = cur
                _render_name()
                last_activity = time.monotonic()
            if press is not None:
                last_activity = time.monotonic()
                slot += 1
                if slot < NAME_LENGTH:
                    self.input._selected_index = 0
                    self.input._max_index = len(chars)
                    if hasattr(self.input, '_encoder') and self.input._encoder:
                        self.input._last_encoder_pos = self.input._encoder.position
                    name[slot] = 0
                    _render_name()
            # End name entry after a stretch of no rotating or pressing, so
            # an abandoned high score doesn't hang the game (keeps whatever
            # has been typed so far).
            if time.monotonic() - last_activity >= NAME_ENTRY_TIMEOUT:
                print("Chicken Challenge: name entry timed out after {}s".format(
                    NAME_ENTRY_TIMEOUT))
                break
            time.sleep(0.03)

        # Restore encoder
        self.input._max_index = saved_max

        result = "".join(chars[c] for c in name).strip()
        if not result:
            result = "ANON"

        if _is_profane(result):
            result = "Rude!"
            print("Chicken Challenge: profanity filtered")

        print("Chicken Challenge: name entered:", result)
        return result

    # ----- question / answer flow ----------------------------------------

    def _pick_target(self):
        """Choose the next question: page 1 with probability
        first_page_bias (else page 2), then a uniform UNASKED item on that
        page. No question repeats within a round until the whole pool is
        exhausted."""
        avail1 = [q for q in self._page1 if id(q) not in self._asked]
        avail2 = [q for q in self._page2 if id(q) not in self._asked]
        if not avail1 and not avail2:      # pool exhausted — allow reuse
            self._asked = set()
            avail1, avail2 = list(self._page1), list(self._page2)
        if random is None:
            page = avail1 or avail2
            q = page[0] if page else None
        else:
            if avail1 and (not avail2 or random.random() < self._first_page_bias):
                page = avail1
            else:
                page = avail2 or avail1
            q = random.choice(page) if page else None
        if q is not None:
            self._asked.add(id(q))
        return q

    def _ask(self, idx):
        if self._showing_score:
            self._dismiss_score_screen()

        q = self._pick_target()
        if q is None:
            self._done = True
            return
        prompt = q.get("prompt")
        raw_answer = str(q.get("answer", ""))
        self._current_path = [
            p for p in raw_answer.replace("\\", "/").split("/") if p
        ]
        self._path_pos = 0

        print("Chicken Challenge: Q{}/{} prompt={} path={}".format(
            idx + 1, self._round_count, prompt, self._current_path))

        self._nav_stack = []
        self._load_menu(self._answer_menu_file)
        # Clear buffered / carried-over key presses so the previous answer's
        # input can't bleed into this question.
        try:
            self.input.flush_keyboards()
        except Exception:
            pass

        # Reset both cursors for the new question: P1 -> cell 1 (yellow),
        # P2 -> cell 8 (blue). Timer opens when the prompt finishes.
        if self._two_player:
            self._p1_idx = 0
            self._p2_idx = NUM_CELLS - 1
            try:
                self.display.set_highlight(self._p1_idx)
            except Exception:
                pass
            self._position_p2_highlight()
            self._q_start = None

        if prompt:
            # Queued (non-blocking) so the player can navigate and answer
            # while the question is still being spoken.
            self._enqueue(self._lang_prompt(prompt))

    def _commit_selection(self):
        if self._round_index >= self._round_count:
            return
        if not self._items:
            return

        selected = self._items[self._sel_index]
        selected_id = str(selected.get("id", ""))

        # Speak the item the player selected (audio confirmation of the
        # pick), for every commit — navigation into a submenu as well as a
        # final answer. Items with no sound (e.g. "More", "Back") stay
        # silent. _finalize_answer then only adds the correct/wrong cue.
        item_sound = selected.get("sound")
        if item_sound:
            self._enqueue(self._lang_word(selected_id, item_sound))

        if "back" in selected:
            self._navigate_back()
            if self._path_pos > 0:
                self._path_pos -= 1
            return

        expected = (self._current_path[self._path_pos]
                    if self._path_pos < len(self._current_path) else None)
        print("Chicken Challenge: selected {} (expected {} at step {}/{})".format(
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
                    print("Chicken Challenge: path expects submenu but item "
                          "'{}' has none".format(selected_id))
                    self._finalize_answer(selected, correct=False)
        else:
            self._finalize_answer(selected, correct=False)

    def _finalize_answer(self, selected, correct):
        # The selected item's word was already spoken in _commit_selection;
        # here we only add the correct / wrong feedback cue.
        if correct:
            self.set_status((0, 255, 0))
            self._enqueue(self._lang_prompt(self._correct_sound))
        else:
            self.set_status((255, 0, 0))
            self._enqueue(self._lang_prompt(self._wrong_sound))
            self._wrong_count += 1
            self._score_sec += self._penalty

        self._round_index += 1
        # Don't jump the board now — wait until the word + feedback finish
        # speaking (handled in tick's audio-finished branch).
        if self._round_index >= self._round_count:
            self._pending_end = True
        else:
            self._pending_ask = True

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

    # ----- two-player cursors --------------------------------------------

    def _move_cursor(self, player, delta):
        """Move a player's cursor (wrapping) and reposition its highlight —
        P1 = yellow (display highlight), P2 = blue."""
        n = len(self._items) or NUM_CELLS
        if player == 1:
            self._p1_idx = (self._p1_idx + delta) % n
            try:
                self.display.set_highlight(self._p1_idx)
            except Exception:
                pass
        else:
            self._p2_idx = (self._p2_idx + delta) % n
            self._position_p2_highlight()

    def _player_select(self, player):
        """A player buzzed in. First selection ends the question: score it,
        speak the word + feedback, and advance (deferred until audio ends)."""
        if not self._items:
            return
        idx = (self._p1_idx if player == 1 else self._p2_idx) % len(self._items)
        selected = self._items[idx]
        selected_id = str(selected.get("id", ""))
        expected = self._current_path[0] if self._current_path else None
        correct = bool(expected and selected_id == expected)

        elapsed = 0.0
        if self._q_start is not None:
            elapsed = time.monotonic() - self._q_start
            self._q_start = None
        # Race time is shared — both players' clocks advance by it.
        self._p1_time += elapsed
        self._p2_time += elapsed
        # Penalty: correct -> the OTHER player is docked 30 s; wrong -> the
        # player who buzzed in is docked.
        loser = (2 if player == 1 else 1) if correct else player
        if loser == 1:
            self._p1_time += self._penalty
        else:
            self._p2_time += self._penalty
        print("2P: P%d picked %s (want %s) -> %s | P1=%.1f P2=%.1f" % (
            player, selected_id, expected, "OK" if correct else "X",
            self._p1_time, self._p2_time))

        item_sound = selected.get("sound")
        if item_sound:
            self._enqueue(self._lang_word(selected_id, item_sound))
        self.set_status((0, 255, 0) if correct else (255, 0, 0))
        self._enqueue(self._lang_prompt(
            self._correct_sound if correct else self._wrong_sound))

        self._round_index += 1
        if self._round_index >= self._round_count:
            self._pending_end = True
        else:
            self._pending_ask = True

    def _make_p2_highlight(self):
        """Create the blue Player-2 highlight (border-only), sized to a cell."""
        import displayio
        zw = getattr(self.display, "_zone_width", self.display._width // 4)
        zh = getattr(self.display, "_zone_height", self.display._height // 2)
        border = max(2, min(zw, zh) // 16)
        bmp = displayio.Bitmap(zw, zh, 2)
        pal = displayio.Palette(2)
        pal[0] = 0x000000
        pal.make_transparent(0)
        pal[1] = 0x33AAFF   # blue
        for x in range(zw):
            for b in range(border):
                bmp[x, b] = 1
                bmp[x, zh - 1 - b] = 1
        for y in range(zh):
            for b in range(border):
                bmp[b, y] = 1
                bmp[zw - 1 - b, y] = 1
        return displayio.TileGrid(bmp, pixel_shader=pal, x=0, y=0)

    def _position_p2_highlight(self):
        if self._p2_hl is None:
            return
        cols = getattr(self.display, "_cols", 4)
        zw = getattr(self.display, "_zone_width", self.display._width // cols)
        zh = getattr(self.display, "_zone_height", self.display._height // 2)
        idx = self._p2_idx % (len(self._items) or NUM_CELLS)
        try:
            self._p2_hl.x = (idx % cols) * zw
            self._p2_hl.y = (idx // cols) * zh
        except Exception:
            pass

    def _update_item_text(self):
        """No-op: item labels are baked into the pre-rendered board image
        per language, so no runtime (ASCII-only) text overlay is drawn."""
        return

    def _attach_score_bar(self):
        """(Re)attach the live 2-player score bar to the bottom of the menu
        splash. Called after each board load because set_background rebuilds
        the splash. It only shows while a board is the active screen."""
        import displayio
        try:
            from adafruit_display_text import label
            import terminalio
        except ImportError:
            return
        splash = getattr(self.display, "_splash", None)
        if splash is None:
            return
        w = self.display._width
        h = self.display._height
        bar_h = 24
        bar = displayio.Bitmap(w, bar_h, 1)
        pal = displayio.Palette(1)
        pal[0] = 0x0A121C
        splash.append(displayio.TileGrid(bar, pixel_shader=pal,
                                         x=0, y=h - bar_h))
        self._p1_label = label.Label(
            terminalio.FONT, text="P1  0:00", color=0xFFFF00, scale=2,
            anchor_point=(0.0, 1.0), anchored_position=(6, h - 3))
        splash.append(self._p1_label)
        p2_txt = "P2  0:00" if self._two_player else "P2  ---"
        self._p2_label = label.Label(
            terminalio.FONT, text=p2_txt, scale=2,
            color=0x33AAFF if self._two_player else 0x8899AA,
            anchor_point=(1.0, 1.0), anchored_position=(w - 6, h - 3))
        splash.append(self._p2_label)
        # Blue P2 cursor lives in the same splash so it clears with the board.
        if self._two_player:
            self._p2_hl = self._make_p2_highlight()
            splash.append(self._p2_hl)
            self._position_p2_highlight()
        self._score_bar_sec = -1
        self._update_score_bar(force=True)

    def _update_score_bar(self, force=False):
        """Refresh the live time(s), once per second."""
        if self._p1_label is None:
            return
        now = time.monotonic()
        if self._two_player:
            live = (now - self._q_start) if self._q_start is not None else 0.0
            secs = int(live)
            if not force and secs == self._score_bar_sec:
                return
            self._score_bar_sec = secs
            try:
                self._p1_label.text = "P1  " + self._format_time(
                    self._p1_time + live)
                if self._p2_label is not None:
                    self._p2_label.text = "P2  " + self._format_time(
                        self._p2_time + live)
            except Exception:
                pass
            return
        paused = (now - self._audio_active_since
                  if self._audio_active_since is not None else 0)
        disp = (now - self._run_start - paused) + self._score_sec
        if disp < 0:
            disp = 0
        secs = int(disp)
        if not force and secs == self._score_bar_sec:
            return
        self._score_bar_sec = secs
        txt = "P1  " + self._format_time(disp)
        if self._wrong_count:
            txt += "  x%d" % self._wrong_count
        try:
            self._p1_label.text = txt
        except Exception:
            pass

    # ----- menu navigation ------------------------------------------------

    def _load_menu(self, menu_file):
        from menu_parser import parse_menu_file
        menus_dir = getattr(self.machine, "_menus_dir", "/menus")
        menu_path = menus_dir + "/" + menu_file
        if self.storage:
            menu_path = self.storage.resolve_path(menu_path)
        print("Chicken Challenge: load menu:", menu_path)
        try:
            header, items = parse_menu_file(menu_path)
        except Exception as e:
            print("Chicken Challenge: cannot load", menu_path, ":", e)
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

        # Choose exactly ONE background: the active language's pre-rendered
        # board image if it's on the SD, else the menu's own background.
        # A single load avoids the visible blank flash (and doubled SD read)
        # of loading the English board and then overwriting it.
        chosen = None
        board = {"base.menu": "board_base",
                 "food.menu": "board_food"}.get(menu_file)
        if board:
            import os as _os
            bp = self._screen_path(board)
            try:
                _os.stat(bp)
                chosen = bp
            except OSError:
                chosen = None
        if chosen is None:
            bg = header.get("background")
            if bg:
                chosen = bg if bg.startswith("/") else menus_dir + "/" + bg
                if self.storage:
                    chosen = self.storage.resolve_path(chosen)
        if chosen:
            try:
                self.display.set_background(chosen)
            except Exception:
                pass

        try:
            self.display._highlight_index = -1
            self.display.set_highlight(0)
        except Exception:
            pass
        self._sel_index = 0
        self._update_item_text()
        self._attach_score_bar()

    def _navigate_back(self):
        if len(self._nav_stack) <= 1:
            return
        self._nav_stack.pop()
        prev = self._nav_stack.pop()
        self._load_menu(prev)

    # ----- audio ----------------------------------------------------------

    def _enqueue(self, path):
        """Queue a clip; tick() plays it non-blocking so the input loop
        never stalls (in-game word / feedback / prompt audio)."""
        if path:
            self._audio_q.append(self._resolve(path))

    def _say(self, path, block=True):
        if not path:
            return
        speak_start = time.monotonic()
        try:
            self.audio.play(self._resolve(path), block=block)
        except Exception as e:
            print("Chicken Challenge: sound error:", e)
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
