import sys, os, glob
from PIL import Image, ImageDraw, ImageFont
src = sys.argv[1]; out = sys.argv[2]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 5
files = sorted(glob.glob(os.path.join(src, "*.png")))
ims = [Image.open(f).convert("RGB") for f in files]
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * (h + 18)), (30, 30, 30))
d = ImageDraw.Draw(sheet)
f = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 13)
for k, (im, fn) in enumerate(zip(ims, files)):
    x, y = (k % cols) * w, (k // cols) * (h + 18)
    sheet.paste(im, (x, y + 18))
    d.text((x + 4, y + 1), os.path.basename(fn), fill=(220, 220, 220), font=f)
sheet.save(out)
print(out, sheet.size)
