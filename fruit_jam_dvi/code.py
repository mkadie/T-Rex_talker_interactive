"""
Fruit Jam — Pim's 8-button board with multi-language sub-program.

Layout (320x240 framebuffer -> 640x480 HDMI):
    +--------------------------------------------------+
    |     4 x 2 button grid                            |
    |     cells 80x100 each (Moana icon + number)      |   200 px
    +--------------------------------------------------+
    |  bottom band: language banner OR last press      |    40 px
    +--------------------------------------------------+

Inputs:
  - Numeric keys / keypad 1..8 -> activate cell 1..8
  - BUTTON1 / BUTTON2 / BUTTON3 -> activate cell 1 / 2 / 3
  - F1                  -> show 5 s help screen (lists all 12 languages)
  - Space               -> manually toggle audio route (most useful while a
                          headphone is plugged in to override the auto-route)
  - Tab                 -> next language
  - Shift-Tab           -> previous language

The Fruit Jam's TLV320DAC3100 has hardware headset detection on the 3.5 mm
jack. The main loop polls dac.headset_status every 500 ms; on a stable
plug/unplug transition it auto-swaps p.audio_output. Manual Space overrides
that until the next physical plug change.

Files expected on the CIRCUITPY drive:
  /boot.py                     usb_host setup (PIO-USB host port)
  /lang/lang_<code>.bmp             320x40 native-font language banners
  /help.bmp                         320x240 help screen (all 12 languages)
  /images/moana/icon_<n>.bmp        80x100 Moana icon for each of 8 cells
  /images/moana_full/icon_<n>.bmp   320x240 full-screen icon shown on press
  /sounds/<code>/<word>.wav    per-language sound files (12 codes,
                               8 words each: milk, water, snack, play,
                               mum, yes, no, thankyou)
"""

import time
import gc
import board
import displayio
import supervisor
import terminalio
import bitmaptools
import audiocore
import audiomp3
from adafruit_display_text import label
from adafruit_fruitjam.peripherals import Peripherals, request_display_config

try:
    import usb.core
    import adafruit_usb_host_descriptors as _usbhd
    _HAS_USB = True
except ImportError:
    _HAS_USB = False


# --- Display ---------------------------------------------------------------
FB_W, FB_H = 320, 240
GRID_H = 200
BAND_H = 40
BAND_Y = GRID_H

displayio.release_displays()
request_display_config(FB_W, FB_H)
display = supervisor.runtime.display
print("DVI ready: %dx%d fb -> 640x480 hdmi (grid %dx%d, band %dx%d)" % (
    FB_W, FB_H, FB_W, GRID_H, FB_W, BAND_H))


# --- Audio ---------------------------------------------------------------
# Headphone-jack output, with levels matching the working speaker config:
#   speaker_volume = 0 dB   (analog speaker DAC volume, max)
#   speaker_gain   = 24 dB  (analog speaker amp gain, max)
# Headphone equivalents are at the same numeric values where possible:
#   headphone_volume       = 0 dB   (analog HP volume, max)
#   headphone_left/right_gain = 9 dB  (HP amp gain, max — the API caps
#                                      this at 9 dB; speaker_gain caps
#                                      at 24, so they can't be exactly
#                                      identical, but both are at max)
p = Peripherals()
audio = p.audio


def _apply_levels():
    """Restore our intended volume/gain settings.

    The Adafruit Peripherals `audio_output` setter calls "quickstart" presets
    on the underlying TLV320DAC3100 driver that clobber several registers:
    * audio_output='speaker'  -> speaker_volume=-10, speaker_gain=12
    * audio_output='headphone'-> headphone_volume=-20.1, hp_l/r_gain=6
    Both also reset DAC channel volumes. We need to re-apply our values
    AFTER each route change so they actually stick.
    """
    p.dac.dac_volume = -10
    p.dac.speaker_volume = 0      # 0 dB analog attenuation (max)
    p.dac.speaker_gain = 24       # 24 dB amp gain (max)
    p.dac.headphone_volume = 0    # 0 dB analog attenuation (max)
    p.dac.headphone_left_gain = 9 # 9 dB amp gain (max — chip cap)
    p.dac.headphone_right_gain = 9


def set_route(route):
    global audio_route
    p.audio_output = route        # this clobbers levels
    _apply_levels()               # ...so we restore them
    audio_route = route


# --- Headset jack detection (auto-route on plug/unplug) -------------------
HP_POLL_SEC = 0.5             # how often we read headset_status
HP_DEBOUNCE_SEC = 1.0         # how long a new status must hold before we act

try:
    # detect_debounce=4 -> 256 ms hardware debounce in the codec
    p.dac.set_headset_detect(True, detect_debounce=4, button_debounce=2)
    time.sleep(0.5)            # let detection settle past wake transient
except Exception as e:
    print("headset detect init err:", type(e).__name__, e)


def _wanted_route_from(status):
    """0 (none) -> speaker; 1 (headphone-no-mic) or 3 (headset+mic) -> headphone."""
    return "speaker" if status == 0 else "headphone"


# Initial route follows the current detection state.
audio_route = "speaker"        # placeholder; set_route assigns the real value
try:
    initial_status = p.dac.headset_status
except Exception:
    initial_status = 0
set_route(_wanted_route_from(initial_status))
last_hp_poll = 0.0
last_hp_status = initial_status
hp_pending_status = initial_status
hp_pending_since = 0.0

print("DAC ready  (route=%s, dac=%+d, spk_vol=%+d, spk_gain=%+d, "
      "hp_vol=%+d, hp_gain=%d/%d, status=%d)" % (
          audio_route,
          p.dac.dac_volume, p.dac.speaker_volume, p.dac.speaker_gain,
          p.dac.headphone_volume,
          p.dac.headphone_left_gain, p.dac.headphone_right_gain,
          initial_status))
# --- Cell + language data -------------------------------------------------
COLS, ROWS = 4, 2
NUM_CELLS = COLS * ROWS
CELL_W = FB_W // COLS    # 80
CELL_H = GRID_H // ROWS  # 100

# Same 8 words, in cell order. The English label is the canonical key for
# the sound filename ('thankyou.wav', not 'thank_you.wav') to match the
# T-Rex_talker_interactive language packs.
WORDS = [
    ("Milk",      "milk"),
    ("Water",     "water"),
    ("Snack",     "snack"),
    ("Play",      "play"),
    ("Mum",       "mum"),
    ("Yes",       "yes"),
    ("No",        "no"),
    ("Thank You", "thankyou"),
]

CELL_COLORS = [
    0xFFEEAA, 0x66CCFF, 0xFFAA66, 0xFF66AA,
    0xCC99FF, 0x66FF66, 0xFF8888, 0xFFCC66,
]
ICON_PATHS = ["/images/moana/icon_%d.bmp" % i for i in range(1, NUM_CELLS + 1)]
ICON_FULL_PATHS = ["/images/moana_full/icon_%d.bmp" % i for i in range(1, NUM_CELLS + 1)]
PRESS_MIN_HOLD = 1.5   # seconds — full-screen stays at least this long

# 12 languages, same order as upstream talker_v3/machine.py LANGUAGES
LANGUAGES = [
    {"code": "th", "english": "Thai",       "banner": "/lang/lang_th.bmp"},
    {"code": "ja", "english": "Japanese",   "banner": "/lang/lang_ja.bmp"},
    {"code": "en", "english": "English",    "banner": "/lang/lang_en.bmp"},
    {"code": "zh", "english": "Mandarin",   "banner": "/lang/lang_zh.bmp"},
    {"code": "hi", "english": "Hindi",      "banner": "/lang/lang_hi.bmp"},
    {"code": "es", "english": "Spanish",    "banner": "/lang/lang_es.bmp"},
    {"code": "fr", "english": "French",     "banner": "/lang/lang_fr.bmp"},
    {"code": "ar", "english": "Arabic",     "banner": "/lang/lang_ar.bmp"},
    {"code": "bn", "english": "Bengali",    "banner": "/lang/lang_bn.bmp"},
    {"code": "pt", "english": "Portuguese", "banner": "/lang/lang_pt.bmp"},
    {"code": "ru", "english": "Russian",    "banner": "/lang/lang_ru.bmp"},
    {"code": "cs", "english": "Czech",      "banner": "/lang/lang_cs.bmp"},
]


def _luma(rgb):
    r = (rgb >> 16) & 0xFF
    g = (rgb >> 8) & 0xFF
    b = rgb & 0xFF
    return (r * 299 + g * 587 + b * 114) // 1000


def build_grid():
    """Top-200px grid: cell-color background, Moana icon, small number label.

    No language-dependent text in the cell — the icon carries the meaning,
    the bottom band carries the language indicator and the press feedback.
    """
    root = displayio.Group()

    # Colored cell-color background
    palette = displayio.Palette(NUM_CELLS + 1)
    palette[0] = 0x000000
    for i in range(NUM_CELLS):
        palette[i + 1] = CELL_COLORS[i]
    bg = displayio.Bitmap(FB_W, GRID_H, NUM_CELLS + 1)
    for i in range(NUM_CELLS):
        col = i % COLS
        row = i // COLS
        x0 = col * CELL_W + 2
        y0 = row * CELL_H + 2
        x1 = (col + 1) * CELL_W - 2
        y1 = (row + 1) * CELL_H - 2
        bitmaptools.fill_region(bg, x0, y0, x1, y1, i + 1)
    root.append(displayio.TileGrid(bg, pixel_shader=palette, x=0, y=0))

    # Moana icon per cell (80x100 each — fills the cell).
    for i in range(NUM_CELLS):
        col = i % COLS
        row = i // COLS
        try:
            odb = displayio.OnDiskBitmap(ICON_PATHS[i])
            tg = displayio.TileGrid(
                odb, pixel_shader=odb.pixel_shader,
                x=col * CELL_W, y=row * CELL_H,
            )
            root.append(tg)
        except Exception as e:
            print("icon %d load failed: %s" % (i + 1, e))

    # Small number label in top-left corner of each cell
    for i in range(NUM_CELLS):
        col = i % COLS
        row = i // COLS
        text_color = 0x000000 if _luma(CELL_COLORS[i]) > 140 else 0xFFFFFF
        num = label.Label(terminalio.FONT, text=str(i + 1),
                          color=text_color, scale=2,
                          background_color=CELL_COLORS[i])
        num.anchor_point = (0.0, 0.0)
        num.anchored_position = (col * CELL_W + 4, row * CELL_H + 4)
        root.append(num)

    return root


def build_highlight():
    """Yellow border that we move around to indicate the active cell."""
    border = 4
    bmp = displayio.Bitmap(CELL_W, CELL_H, 2)
    pal = displayio.Palette(2)
    pal[0] = 0x000000
    pal.make_transparent(0)
    pal[1] = 0xFFFF00
    for x in range(CELL_W):
        for b in range(border):
            bmp[x, b] = 1
            bmp[x, CELL_H - 1 - b] = 1
    for y in range(CELL_H):
        for b in range(border):
            bmp[b, y] = 1
            bmp[CELL_W - 1 - b, y] = 1
    return displayio.TileGrid(bmp, pixel_shader=pal, x=0, y=0)


def load_band_banner(path):
    """Wrap a 320x40 language banner BMP as a TileGrid in the bottom band."""
    try:
        odb = displayio.OnDiskBitmap(path)
        return displayio.TileGrid(
            odb, pixel_shader=odb.pixel_shader, x=0, y=BAND_Y,
        )
    except Exception as e:
        print("banner load failed (%s):" % path, type(e).__name__, e)
        bmp = displayio.Bitmap(FB_W, BAND_H, 1)
        pal = displayio.Palette(1); pal[0] = 0x202020
        return displayio.TileGrid(bmp, pixel_shader=pal, x=0, y=BAND_Y)


def make_idle_band(banner_tile):
    g = displayio.Group()
    g.append(banner_tile)
    return g


# Cache OnDiskBitmap objects so repeated presses don't churn memory.
_full_odb_cache = [None] * NUM_CELLS
_full_pal_cache = [None] * NUM_CELLS


def build_full_icon(idx):
    """320x240 full-screen icon shown while the press sound plays.

    OnDiskBitmap is loaded once per icon and cached. Each call still
    allocates a fresh Group + TileGrid (cheap; the TileGrid can only have
    one parent), but no per-press image read/parse.
    """
    g = displayio.Group()
    odb = _full_odb_cache[idx]
    if odb is None:
        try:
            odb = displayio.OnDiskBitmap(ICON_FULL_PATHS[idx])
            _full_odb_cache[idx] = odb
            _full_pal_cache[idx] = odb.pixel_shader
        except Exception as e:
            print("full icon load failed (%s):" % ICON_FULL_PATHS[idx],
                  type(e).__name__, e)
            bmp = displayio.Bitmap(FB_W, FB_H, 1)
            pal = displayio.Palette(1); pal[0] = CELL_COLORS[idx]
            g.append(displayio.TileGrid(bmp, pixel_shader=pal))
            return g
    g.append(displayio.TileGrid(odb, pixel_shader=_full_pal_cache[idx]))
    return g


# --- Audio playback --------------------------------------------------------
def sound_path(lang_code, word_key):
    return "/sounds/%s/%s.wav" % (lang_code, word_key)


def play_sound(path):
    try:
        f = open(path, "rb")
    except OSError:
        print("sound missing:", path)
        return
    try:
        if path.lower().endswith(".mp3"):
            sample = audiomp3.MP3Decoder(f)
        else:
            sample = audiocore.WaveFile(f)
        t0 = time.monotonic()
        audio.play(sample)
        while audio.playing:
            time.sleep(0.02)
        print("  played %s in %.2fs" % (path, time.monotonic() - t0))
    finally:
        f.close()


# --- USB HID keyboard ------------------------------------------------------
KEY_F1    = 0x3A
KEY_TAB   = 0x2B
KEY_SPACE = 0x2C
# Modifier byte (boot report byte 0)
MOD_LSHIFT = 0x02
MOD_RSHIFT = 0x20
SHIFT_MASK = MOD_LSHIFT | MOD_RSHIFT

# HID usage code -> button index 0..7 (cell 1..8)
KEY_TO_IDX = {
    0x1E: 0, 0x1F: 1, 0x20: 2, 0x21: 3,
    0x22: 4, 0x23: 5, 0x24: 6, 0x25: 7,
    0x59: 0, 0x5A: 1, 0x5B: 2, 0x5C: 3,
    0x5D: 4, 0x5E: 5, 0x5F: 6, 0x60: 7,
}


class Kbd:
    def __init__(self):
        self._dev = None
        self._ep = 0x81
        self._buf = bytearray(8)
        self._prev = set()
        self._next = 0.0

    def _try_attach(self):
        if not _HAS_USB:
            return
        try:
            devs = list(usb.core.find(find_all=True))
        except Exception as e:
            print("usb.find err:", type(e).__name__, repr(e))
            return
        for d in devs:
            try:
                info = _usbhd.find_boot_keyboard_endpoint(d)
            except Exception as e:
                print("descriptor err:", type(e).__name__, repr(e))
                continue
            if info is None:
                continue
            if isinstance(info, tuple):
                ep = None
                for x in info:
                    if isinstance(x, int) and (x & 0x80):
                        ep = x; break
                if ep is None:
                    continue
            else:
                ep = info
            try:
                d.set_configuration()
            except Exception:
                pass
            self._dev = d
            self._ep = ep
            print("kbd VID:%04x PID:%04x ep=0x%02x" % (
                d.idVendor, d.idProduct, ep))
            return

    def poll(self):
        """Return (cell_indices, raw_key_codes, modifier_byte)."""
        if self._dev is None:
            now = time.monotonic()
            if now < self._next:
                return set(), set(), 0
            self._next = now + 1.0
            self._try_attach()
            if self._dev is None:
                return set(), set(), 0
        try:
            self._dev.read(self._ep, self._buf, timeout=2)
        except Exception as e:
            if "timeout" in str(e).lower() or type(e).__name__ == "USBTimeoutError":
                return set(), set(), 0
            print("kbd read err, dropping:", type(e).__name__, repr(e))
            self._dev = None
            self._prev = set()
            return set(), set(), 0
        mods = self._buf[0]
        keys_now = set(b for b in self._buf[2:8] if b)
        new_keys = keys_now - self._prev
        self._prev = keys_now
        cells = set(KEY_TO_IDX[k] for k in new_keys if k in KEY_TO_IDX)
        return cells, new_keys, mods


# --- Main ------------------------------------------------------------------
lang_idx = 0   # start on Thai

# Persistent layers, attached to root in this order:
#   root[0] = grid (cells + icons + numbers)  -- swapped on language change
#   root[1] = bottom band (idle banner OR selection panel)
#   root[2] = highlight (yellow rectangle, moves with selection)
grid_layer = build_grid()
banner_tile = load_band_banner(LANGUAGES[lang_idx]["banner"])
band_idle_group = make_idle_band(banner_tile)
highlight = build_highlight()

root = displayio.Group()
root.append(grid_layer)
root.append(band_idle_group)
root.append(highlight)
display.root_group = root


# --- Help screen -----------------------------------------------------------
HELP_DURATION = 5.0   # seconds


def build_help_screen():
    """Full-screen 320x240 group: pre-rendered help BMP + movable highlight.

    The BMP at /help.bmp shows a title bar plus 12 numbered language entries.
    A 320x17 yellow border overlay marks the currently active language.
    Layout in the BMP: ENTRY_TOP=32, LINE_H=17.
    """
    g = displayio.Group()
    try:
        odb = displayio.OnDiskBitmap("/help.bmp")
        g.append(displayio.TileGrid(odb, pixel_shader=odb.pixel_shader))
    except Exception as e:
        print("help.bmp load failed:", type(e).__name__, e)
        bmp = displayio.Bitmap(FB_W, FB_H, 1)
        pal = displayio.Palette(1); pal[0] = 0x202050
        g.append(displayio.TileGrid(bmp, pixel_shader=pal))

    # Yellow border overlay for the currently active language line
    line_h = 17
    bmp = displayio.Bitmap(FB_W, line_h, 2)
    pal = displayio.Palette(2)
    pal[0] = 0x000000
    pal.make_transparent(0)
    pal[1] = 0xFFFF00
    border = 2
    for x in range(FB_W):
        for b in range(border):
            bmp[x, b] = 1
            bmp[x, line_h - 1 - b] = 1
    for y in range(line_h):
        for b in range(border):
            bmp[b, y] = 1
            bmp[FB_W - 1 - b, y] = 1
    cursor = displayio.TileGrid(bmp, pixel_shader=pal, x=0, y=0)
    g.append(cursor)
    return g, cursor


HELP_ENTRY_TOP = 32
HELP_LINE_H = 17

help_screen, help_cursor = build_help_screen()
help_until = 0.0   # 0 = help not active


def set_language(new_idx):
    """Swap only the bottom-band banner — grid stays the same. Avoids
    re-parenting any TileGrid (which causes ValueError in displayio)."""
    global lang_idx, band_idle_group
    lang_idx = new_idx % len(LANGUAGES)
    new_banner_tile = load_band_banner(LANGUAGES[lang_idx]["banner"])
    new_band_idle = make_idle_band(new_banner_tile)
    root[1] = new_band_idle
    band_idle_group = new_band_idle
    L = LANGUAGES[lang_idx]
    print("language -> %s (%s) [%d/%d]" % (
        L["english"], L["code"], lang_idx + 1, len(LANGUAGES)))


kb = Kbd()
kb._try_attach()

prev_phys = (p.button1, p.button2, p.button3)
last_heartbeat = 0.0

print("\nREADY  keys 1..8 / BUTTON1-3 to play")
print("       F1              -> help screen (5 s)")
print("       Space           -> toggle speaker/headphone")
print("       Tab             -> next language")
print("       Shift-Tab       -> previous language")
for i, L in enumerate(LANGUAGES):
    print("  %2d. %s (%s)" % (i + 1, L["english"], L["code"]))

while True:
    pressed_cells = set()
    raw_keys = set()
    mods = 0

    cur_phys = (p.button1, p.button2, p.button3)
    for i in range(3):
        if cur_phys[i] and not prev_phys[i]:
            pressed_cells.add(i)
    prev_phys = cur_phys

    cells, raw, m = kb.poll()
    pressed_cells |= cells
    raw_keys |= raw
    mods |= m

    t = time.monotonic()
    if t - last_heartbeat >= 15.0:
        last_heartbeat = t
        print("alive  lang=%s  kbd=%s  route=%s  hp_status=%d" % (
            LANGUAGES[lang_idx]["code"], kb._dev is not None,
            audio_route, last_hp_status))

    # Headset auto-route: poll status, debounce, swap when status stably
    # changes. Manual Space override (below) is not affected unless the
    # physical plug state actually changes.
    if t - last_hp_poll >= HP_POLL_SEC:
        last_hp_poll = t
        try:
            hps = p.dac.headset_status
        except Exception as hp_e:
            hps = hp_pending_status
            print("headset_status read err:", type(hp_e).__name__, hp_e)
        if hps != hp_pending_status:
            hp_pending_status = hps
            hp_pending_since = t
        elif (hp_pending_status != last_hp_status
              and (t - hp_pending_since) >= HP_DEBOUNCE_SEC):
            last_hp_status = hp_pending_status
            wanted = _wanted_route_from(last_hp_status)
            print("headset_status stable at %d -> route should be %s" % (
                last_hp_status, wanted))
            if wanted != audio_route and not audio.playing:
                set_route(wanted)
                print("auto route -> %s" % audio_route)

    # Space -> toggle audio route (and re-apply our levels after the swap)
    if KEY_SPACE in raw_keys:
        new_route = "speaker" if audio_route == "headphone" else "headphone"
        if not audio.playing:
            try:
                set_route(new_route)
                print("audio route -> %s" % audio_route)
            except Exception as e:
                print("audio_output set err:", type(e).__name__, e)
        else:
            print("space deferred: audio still playing (route=%s)" % audio_route)

    # If help screen is up, only the timeout (or another F1) dismisses
    if help_until:
        if t >= help_until or KEY_F1 in raw_keys:
            help_until = 0.0
            display.root_group = root
            print("help dismissed")
        # Skip other input handling while help is showing
        time.sleep(0.02)
        prev_phys = (p.button1, p.button2, p.button3)
        continue

    # F1 -> show the help screen, with current language highlighted
    if KEY_F1 in raw_keys:
        try:
            help_cursor.x = 0
            help_cursor.y = HELP_ENTRY_TOP + lang_idx * HELP_LINE_H
            display.root_group = help_screen
            help_until = t + HELP_DURATION
            print("help shown (lang=%s, %d/%d) — timeout %.0fs" % (
                LANGUAGES[lang_idx]["code"], lang_idx + 1,
                len(LANGUAGES), HELP_DURATION))
        except Exception as e:
            print("help handler error:", type(e).__name__, repr(e))
            help_until = 0.0
            try:
                display.root_group = root
            except Exception:
                pass
        time.sleep(0.02)
        continue

    # Language cycle: Tab forward, Shift-Tab backward
    if KEY_TAB in raw_keys:
        if mods & SHIFT_MASK:
            set_language(lang_idx - 1)
        else:
            set_language(lang_idx + 1)

    if pressed_cells:
        idx = min(pressed_cells)
        try:
            en_word, key = WORDS[idx]
            L = LANGUAGES[lang_idx]
            snd = sound_path(L["code"], key)
            free = gc.mem_free() if hasattr(gc, "mem_free") else -1
            print("PRESS idx=%d  %s [%s]  -> %s  (mem_free=%d)" % (
                idx, en_word, L["code"], snd, free))

            # Move highlight to active cell so it's correct when grid returns
            col = idx % COLS
            row = idx // COLS
            highlight.x = col * CELL_W
            highlight.y = row * CELL_H

            # Show the icon full-screen while audio plays
            full = build_full_icon(idx)
            display.root_group = full
            t0 = time.monotonic()
            play_sound(snd)
            # Hold the full-screen view for at least PRESS_MIN_HOLD total
            elapsed = time.monotonic() - t0
            if elapsed < PRESS_MIN_HOLD:
                time.sleep(PRESS_MIN_HOLD - elapsed)
            display.root_group = root
            full = None        # drop reference; let GC reclaim the Group/TileGrid
            gc.collect()
        except Exception as e:
            print("press handler error:", type(e).__name__, repr(e))
            # Make sure we end up back on the grid even if we crashed mid-press
            try:
                display.root_group = root
            except Exception:
                pass

        prev_phys = (p.button1, p.button2, p.button3)

    time.sleep(0.02)
