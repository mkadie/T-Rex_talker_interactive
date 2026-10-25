"""Pip-Boy (AnimePipBoy) wake-from-sleep benchmark.

Paste into the REPL (Ctrl-C the app, Ctrl-E, paste, Ctrl-D). Runs the REAL
SleepManager._enter_software_idle() (rail cut, panel rebuilt) several times.
Each wake is triggered by a simulated encoder turn at a random moment, so
the wake-poll latency is sampled honestly. It reports, from that trigger:

  picture  the menu is actually on the panel (return + forced refresh)
  ready    a press would be accepted, following Machine.run()'s wake logic
           (fixed wake grace, or the release gate if Machine has it)

The screen goes dark and comes back once per cycle. No files are changed;
hard-reset afterwards (microcontroller.reset()) to get the app back.
"""
import time, random
T = time.monotonic

def rep(name, xs):
    xs = [x * 1000 for x in xs]
    print("BENCH %-24s n=%d min=%7.0f avg=%7.0f max=%7.0f ms" % (
        name, len(xs), min(xs), sum(xs) / len(xs), max(xs)))

from machine import Machine
m = Machine()
m._has_encoder_nav = m._config.get("encoder_navigation", False)
m._last_shown_index = -1
m._lang_active = False
sm = m.sleep
d = m.display
real_enc = m.input._encoder


class FakeEncoder:
    """Reads position 0 until `at`, then 1 — one simulated detent."""
    def __init__(self, at):
        self.at = at

    @property
    def position(self):
        return 1 if T() >= self.at else 0


pic, ready, audio_t = [], [], []
for cycle in range(4):
    trigger = T() + 2.0 + random.random() * 0.2
    m.input._encoder = FakeEncoder(trigger)
    sm._enter_software_idle()                 # the real sleep + wake path
    d.display.refresh()                       # picture is on the panel now
    t_pic = T()
    m.input._encoder = real_enc
    if hasattr(m, "_after_wake"):             # stage D and later
        t = T(); m._after_wake(); audio_t.append(T() - t)
        while not m._wake_gate_open():
            time.sleep(0.01)                  # same tick as Machine.run()
        t_ready = T()
    else:                                     # original Machine.run() logic
        wake_until = T() + m._config.get("wake_ignore_seconds", 1.0)
        t = T(); m.audio.reinit_after_wake(); audio_t.append(T() - t)
        t_ready = max(T(), wake_until)
    pic.append(t_pic - trigger)
    ready.append(t_ready - trigger)
    time.sleep(1.0)

rep("wake_to_picture", pic)
rep("wake_to_presses_ready", ready)
rep("post_wake_audio_step", audio_t)
print("BENCH DONE")
