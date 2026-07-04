"""Generate language selection banner images for T-Rex Talker.

Creates one full-screen banner per language: 320x240, 1-bit (black
background, white bold text) showing the English name on top and the
native-script name below. The multi-lingual picker (stim_games/
multi_lingual.py) shows these while the encoder scrolls.

Font is chosen per writing system using Google Noto Sans Bold so every
script (Latin, Cyrillic, Thai, CJK, Arabic, Devanagari, Bengali) renders.

Existing images are skipped (like generate_language_sounds.py). Pass
--force to regenerate everything.

Output: out/lang_images/lang_<code>.bmp

Usage:
    pip install Pillow
    python tools/generate_language_images.py [--out DIR] [--force]
"""

import os
import sys
import argparse

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

# Import the language table from the sound generator (single source of truth).
sys.path.insert(0, os.path.dirname(__file__))
from generate_language_sounds import LANGUAGES

WIDTH, HEIGHT = 320, 240
MAX_TEXT_WIDTH = 300     # ~94% of width, matches the existing banners
MAX_FONT_SIZE = 58
MIN_FONT_SIZE = 20
EN_CENTER_Y = 78         # vertical centre of the English line
NATIVE_CENTER_Y = 165    # vertical centre of the native-script line

_NOTO = "/usr/share/fonts/truetype/noto/{}.ttf"
_NOTO_CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
LATIN_FONT = _NOTO.format("NotoSans-Bold")

# Native script -> font file. Latin/Cyrillic use the base NotoSans-Bold.
# Keyed by language code; unlisted codes fall back to LATIN_FONT.
SCRIPT_FONTS = {
    "th": _NOTO.format("NotoSansThai-Bold"),
    "ja": _NOTO_CJK,
    "zh": _NOTO_CJK,
    "hi": _NOTO.format("NotoSansDevanagari-Bold"),
    "ar": _NOTO.format("NotoSansArabic-Bold"),
    "bn": _NOTO.format("NotoSansBengali-Bold"),
}


def _fit_font(draw, text, font_path):
    """Return the largest ImageFont that keeps `text` within MAX_TEXT_WIDTH."""
    for size in range(MAX_FONT_SIZE, MIN_FONT_SIZE - 1, -2):
        font = ImageFont.truetype(font_path, size)
        left, _, right, _ = draw.textbbox((0, 0), text, font=font)
        if right - left <= MAX_TEXT_WIDTH:
            return font
    return ImageFont.truetype(font_path, MIN_FONT_SIZE)


def generate_image(lang_code, en_name, native_name, out_dir, force):
    """Render one lang_<code>.bmp banner."""
    filepath = os.path.join(out_dir, "lang_{}.bmp".format(lang_code))
    if os.path.exists(filepath) and not force:
        print("  SKIP (exists): {}".format(os.path.basename(filepath)))
        return

    img = Image.new("1", (WIDTH, HEIGHT), 0)  # 1-bit, black background
    draw = ImageDraw.Draw(img)

    en_font = _fit_font(draw, en_name, LATIN_FONT)
    native_path = SCRIPT_FONTS.get(lang_code, LATIN_FONT)
    native_font = _fit_font(draw, native_name, native_path)

    draw.text((WIDTH // 2, EN_CENTER_Y), en_name,
              fill=1, font=en_font, anchor="mm")
    draw.text((WIDTH // 2, NATIVE_CENTER_Y), native_name,
              fill=1, font=native_font, anchor="mm")

    img.save(filepath)
    print("  OK: {}".format(os.path.basename(filepath)))


def main():
    parser = argparse.ArgumentParser(description="Generate language banner images")
    parser.add_argument("--out", default="out/lang_images",
                        help="Output directory (default: out/lang_images)")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate images that already exist")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    print("Generating language banner images...")

    for lang_code, _, en_name, native_name, _ in LANGUAGES:
        generate_image(lang_code, en_name, native_name, args.out, args.force)

    print("\n=== Processed {} languages ===".format(len(LANGUAGES)))


if __name__ == "__main__":
    main()
