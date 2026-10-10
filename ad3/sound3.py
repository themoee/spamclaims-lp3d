"""Ad 3's sound: ElevenLabs effects for the phone (taps, key clicks, swipes, counting pops, check ticks), the ones
reused from ad 2 (send, receive, shutter, the SpamClaims chime), and an Eleven Music tutorial beat (composition plan,
so it stays one continuous groove).

python ad3/sound3.py [only=sfx|music] [kinds=key,tap]  ->  ad3/audio/sfx_<kind>.wav, ad3/audio/music.wav
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
A2 = os.path.join(HERE, "..", "ad2", "audio")
os.makedirs(A, exist_ok=True)
REUSE = {"sent": "sfx_sent.wav", "recv": "sfx_ping.wav", "shutter": "sfx_shutter.wav", "chime": "sfx_jingle.wav"}
SFX = {  # kind: (prompt, seconds)
    "key": ("a single soft smartphone keyboard key tap click, very short, clean, close mic", 0.5),
    "tap": ("a soft muted UI tap on a phone touchscreen, short subtle click", 0.5),
    "swipe": ("a quick soft swipe whoosh of a phone screen sliding sideways, short, airy, subtle", 0.5),
    "pop": ("a bright cheerful bubble pop notification sound, short, clean, positive", 0.5),
    "tick": ("a soft satisfying positive checkmark ding, short, clean UI success sound", 0.6),
    "drop": ("a quick upward swoosh then a soft pop, a photo dropping into an app, short", 0.7),
}
PLAN = {
    "positive_global_styles": ["modern lo-fi hip hop", "light trap", "friendly how-to video", "92 bpm", "warm electric piano chords",
                               "soft finger snaps", "gentle 808 bass", "clean mix", "positive", "confident", "steady groove"],
    "negative_global_styles": ["vocals", "singing", "breakdown", "silence", "pauses", "build-up", "drop", "ending", "fade out",
                               "dark", "aggressive", "dramatic"],
    "sections": [
        {"section_name": "Groove", "positive_local_styles": ["starts on the beat right away", "steady groove", "light and bouncy"],
         "negative_local_styles": ["intro", "quiet", "build-up"], "duration_ms": 15000, "lines": []},
        {"section_name": "Groove 2", "positive_local_styles": ["same steady groove", "a little fuller", "warm keys"],
         "negative_local_styles": ["breakdown", "ending", "quiet"], "duration_ms": 15000, "lines": []},
    ],
}


def sfx():
    for kind, src in REUSE.items():
        shutil.copyfile(os.path.join(A2, src), os.path.join(A, f"sfx_{kind}.wav"))
    for kind, (prompt, sec) in SFX.items():
        if args.get("kinds") and kind not in args["kinds"].split(","):
            continue
        raw = voice.call("/v1/sound-generation?output_format=mp3_44100_128",
                         {"text": prompt, "duration_seconds": max(0.5, sec), "prompt_influence": 0.65}, accept="audio/mpeg")
        x = voice.trim(voice.mp3_to_np(raw), 0.004)
        voice.write_wav(os.path.join(A, f"sfx_{kind}.wav"), x)
        print(f"sfx {kind:6} {len(x) / voice.SR:.2f}s")


def music():
    raw = voice.call("/v1/music?output_format=mp3_44100_128", {"composition_plan": PLAN}, accept="audio/mpeg")
    x = voice.mp3_to_np(raw)
    voice.write_wav(os.path.join(A, "music.wav"), x)
    q = int(0.25 * voice.SR)
    r = [float(np.sqrt(np.mean(x[i * q:(i + 1) * q] ** 2))) for i in range(len(x) // q)]
    last = (max(i for i, v in enumerate(r) if v > 0.02) + 1) * 0.25 if any(v > 0.02 for v in r) else 0
    quiet = sum(1 for v in r[:int(last / 0.25)] if v < 0.25 * np.median([v for v in r if v > 0.01])) / max(1, int(last / 0.25))
    print(f"music: {len(x) / voice.SR:.2f}s, content to {last:.2f}s, quiet quarters {100 * quiet:.0f}%")


if args.get("only") in (None, "sfx"):
    sfx()
if args.get("only") in (None, "music"):
    music()
