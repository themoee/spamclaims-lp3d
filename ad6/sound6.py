"""Ad 6's sound: a Gen Z trap score that follows the story (Eleven Music composition plan, sections timed to the edit),
new effects (the $500 sparkle and riser, punchy hits for the stamps, a wrong-answer buzzer for "SCAM?", a highlighter
swipe) and UI sounds reused from ads 2-5 (buzz, text tone, sent/received, keys, taps, ticks, pops, shutter, scratch,
boom, whoosh, the SpamClaims chime).

python ad6/sound6.py [only=sfx|music] [kinds=sparkle,riser] -> ad6/audio/sfx_<kind>.wav, ad6/audio/music_a.wav + music_b.wav
"""
import json
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
E = json.load(open(os.path.join(HERE, "edit.json"), encoding="utf-8"))
EV = E["events"]
REUSE = {"buzz": ("ad5", "sfx_buzz.wav"), "tone": ("ad5", "sfx_tone.wav"), "sent": ("ad3", "sfx_sent.wav"),
         "recv": ("ad3", "sfx_recv.wav"), "key": ("ad3", "sfx_key.wav"), "tap": ("ad3", "sfx_tap.wav"),
         "tick": ("ad3", "sfx_tick.wav"), "pop": ("ad3", "sfx_pop.wav"), "shutter": ("ad3", "sfx_shutter.wav"),
         "swipe": ("ad3", "sfx_swipe.wav"), "scratch": ("ad2", "sfx_scratch.wav"), "whoosh": ("ad2", "sfx_whoosh_out.wav"),
         "boom": ("ad4", "sfx_boom.wav"), "chime": ("ad5", "sfx_chime.wav"), "room": ("ad5", "sfx_room.wav")}
SFX = {
    "sparkle": ("a bright magical sparkle shimmer burst, glittering chimes, short and dazzling", 1.6),
    "riser": ("a fast tense cinematic riser building up, white noise sweep up, ending abruptly", 1.3),
    "hit": ("a punchy deep cinematic bass hit with a short snappy tail, modern trailer impact", 0.8),
    "buzzer": ("a short game show wrong answer buzzer, comedic, two quick low buzzes", 0.7),
    "marker": ("a highlighter marker swiping across paper, one quick squeaky stroke", 0.6),
    "gasp": ("a small group of young friends gasping in surprise together, short", 1.0),
}


def dur_ms(a, b):
    return int(round((b - a) * 1000))


V4 = next(v["at"] for v in E["voice"] if v["line"] == "V4")
V6 = next(v["at"] for v in E["voice"] if v["line"] == "V6")
GLOBAL_POS = ["modern trap", "Gen Z hype", "punchy 808 bass", "crisp hi-hats", "catchy synth pluck", "energetic",
              "social media ad", "polished mix"]
GLOBAL_NEG = ["vocals", "lyrics", "rap", "singing", "silence", "long fade in", "lo-fi hiss"]
# Two pieces, cut on the $500 slam (the riser, the boom and the flash cover the switch): A = the story up to the reveal,
# B = starts ON the drop and carries the rest. The model tends to end early, so the last section of each is padded.
PLANS = {
    "a": {"positive_global_styles": GLOBAL_POS, "negative_global_styles": GLOBAL_NEG, "sections": [
        {"section_name": "Hook", "positive_local_styles": ["instant hype", "punchy drums from the very first beat",
                                                           "playful pluck melody", "bouncy 808"],
         "negative_local_styles": ["slow intro", "silence", "fade in"], "duration_ms": int(EV["thread"] * 1000), "lines": []},
        {"section_name": "Late night", "positive_local_styles": ["late night", "moody keys", "muted drums", "sparse hi-hats",
                                                                 "lighter", "leaves room for a voice"],
         "negative_local_styles": ["loud", "busy"], "duration_ms": int((V4 - EV["thread"]) * 1000), "lines": []},
        {"section_name": "Build", "positive_local_styles": ["building tension", "snare roll building", "rising synth",
                                                            "filter opening", "anticipation", "keeps building"],
         "negative_local_styles": ["drop", "release", "ending"], "duration_ms": int((EV["money"] - V4) * 1000) + 4000, "lines": []},
    ]},
    "b": {"positive_global_styles": GLOBAL_POS, "negative_global_styles": GLOBAL_NEG + ["intro", "build up"], "sections": [
        {"section_name": "Drop", "positive_local_styles": ["huge trap drop from the very first beat", "hard 808s",
                                                           "fast hi-hat rolls", "bright synth lead", "hype", "celebratory"],
         "negative_local_styles": ["quiet start", "intro", "breakdown"], "duration_ms": int((V6 - EV["money"]) * 1000), "lines": []},
        {"section_name": "Confident", "positive_local_styles": ["confident bouncy groove", "big claps", "uplifting chords",
                                                                "a little lighter under a voice"],
         "negative_local_styles": ["silence", "breakdown"], "duration_ms": int((EV["cta"] - V6) * 1000), "lines": []},
        {"section_name": "Outro", "positive_local_styles": ["uplifting", "inspiring", "warm synth pads", "triumphant",
                                                            "resolving final chord"],
         "negative_local_styles": ["abrupt cut", "silence before the end"],
         "duration_ms": int((E["duration"] - EV["cta"]) * 1000) + 7000, "lines": []},
    ]},
}


def sfx():
    for kind, (ad, name) in REUSE.items():
        shutil.copyfile(os.path.join(HERE, "..", ad, "audio", name), os.path.join(A, f"sfx_{kind}.wav"))
    for kind, (prompt, sec) in SFX.items():
        if args.get("kinds") and kind not in args["kinds"].split(","):
            continue
        raw = voice.call("/v1/sound-generation?output_format=mp3_44100_128",
                         {"text": prompt, "duration_seconds": max(0.5, sec), "prompt_influence": 0.6}, accept="audio/mpeg")
        x = voice.trim(voice.mp3_to_np(raw), 0.003)
        voice.write_wav(os.path.join(A, f"sfx_{kind}.wav"), x)
        print(f"sfx {kind:8} {len(x) / voice.SR:.2f}s")


def music():
    for name in (args.get("parts") or "a,b").split(","):
        plan = PLANS[name]
        print(f"plan {name} sections (s):", [round(s["duration_ms"] / 1000, 2) for s in plan["sections"]])
        raw = voice.call("/v1/music?output_format=mp3_44100_128", {"composition_plan": plan}, accept="audio/mpeg")
        x = voice.mp3_to_np(raw)
        voice.write_wav(os.path.join(A, f"music_{name}.wav"), x)
        q = int(0.5 * voice.SR)
        r = [float(np.sqrt(np.mean(x[i * q:(i + 1) * q] ** 2))) for i in range(len(x) // q)]
        print(f"music {name}: {len(x) / voice.SR:.2f}s  rms/0.5s: " + " ".join(f"{v:.2f}" for v in r))


if args.get("only") in (None, "sfx"):
    sfx()
if args.get("only") in (None, "music"):
    music()
