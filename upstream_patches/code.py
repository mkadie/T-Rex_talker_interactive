"""AAC Communication Device — main entry point.

Change the machine variant in hardware_config.py (DEFAULT_VARIANT)
or pass it directly: Machine("CYD_PLUS") or Machine("TALKER_PICO2").
"""

import time
import gc


def _warm_flash():
    """Touch flash-resident modules CP otherwise loads lazily.

    The ESP32-S3 N16R8 hits a first-read race that produces phantom
    ImportError / SyntaxError / MemoryError on lazily-loaded modules
    during the first ~50 ms of boot. Importing them here, with the
    Machine still uncreated, lets a retry below recover cleanly.
    """
    import es8311  # used by audio_player._init_i2s
    from adafruit_display_text import label  # used by display_manager.set_text
    # All stim_games modules used by _launch_subprogram:
    from stim_games import subprogram, multi_lingual, game_config
    _ = (es8311, label, subprogram, multi_lingual, game_config)


_LAST_ERR = None
for _attempt in range(3):
    try:
        gc.collect()
        _warm_flash()
        from machine import Machine
        app = Machine()
        app.run()
        break
    except Exception as e:
        _LAST_ERR = e
        print("Boot attempt {} failed: {}: {}".format(
            _attempt + 1, type(e).__name__, e))
        time.sleep(0.1)
        gc.collect()
else:
    raise _LAST_ERR
