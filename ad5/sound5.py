"""Ad 5's sound: a quiet bedroom at night (room tone), the phone rattling on walnut with each text, a soft text tone,
reused UI sounds (pop, tick, shutter, the SpamClaims chime), and an intimate felt-piano score (Eleven Music plan).

python ad5/sound5.py [only=sfx|music] [kinds=buzz,room] -> ad5/audio/sfx_<kind>.wav, ad5/audio/music.wav
"""
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ad"))
_argv = sys.argv[1:]
sys.argv = [sys.argv[0]]
import voice  # noqa: E402

args = dict(a.split("=", 1) for a in _argv if "=" in a)
A = os.path.join(HERE, "audio")
os.makedirs(A, exist_ok=True)
REUSE = {"pop": ("ad3", "sfx_pop.wav"), "tick": ("ad3", "sfx_tick.wav"), "shutter": ("ad2", "sfx_shutter.wav"),
         "chime": ("ad2", "sfx_jingle.wav"), "swipe": ("ad3", "sfx_swipe.wav")}
SFX = {
    "room": ("a quiet bedroom at night, very soft air conditioner hum, faint distant city traffic, calm room tone", 10.0),
    "buzz": ("a smartphone vibrating on a wooden nightstand, a short double buzz with a light wooden rattle", 0.9),
    "tone": ("a soft gentle modern text message notification tone, two warm notes, quiet", 0.7),
}
PLAN = {
    "positive_global_styles": ["minimal cinematic", "felt piano", "intimate", "late night", "warm", "emotional", "soft"],
    "negative_global_styles": ["vocals", "lyrics", "drums at the start", "aggressive", "loud", "silence", "ending fade"],
    "sections": [
        {"section_name": "Night", "positive_local_styles": ["sparse felt piano notes", "soft warm pad", "quiet", "suspended"],
         "negative_local_styles": ["drums", "fast"], "duration_ms": 9000, "lines": []},
        {"section_name": "Build", "positive_local_styles": ["a gentle pulse enters", "warm strings", "hopeful", "rising"],
         "negative_local_styles": ["loud drums"], "duration_ms": 8000, "lines": []},
        {"section_name": "Resolve", "positive_local_styles": ["fuller", "hopeful resolution", "warm piano chords", "confident"],
         "negative_local_styles": ["silence", "abrupt ending"], "duration_ms": 8000, "lines": []},
    ],
}


def sfx():
    for kind, (ad, name) in REUSE.items():
        shutil.copyfile(os.path.join(HERE, "..", ad, "audio", name), os.path.join(A, f"sfx_{kind}.wav"))
    for kind, (prompt, sec) in SFX.items():
        if args.get("kinds") and kind not in args["kinds"].split(","):
            continue
        raw = voice.call("/v1/sound-generation?output_format=mp3_44100_128",
                         {"text": prompt, "duration_seconds": max(0.5, sec), "prompt_influence": 0.6}, accept="audio/mpeg")
        x = voice.mp3_to_np(raw)
        if kind != "room":
            x = voice.trim(x, 0.003)
        voice.write_wav(os.path.join(A, f"sfx_{kind}.wav"), x)
        print(f"sfx {kind:6} {len(x) / voice.SR:.2f}s")


def music():
    raw = voice.call("/v1/music?output_format=mp3_44100_128", {"composition_plan": PLAN}, accept="audio/mpeg")
    x = voice.mp3_to_np(raw)
    voice.write_wav(os.path.join(A, "music.wav"), x)
    q = int(0.5 * voice.SR)
    r = [float(np.sqrt(np.mean(x[i * q:(i + 1) * q] ** 2))) for i in range(len(x) // q)]
    print(f"music: {len(x) / voice.SR:.2f}s  rms/0.5s: " + " ".join(f"{v:.2f}" for v in r))


if args.get("only") in (None, "sfx"):
    sfx()
if args.get("only") in (None, "music"):
    music()
