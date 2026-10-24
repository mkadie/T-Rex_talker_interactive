"""Generate the AnimePipBoy English/Japanese toggle audio with gTTS.

Writes, under <root> (a CIRCUITPY drive or a staging dir):
  button_sounds/how_much_for_that.mp3   English "How much for that?"
  button_sounds/lang_en.mp3             "English" (toggle announcement)
  button_sounds/ja/*.mp3                Japanese base + food words and
                                        the "日本語" announcement

Clips are re-encoded to match the board's existing sounds (44.1 kHz mono
64 kbps MP3). Needs gTTS, ffmpeg and network access.

Usage:
    python3 tools/make_animepipboy_sounds.py /media/$USER/CIRCUITPY
"""

import os
import subprocess
import sys
import tempfile

from gtts import gTTS

# (relative output path, gTTS lang, text)
CLIPS = [
    ("button_sounds/how_much_for_that.mp3", "en", "How much for that?"),
    ("button_sounds/lang_en.mp3", "en", "English"),
    ("button_sounds/ja/lang_ja.mp3", "ja", "日本語"),
    # Base menu
    ("button_sounds/ja/yes.mp3", "ja", "はい"),
    ("button_sounds/ja/no.mp3", "ja", "いいえ"),
    ("button_sounds/ja/please_and_thank_you.mp3", "ja",
     "お願いします。ありがとう。"),
    ("button_sounds/ja/how_much_for_that.mp3", "ja", "それはいくらですか？"),
    # Food & drink menu (single words, like the English clips)
    ("button_sounds/ja/water.mp3", "ja", "お水"),
    ("button_sounds/ja/apple.mp3", "ja", "りんご"),
    ("button_sounds/ja/milk.mp3", "ja", "牛乳"),
    ("button_sounds/ja/banana.mp3", "ja", "バナナ"),
    ("button_sounds/ja/cracker.mp3", "ja", "クラッカー"),
]


def main():
    root = sys.argv[1].rstrip("/")
    with tempfile.TemporaryDirectory() as tmp:
        for rel, lang, text in CLIPS:
            raw = os.path.join(tmp, "raw.mp3")
            gTTS(text=text, lang=lang).save(raw)
            out = os.path.join(root, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", raw,
                 "-ar", "44100", "-ac", "1", "-b:a", "64k", out],
                check=True)
            print("wrote", rel, "-", text)


if __name__ == "__main__":
    main()
