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
    out/sounds/trainer/you_want_something_cold_and_white.mp3
    out/sounds/trainer/you_finished_your_snack.mp3
    out/sounds/trainer/someone_helped_you.mp3
"""

import argparse
import os
import subprocess
import sys


# ---- The corpus --------------------------------------------------------

# Keep this list in sync with aac_trainer.cfg.
PROMPTS = [
    # Framing prompts
    ("welcome.mp3",
     "Welcome to the AAC Trainer. Squeeze the chicken to begin."),
    ("correct.mp3",        "Yes, that's right!"),
    ("try_again.mp3",      "Not quite — try again."),
    ("finished.mp3",       "Great job! You finished the round."),

    # Question prompts (must match aac_trainer.cfg [question] entries)
    ("you_are_thirsty.mp3",
     "You have been outside and you are thirsty. What do you want?"),
    ("you_are_hungry.mp3",
     "Your tummy is rumbling. What do you want to say?"),
    ("you_drank_too_much_soda.mp3",
     "You drank too much soda. What do you need?"),
    ("the_dog_made_a_mess.mp3",
     "The dog made a mess. How do you feel about it?"),
    ("do_you_want_ice_cream.mp3",
     "Dad asked if you want ice cream for dessert. What do you say?"),
    ("do_you_want_broccoli.mp3",
     "Mom asked if you want to eat broccoli. What do you say?"),
    ("you_want_a_sweet_drink.mp3",
     "You want a sweet drink. What do you ask for?"),
    ("you_want_something_cold_and_white.mp3",
     "You want something cold and white to drink. What is it?"),
    ("you_finished_your_snack.mp3",
     "You finished your snack and want another. What do you say?"),
    ("someone_helped_you.mp3",
     "Someone helped you. What should you say back?"),
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
