"""AAC Communication Device — main entry point."""

import time
import gc
import supervisor

# No auto-reload (AnimePipBoy): any write to CIRCUITPY by a connected
# computer -- even a metadata touch -- restarted the talker mid-use.
# Updates are copied over and then the board is hard-reset, so nothing
# relies on it. Ctrl-D in the REPL still reloads by hand.
supervisor.runtime.autoreload = False


def _quiet_unused_hardware():
    """Switch off Fruit Jam parts the talker never uses (AnimePipBoy).

    - USB-host 5 V switch: its enable line floats; drive it off.

    The clone board has no ESP32-C6 fitted. Its board definition names the
    audio codec's reset pin both ESP_RESET and PERIPH_RESET (one pin), so
    do not hold "ESP_RESET" here -- that silences the codec. Sleep holds
    that pin low on its own.

    The pin must stay claimed, or it floats back, so it is returned and
    kept for the life of the program.
    """
    import board
    import digitalio
    held = []
    for name in ("USB_HOST_5V_POWER",):
        try:
            pin = digitalio.DigitalInOut(getattr(board, name))
            pin.switch_to_output(value=False)
            held.append(pin)
            print("Power: {} held low".format(name))
        except Exception as e:
            print("Power: {} not held: {}".format(name, e))
    return held


_held_pins = _quiet_unused_hardware()


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
