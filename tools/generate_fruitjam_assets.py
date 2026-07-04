"""Generate the Fruit Jam DVI demo's language UI assets.

The fruit_jam_dvi/code.py demo (320x240 framebuffer doubled to 640x480
HDMI) needs two kinds of image asset that differ from the full-screen
picker banners in generate_language_images.py:

  1. Band banners (320x40) — the bottom strip shown idle in the talker:
     native name on the left, a thin divider, English name on the right,
     white bold on navy.  One per language: lang_<code>.bmp.

  2. Help screen (320x240) — a single image listing every language,
     numbered, in its native script, under a title bar.  Shown for 5 s on
     F1.  code.py overlays a movable yellow cursor at
     ENTRY_TOP + i*LINE_H, so the geometry constants here MUST match the
     HELP_ENTRY_TOP / HELP_LINE_H constants in fruit_jam_dvi/code.py.

Both derive their language list from generate_language_sounds.LANGUAGES,
so adding a language there flows through here (and into the sound and
picker-image generators).

Band banners are skipped if they already exist (like the sound and
picker-image generators); pass --force to regenerate.  The help screen is
a single file listing every language, so it is always rebuilt.

Output:
    out/lang_banners_320x40/lang_<code>.bmp
    out/help_screen_320x240.bmp

Usage:
    pip install Pillow
    python tools/generate_fruitjam_assets.py [--out-dir DIR] [--force]
"""

import os
import sys
import argparse

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(__file__))
from generate_language_sounds import LANGUAGES
# Reuse the exact per-script font mapping the picker-image generator uses.
from generate_language_images import SCRIPT_FONTS, LATIN_FONT

# --- Shared palette (sampled from the original tested assets) -------------
NAVY_BAND = (16, 48, 128)     # band-banner background
DIVIDER = (204, 204, 204)     # band-banner centre divider
WHITE = (255, 255, 255)
HELP_BG = (16, 16, 32)        # help-screen background
HELP_TITLE_BG = (32, 32, 80)  # help-screen title bar
HELP_TITLE_RULE = (128, 128, 160)

# --- Band banner geometry ------------------------------------------------
BAND_W, BAND_H = 320, 40
BAND_HALF = BAND_W // 2       # divider column
BAND_MAX_FONT = 26

# --- Help screen geometry (MUST match fruit_jam_dvi/code.py) -------------
HELP_W, HELP_H = 320, 240
HELP_TITLE_H = 30             # title bar height (rule sits on its last row)
HELP_TITLE = "T-Rex Talker Multi-Lingual Demo"
# code.py: HELP_ENTRY_TOP = 32, HELP_LINE_H = 16.
# 13 entries: 32 + 13*16 = 240 -> fills the screen exactly.
HELP_ENTRY_TOP = 32
HELP_LINE_H = 16
HELP_TITLE_MAX_FONT = 20


def _fit_font(draw, text, font_path, max_width, max_font, min_font=8):
    """Largest ImageFont keeping `text` within `max_width` pixels."""
    for size in range(max_font, min_font - 1, -1):
        font = ImageFont.truetype(font_path, size)
        left, _, right, _ = draw.textbbox((0, 0), text, font=font)
        if right - left <= max_width:
            return font
    return ImageFont.truetype(font_path, min_font)


def _font_for(lang_code):
    return SCRIPT_FONTS.get(lang_code, LATIN_FONT)


def generate_band(lang_code, en_name, native_name, out_dir, force):
    """Render one 320x40 band banner: native | English on navy."""
    path = os.path.join(out_dir, "lang_{}.bmp".format(lang_code))
    if os.path.exists(path) and not force:
        print("  SKIP (exists): {}".format(os.path.basename(path)))
        return

    img = Image.new("RGB", (BAND_W, BAND_H), NAVY_BAND)
    draw = ImageDraw.Draw(img)

    # Centre divider (matches the sampled x=160, y6..34 rule).
    for y in range(6, 35):
        img.putpixel((BAND_HALF, y), DIVIDER)

    half_max = BAND_HALF - 24   # padding either side of the divider
    native_font = _fit_font(draw, native_name, _font_for(lang_code),
                            half_max, BAND_MAX_FONT)
    en_font = _fit_font(draw, en_name, LATIN_FONT, half_max, BAND_MAX_FONT)

    draw.text((BAND_HALF // 2, BAND_H // 2), native_name,
              fill=WHITE, font=native_font, anchor="mm")
    draw.text((BAND_HALF + BAND_HALF // 2, BAND_H // 2), en_name,
              fill=WHITE, font=en_font, anchor="mm")

    img.save(path)
    print("  OK: {}".format(os.path.basename(path)))


def generate_help(out_dir):
    """Render the 320x240 help screen listing every language, numbered."""
    path = os.path.join(out_dir, "help_screen_320x240.bmp")
    img = Image.new("RGB", (HELP_W, HELP_H), HELP_BG)
    draw = ImageDraw.Draw(img)

    # Title bar.
    draw.rectangle((0, 0, HELP_W - 1, HELP_TITLE_H - 1), fill=HELP_TITLE_BG)
    draw.line((0, HELP_TITLE_H, HELP_W - 1, HELP_TITLE_H), fill=HELP_TITLE_RULE)
    title_font = _fit_font(draw, HELP_TITLE, LATIN_FONT,
                           HELP_W - 12, HELP_TITLE_MAX_FONT)
    draw.text((HELP_W // 2, HELP_TITLE_H // 2), HELP_TITLE,
              fill=WHITE, font=title_font, anchor="mm")

    # Numbered native-script entries. The number column uses the Latin font;
    # the native name uses its script font. Each line centred in its slot so
    # code.py's HELP_LINE_H cursor lands on it.
    num_font = ImageFont.truetype(LATIN_FONT, HELP_LINE_H - 3)
    for i, (code, _g, _en, native, _w) in enumerate(LANGUAGES):
        cy = HELP_ENTRY_TOP + i * HELP_LINE_H + HELP_LINE_H // 2
        num = "{:2d}.".format(i + 1)
        draw.text((6, cy), num, fill=WHITE, font=num_font, anchor="lm")
        nat_font = _fit_font(draw, native, _font_for(code),
                             HELP_W - 46, HELP_LINE_H + 2)
        draw.text((42, cy), native, fill=WHITE, font=nat_font, anchor="lm")

    img.save(path)
    print("  OK: {} ({} languages)".format(
        os.path.basename(path), len(LANGUAGES)))


def main():
    parser = argparse.ArgumentParser(
        description="Generate Fruit Jam DVI demo language assets")
    parser.add_argument("--out-dir", default="out",
                        help="Base output dir (default: out)")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate band banners that already exist")
    args = parser.parse_args()

    band_dir = os.path.join(args.out_dir, "lang_banners_320x40")
    os.makedirs(band_dir, exist_ok=True)

    print("Generating band banners (320x40)...")
    for code, _g, en_name, native_name, _w in LANGUAGES:
        generate_band(code, en_name, native_name, band_dir, args.force)

    print("Generating help screen (320x240)...")
    generate_help(args.out_dir)

    print("\n=== Done: {} languages ===".format(len(LANGUAGES)))


if __name__ == "__main__":
    main()
