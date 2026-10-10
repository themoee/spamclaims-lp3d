"""Sync each caption line to the moment its words are spoken (ElevenLabs word timings in ad/audio/vo*.json).

python ad/sync.py [variant=b]  -> adds captions[k].line_at to ad/edit*.json (ad.html reveals line j at line_at[j])
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
VAR = args.get("variant", "a")
TAG = "" if VAR == "a" else "_" + VAR
edit_path = os.path.join(HERE, f"edit{TAG}.json")
vo_path = os.path.join(HERE, "audio", f"vo{TAG}.json")
edit = json.load(open(edit_path, encoding="utf-8"))
if not os.path.exists(vo_path):
    sys.exit(f"no voice timings yet ({vo_path}); captions keep their default schedule")
words = [w for line in json.load(open(vo_path, encoding="utf-8"))["lines"] for w in line["words"]]

SPOKEN = {"17": "seventeen", "500": "five", "$500": "five", "$500*": "five"}


def norm(w):
    w = w.lower().strip()
    w = SPOKEN.get(w, w)
    return re.sub(r"[^a-z0-9']", "", w)


def first_hit(c):
    for k, lw in enumerate(c["lines"][0].split()):
        target = norm(lw)
        for vw in words:
            if target and c["in"] - 0.8 <= vw["s"] <= c["out"] + 0.2 and norm(vw["w"]) == target:
                return vw["s"] - 0.10 - 0.04 * k
    return None


# caption boundaries follow the voice: a caption starts when its first words are spoken and ends the one before
caps = edit["captions"]
for k in range(1, len(caps)):
    h = first_hit(caps[k])
    if h is not None and h < caps[k]["in"]:
        caps[k]["in"] = round(h, 3)
        caps[k - 1]["out"] = round(min(caps[k - 1]["out"], h), 3)

for c in edit["captions"]:
    times = []
    for j, line in enumerate(c["lines"]):
        hit = None
        for k, lw in enumerate(line.split()):
            target = norm(lw)
            if not target:
                continue
            for vw in words:
                if c["in"] - 0.8 <= vw["s"] <= c["out"] + 0.2 and norm(vw["w"]) == target:
                    hit = vw["s"] - 0.10 - 0.04 * k                     # land just before the word is heard
                    break
            if hit is not None:
                break
        default = c["in"] + j * 0.22
        t = hit if hit is not None else (times[-1] + 0.22 if times else default)
        if times:
            t = max(t, times[-1] + 0.12)
        times.append(round(max(c["in"] - 0.05, t), 3))
    c["line_at"] = times
json.dump(edit, open(edit_path, "w", encoding="utf-8"), indent=1)
for c in edit["captions"]:
    print(f"{c['in']:6.2f}-{c['out']:5.2f}  " + " | ".join(f"{t:5.2f} {l}" for t, l in zip(c["line_at"], c["lines"])))
