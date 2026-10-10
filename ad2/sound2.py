"""Ad 2's sound: ElevenLabs sound effects for every beat and a two-part Eleven Music score
(quirky until the record scratch, triumphant after it).

python ad2/sound2.py [only=sfx|music] -> ad2/audio/sfx_<kind>.wav, music_a.wav (comedy), music_b.wav (payoff)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ad"))
_argv = sys.argv[1:]
sys.argv = [sys.argv[0]]
import voice  # noqa: E402

args = dict(a.split("=", 1) for a in _argv if "=" in a)
A = os.path.join(HERE, "audio")
SFX = {  # kind: (prompt, seconds)
    "drop": ("a quick cartoon whoosh of something falling fast from above, short", 0.6),
    "land": ("a soft rubbery cartoon bounce, a phone landing on a cushion, playful boing, short", 0.5),
    "incoming": ("a single phone vibration buzz on a table, short double buzz", 0.5),
    "ping": ("a soft modern text message received pop, bubbly, short", 0.4),
    "sent": ("a short airy whoosh of a text message being sent", 0.4),
    "scratch": ("a classic vinyl record scratch, comedic, abrupt stop", 0.8),
    "spin": ("a fast whooshing spin, something twirling through the air, short", 0.7),
    "shutter": ("a crisp phone camera shutter click", 0.4),
    "chaching": ("a satisfying cash register cha-ching with coins, bright and cheerful", 1.2),
    "coin": ("a single bright coin clink, short sparkle", 0.4),
    "whoosh_out": ("a quick downward whoosh, something dropping out of frame", 0.5),
    "jingle": ("a short bright playful logo jingle: three quick sparkling bell chimes rising in pitch, cheerful, clean", 1.3),
    "crickets": ("crickets chirping at night, a few quiet chirps, awkward silence, comedic", 1.4),
}


def sfx():
    for kind, (prompt, sec) in SFX.items():
        if args.get("kinds") and kind not in args["kinds"].split(","):
            continue
        raw = voice.call("/v1/sound-generation?output_format=mp3_44100_128",
                         {"text": prompt, "duration_seconds": max(0.5, sec), "prompt_influence": 0.6}, accept="audio/mpeg")
        x = voice.trim(voice.mp3_to_np(raw), 0.003)
        voice.write_wav(os.path.join(A, f"sfx_{kind}.wav"), x)
        print(f"sfx {kind:10} {len(x) / voice.SR:.2f}s")


def music():
    parts = {
        "music_a": ("playful quirky comedic underscore for a funny social video: plucky pizzicato strings over a "
                    "steady bouncy bass line and a constant light shuffle beat, cheeky and cartoonish, 112 bpm. "
                    "One continuous loop-like groove with no breaks, no stops, no pauses, no build-ups, no ending, "
                    "no vocals", 17000),
        "music_b": ("triumphant feel-good payoff groove: upbeat funky pop, punchy drums, bright brass stabs and "
                    "claps, confident and celebratory, full energy from the very first beat. One continuous steady "
                    "groove for the whole length with no breaks, no breakdown, no ending, no fade, no vocals", 10000),
    }
    for name, (prompt, ms) in parts.items():
        raw = voice.call("/v1/music?output_format=mp3_44100_128", {"prompt": prompt, "music_length_ms": ms},
                         accept="audio/mpeg")
        x = voice.mp3_to_np(raw)
        voice.write_wav(os.path.join(A, f"{name}.wav"), x)
        per = " ".join(f"{float((x[i * voice.SR:(i + 1) * voice.SR] ** 2).mean() ** 0.5):.2f}" for i in range(int(len(x) / voice.SR)))
        print(f"{name}: {len(x) / voice.SR:.2f}s, rms per second: {per}")


if args.get("only") in (None, "sfx"):
    sfx()
if args.get("only") in (None, "music"):
    music()
