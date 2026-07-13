"""Generate per-language .menu files for T-Rex Talker.

Creates menus/lang_<code>.menu for each supported language,
all with the same 4x2 Moana button layout but different
sound paths and text_descriptions.

Usage:
    python tools/generate_language_menus.py [--out DIR]
"""

import os
import sys
import argparse

# Import the language table from the sound generator
sys.path.insert(0, os.path.dirname(__file__))
from generate_language_sounds import LANGUAGES

# Button layout: position, id, label, image path
BUTTONS = [
    (1, "tired",    "Tired",     "/lcd_images/8_Icons-01.bmp"),
    (2, "happy",    "Happy",     "/lcd_images/8_Icons-02.bmp"),
    (3, "snack",    "Snack",     "/lcd_images/8_Icons-03.bmp"),
    (4, "play",     "Play",      "/lcd_images/8_Icons-04.bmp"),
    (5, "mum",      "Mum",      "/lcd_images/8_Icons-05.bmp"),
    (6, "yes",      "Yes",       "/lcd_images/8_Icons-06.bmp"),
    (7, "no",       "No",        "/lcd_images/8_Icons-07.bmp"),
    (8, "thankyou", "Thank You", "/lcd_images/8_Icons-08.bmp"),
]

MENU_TEMPLATE = """# ===================================================
#  Language Menu — {en_name} / {native_name}
#
#  Layout (4 columns x 2 rows):
#
#  +----------+----------+----------+----------+
#  |   Milk   |  Water   |  Snack   |   Play   |
#  |    1     |    2     |    3     |    4     |
#  +----------+----------+----------+----------+
#  |   Mum    |   Yes    |    No    | Thank You|
#  |    5     |    6     |    7     |    8     |
#  +----------+----------+----------+----------+
# ===================================================

[menu]
name = {en_name} / {native_name}
text_description = {native_name}
type = grid
columns = 4
rows = 2
background = /lcd_images/0_needs_small_unc.bmp
"""

BUTTON_TEMPLATE = """
[{btn_id}]
label = {label}
text_description = {label} / {native_word}
image = {image}
sound = {sound_path}
position = {position}
"""


def generate_menu(lang_code, en_name, native_name, words, out_dir):
    """Generate a single language .menu file."""
    content = MENU_TEMPLATE.format(en_name=en_name, native_name=native_name)

    for pos, btn_id, label, image in BUTTONS:
        native_word = words[btn_id]

        # All languages read from the on-device word-indexed audio tree
        # /sounds/<code>/<word>.wav (the tree the 13-language pack ships
        # populated). Uniform, word-only names — no per-language suffix,
        # no separate /button_sounds/languages tree to keep in sync.
        sound_path = "/sounds/{}/{}.wav".format(lang_code, btn_id)

        content += BUTTON_TEMPLATE.format(
            btn_id=btn_id,
            label=label,
            native_word=native_word,
            image=image,
            sound_path=sound_path,
            position=pos,
        )

    filename = "lang_{}.menu".format(lang_code)
    filepath = os.path.join(out_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("  Generated: {}".format(filename))


def main():
    parser = argparse.ArgumentParser(description="Generate language menu files")
    parser.add_argument("--out", default="out/menus",
                        help="Output directory (default: out/menus)")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    print("Generating language menus...")

    for lang_code, _, en_name, native_name, words in LANGUAGES:
        generate_menu(lang_code, en_name, native_name, words, args.out)

    print("\n=== Generated {} menu files ===".format(len(LANGUAGES)))


if __name__ == "__main__":
    main()
