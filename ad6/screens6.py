"""Ad 6 ("Storytime"): the screens on Dre's phone in the 3D shots, rendered by the iOS kit at 1206 x 2622.

python ad6/screens6.py -> blender/textures/ad6/
  lock    the lock screen at 2:07 AM with two texts from the sneaker brand (after his STOP)
  thread  the conversation (dark mode): the promo, STOP, the opt-out confirmation, three texts after it
  web     spamclaims.com/lp/money in Safari (ad6/shoot_lp6.cjs capture with a status bar and the address field)
The brand (Kixrush), the number (555-0193) and every message are invented.
"""
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:\Users\moise\Projects\ios-ui-kit"
OUT = os.path.join(HERE, "..", "blender", "textures", "ad6")
TMP = os.path.join(HERE, "out", "_states")
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)
NUM = "+1 (844) 555-0193"
B = "Kixrush"
THREAD = [
    {"type": "header", "label": "Text Message \u2022 SMS", "time": "Wed, Sep 3 at 6:12\u202fPM"},
    {"type": "in", "text": f"{B}: Your size is BACK. 30% off restocks tonight only. Reply STOP to opt out"},
    {"type": "out", "text": "STOP"},
    {"type": "in", "text": f"{B}: You have been unsubscribed. No more messages will be sent."},
    {"type": "time", "day": "Sun, Sep 21", "time": "7:40\u202fPM"},
    {"type": "in", "text": f"{B}: New drop alert! Members get early access tonight"},
    {"type": "time", "day": "Thu, Oct 2", "time": "1:15\u202fPM"},
    {"type": "in", "text": f"{B}: Still thinking about it? Your cart expires in 2 hrs"},
    {"type": "time", "day": "Today", "time": "2:06\u202fAM"},
    {"type": "in", "text": f"{B}: LAST CALL. 40% off ends at 3 AM"},
]


def render(state, name):
    sp = os.path.join(TMP, name + ".json")
    json.dump(state, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    png, lay = os.path.join(OUT, name + ".png"), os.path.join(OUT, name + ".layout.json")
    subprocess.run(["node", os.path.join(KIT, "render.mjs"), sp, png, "--layout", lay], check=True, cwd=KIT, capture_output=True)
    return png


def main():
    render({"screen": "lock", "mode": "dark", "date": "Saturday, October 11", "time": "2:07",
            "notifications": [{"title": NUM, "body": f"{B}: Members only: 40% off starts NOW", "age": "1h ago"},
                              {"title": NUM, "body": f"{B}: LAST CALL. 40% off ends at 3 AM", "age": "now"}]}, "lock")
    render({"statusTime": "2:07", "battery": 0.22, "signalBars": 3, "compose": True, "scroll": "bottom", "screen": "messages",
            "mode": "dark", "header": {"name": NUM}, "items": THREAD}, "thread")
    lp = Image.open(os.path.join(HERE, "assets", "lp_money.png")).convert("RGB")
    W, H = lp.size
    web = Image.new("RGB", (W, H), (20, 12, 39))
    web.paste(lp.crop((0, 0, W, H - 150)), (0, 150))          # the page starts below the status bar, as in Safari
    dw = ImageDraw.Draw(web, "RGBA")
    ft = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 52)
    dw.text((96, 46), "2:09", font=ft, fill=(255, 255, 255, 255))
    for k in range(4):
        bh_ = 14 + 9 * k
        dw.rounded_rectangle([W - 330 + k * 22, 92 - bh_, W - 316 + k * 22, 92], radius=3, fill=(255, 255, 255, 255 if k < 3 else 110))
    dw.rounded_rectangle([W - 200, 56, W - 110, 96], radius=12, outline=(255, 255, 255, 200), width=4)
    dw.rectangle([W - 194, 62, W - 176, 90], fill=(255, 255, 255, 255))
    dw.rounded_rectangle([60, H - 250, W - 60, H - 100], radius=75, fill=(42, 34, 66, 235))
    fu = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 50)
    u = "spamclaims.com"
    dw.text(((W - fu.getlength(u)) / 2, H - 208), u, font=fu, fill=(255, 255, 255, 255))
    web.save(os.path.join(OUT, "web.png"))
    print("screens ->", OUT)


if __name__ == "__main__":
    main()
