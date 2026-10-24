"""English <-> Japanese toggle for the AnimePipBoy base menu.

Launched from a menu item (`subprogram = stim_games/lang_toggle.py`).
Swaps the Machine's whole menu stack to the other language's base menu,
announces the new language, and returns straight to the talker. The
Machine redraws the (new) current menu when the subprogram exits.

Each language has its own base menu (and food submenu) pointing at that
language's sounds; the board always boots in English (config.txt
start_menu).
"""

import time

# (base menu, announcement sound) per language, toggled in order.
LANGS = (
    ("base_fruitjam.menu", "/button_sounds/lang_en.mp3"),
    ("base_fruitjam_ja.menu", "/button_sounds/ja/lang_ja.mp3"),
)


def run(machine, config=None):
    from menu_parser import MenuStack

    stack = machine._menu_stack
    current = stack._stack[0] if stack and stack._stack else LANGS[0][0]
    idx = 0
    for i, (menu_file, _sound) in enumerate(LANGS):
        if menu_file == current:
            idx = i
            break
    menu_file, sound = LANGS[(idx + 1) % len(LANGS)]
    print("Lang toggle:", current, "->", menu_file)

    # Retry like multi_lingual: first-time .menu reads can race on flash.
    for attempt in range(3):
        try:
            machine._menu_stack = MenuStack(
                machine._menus_dir, menu_file, storage=machine.storage)
            machine._build_grid()
            if hasattr(machine, "_reset_selection"):
                machine._reset_selection()
            break
        except Exception as e:  # noqa: BLE001
            print("Lang toggle: load attempt {} failed: {}".format(
                attempt + 1, e))
            time.sleep(0.1)
    else:
        print("Lang toggle: gave up loading", menu_file)
        machine._menu_stack = stack
        return

    try:
        machine.audio.play(sound)
    except Exception as e:  # noqa: BLE001
        print("Lang toggle: sound error:", e)
    # Drop the latched press so the talker doesn't re-trigger on resume.
    if hasattr(machine.input, "reset_button_latch"):
        machine.input.reset_button_latch()
