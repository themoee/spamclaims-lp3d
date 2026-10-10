"""Blender PNG frames -> the web sequence: public/seq/<set>/<index>.webp + manifest.json.

python tools/frames_to_webp.py desktop [src=blender/frames/desktop] [q=74] [n=300] [width=1600]
python tools/frames_to_webp.py mobile  [src=blender/frames/mobile]  [q=72] [n=300]

The manifest lists the frame indices that exist, so a partial render (every 3rd frame, say) still plays:
the player draws the nearest frame it has and crossfades between neighbours.
"""
import glob
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SET = sys.argv[1]
args = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
SRC = os.path.join(ROOT, args.get("src", f"blender/frames/{SET}"))
Q = int(args.get("q", "74" if SET == "desktop" else "72"))
N = int(args.get("n", "300"))
WIDTH = int(args["width"]) if "width" in args else None
OUT = os.path.join(ROOT, "public", "seq", SET)
os.makedirs(OUT, exist_ok=True)

frames, total, size = [], 0, None
for p in sorted(glob.glob(os.path.join(SRC, "*.png"))):
    stem = os.path.splitext(os.path.basename(p))[0]
    if not stem.isdigit():
        continue
    i = int(stem)
    im = Image.open(p).convert("RGB")
    if WIDTH and im.width != WIDTH:
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    dst = os.path.join(OUT, f"{i:04d}.webp")
    im.save(dst, "WEBP", quality=Q, method=6)
    total += os.path.getsize(dst)
    frames.append(i)
    size = im.size

keep = {f"{i:04d}.webp" for i in frames}
for old in glob.glob(os.path.join(OUT, "*.webp")):          # drop frames from an older, denser render
    if os.path.basename(old) not in keep:
        os.remove(old)

json.dump({"n": N, "w": size[0], "h": size[1], "frames": frames, "ext": "webp"},
          open(os.path.join(OUT, "manifest.json"), "w"))
print(f"{SET}: {len(frames)} frames {size[0]}x{size[1]}, {total / 1e6:.1f} MB, avg {total / max(len(frames), 1) / 1e3:.0f} KB")
