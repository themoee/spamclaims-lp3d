"""Ad 4's sound: ElevenLabs effects for every beat and two Eleven Music cues (a tension build that lands on the STOP,
an uplifting rise that peaks when the shield forms), aligned to the picture in build4.py.

python ad4/sound4.py [only=sfx|music] [kinds=boom,shatter]  ->  ad4/audio/sfx_<kind>.wav, cue_a.wav, cue_b.wav
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
SFX = {  # kind: (prompt, seconds)
    "wind": ("high altitude wind over a city at night, distant traffic hum far below, airy and wide", 8.0),
    "ping": ("a single magical message notification chime, clean, with a long airy echo tail", 2.0),
    "swarm": ("a massive swarm of thousands of fluttering paper sheets rushing past at high speed, roaring whoosh", 4.0),
    "flyby": ("a deep cinematic whoosh fly-by, fast camera swoop, powerful air movement", 1.6),
    "dings": ("dozens of phone message notification dings overlapping faster and faster, chaotic, frantic", 2.5),
    "buzz": ("a smartphone vibrating repeatedly on a wooden desk, rattling buzz", 2.0),
    "sent": ("a crisp short text message sent whoosh", 0.6),
    "boom": ("a massive cinematic impact boom with a shockwave, deep sub bass, glass resonance, trailer hit", 3.0),
    "freeze": ("time freezing: a sudden reverse suck-in whoosh, then a low eerie drone with a thin high ringing tone", 2.2),
    "shatter": ("a huge glass dome shattering explosion, thousands of glass shards flying, cinematic", 2.5),
    "avalanche": ("an avalanche of paper cards and plastic tiles tumbling and pouring onto a floor, rushing", 2.2),
    "power": ("a magical shimmering power-up sweep, warm rising glow, sparkle", 1.6),
    "cityboom": ("a deep cinematic boom that rolls out across a whole city, distant thunder-like, epic", 3.0),
    "lanterns": ("magical rising shimmer, hundreds of glowing lanterns floating up into the night sky, airy chimes", 5.0),
    "triumph": ("a triumphant cinematic orchestral hit with a bright shimmering tail, epic resolution", 3.0),
}
CUES = {
    "cue_a": {"positive_global_styles": ["epic cinematic trailer", "hybrid orchestral", "dark tension", "pulsing synth bass",
                                         "ticking clock percussion", "rising strings", "braams", "big drums"],
              "negative_global_styles": ["vocals", "lyrics", "happy", "acoustic guitar", "ending fade"],
              "sections": [
                  {"section_name": "Mystery", "positive_local_styles": ["quiet", "a single low piano note", "eerie synth drone",
                                                                        "ticking"], "negative_local_styles": ["drums", "loud"],
                   "duration_ms": 3000, "lines": []},
                  {"section_name": "Build", "positive_local_styles": ["pulsing synth bass", "driving percussion", "rising tension",
                                                                      "a riser building to a massive hit"], "negative_local_styles": ["calm"],
                   "duration_ms": 5000, "lines": []},
                  {"section_name": "Hit", "positive_local_styles": ["one massive cinematic impact hit then silence"],
                   "negative_local_styles": ["melody"], "duration_ms": 3000, "lines": []},
              ]},
    "cue_b": {"positive_global_styles": ["uplifting cinematic", "hopeful", "triumphant orchestral", "warm strings", "choir",
                                         "big drums", "inspiring trailer"],
              "negative_global_styles": ["vocals", "lyrics", "dark", "sad", "silence"],
              "sections": [
                  {"section_name": "Hope", "positive_local_styles": ["warm rising strings", "gentle pulse", "hopeful"],
                   "negative_local_styles": ["drums"], "duration_ms": 4000, "lines": []},
                  {"section_name": "Rise", "positive_local_styles": ["building", "choir enters", "drums build", "rising"],
                   "negative_local_styles": ["quiet"], "duration_ms": 4000, "lines": []},
                  {"section_name": "Triumph", "positive_local_styles": ["full orchestra", "triumphant", "huge", "choir", "big drums"],
                   "negative_local_styles": ["quiet", "breakdown"], "duration_ms": 6000, "lines": []},
                  {"section_name": "Resolve", "positive_local_styles": ["sustained triumphant chord", "resolving", "shimmering"],
                   "negative_local_styles": ["drums"], "duration_ms": 4000, "lines": []},
              ]},
}


def sfx():
    shutil.copyfile(os.path.join(HERE, "..", "ad2", "audio", "sfx_jingle.wav"), os.path.join(A, "sfx_chime.wav"))
    for kind, (prompt, sec) in SFX.items():
        if args.get("kinds") and kind not in args["kinds"].split(","):
            continue
        raw = voice.call("/v1/sound-generation?output_format=mp3_44100_128",
                         {"text": prompt, "duration_seconds": max(0.5, sec), "prompt_influence": 0.55}, accept="audio/mpeg")
        x = voice.trim(voice.mp3_to_np(raw), 0.003)
        voice.write_wav(os.path.join(A, f"sfx_{kind}.wav"), x)
        print(f"sfx {kind:10} {len(x) / voice.SR:.2f}s")


def music():
    for name, plan in CUES.items():
        if args.get("kinds") and name not in args["kinds"].split(","):
            continue
        raw = voice.call("/v1/music?output_format=mp3_44100_128", {"composition_plan": plan}, accept="audio/mpeg")
        x = voice.mp3_to_np(raw)
        voice.write_wav(os.path.join(A, f"{name}.wav"), x)
        q = int(0.25 * voice.SR)
        r = [float(np.sqrt(np.mean(x[i * q:(i + 1) * q] ** 2))) for i in range(len(x) // q)]
        print(f"{name}: {len(x) / voice.SR:.2f}s  rms/0.25s: " + " ".join(f"{v:.2f}" for v in r))


if args.get("only") in (None, "sfx"):
    sfx()
if args.get("only") in (None, "music"):
    music()
