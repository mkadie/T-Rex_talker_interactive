"""Generate the AAC Trainer prompt MP3s from a list of (filename, text) pairs.

Run this on your PC (NOT on the device) to produce all the MP3 files the
AAC Trainer expects to find under /sounds/trainer/. Copy the resulting
folder to the SD card or flash the files into the T-Rex Talker's
/sounds/trainer/ directory.

Two TTS backends are supported (auto-selected, first wins):

1. `gtts` (Google TTS, online, free, very natural):
       pip install gTTS
       python make_trainer_sounds.py --backend gtts

2. `pyttsx3` (offline, uses host OS voices — SAPI5 on Windows,
   NSSpeech on macOS, espeak on Linux):
       pip install pyttsx3
       python make_trainer_sounds.py --backend pyttsx3

3. `piper` (recommended for a fully-offline, open-source pipeline):
       Install piper-tts per https://github.com/rhasspy/piper and put
       `piper` on your PATH, then:
       python make_trainer_sounds.py --backend piper \\
           --piper-voice en_US-amy-medium.onnx

The script writes WAV first (universal), then transcodes to MP3 with
ffmpeg. Make sure ffmpeg is on your PATH for the MP3 step.

Output layout (matches aac_trainer.cfg defaults):
    out/sounds/trainer/welcome.mp3
    out/sounds/trainer/correct.mp3
    out/sounds/trainer/try_again.mp3
    out/sounds/trainer/finished.mp3
    out/sounds/trainer/you_are_thirsty.mp3
    out/sounds/trainer/you_are_hungry.mp3
    out/sounds/trainer/you_drank_too_much_soda.mp3
    out/sounds/trainer/the_dog_made_a_mess.mp3
    out/sounds/trainer/do_you_want_ice_cream.mp3
    out/sounds/trainer/do_you_want_broccoli.mp3
    out/sounds/trainer/you_want_a_sweet_drink.mp3
    out/sounds/trainer/someone_held_the_door.mp3
    out/sounds/trainer/bad_smell_making_me_angry.mp3
    out/sounds/trainer/i_need_to_number_one.mp3
    out/sounds/trainer/want_to_go_to_the_park.mp3
    out/sounds/trainer/want_to_eat_broccoli.mp3
    out/sounds/trainer/im_thirsty_want_water.mp3
    out/sounds/trainer/want_a_crunchy_red_apple.mp3
    out/sounds/trainer/want_a_cold_glass_of_milk.mp3
    out/sounds/trainer/want_a_banana_only_a_banana.mp3
    out/sounds/trainer/a_little_hungry_just_a_cracker.mp3
"""

import argparse
import os
import subprocess
import sys


# ---- The corpus --------------------------------------------------------
#
# Prompts below are keyed for the DEFAULT rotary-encoder menus:
#     base_fruitjam.menu  ->  thankyou, stinky, more, bathroom, yes, no
#         more -> food_fruitjam.menu -> water, apple, milk, banana, cracker
#
# Five direct answers + five food items reached via "more" = 10 rounds.
# Keep this list in sync with aac_trainer.cfg.

PROMPTS = [
    # --- Framing prompts ---
    ("welcome.mp3",
     "Welcome to the AAC Trainer. Squeeze the chicken to begin."),
    ("correct.mp3",   "Yes, that's right!"),
    ("try_again.mp3", "Not quite — try again."),
    ("finished.mp3",  "Great job! You finished the round."),

    # --- 5 direct answers from base_fruitjam.menu ---
    ("someone_held_the_door.mp3",
     "Someone just held the door open for you. What do you want to say?"),
    ("bad_smell_making_me_angry.mp3",
     "There is a bad smell making me angry."),
    ("i_need_to_number_one.mp3",
     "I need to go number one."),
    ("want_to_go_to_the_park.mp3",
     "Your friend asked if you want to go to the park. You want to say?"),
    ("want_to_eat_broccoli.mp3",
     "Mom asked if you want to eat broccoli for dessert. You want to say?"),

    # --- 5 food answers, reached via the "more" button ---
    ("im_thirsty_want_water.mp3",
     "I'm thirsty and I want a glass of water."),
    ("want_a_crunchy_red_apple.mp3",
     "I want to eat a crunchy red apple."),
    ("want_a_cold_glass_of_milk.mp3",
     "I want a cold glass of milk."),
    ("want_a_banana_only_a_banana.mp3",
     "I am hungry and I want a banana, and only a banana."),
    ("a_little_hungry_just_a_cracker.mp3",
     "I am a little hungry; I just want a cracker."),
]


# ---- Backends ----------------------------------------------------------

def _say_gtts(text, wav_path):
    from gtts import gTTS  # noqa: F401  # type: ignore
    # gTTS writes MP3 directly, skipping the WAV intermediate.
    mp3_path = wav_path.replace(".wav", ".mp3")
    from gtts import gTTS as _gTTS  # type: ignore
    tts = _gTTS(text=text, lang="en")
    tts.save(mp3_path)
    return mp3_path


def _say_pyttsx3(text, wav_path):
    import pyttsx3  # type: ignore
    engine = pyttsx3.init()
    engine.save_to_file(text, wav_path)
    engine.runAndWait()
    return wav_path


def _say_piper(text, wav_path, voice):
    # piper reads text from stdin, writes WAV to stdout when --output_file is given
    cmd = ["piper", "--model", voice, "--output_file", wav_path]
    proc = subprocess.run(cmd, input=text.encode("utf-8"), check=True)
    if proc.returncode != 0:
        raise RuntimeError("piper failed for: " + text)
    return wav_path


def _wav_to_mp3(wav_path):
    mp3_path = wav_path[:-4] + ".mp3"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", wav_path,
        "-codec:a", "libmp3lame",
        "-qscale:a", "4",
        mp3_path,
    ]
    subprocess.run(cmd, check=True)
    os.remove(wav_path)
    return mp3_path


# ---- Main --------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="out/sounds/trainer",
                        help="Output directory (default: out/sounds/trainer)")
    parser.add_argument("--backend", default="auto",
                        choices=("auto", "gtts", "pyttsx3", "piper"))
    parser.add_argument("--piper-voice",
                        default="en_US-amy-medium.onnx",
                        help="Piper voice model path (piper backend only)")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    backend = args.backend
    if backend == "auto":
        try:
            import gtts  # noqa: F401  # type: ignore
            backend = "gtts"
        except ImportError:
            try:
                import pyttsx3  # noqa: F401  # type: ignore
                backend = "pyttsx3"
            except ImportError:
                backend = "piper"

    print("Using backend:", backend)

    for fname, text in PROMPTS:
        out_path = os.path.join(args.out, fname)
        wav_path = out_path[:-4] + ".wav"
        print("  ", fname, "-", text[:60])
        try:
            if backend == "gtts":
                _say_gtts(text, wav_path)
            elif backend == "pyttsx3":
                _say_pyttsx3(text, wav_path)
                _wav_to_mp3(wav_path)
            elif backend == "piper":
                _say_piper(text, wav_path, args.piper_voice)
                _wav_to_mp3(wav_path)
        except Exception as e:  # noqa: BLE001
            print("ERROR on", fname, "->", e)
            sys.exit(1)

    print("Done. Copy", args.out, "to the device at /sounds/trainer/.")


if __name__ == "__main__":
    main()
