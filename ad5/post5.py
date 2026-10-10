"""Ad 5's camera look, applied to every rendered frame: soft bloom around the bright screen, a hair of lateral chromatic
aberration, a vignette, and fine per-frame grain (seeded, so re-runs match).

python ad5/post5.py [src=blender/frames/ad5] [dst=ad5/out/post] [workers=6]
"""
import os
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
SRC = os.path.join(HERE, "..", args.get("src", "blender/frames/ad5"))
DST = os.path.join(HERE, "..", args.get("dst", "ad5/out/post"))
os.makedirs(DST, exist_ok=True)


def lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def process(name):
    im = Image.open(os.path.join(SRC, name)).convert("RGB")
    w, h = im.size
    a = np.asarray(im).astype(np.float32) / 255.0
    L = lin(a)
    # bloom: bright parts, blurred at quarter size, added back in linear light
    small = im.resize((w // 4, h // 4), Image.BILINEAR)
    s = lin(np.asarray(small).astype(np.float32) / 255.0)
    lum = s @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    bright = s * np.clip((lum - 0.32) / 0.4, 0, 1)[..., None]
    b_img = Image.fromarray((srgb(bright) * 255).astype(np.uint8))
    b1 = b_img.filter(ImageFilter.GaussianBlur(6)).resize((w, h), Image.BILINEAR)
    b2 = b_img.filter(ImageFilter.GaussianBlur(22)).resize((w, h), Image.BILINEAR)
    bloom = lin(np.asarray(b1).astype(np.float32) / 255.0) * 0.08 + lin(np.asarray(b2).astype(np.float32) / 255.0) * 0.06
    L = L + bloom
    out = srgb(L)
    # lateral chromatic aberration: red a touch larger, blue a touch smaller, about the centre
    o_img = Image.fromarray((out * 255).astype(np.uint8))
    r, g, bch = o_img.split()
    def scale(ch, k):
        cw, chh = int(round(w * k)), int(round(h * k))
        big = ch.resize((cw, chh), Image.BICUBIC)
        x0, y0 = (cw - w) // 2, (chh - h) // 2
        if k >= 1:
            return big.crop((x0, y0, x0 + w, y0 + h))
        pad = Image.new("L", (w, h))
        pad.paste(big, (-x0, -y0))
        return pad
    o_img = Image.merge("RGB", (scale(r, 1.0011), g, scale(bch, 0.9991)))
    out = np.asarray(o_img).astype(np.float32) / 255.0
    # vignette and grain
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rr = ((xx - w / 2) / (w / 2)) ** 2 * 0.6 + ((yy - h / 2) / (h / 2)) ** 2 * 0.4
    out = out * (1 - 0.2 * np.clip(rr, 0, 1.4))[..., None]
    rng = np.random.default_rng(int(name[:4]) + 7)
    grain = rng.normal(0, 0.008, (h // 2, w // 2)).astype(np.float32)
    grain = np.asarray(Image.fromarray(((grain + 0.5) * 255).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)).astype(np.float32) / 255 - 0.5
    out = out + grain[..., None] * (0.6 + 0.4 * (1 - out))
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(os.path.join(DST, name))
    return name


if __name__ == "__main__":
    names = sorted(f for f in os.listdir(SRC) if f.endswith(".png"))
    only = args.get("only")
    if only:
        names = [n for n in names if int(n[:4]) in {int(v) for v in only.split(",")}]
    with Pool(int(args.get("workers", "6"))) as p:
        for k, _ in enumerate(p.imap_unordered(process, names)):
            pass
    print("post:", len(names), "frames ->", DST)
