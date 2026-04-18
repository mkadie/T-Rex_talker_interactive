"""Base class and protocol for T-Rex Talker subprograms (stim games etc.).

A Subprogram is a short-lived Python module that takes over the device's
input and output for a while, then returns control to the menu system.

Design principles
-----------------
1. The Machine already initialized ALL hardware (display, audio, input,
   pixel, storage, sleep). Subprograms RECEIVE these references — they
   should NEVER re-initialize hardware, and they MUST NOT deinit any
   shared resource on exit.
2. A subprogram runs its own input-poll loop. It calls `machine.input.poll()`
   directly (or reads `machine.input.selected_index`, `encoder_button_held`,
   etc.) instead of going through `_handle_press`.
3. Exit is triggered by a game-defined gesture (e.g. encoder long-press,
   emergency hold, or a game-over condition). When `run()` returns, the
   Machine's menu loop resumes exactly where it left off.
4. Subprograms can play sounds, draw on the display, and set the status
   pixel, but should `machine.display.restore_background()` (or paint
   a fresh background) before returning so the menu is legible.

Subclass interface
------------------
class MyGame(Subprogram):
    name = "My Stim Game"

    def setup(self):
        # Called once before the loop.
        ...

    def tick(self):
        # Called once per frame. Return False to exit.
        ...

    def teardown(self):
        # Called once before returning to the menu.
        ...

Or expose a plain `run(machine, config=None)` function at module level.
"""

import time


class Subprogram:
    """Base class — games may subclass, or just provide a run() function."""

    name = "Subprogram"
    # When True, the Machine will hide the menu background on entry
    # and restore it on exit. When False, the subprogram is responsible
    # for all drawing.
    auto_clear_display = True

    def __init__(self, machine, config=None):
        self.machine = machine
        # A dict — either loaded from a .cfg sidecar or passed explicitly
        self.config = config or {}
        # Convenience aliases for the subsystems the Machine already owns
        self.display = machine.display
        self.audio = machine.audio
        self.input = machine.input
        self.pixel = getattr(machine, "_pixel", None)
        self.storage = machine.storage
        self._running = False

    # --- lifecycle hooks — override these in subclasses --------------------

    def setup(self):
        """Called once before the main loop."""
        pass

    def tick(self):
        """Called every iteration of the main loop.

        Return True  — keep running
        Return False — exit subprogram, back to menu
        """
        return False

    def teardown(self):
        """Called once on exit, even if tick() raised.

        Default: no-op. Subclasses can override to clean up game state.
        Note: do NOT deinit shared hardware; the Machine still needs it.
        """
        pass

    # --- convenience helpers available to subclasses ----------------------

    def play_sound(self, path, wait=True):
        """Play a sound through the shared audio player."""
        if not path or not self.audio:
            return
        try:
            self.audio.play(path)
            # AudioPlayer.play is typically blocking on CircuitPython;
            # the `wait` flag is retained for clarity / future async.
        except Exception as e:  # noqa: BLE001
            print("Subprogram sound error:", e)

    def set_status(self, color):
        """Set the onboard NeoPixel to a (r,g,b) tuple."""
        if self.pixel is None:
            return
        try:
            self.pixel[0] = color
        except Exception:  # noqa: BLE001
            pass

    def exit_requested(self):
        """Default exit gesture: encoder-hold for 2 seconds.

        Subclasses can override to use a different exit gesture.
        Returns True if the user wants to leave the subprogram.
        """
        hold_ok = getattr(self.input, "encoder_button_held", False)
        if hold_ok:
            if not hasattr(self, "_exit_hold_start"):
                self._exit_hold_start = time.monotonic()
            elif time.monotonic() - self._exit_hold_start >= 2.0:
                return True
        else:
            if hasattr(self, "_exit_hold_start"):
                del self._exit_hold_start
        return False

    # --- default main-loop driver (subclasses may override run) -----------

    def run(self):
        """Run the subprogram to completion."""
        self._running = True
        try:
            self.setup()
            while self._running:
                cont = self.tick()
                if cont is False:
                    break
                if self.exit_requested():
                    break
                time.sleep(0.01)
        finally:
            try:
                self.teardown()
            except Exception as e:  # noqa: BLE001
                print("Subprogram teardown error:", e)


# ---- Module loader ------------------------------------------------------

def load_subprogram(module_path, machine, config=None):
    """Import a subprogram module by dotted path or file path.

    Accepts either:
        "stim_games.bubble_pop"
        "stim_games/bubble_pop.py"
        "/stim_games/bubble_pop.py"

    Returns a callable `runner()` that drives the subprogram.
    """
    mod_name = module_path
    # Normalize "stim_games/foo.py" → "stim_games.foo"
    if mod_name.endswith(".py"):
        mod_name = mod_name[:-3]
    mod_name = mod_name.replace("\\", "/").strip("/").replace("/", ".")

    mod = __import__(mod_name, globals(), locals(), [mod_name.rsplit(".", 1)[-1]])

    # Prefer an explicit GAME attribute (subclass of Subprogram)
    game_cls = getattr(mod, "GAME", None)
    if game_cls is not None:
        instance = game_cls(machine, config=config)
        return instance.run

    # Fall back to a plain run(machine, config) function
    run_fn = getattr(mod, "run", None)
    if run_fn is None:
        raise AttributeError(
            "Subprogram '{}' must expose a Subprogram subclass as "
            "GAME or a top-level run() function".format(mod_name)
        )

    def runner():
        return run_fn(machine, config=config)

    return runner


def launch_subprogram(machine, module_path, config=None):
    """Load and run a subprogram, restoring the display on exit.

    This is the function the Machine calls when it encounters a
    `subprogram:` navigation action.
    """
    print("Subprogram launch:", module_path)
    prev_status = getattr(machine, "_status", None)
    try:
        runner = load_subprogram(module_path, machine, config=config)
        runner()
    except Exception as e:  # noqa: BLE001
        print("Subprogram error:", e)
    finally:
        # Always restore the menu background so the user sees something sensible.
        try:
            machine.display.restore_background()
        except Exception:  # noqa: BLE001
            pass
        try:
            machine.set_status("ready")
        except Exception:  # noqa: BLE001
            pass
    print("Subprogram returned:", module_path)
