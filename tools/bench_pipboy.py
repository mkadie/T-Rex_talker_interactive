"""Pip-Boy (AnimePipBoy) on-device benchmark.

Paste into the REPL (Ctrl-C the app, Ctrl-E, paste, Ctrl-D). It builds a
Machine without starting run(), times paints, navigation, sound and the
language toggle, and prints "BENCH ..." lines. It changes no files; the
board makes sounds and switches screens. Hard-reset afterwards
(microcontroller.reset()) to get the app back.
"""
import time, gc
T = time.monotonic_ns

def rep(name, xs):
    xs = [x / 1e6 for x in xs]
    print("BENCH %-28s n=%d min=%8.1f avg=%8.1f max=%8.1f ms" % (
        name, len(xs), min(xs), sum(xs) / len(xs), max(xs)))

gc.collect()
free0 = gc.mem_free()
t0 = T()
from machine import Machine
m = Machine()
rep("boot_machine_init", [T() - t0])
gc.collect()
print("BENCH mem_free_before_init %d after_init %d bytes" % (free0, gc.mem_free()))

d = m.display
disp = d.display
BASE = "/menus/images/base/base_board.bmp"
FOOD = "/menus/images/food/food_board.bmp"
N = 6

# 1. Raw flash read of a 61 KB board BMP
xs = []
for _ in range(N):
    t = T()
    with open(BASE, "rb") as f:
        while f.read(4096):
            pass
    xs.append(T() - t)
rep("flash_read_board_61KB", xs)

# 2. Full-screen paint cost (auto_refresh off, explicit refresh)
disp.auto_refresh = False
load, paint = {BASE: [], FOOD: []}, {BASE: [], FOOD: []}
for i in range(N * 2):
    p = BASE if i % 2 == 0 else FOOD
    t = T(); d.set_background(p); load[p].append(T() - t)
    t = T(); disp.refresh(); paint[p].append(T() - t)
rep("set_background_base(py)", load[BASE])
rep("refresh_base_board", paint[BASE])
rep("set_background_food(py)", load[FOOD])
rep("refresh_food_board", paint[FOOD])

# 3. Restore (group swap) + refresh — what restore_background() costs
xs = []
for _ in range(N):
    d.set_background(FOOD); disp.refresh()
    d.restore_background()
    t = T(); disp.refresh(); xs.append(T() - t)
rep("refresh_after_restore_bg", xs)

# 4. Encoder highlight move
d.set_background(BASE); disp.refresh()
pyx, rx = [], []
for i in range(N * 2):
    t = T(); d.set_highlight(i % 6); pyx.append(T() - t)
    t = T(); disp.refresh(); rx.append(T() - t)
rep("set_highlight(py)", pyx)
rep("refresh_highlight_move", rx)

# 5. Hint text
pyx, rx = [], []
for i in range(N):
    t = T(); d.set_text("How much for that? %d" % i); pyx.append(T() - t)
    t = T(); disp.refresh(); rx.append(T() - t)
rep("set_text(py)", pyx)
rep("refresh_text", rx)

# 6. Menu parse
from menu_parser import parse_menu_file
for name in ("base_fruitjam.menu", "food_fruitjam.menu"):
    xs = []
    for _ in range(N):
        t = T(); parse_menu_file("/menus/" + name); xs.append(T() - t)
    rep("parse_" + name, xs)

# run() sets these before the main loop; navigation needs them.
m._has_encoder_nav = m._config.get("encoder_navigation", False)
m._last_shown_index = -1
m._lang_active = False

# 7. Food/Drink in and Back out — explicit refresh (paint included)
m._update_display(); m._reset_selection(); disp.refresh()
ins, outs = [], []
for _ in range(3):
    t = T(); m._execute_menu_press(5); disp.refresh(); ins.append(T() - t)
    t = T(); m._execute_menu_press(5); disp.refresh(); outs.append(T() - t)
rep("nav_food_in(total)", ins)
rep("nav_back_out(total)", outs)

# 8. Same navigation as shipped (auto_refresh on) — python time only
disp.auto_refresh = True
time.sleep(0.5)
ins, outs = [], []
for _ in range(3):
    t = T(); m._execute_menu_press(5); ins.append(T() - t); time.sleep(0.5)
    t = T(); m._execute_menu_press(5); outs.append(T() - t); time.sleep(0.5)
rep("nav_food_in(autorefresh,py)", ins)
rep("nav_back_out(autorefresh,py)", outs)

# 9. Sound: play() wall time (subtract clip length host-side)
for path in ("/button_sounds/yes.mp3", "/button_sounds/ja/yes.mp3",
             "/button_sounds/how_much_for_that.mp3"):
    xs = []
    for _ in range(3):
        t = T(); m.audio.play(path); xs.append(T() - t)
    rep("play " + path.split("/button_sounds/")[1], xs)

# 10. Full button press with sound (Yes), as shipped
xs = []
for _ in range(3):
    t = T(); m._execute_menu_press(0); xs.append(T() - t)
rep("press_yes(total)", xs)

# 11. Language toggle press (includes announcement clip), there and back
xs = []
for _ in range(2):
    t = T(); m._execute_menu_press(4); xs.append(T() - t)
rep("press_swap_language(total)", xs)

gc.collect()
print("BENCH mem_free_end %d bytes" % gc.mem_free())
print("BENCH DONE")
