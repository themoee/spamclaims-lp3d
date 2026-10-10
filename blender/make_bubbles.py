"""Textures + outlines for the floating 3D spam bubbles (system Python + Pillow).
Writes textures/bubble_<i>.png (transparent outside the bubble) and bubbles.json (size in meters + outline)
so Blender builds meshes with exactly the drawn shape."""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "textures")
PX_PER_M = 9000          # texture resolution: 9 px per mm
FONT = "C:/Windows/Fonts/segoeui.ttf"
FONT_PT_M = 0.0026       # glyph size in meters (the 3D bubbles are ~2-3x a real one so they read from far)
PAD_H, PAD_V = 0.0021, 0.0015
LINE_M = 0.0034
MAXW_M = 0.034

PHRASES = [
    ("in", "FINAL NOTICE: Your vehicle warranty expires today. Call now."),
    ("in", "You're pre-approved for up to $15,000. Reply YES to claim."),
    ("in", "Congrats! You've been selected for a $1,000 gift card."),
    ("in", "Your package is on hold. Confirm your address: pkg-dlv.co/r7"),
    ("in", "Rates just dropped! Lock in $49.99/mo before Friday."),
    ("in", "Hi! It's Amanda with HomeFast. Still thinking about selling?"),
    ("in", "Last chance: your offer expires tonight at midnight."),
    ("in", "Your account is on hold. Verify now to avoid fees."),
    ("in", "Exclusive: 0% APR for 18 months. Apply in 60 seconds."),
    ("in", "We found a full auto policy at $59.75/mo for you."),
    ("in", "Reply STOP to opt out"),
    ("in", "FLASH SALE 40% off today only"),
    ("out", "STOP"),
    ("out", "Stop texting me"),
]


def bubble_outline(w, h, side, r=None, n=14):
    """iOS-style bubble: rounded rect (radius r, full pill for one line) with a tail at the bottom outer corner.
    Points CCW in meters, origin at the bubble center, y up. side 'in' = tail bottom-left, 'out' = bottom-right."""
    r = min(r if r else 0.0034, h / 2)
    hw, hh = w / 2, h / 2
    pts = []
    def arc(cx, cy, a0, a1):
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    # start bottom-right, go CCW: right side up, top, left side down, bottom
    arc(hw - r, hh - r, 0.0, math.pi / 2)                    # top-right
    arc(-hw + r, hh - r, math.pi / 2, math.pi)               # top-left
    if side == "in":
        # bottom-left corner replaced by a tail that curls out to the left
        pts += [(-hw, -hh + r * 0.9), (-hw - 0.0003, -hh + 0.0002), (-hw - 0.0011, -hh - 0.0002),
                (-hw - 0.0004, -hh - 0.0001), (-hw + 0.0007, -hh + 0.0001), (-hw + r * 1.1, -hh)]
    else:
        arc(-hw + r, -hh + r, math.pi, 1.5 * math.pi)        # bottom-left
    if side == "out":
        pts += [(hw - r * 1.1, -hh), (hw - 0.0007, -hh + 0.0001), (hw + 0.0004, -hh - 0.0001),
                (hw + 0.0011, -hh - 0.0002), (hw + 0.0003, -hh + 0.0002), (hw, -hh + r * 0.9)]
    else:
        arc(hw - r, -hh + r, 1.5 * math.pi, 2 * math.pi)     # bottom-right
    return pts


def wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def main():
    os.makedirs(OUT, exist_ok=True)
    font = ImageFont.truetype(FONT, int(FONT_PT_M * PX_PER_M))
    meta = []
    scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    for i, (side, text) in enumerate(PHRASES):
        lines = wrap(scratch, text, font, (MAXW_M - 2 * PAD_H) * PX_PER_M)
        tw = max(scratch.textlength(l, font=font) for l in lines) / PX_PER_M
        w = tw + 2 * PAD_H
        h = len(lines) * LINE_M + 2 * PAD_V
        outline = bubble_outline(w, h, side)
        xs = [p[0] for p in outline]; ys = [p[1] for p in outline]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        pw, ph = int(math.ceil((x1 - x0) * PX_PER_M)) + 4, int(math.ceil((y1 - y0) * PX_PER_M)) + 4
        img = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        to_px = lambda p: ((p[0] - x0) * PX_PER_M + 2, (y1 - p[1]) * PX_PER_M + 2)
        fill = (38, 38, 40, 255) if side == "in" else (48, 209, 88, 255)
        d.polygon([to_px(p) for p in outline], fill=fill)
        tx, ty = to_px((-w / 2 + PAD_H, h / 2 - PAD_V))
        for k, line in enumerate(lines):
            d.text((tx, ty + k * LINE_M * PX_PER_M + LINE_M * PX_PER_M * 0.08), line, font=font, fill=(255, 255, 255, 255))
        path = os.path.join(OUT, f"bubble_{i}.png")
        img.save(path)
        meta.append(dict(i=i, side=side, text=text, w=w, h=h, bbox=[x0, x1, y0, y1], outline=outline, png=os.path.basename(path)))
    json.dump(meta, open(os.path.join(HERE, "bubbles.json"), "w"), indent=0)
    print("bubbles", len(meta))


if __name__ == "__main__":
    main()
