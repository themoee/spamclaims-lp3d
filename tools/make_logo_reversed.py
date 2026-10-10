"""Reversed SpamClaims logo for dark backgrounds: the navy parts of the wordmark turn white, the orange stays,
and the navy shield keeps its color inside a thin white keyline so it reads on near-black.

python tools/make_logo_reversed.py  ->  public/logo-reversed.png (+ public/logo-reversed@1x.png, 2x header size)
"""
import os

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "public", "logo.png")
OUT = os.path.join(HERE, "..", "public", "logo-reversed.png")

src = Image.open(SRC).convert("RGBA")
PAD = 8                                          # room for the keyline where the shield touches the image edge
im = Image.new("RGBA", (src.width + 2 * PAD, src.height + 2 * PAD), (0, 0, 0, 0))
im.paste(src, (PAD, PAD))
a = np.asarray(im).astype(np.float32)
rgb, alpha = a[..., :3], a[..., 3]
r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

# orange-ness: red well above blue; navy-ness: blue at or above red. Smooth 0..1 so anti-aliased edges stay soft.
orange = np.clip((r - b - 40.0) / 60.0, 0.0, 1.0)
h, w = alpha.shape
xs = np.arange(w)[None, :].repeat(h, axis=0)
SHIELD_X = 400 + PAD                             # the shield and its speech tail live left of x=400 px
in_shield = xs < SHIELD_X

out = rgb.copy()
white = np.array([255.0, 255.0, 255.0])
# wordmark: navy -> white, orange kept (blend by orange-ness at the edges)
word = ~in_shield
for c in range(3):
    out[..., c] = np.where(word, white[c] * (1 - orange) + rgb[..., c] * orange, out[..., c])

res = np.dstack([out, alpha]).clip(0, 255).astype(np.uint8)
logo = Image.fromarray(res, "RGBA")

# keyline around the shield: dilate its alpha a few px, paint white, put the logo on top
shield_alpha = Image.fromarray(np.where(in_shield, alpha, 0).astype(np.uint8), "L")
grow = shield_alpha.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(0.8))
key = Image.new("RGBA", logo.size, (255, 255, 255, 0))
key.putalpha(grow)
final = Image.alpha_composite(key, logo)
final.save(OUT, optimize=True)

# a 2x-header-sized copy (header shows it ~40 px tall)
small = final.resize((int(final.width * 96 / final.height), 96), Image.LANCZOS)
small.save(OUT.replace(".png", "@96.png"), optimize=True)
print("wrote", OUT, final.size, "and", small.size)
