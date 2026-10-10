"""Smooth the traced logo outlines (shield_outline.json) without losing the real corners.

The trace is a pixel staircase with a few kinks where anti-aliasing fooled it; extruded and bevelled, the kinks
show up as bumps on the shield's edge. This resamples each polygon evenly, finds the true corners (a sharp turn
over a long baseline: the shield's top peak, its shoulders, the speech-tail tip; the dollar's ends), and
Gaussian-smooths everything else, easing the smoothing to zero at the corners.

python smooth_outline.py            (keeps shield_outline.raw.json as the untouched trace)
"""
import json
import math
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "shield_outline.json")
RAW = os.path.join(HERE, "shield_outline.raw.json")
if not os.path.exists(RAW):
    shutil.copy(SRC, RAW)
data = json.load(open(RAW))


def resample(pts, n):
    segs = [math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    total = sum(segs)
    out, acc, i = [], 0.0, 0
    for k in range(n):
        target = total * k / n
        while acc + segs[i] < target:
            acc += segs[i]
            i += 1
        u = (target - acc) / segs[i] if segs[i] > 0 else 0.0
        a, b = pts[i], pts[(i + 1) % len(pts)]
        out.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
    return out


def turn(pts, i, base):
    n = len(pts)
    a, b, c = pts[(i - base) % n], pts[i], pts[(i + base) % n]
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    return abs(math.degrees(math.atan2(v1[0] * v2[1] - v1[1] * v2[0], v1[0] * v2[0] + v1[1] * v2[1])))


def corners(pts, base, min_turn, spacing):
    n = len(pts)
    t = [turn(pts, i, base) for i in range(n)]
    found = []
    for i in sorted(range(n), key=lambda k: -t[k]):
        if t[i] < min_turn:
            break
        if all(min(abs(i - j), n - abs(i - j)) > spacing for j in found):
            found.append(i)
    return sorted(found)


def smooth(pts, sigma, corner_idx, guard):
    n = len(pts)
    rad = int(3 * sigma)
    w = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-rad, rad + 1)]
    out = []
    for i in range(n):
        d = min((min(abs(i - c), n - abs(i - c)) for c in corner_idx), default=10 ** 9)
        keep = max(0.0, 1.0 - d / guard)               # 1 at a corner, 0 beyond `guard` samples away
        sx = sum(wk * pts[(i + k) % n][0] for wk, k in zip(w, range(-rad, rad + 1))) / sum(w)
        sy = sum(wk * pts[(i + k) % n][1] for wk, k in zip(w, range(-rad, rad + 1))) / sum(w)
        out.append((pts[i][0] * keep + sx * (1 - keep), pts[i][1] * keep + sy * (1 - keep)))
    return out


def clean(pts, n, sigma, base, min_turn, spacing, guard):
    pts = resample(pts, n)
    c = corners(pts, base, min_turn, spacing)
    for _ in range(2):
        pts = smooth(pts, sigma, c, guard)
    return pts, c


shield, sc = clean(data["points"], 720, sigma=5.0, base=14, min_turn=28, spacing=30, guard=7)
dollar = []
for poly in data["dollar"]:
    p, dc = clean(poly, 480, sigma=2.5, base=7, min_turn=40, spacing=10, guard=4)
    dollar.append([[round(x, 5), round(y, 5)] for x, y in p])
out = dict(data, points=[[round(x, 5), round(y, 5)] for x, y in shield], dollar=dollar)
json.dump(out, open(SRC, "w"))
print("shield corners", [tuple(round(v, 3) for v in shield[i]) for i in sc])
print("points", len(shield), "dollar", [len(d) for d in dollar])
