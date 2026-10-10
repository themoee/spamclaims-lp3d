"""The Reel's music bed from Eleven Music, composed in two sections that follow the edit:
tension until the cut to the screenshot (9.4 s), then a confident lift through the money line and the end card.

python ad/music.py  ->  ad/audio/music.wav (15 s)
"""
import json
import os
import sys

sys.argv = [sys.argv[0]]                       # voice.py parses argv at import; give it none
import voice  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
edit = json.load(open(os.path.join(HERE, "edit.json"), encoding="utf-8"))
cut = 9.40
plan = {
    "positive_global_styles": ["modern electronic", "cinematic ad score", "clean mix", "punchy low end", "100 bpm"],
    "negative_global_styles": ["vocals", "lyrics", "lo-fi", "acoustic guitar", "long fade out"],
    "sections": [
        {"section_name": "Tension", "duration_ms": int(cut * 1000), "lines": [],
         "positive_local_styles": ["tense minimal synth pulse", "ticking hi-hats", "rising unease", "building"],
         "negative_local_styles": ["melody", "drop"]},
        {"section_name": "Resolve", "duration_ms": int((edit["duration"] - cut) * 1000), "lines": [],
         "positive_local_styles": ["confident uplifting resolve", "warm synth chords", "steady beat", "hopeful", "ends on a strong final hit"],
         "negative_local_styles": ["silence", "tension"]},
    ],
}
try:
    raw = voice.call("/v1/music?output_format=mp3_44100_128", {"composition_plan": plan}, accept="audio/mpeg")
except voice.ApiError as e:
    print("composition plan refused, falling back to a prompt:", str(e)[:200])
    raw = voice.call("/v1/music?output_format=mp3_44100_128", {
        "prompt": "15 second modern electronic ad bed for a vertical social video: a tense minimal synth pulse with "
                  "ticking hi-hats for the first 9 seconds, then a confident uplifting resolve with warm synth chords "
                  "and a steady beat that keeps going to the very end, finishing on a strong final hit. No vocals.",
        "music_length_ms": int(edit["duration"] * 1000)}, accept="audio/mpeg")
x = voice.mp3_to_np(raw)
voice.write_wav(os.path.join(HERE, "audio", "music.wav"), x)
print(f"music.wav {len(x) / voice.SR:.2f} s")
