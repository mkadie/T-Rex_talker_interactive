"""AAC Communication Device — main entry point."""

import time
import gc
import supervisor

# No auto-reload (AnimePipBoy): any write to CIRCUITPY by a connected
# computer -- even a metadata touch -- restarted the talker mid-use.
# Updates are copied over and then the board is hard-reset, so nothing
# relies on it. Ctrl-D in the REPL still reloads by hand.
supervisor.runtime.autoreload = False


def _warm_flash():
    try:
        import es8311
    except ImportError:
        es8311 = None
    from adafruit_display_text import label
    from stim_games import subprogram, multi_lingual, game_config
    _ = (es8311, label, subprogram, multi_lingual, game_config)


gc.collect()
_warm_flash()
from machine import Machine
app = Machine()
app.run()
