"""Generate multilingual sound files for T-Rex Talker AAC device.

Uses gTTS to generate spoken words in 13 languages.
Each file says the word in the target language.

Output: button_sounds/languages/<lang_code>/<english>_<native>.mp3

Usage:
    pip install gTTS
    python tools/generate_language_sounds.py [--out DIR]
"""

import os
import sys
import argparse

try:
    from gtts import gTTS
except ImportError:
    print("ERROR: gTTS not installed. Run: pip install gTTS")
    sys.exit(1)


# Language definitions: (code, gtts_code, english_name, native_name, words)
# Words: {english_key: native_word}
LANGUAGES = [
    ("th", "th", "Thai", "ไทย", {
        "milk": "นม", "water": "น้ำ", "snack": "ขนม",
        "play": "เล่น", "mum": "แม่", "yes": "ใช่",
        "no": "ไม่ใช่", "thankyou": "ขอบคุณ",
    }),
    ("ja", "ja", "Japanese", "日本語", {
        "milk": "牛乳", "water": "お水", "snack": "おやつ",
        "play": "遊ぶ", "mum": "ママ", "yes": "はい",
        "no": "いいえ", "thankyou": "ありがとう",
    }),
    ("en", "en", "English", "English", {
        "milk": "milk", "water": "water", "snack": "snack",
        "play": "play", "mum": "mum", "yes": "yes",
        "no": "no", "thankyou": "thank you",
    }),
    ("zh", "zh-cn", "Mandarin", "中文", {
        "milk": "牛奶", "water": "水", "snack": "零食",
        "play": "玩", "mum": "妈妈", "yes": "是",
        "no": "不是", "thankyou": "谢谢",
    }),
    ("hi", "hi", "Hindi", "हिन्दी", {
        "milk": "दूध", "water": "पानी", "snack": "नाश्ता",
        "play": "खेलो", "mum": "माँ", "yes": "हाँ",
        "no": "नहीं", "thankyou": "धन्यवाद",
    }),
    ("es", "es", "Spanish", "Español", {
        "milk": "leche", "water": "agua", "snack": "merienda",
        "play": "jugar", "mum": "mamá", "yes": "sí",
        "no": "no", "thankyou": "gracias",
    }),
    ("fr", "fr", "French", "Français", {
        "milk": "lait", "water": "eau", "snack": "goûter",
        "play": "jouer", "mum": "maman", "yes": "oui",
        "no": "non", "thankyou": "merci",
    }),
    ("ar", "ar", "Arabic", "العربية", {
        "milk": "حليب", "water": "ماء", "snack": "وجبة",
        "play": "لعب", "mum": "ماما", "yes": "نعم",
        "no": "لا", "thankyou": "شكراً",
    }),
    ("bn", "bn", "Bengali", "বাংলা", {
        "milk": "দুধ", "water": "জল", "snack": "নাস্তা",
        "play": "খেলা", "mum": "মা", "yes": "হ্যাঁ",
        "no": "না", "thankyou": "ধন্যবাদ",
    }),
    ("pt", "pt", "Portuguese", "Português", {
        "milk": "leite", "water": "água", "snack": "lanche",
        "play": "brincar", "mum": "mamãe", "yes": "sim",
        "no": "não", "thankyou": "obrigado",
    }),
    ("ru", "ru", "Russian", "Русский", {
        "milk": "молоко", "water": "вода", "snack": "перекус",
        "play": "играть", "mum": "мама", "yes": "да",
        "no": "нет", "thankyou": "спасибо",
    }),
    ("cs", "cs", "Czech", "Čeština", {
        "milk": "mléko", "water": "voda", "snack": "svačina",
        "play": "hrát", "mum": "máma", "yes": "ano",
        "no": "ne", "thankyou": "děkuji",
    }),
    ("de", "de", "German", "Deutsch", {
        "milk": "Milch", "water": "Wasser", "snack": "Snack",
        "play": "spielen", "mum": "Mama", "yes": "ja",
        "no": "nein", "thankyou": "danke",
    }),
]


def generate(out_dir):
    """Generate all language sound files."""
    total = 0
    errors = 0

    for lang_code, gtts_code, en_name, native_name, words in LANGUAGES:
        lang_dir = os.path.join(out_dir, lang_code)
        os.makedirs(lang_dir, exist_ok=True)
        print("\n--- {} ({}) ---".format(en_name, native_name))

        for english_key, native_word in words.items():
            if lang_code == "en":
                filename = "{}.mp3".format(english_key)
            else:
                filename = "{}_{}.mp3".format(english_key, native_word)

            filepath = os.path.join(lang_dir, filename)

            if os.path.exists(filepath):
                print("  SKIP (exists): {}".format(filename))
                total += 1
                continue

            try:
                tts = gTTS(text=native_word, lang=gtts_code, slow=True)
                tts.save(filepath)
                print("  OK: {}".format(filename))
                total += 1
            except Exception as e:
                print("  ERROR: {} — {}".format(filename, e))
                errors += 1

    print("\n=== Generated {} files, {} errors ===".format(total, errors))


def main():
    parser = argparse.ArgumentParser(description="Generate multilingual AAC sounds")
    parser.add_argument("--out", default="out/button_sounds/languages",
                        help="Output directory (default: out/button_sounds/languages)")
    args = parser.parse_args()
    generate(args.out)


if __name__ == "__main__":
    main()
