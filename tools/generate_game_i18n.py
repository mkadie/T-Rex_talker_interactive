#!/usr/bin/env python3
"""Generate the localized audio for T-Rex's Rubber Chicken Challenge.

For every non-English language we translate (Google Translate via
deep-translator) then speak (gTTS) two sets of clips:

  words   — the 14 spoken AAC choices the board offers
  prompts — the 18 trainer lines (14 question scenarios + welcome /
            correct / try_again / finished framing)

Output layout (mirrors what the game expects under /sounds/game on the
SD card; resolve_path() maps /sounds/... -> /sd/sounds/...):

    out/game_i18n/<code>/words/<word>.wav
    out/game_i18n/<code>/prompts/<prompt_id>.wav

English is intentionally skipped — the game plays the existing English
assets for `en`, so it still runs with no SD card.

WAV format matches the on-device language tree: 16 kHz, mono, 16-bit.
Translations are cached in out/game_i18n/translations.json so re-runs
(and resumes) don't re-hit the translate endpoint. Existing wavs are
skipped, so the build is resumable.

Usage:
    pip install gTTS deep-translator
    python tools/generate_game_i18n.py [--only es,fr] [--force]
"""

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from make_trainer_sounds import PROMPTS  # (filename.mp3, english_text)

# code, gtts_code, google_translate_code, english_name, native_name
LANGS = [
    ("th", "th",    "th",    "Thai",       "ไทย"),
    ("ja", "ja",    "ja",    "Japanese",   "日本語"),
    ("zh", "zh-cn", "zh-CN", "Mandarin",   "中文"),
    ("hi", "hi",    "hi",    "Hindi",      "हिन्दी"),
    ("es", "es",    "es",    "Spanish",    "Español"),
    ("fr", "fr",    "fr",    "French",     "Français"),
    ("ar", "ar",    "ar",    "Arabic",     "العربية"),
    ("bn", "bn",    "bn",    "Bengali",    "বাংলা"),
    ("pt", "pt",    "pt",    "Portuguese", "Português"),
    ("ru", "ru",    "ru",    "Russian",    "Русский"),
    ("cs", "cs",    "cs",    "Czech",      "Čeština"),
    ("de", "de",    "de",    "German",     "Deutsch"),
]

# The 14 spoken AAC choices (must match the base/food menu item ids).
WORDS = [
    "tired", "happy", "bathroom", "stinky", "yes", "no", "please",   # base
    "water", "juice", "apple", "milk", "banana", "cracker", "yogurt",  # food
]

# Buttons that speak a fuller phrase than their id.
WORD_SPEECH = {"please": "please and thank you"}

OUT = "out/game_i18n"
CACHE = os.path.join(OUT, "translations.json")


def load_cache():
    try:
        with open(CACHE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    os.makedirs(OUT, exist_ok=True)
    with open(CACHE, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=0)


def translate(text, gt_code, cache):
    key = gt_code + "\t" + text
    if key in cache:
        return cache[key]
    from deep_translator import GoogleTranslator
    for attempt in range(4):
        try:
            out = GoogleTranslator(source="en", target=gt_code).translate(text)
            if out:
                cache[key] = out
                return out
        except Exception as e:
            print("    translate retry (%s): %s" % (attempt, e))
            time.sleep(1.5 * (attempt + 1))
    print("    TRANSLATE FAILED, using English:", text)
    return text


def tts_wav(text, gtts_code, wav_path):
    from gtts import gTTS
    os.makedirs(os.path.dirname(wav_path), exist_ok=True)
    mp3 = wav_path[:-4] + ".mp3.tmp"
    for attempt in range(4):
        try:
            gTTS(text=text, lang=gtts_code, slow=True).save(mp3)
            break
        except Exception as e:
            print("    tts retry (%s): %s" % (attempt, e))
            time.sleep(1.5 * (attempt + 1))
    else:
        return False
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", mp3,
         "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", wav_path],
        capture_output=True)
    try:
        os.remove(mp3)
    except OSError:
        pass
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma list of codes to build")
    ap.add_argument("--force", action="store_true", help="rebuild existing wavs")
    args = ap.parse_args()
    only = set(c.strip() for c in args.only.split(",") if c.strip())

    cache = load_cache()
    made = skipped = failed = 0
    prompts = [(fn[:-4], txt) for fn, txt in PROMPTS]  # (id, english)

    for code, gtts_code, gt_code, en_name, native in LANGS:
        if only and code not in only:
            continue
        print("\n=== %s (%s) ===" % (en_name, native))

        # Words
        for w in WORDS:
            wav = "%s/%s/words/%s.wav" % (OUT, code, w)
            if os.path.exists(wav) and not args.force:
                skipped += 1
                continue
            native_word = translate(WORD_SPEECH.get(w, w), gt_code, cache)
            if tts_wav(native_word, gtts_code, wav):
                print("  word %-9s -> %s" % (w, native_word))
                made += 1
            else:
                print("  WORD FAIL:", w); failed += 1
            save_cache(cache)

        # Prompts + framing
        for pid, text in prompts:
            wav = "%s/%s/prompts/%s.wav" % (OUT, code, pid)
            if os.path.exists(wav) and not args.force:
                skipped += 1
                continue
            native_text = translate(text, gt_code, cache)
            if tts_wav(native_text, gtts_code, wav):
                print("  prompt %-28s ok" % pid)
                made += 1
            else:
                print("  PROMPT FAIL:", pid); failed += 1
            save_cache(cache)

    save_cache(cache)
    print("\n=== made %d, skipped %d, failed %d ===" % (made, skipped, failed))


if __name__ == "__main__":
    main()
