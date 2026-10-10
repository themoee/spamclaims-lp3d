"""Ad 5 ("2:13 AM"): the phone screens, rendered by the iOS kit (C:\\Users\\moise\\Projects\\ios-ui-kit) at 1206 x 2622.

python ad5/screens5.py -> blender/textures/ad5/
  lock1..lock3   the lock screen at 2:13 AM, waking up with one, two, three texts from the same sender
  thread         the conversation (dark mode): the promo, STOP, the opt-out confirmation, then three texts after it
  evidence       the same thread with the STOP outlined and the texts after it numbered, with days since the STOP
  web            spamclaims.com in Safari (the landing page capture from ad 3, with a status bar and address bar)
The brand (Lumalane) and the number (555-0147) are invented.
"""
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:\Users\moise\Projects\ios-ui-kit"
OUT = os.path.join(HERE, "..", "blender", "textures", "ad5")
TMP = os.path.join(HERE, "out", "_states")
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)
NUM = "+1 (877) 555-0147"
B = "Lumalane"
DATE = "Wednesday, October 8"
LOCK_TEXTS = [
    (f"{B}: We saved your faves. Come back for 20% off", "2h ago"),
    (f"{B}: Flash sale extended! 30% off until 3 AM", "1m ago"),
    (f"{B}: Last chance! Free shipping ends tonight", "now"),
]
THREAD = [
    {"type": "header", "label": "Text Message \u2022 SMS", "time": "Sat, Aug 2 at 6:40\u202fPM"},
    {"type": "in", "text": f"{B}: Your cart misses you! 25% off ends tonight. Reply STOP to opt out"},
    {"type": "out", "text": "STOP"},
    {"type": "in", "text": f"{B}: You've been unsubscribed. No more messages will be sent."},
    {"type": "time", "day": "Fri, Aug 22", "time": "7:15\u202fPM"},
    {"type": "in", "text": f"{B}: Flash sale! 30% off everything this weekend"},
    {"type": "time", "day": "Thu, Sep 11", "time": "12:02\u202fPM"},
    {"type": "in", "text": f"{B}: We saved your faves. Come back for 20% off"},
    {"type": "time", "day": "Today", "time": "2:13\u202fAM"},
    {"type": "in", "text": f"{B}: Last chance! Free shipping ends tonight"},
]
DAYS = ["+20 days", "+40 days", "+67 days"]


def render(state, name):
    sp = os.path.join(TMP, name + ".json")
    json.dump(state, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    png, lay = os.path.join(OUT, name + ".png"), os.path.join(OUT, name + ".layout.json")
    subprocess.run(["node", os.path.join(KIT, "render.mjs"), sp, png, "--layout", lay], check=True, cwd=KIT, capture_output=True)
    return png, json.load(open(lay, encoding="utf-8"))


def lock(n):
    notes = [{"title": NUM, "body": b, "age": a} for b, a in LOCK_TEXTS[3 - n:]]
    return {"screen": "lock", "mode": "dark", "date": DATE, "time": "2:13", "notifications": notes}


for k in (1, 2, 3):
    render(lock(k), f"lock{k}")
png, lay = render({"statusTime": "2:13", "battery": 0.34, "signalBars": 3, "compose": True, "scroll": "bottom", "screen": "messages",
                   "mode": "dark", "header": {"name": NUM}, "items": THREAD}, "thread")

# the evidence versions: the texts after the STOP numbered one by one (ev1..ev3), then the STOP outlined with the
# days since it (evidence)
S = 3.0                                          # px per pt (the kit renders at 3x)
base = Image.open(png).convert("RGB")


def evidence(n_badges, outline, days, name):
    im = base.copy()
    d = ImageDraw.Draw(im)
    if outline:
        x, y, w, h = (stop[k] * S for k in ("x", "y", "w", "h"))
        d.rounded_rectangle([x - 14, y - 14, x + w + 14, y + h + 14], radius=int((h + 28) / 2), outline=(255, 122, 26), width=9)
    for k, b in enumerate(after[:n_badges]):
        bx, by, bw, bh = (b[q] * S for q in ("x", "y", "w", "h"))
        cx, cy, r = bx + bw + 58, by + bh / 2, 40
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 122, 26))
        t = str(k + 1)
        d.text((cx - font_b.getlength(t) / 2, cy - 31), t, font=font_b, fill=(255, 255, 255))
        if days:
            d.text((cx - font_s.getlength(DAYS[k]) / 2, cy + r + 6), DAYS[k], font=font_s, fill=(255, 150, 70))
    im.save(os.path.join(OUT, name + ".png"))


im = base.copy()
d = ImageDraw.Draw(im)
font_b = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 46)
font_s = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 34)
bubbles = [b for b in lay["boxes"] if b["cls"].startswith("ios-b ")]
stop = next(b for b in bubbles if b["text"].strip() == "STOP")
x, y, w, h = (stop[k] * S for k in ("x", "y", "w", "h"))
d.rounded_rectangle([x - 14, y - 14, x + w + 14, y + h + 14], radius=int((h + 28) / 2), outline=(255, 122, 26), width=9)
after = [b for b in bubbles if b["y"] > stop["y"] and "unsubscribed" not in b["text"]]
for k, b in enumerate(after[:3]):
    bx, by, bw, bh = (b[q] * S for q in ("x", "y", "w", "h"))
    cx, cy, r = bx + bw + 58, by + bh / 2, 40
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 122, 26))
    t = str(k + 1)
    d.text((cx - font_b.getlength(t) / 2, cy - 31), t, font=font_b, fill=(255, 255, 255))
    d.text((cx - font_s.getlength(DAYS[k]) / 2, cy + r + 6), DAYS[k], font=font_s, fill=(255, 150, 70))
im.save(os.path.join(OUT, "evidence.png"))
for n in (1, 2, 3):
    evidence(n, False, False, f"ev{n}")

# spamclaims.com in Safari: the landing page capture, a status bar on top, the address field at the bottom
web = Image.open(os.path.join(HERE, "..", "ad3", "assets", "lp_stop.png")).convert("RGB")
W, H = web.size
dw = ImageDraw.Draw(web, "RGBA")
dw.rectangle([0, 0, W, 162], fill=(20, 12, 39, 255))
ft = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 52)
dw.text((96, 52), "2:14", font=ft, fill=(255, 255, 255, 255))
for k in range(4):                                  # signal bars, wifi-less, battery
    bh_ = 14 + 9 * k
    dw.rounded_rectangle([W - 330 + k * 22, 98 - bh_, W - 316 + k * 22, 98], radius=3, fill=(255, 255, 255, 255 if k < 3 else 110))
dw.rounded_rectangle([W - 200, 62, W - 110, 102], radius=12, outline=(255, 255, 255, 200), width=4)
dw.rectangle([W - 194, 68, W - 166, 96], fill=(255, 255, 255, 255))
dw.rounded_rectangle([60, H - 250, W - 60, H - 100], radius=75, fill=(42, 34, 66, 235))
fu = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 50)
u = "spamclaims.com"
dw.text(((W - fu.getlength(u)) / 2, H - 208), u, font=fu, fill=(255, 255, 255, 255))
web.save(os.path.join(OUT, "web.png"))
print("screens ->", OUT)
