"""The share card (public/og.jpg, 1200x630): a frame of the story, the reversed logo and the headline.

python tools/make_og.py [frame=blender/frames/desktop/0042.png]
"""
import io
import os
import sys

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
FRAME = os.path.join(ROOT, args.get("frame", "blender/frames/desktop/0042.png"))
OUT = os.path.join(ROOT, "public", "og.jpg")
W, H = 1200, 630


def inter(size, weight):
    """Inter (variable, from the woff2 the page ships) at a given weight, via an in-memory TTF."""
    tt = TTFont(os.path.join(ROOT, "public", "fonts", "inter-latin-opsz-normal.woff2"))
    tt.flavor = None
    buf = io.BytesIO()
    tt.save(buf)
    buf.seek(0)
    f = ImageFont.truetype(buf, size)
    axes = f.get_variation_axes()
    vals = []
    for a in axes:
        name = a.get("name", b"")
        name = name.decode() if isinstance(name, bytes) else str(name)
        if "eight" in name:
            vals.append(weight)
        elif "ptical" in name or "opsz" in name.lower():
            vals.append(min(max(size * 0.75, a["minimum"]), a["maximum"]))
        else:
            vals.append(a.get("default", a["minimum"]))
    f.set_variation_by_axes(vals)
    return f


im = Image.open(FRAME).convert("RGB")
s = W / im.width
im = im.resize((W, round(im.height * s)), Image.LANCZOS)
top = (im.height - H) // 2
im = im.crop((0, top, W, top + H)).convert("RGBA")

shade = Image.new("RGBA", (W, H))
d = ImageDraw.Draw(shade)
for x in range(W):                                        # the page's left scrim
    a = 0.92 if x < W * 0.26 else max(0.0, 0.92 - (x - W * 0.26) / (W * 0.30) * 0.92)
    d.line([(x, 0), (x, H)], fill=(0, 4, 17, int(255 * a)))
im = Image.alpha_composite(im, shade)

logo = Image.open(os.path.join(ROOT, "public", "logo-reversed.png")).convert("RGBA")
lh = 62
logo = logo.resize((round(logo.width * lh / logo.height), lh), Image.LANCZOS)
im.alpha_composite(logo, (64, 58))

d = ImageDraw.Draw(im)
h1 = inter(76, 800)
sub = inter(30, 500)
x, y = 64, 210
d.text((x, y), "You said ", font=h1, fill=(245, 247, 251))
d.text((x + d.textlength("You said ", font=h1), y), "STOP.", font=h1, fill=(255, 157, 69))
d.text((x, y + 84), "They kept texting.", font=h1, fill=(245, 247, 251))
d.text((x, y + 196), "See if your screenshots may qualify.", font=sub, fill=(213, 219, 231))
d.text((x, y + 240), "Free to check · No sign-up", font=inter(24, 600), fill=(255, 157, 69))

im.convert("RGB").save(OUT, "JPEG", quality=88, optimize=True, progressive=True)
print("wrote", OUT, os.path.getsize(OUT) // 1024, "KB")
