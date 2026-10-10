"""Ad 2's phone screens: the CrumbClub conversation built up one message at a time, light mode, rendered by the
iOS kit (C:\\Users\\moise\\Projects\\ios-ui-kit) to 1206x2622 textures with layouts.

The newest message must sit high on the screen (Instagram's Reels UI covers the bottom of the video), so each
state is rendered twice: once unscrolled to measure where the last bubble ends, then scrolled so it ends at TARGET.

python ad2/states.py  ->  blender/textures/ad2/S00.png ... S10.png (+ .layout.json)
"""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:\Users\moise\Projects\ios-ui-kit"
OUT = os.path.join(HERE, "..", "blender", "textures", "ad2")
TMP = os.path.join(HERE, "out", "_states")
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)
TARGET = 560.0            # pt: where the newest bubble's bottom sits (screen is 874 pt tall)

SENDER = "+1 (877) 555-0134"
ITEMS = [
    {"type": "header", "label": "Text Message \u2022 SMS", "time": "Mon, Sep 22 at 4:12\u202fPM"},
    {"type": "in", "text": "CrumbClub: Your cookies miss you! 30% off today only. Reply STOP to opt out"},
    {"type": "out", "text": "STOP"},
    {"type": "in", "text": "CrumbClub: Got it! Here's 40% off as a goodbye gift"},
    {"type": "out", "text": "STOP."},
    {"type": "in", "text": "CrumbClub: Last chance!! These cookies won't eat themselves"},
    {"type": "out", "text": "STOP!!!"},
    {"type": "in", "text": "CrumbClub: We miss you. Come back? 50% off"},
    {"type": "out", "text": "PLEASE STOP"},
    {"type": "time", "day": "Today", "time": "2:04\u202fAM"},
    {"type": "in", "text": "CrumbClub: u up? midnight cookie drop"},
    {"type": "out", "text": "i will throw my phone in a lake"},
    {"type": "in", "text": "CrumbClub: Did you mean START?"},
]
# state k shows ITEMS[:CUT[k]]
CUT = [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13]


def state(n_items, scroll):
    return {"statusTime": "9:41", "battery": 1, "signalBars": 4, "compose": True, "scroll": scroll,
            "screen": "messages", "mode": "light", "header": {"name": SENDER}, "items": ITEMS[:n_items]}


def render(st, png, layout):
    sp = os.path.join(TMP, os.path.basename(png).replace(".png", ".json"))
    json.dump(st, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    subprocess.run(["node", os.path.join(KIT, "render.mjs"), sp, png, "--layout", layout], check=True, cwd=KIT,
                   capture_output=True)
    return json.load(open(layout, encoding="utf-8"))


def last_bottom(lay):
    b = [x for x in lay["boxes"] if x["cls"].startswith("ios-b ") or x["cls"].startswith("ios-ts")]
    return max(x["y"] + x["h"] for x in b)


for k, n in enumerate(CUT):
    name = f"S{k:02d}"
    lay0 = render(state(n, 0), os.path.join(TMP, f"{name}_0.png"), os.path.join(TMP, f"{name}_0.layout.json"))
    offset = max(0.0, last_bottom(lay0) - TARGET)
    lay = render(state(n, round(offset, 2)), os.path.join(OUT, f"{name}.png"), os.path.join(OUT, f"{name}.layout.json"))
    print(f"{name}: {n} items, scrolled {offset:6.1f} pt, newest ends at {last_bottom(lay):6.1f} pt")
