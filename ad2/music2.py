"""Ad 2's payoff score, take 2: a composition plan keeps the groove continuous (the plain prompt gave stabs and gaps).

python ad2/music2.py [takes=2] -> ad2/audio/music_b<k>.wav, with a continuity report (the share of quiet 50 ms windows)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ad"))
_argv = sys.argv[1:]
sys.argv = [sys.argv[0]]
import voice  # noqa: E402

args = dict(a.split("=", 1) for a in _argv if "=" in a)
A = os.path.join(HERE, "audio")
GROOVE = ["upbeat funk pop", "punchy drums", "four-on-the-floor kick", "driving bass line", "bright brass", "claps",
          "celebratory", "confident", "118 bpm"]
NOT = ["vocals", "singing", "breakdown", "silence", "pauses", "stops", "fade out", "slow intro", "ambient", "ending"]
PLAN = {
    "positive_global_styles": GROOVE,
    "negative_global_styles": NOT,
    "sections": [
        {"section_name": "Hit and groove", "positive_local_styles": ["starts on a big full-band hit", "full energy",
                                                                     "steady groove"],
         "negative_local_styles": ["build-up", "intro", "quiet"], "duration_ms": 6000, "lines": []},
        {"section_name": "Groove", "positive_local_styles": ["same steady groove", "full energy", "brass riffs"],
         "negative_local_styles": ["breakdown", "ending", "quiet"], "duration_ms": 6000, "lines": []},
    ],
}


def report(x):
    q = int(0.05 * voice.SR)
    r = np.array([np.sqrt(np.mean(x[i * q:(i + 1) * q] ** 2)) for i in range(len(x) // q)])
    live = r > 0.25 * np.median(r[r > 0.01]) if (r > 0.01).any() else r > 1
    last = (np.where(r > 0.02)[0][-1] + 1) * 0.05 if (r > 0.02).any() else 0
    return f"{len(x) / voice.SR:.2f}s, content to {last:.2f}s, quiet windows {100 * (1 - live[:int(last / 0.05)].mean()):.0f}%"


for k in range(int(args.get("takes", "2"))):
    raw = voice.call("/v1/music?output_format=mp3_44100_128", {"composition_plan": PLAN}, accept="audio/mpeg")
    x = voice.mp3_to_np(raw)
    voice.write_wav(os.path.join(A, f"music_b{k + 2}.wav"), x)
    print(f"music_b{k + 2}: {report(x)}")
