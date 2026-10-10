"""Ad 4's bubble atlas (system Python + Pillow): 48 spam texts drawn as iOS light-mode bubbles, 8 x 6 tiles of
512 x 256 px, so thousands of instanced 3D bubbles can each show readable text from one material.

python blender/ad4_atlas.py -> blender/textures/ad4/atlas.png (+ atlas.json: tile grid and texts)
The brands and numbers are invented (555 numbers are reserved for fiction).
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "textures", "ad4")
os.makedirs(OUT, exist_ok=True)
COLS, ROWS, TW, TH = 8, 6, 512, 256
FONT = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 36)
FONT_B = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 36)
TEXTS = [
    "Lumalane: Flash sale! 30% off everything this weekend",
    "PizzaPal: 2 large pizzas for $15 tonight only!",
    "GlowMart: Your cart misses you. Come back for 20% off",
    "FitCore: Your membership deal ends at midnight",
    "AutoMax: Your car could be worth more than you think",
    "HomeFast: Still thinking about selling your home?",
    "QuickLend: You're pre-approved. Reply YES to claim",
    "SunWave Solar: Cut your power bill by 40%",
    "Brightlane: Last chance! Free shipping ends tonight",
    "TrendHive: New arrivals just dropped. Shop now",
    "CrumbClub: Your cookies miss you! 30% off today",
    "StyleNest: VIP sale starts NOW. Don't miss it",
    "PetPals: Treat your pup! 25% off toys and food",
    "ZipCart: Your order is waiting. Complete checkout",
    "MegaDeals: Doorbuster prices all weekend long",
    "CoolAir HVAC: Book your tune-up for just $49",
    "SnackBox: Free snacks with your next order",
    "UrbanFit: Leggings 2 for $30. Today only",
    "FreshBowl: Lunch is on us! Use code YUM",
    "SkyTel: Upgrade your phone for $0 down",
    "Reply STOP to opt out. Msg & data rates may apply",
    "DealDash: Prices drop at 9 PM. Set a reminder",
    "GreenLeaf Lawn: Spring special, first cut free",
    "CasaFurn: Sofas up to 60% off this week",
    "Glossaria: Your favorite shade is back in stock",
    "TurboWash: Unlimited car washes $19.99/mo",
    "BeanBar: Your free coffee expires tomorrow",
    "MoveIt: Moving soon? Get a free quote today",
    "RoofRight: Storm damage? Free inspection",
    "ShoeVault: Flash sale! Extra 40% off clearance",
    "HappyPaws Vet: Time for Max's checkup",
    "LuxeLeaf: We saved your faves. 15% off inside",
    "NovaBank: Open an account, get a bonus",
    "DriveSafe Ins: Lower your rate in 2 minutes",
    "FlexGym: Rejoin for $1. This week only",
    "TasteTrail: Your meal kit discount is waiting",
    "ClickShop: Items in your cart are selling out",
    "WindowPro: Replacement windows, 0% financing",
    "BrightSmile: Teeth whitening $99 this month",
    "GameZone: Pre-order now and save 20%",
    "+1 (877) 555-0147: Reminder! Sale ends tonight",
    "+1 (844) 555-0182: Your exclusive offer inside",
    "Lumalane: Summer drop is LIVE. Shop before it's gone",
    "PizzaPal: Hungry? Free delivery for 2 hours",
    "GlowMart: Restock alert! Back in limited sizes",
    "FitCore: Bring a friend, both get 50% off",
    "AutoMax: Trade-in values just went UP",
    "HomeFast: Your neighbor's home just sold!",
]
assert len(TEXTS) == COLS * ROWS


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if FONT.getlength(t) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


atlas = Image.new("RGBA", (COLS * TW, ROWS * TH), (233, 233, 235, 255))
d = ImageDraw.Draw(atlas)
tiles = []
for k, text in enumerate(TEXTS):
    cx, cy = (k % COLS) * TW, (k // COLS) * TH
    # the tile is the bubble's face: the iOS received-bubble gray, text in black (the brand name in semibold)
    lines = wrap(text, TW - 70)[:4]
    lh = 45
    y = cy + (TH - lh * len(lines)) // 2 - 4
    for j, ln in enumerate(lines):
        x = cx + 35
        if j == 0 and ":" in ln:
            head, tail = ln.split(":", 1)
            d.text((x, y), head + ":", font=FONT_B, fill=(0, 0, 0, 255))
            x += FONT_B.getlength(head + ":")
            d.text((x, y), tail, font=FONT, fill=(0, 0, 0, 255))
        else:
            d.text((x, y), ln, font=FONT, fill=(0, 0, 0, 255))
        y += lh
    tiles.append({"k": k, "text": text, "lines": len(lines)})
atlas.convert("RGB").save(os.path.join(OUT, "atlas.png"), optimize=True)
json.dump({"cols": COLS, "rows": ROWS, "tile": [TW, TH], "tiles": tiles}, open(os.path.join(OUT, "atlas.json"), "w"), indent=1)
print("atlas", atlas.size, len(tiles), "tiles")

# the STOP bubble (sent, iMessage-green SMS style) for the shockwave moment
stop = Image.new("RGB", (TW, TH), (52, 199, 89))
ds = ImageDraw.Draw(stop)
big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 132)
tw = big.getlength("STOP")
ds.text(((TW - tw) / 2, (TH - 160) / 2 - 8), "STOP", font=big, fill=(255, 255, 255))
stop.save(os.path.join(OUT, "stop.png"))
print("stop bubble", stop.size)
