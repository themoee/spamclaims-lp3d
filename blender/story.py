"""The scroll story, rendered as a frame sequence (Cycles). t in [0, 1] is scroll progress.

blender -b --factory-startup -P story.py -- set=desktop|mobile [frames=300] [start=0] [end=299] [step=1]
    [only=0,40,80] [samples=96] [res=1600x900] [out=frames/desktop] [preview=0] [force=0] [screen=1.25]

Acts (t ranges; the page's overlay copy uses the same numbers, see ACTS below and web/src/acts.json):
  0.00-0.17  hero: the lock screen, spam notifications pile in, message bubbles orbit the phone
  0.17-0.36  STOP: the phone turns to us, the conversation builds, STOP freezes every bubble mid-air
  0.36-0.50  "they texted again": "Today 9:12 AM", a new spam lands, the storm closes in
  0.50-0.72  "do your texts look like this?": strong / may qualify / weaker, a close-up of each
  0.72-0.88  how it works: the screenshot flash, the screenshot flies out and gets read
  0.88-1.00  finale: the SpamClaims shield rises

The camera is framed, not placed: each key says which subject sits where on screen (u from the left, v from
the top), at what distance and lens; desktop keeps the left ~40 % clear for copy, mobile the top ~35 %.
"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

import emblem as em  # noqa: E402
import iphone17pro as ip  # noqa: E402
import studio  # noqa: E402

args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
SET = args.get("set", "desktop")
DESKTOP = SET == "desktop"
N = int(args.get("frames", "300"))
START, END = int(args.get("start", "0")), int(args.get("end", str(N - 1)))
STEP = int(args.get("step", "1"))
ONLY = [int(v) for v in args["only"].split(",")] if args.get("only") else None
PREVIEW = args.get("preview", "0") == "1"
SAMPLES = int(args.get("samples", "16" if PREVIEW else "96"))
FULL_RES = "1600x900" if DESKTOP else "864x1536"
RES = tuple(int(v) for v in args.get("res", ("480x270" if DESKTOP else "270x480") if PREVIEW else FULL_RES).split("x"))
ASPECT = RES[0] / RES[1]
OUT = os.path.join(HERE, args.get("out", f"frames/{SET}{'_preview' if PREVIEW else ''}"))
FORCE = args.get("force", "0") == "1"
SCREEN_STRENGTH = float(args.get("screen", "1.25"))
TEX = os.path.join(HERE, "textures")
os.makedirs(OUT, exist_ok=True)

ACTS = [(0.00, 0.17, "hero"), (0.17, 0.36, "stop"), (0.36, 0.50, "again"), (0.50, 0.72, "examples"),
        (0.72, 0.88, "how"), (0.88, 1.00, "finale")]


# ============================================================================================ math helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def win(t, t0, t1):
    """0 before t0, 1 after t1, smooth between."""
    return smooth((t - t0) / (t1 - t0)) if t1 > t0 else float(t >= t0)


def bump(t, t0, t1):
    """0 -> 1 -> 0 across [t0, t1]."""
    u = clamp((t - t0) / (t1 - t0))
    return math.sin(math.pi * u) ** 2


def lerp(a, b, s):
    return tuple(x + (y - x) * s for x, y in zip(a, b))


class Track:
    """Monotone cubic (PCHIP) through (t, value_tuple) keys: no overshoot, holds stay still, eases at both ends."""

    def __init__(self, keys):
        self.ts = [float(k[0]) for k in keys]
        self.vs = [tuple(float(c) for c in k[1]) for k in keys]
        assert all(b > a for a, b in zip(self.ts, self.ts[1:])), "key times must increase"
        n, dim = len(keys), len(self.vs[0])
        self.h = [self.ts[i + 1] - self.ts[i] for i in range(n - 1)]
        self.m = [[0.0] * dim for _ in range(n)]
        for c in range(dim):
            d = [(self.vs[i + 1][c] - self.vs[i][c]) / self.h[i] for i in range(n - 1)]
            for i in range(1, n - 1):
                if d[i - 1] * d[i] > 0:
                    w1, w2 = 2 * self.h[i] + self.h[i - 1], self.h[i] + 2 * self.h[i - 1]
                    self.m[i][c] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def seg(self, t):
        i = max(j for j in range(len(self.ts) - 1) if self.ts[j] <= t)
        return i, (t - self.ts[i]) / self.h[i]

    def __call__(self, t):
        if t <= self.ts[0]:
            return self.vs[0]
        if t >= self.ts[-1]:
            return self.vs[-1]
        i, s = self.seg(t)
        h = self.h[i]
        h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
        return tuple(h00 * a + h10 * h * ma + h01 * b + h11 * h * mb
                     for a, b, ma, mb in zip(self.vs[i], self.vs[i + 1], self.m[i], self.m[i + 1]))


# ============================================================================================ the beats
STOP_T = 0.262            # the STOP bubble lands: the world freezes
T_AGAIN = 0.395           # "Today 9:12 AM": they are back
STORM_T0, STORM_T1 = 0.428, 0.500
SHOT_T = 0.745            # the screenshot flash
MERGE_T0, MERGE_T1 = 0.868, 0.895   # the read screenshot folds into the shield
P1_SCREENS = [(0.000, "lock_0"), (0.080, "lock_1"), (0.100, "lock_2"), (0.120, "lock_3"), (0.140, "lock_4"),
              (0.160, "lock_5"), (0.184, "home_blank_dark"), (0.196, "msgA_1"), (0.252, "msgA_2"),
              (0.300, "msgA_3"), (0.392, "msgA_4"),
              (0.424, "msgA_5")]
FADE = 0.010

# ============================================================================================ choreography
HERO_YAW = -22.0 if DESKTOP else -16.0     # the screen turns toward the copy side (into the frame)
ROW = 0.24 if DESKTOP else 0.115           # act-4 spacing: a neighbour never intrudes on a close-up

P1_TRACK = Track([  # (t, (x, y, z, pitch, roll, yaw)) of the phone's turn empty
    (0.000, (0.0, 0.0, 0.000, 6.0, 0.0, -154.0)),        # opens on the back: the Cosmic Orange camera plateau
    (0.030, (0.0, 0.0, 0.001, 6.0, 0.5, -140.0)),
    (0.075, (0.0, 0.0, 0.002, 5.0, 2.5, HERO_YAW - 14.0)),   # ...and turns around to the lock screen
    (0.100, (0.0, 0.0, 0.002, 5.0, 3.0, HERO_YAW)),
    (0.160, (0.0, 0.0, 0.002, 4.0, 2.0, HERO_YAW + 5.0)),
    (0.205, (0.0, 0.0, 0.000, 3.0, 1.0, -9.0)),
    (0.265, (0.0, 0.0, 0.000, 2.0, 0.0, -5.0)),
    (0.360, (0.0, 0.0, -0.002, 2.0, 0.0, -5.0)),
    (0.460, (0.0, 0.0, -0.003, 3.0, 0.5, -8.0)),
    (0.505, (0.0, 0.0, 0.000, 2.0, 0.0, -2.0)),
    (0.552, (-ROW, 0.0, 0.000, 2.0, 0.0, 5.0)),
    (0.705, (-ROW, 0.0, 0.000, 2.0, 0.0, 5.0)),
    (0.740, (0.0, 0.0, 0.000, 2.0, 0.0, 0.0)),
    (0.762, (0.0, 0.0, 0.000, 2.0, 0.0, -2.0)),
    # drops back into the dark behind the screenshot (never through the copy side), out low and right
    (0.795, (0.06, 0.25, -0.060, 6.0, 0.0, 10.0)),
    (0.840, (0.20, 0.55, -0.150, 12.0, 0.0, 22.0)),
    (0.890, (0.45, 0.85, -0.250, 18.0, 0.0, 32.0)),
])
P2_TRACK = Track([  # conversation B (may qualify), Deep Blue: comes forward out of the dark behind P1
    (0.000, (0.0, 0.70, -0.030, 2.0, 0.0, 0.0)),
    (0.505, (0.0, 0.70, -0.030, 2.0, 0.0, 0.0)),
    (0.556, (0.0, 0.0, 0.000, 2.0, 0.0, 0.0)),
    (0.705, (0.0, 0.0, 0.000, 2.0, 0.0, 0.0)),
    (0.745, (0.10, 0.70, -0.200, 2.0, 0.0, -20.0)),
    (1.000, (0.10, 0.70, -0.200, 2.0, 0.0, -20.0)),
])
P3_TRACK = Track([  # conversation C (weaker), Silver: slides in from the right
    (0.000, (ROW + 0.30, 0.60, -0.020, 2.0, 0.0, -30.0)),
    (0.510, (ROW + 0.30, 0.60, -0.020, 2.0, 0.0, -30.0)),
    (0.560, (ROW, 0.0, 0.000, 2.0, 0.0, -5.0)),
    (0.705, (ROW, 0.0, 0.000, 2.0, 0.0, -5.0)),
    (0.745, (ROW + 0.35, 0.65, -0.050, 2.0, 0.0, -35.0)),
    (1.000, (ROW + 0.35, 0.65, -0.050, 2.0, 0.0, -35.0)),
])
PHONE_TRACKS = {"P1": P1_TRACK, "P2": P2_TRACK, "P3": P3_TRACK}
CARD_AT = (0.0, -0.100, 0.002)
EMBLEM_AT = (0.0, 0.020, 0.000)

# camera: (t, subject, (u, v, distance m, lens mm, f-stop, rise m, orbit deg)); subjects blend between keys
if DESKTOP:
    SHOTS = [
        (0.000, "P1", (0.70, 0.52, 0.66, 70, 5.6, 0.016, 6.0)),
        (0.075, "P1", (0.70, 0.52, 0.76, 70, 5.6, 0.013, 0.0)),
        (0.160, "P1", (0.70, 0.52, 0.70, 70, 5.6, 0.011, -4.0)),
        (0.205, "P1", (0.69, 0.51, 0.62, 70, 5.6, 0.008, -3.0)),
        (0.265, "P1", (0.68, 0.50, 0.56, 70, 5.6, 0.006, -1.0)),
        (0.360, "P1", (0.68, 0.50, 0.52, 70, 5.6, 0.004, 4.0)),       # the frozen beat drifts, it never stops
        (0.440, "P1", (0.67, 0.50, 0.58, 70, 5.6, 0.003, 1.5)),
        (0.500, "P1", (0.66, 0.50, 0.66, 70, 6.3, 0.006, 0.0)),
        (0.556, "ROW", (0.50, 0.54, 1.32, 70, 8.0, 0.030, 0.0)),
        (0.576, "ROW", (0.50, 0.54, 1.28, 70, 8.0, 0.028, 0.0)),
        (0.600, "P1", (0.66, 0.50, 0.56, 70, 6.3, 0.006, 0.0)),
        (0.618, "P1", (0.66, 0.50, 0.55, 70, 6.3, 0.006, 0.0)),
        (0.645, "P2", (0.66, 0.50, 0.56, 70, 6.3, 0.006, 0.0)),
        (0.663, "P2", (0.66, 0.50, 0.55, 70, 6.3, 0.006, 0.0)),
        (0.690, "P3", (0.66, 0.50, 0.56, 70, 6.3, 0.006, 0.0)),
        (0.705, "P3", (0.66, 0.50, 0.55, 70, 6.3, 0.006, 0.0)),
        (0.723, "ROW", (0.56, 0.52, 0.95, 70, 7.1, 0.014, 0.0)),     # pull wide while P1 slides back to center
        (0.740, "P1", (0.64, 0.50, 0.62, 70, 6.3, 0.006, 0.0)),
        (0.765, "P1", (0.64, 0.50, 0.60, 70, 6.3, 0.006, 0.0)),
        (0.805, "CARD", (0.66, 0.50, 0.50, 70, 5.6, 0.004, 0.0)),
        (0.870, "CARD", (0.66, 0.50, 0.48, 70, 5.6, 0.004, 0.0)),
        (0.925, "EMBLEM", (0.66, 0.50, 0.56, 70, 5.6, 0.008, 0.0)),
        (1.000, "EMBLEM", (0.66, 0.50, 0.52, 70, 5.6, 0.010, 0.0)),
    ]
else:
    SHOTS = [
        (0.000, "P1", (0.50, 0.64, 0.47, 60, 5.6, 0.016, 6.0)),
        (0.075, "P1", (0.50, 0.64, 0.54, 60, 5.6, 0.014, 0.0)),
        (0.160, "P1", (0.50, 0.64, 0.50, 60, 5.6, 0.012, -3.0)),
        (0.205, "P1", (0.50, 0.63, 0.46, 60, 5.6, 0.010, -2.0)),
        (0.265, "P1", (0.50, 0.62, 0.42, 60, 5.6, 0.008, 0.0)),
        (0.360, "P1", (0.50, 0.62, 0.40, 60, 5.6, 0.006, 3.0)),
        (0.440, "P1", (0.50, 0.62, 0.45, 60, 5.6, 0.005, 1.5)),
        (0.500, "P1", (0.50, 0.62, 0.50, 60, 6.3, 0.008, 0.0)),
        (0.556, "ROW", (0.50, 0.58, 1.02, 60, 8.0, 0.030, 0.0)),
        (0.576, "ROW", (0.50, 0.58, 0.99, 60, 8.0, 0.028, 0.0)),
        (0.600, "P1", (0.50, 0.62, 0.44, 60, 6.3, 0.008, 0.0)),
        (0.618, "P1", (0.50, 0.62, 0.43, 60, 6.3, 0.008, 0.0)),
        (0.645, "P2", (0.50, 0.62, 0.44, 60, 6.3, 0.008, 0.0)),
        (0.663, "P2", (0.50, 0.62, 0.43, 60, 6.3, 0.008, 0.0)),
        (0.690, "P3", (0.50, 0.62, 0.44, 60, 6.3, 0.008, 0.0)),
        (0.705, "P3", (0.50, 0.62, 0.43, 60, 6.3, 0.008, 0.0)),
        (0.723, "ROW", (0.50, 0.60, 0.80, 60, 7.1, 0.018, 0.0)),
        (0.740, "P1", (0.50, 0.62, 0.48, 60, 6.3, 0.008, 0.0)),
        (0.765, "P1", (0.50, 0.62, 0.47, 60, 6.3, 0.008, 0.0)),
        (0.805, "CARD", (0.50, 0.60, 0.40, 60, 5.6, 0.006, 0.0)),
        (0.870, "CARD", (0.50, 0.60, 0.38, 60, 5.6, 0.006, 0.0)),
        (0.925, "EMBLEM", (0.50, 0.56, 0.44, 60, 5.6, 0.010, 0.0)),
        (1.000, "EMBLEM", (0.50, 0.56, 0.41, 60, 5.6, 0.012, 0.0)),
    ]
if args.get("adcam") == "1" and not DESKTOP:
    # the Reel's end card stacks logo, headline and URL above the shield: the shield sits lower and smaller
    SHOTS[-2] = (0.925, "EMBLEM", (0.50, 0.63, 0.52, 60, 5.6, 0.010, 0.0))
    SHOTS[-1] = (1.000, "EMBLEM", (0.50, 0.63, 0.50, 60, 5.6, 0.012, 0.0))
SHOT_TRACK = Track([(tk, p) for tk, _, p in SHOTS])
SHOT_SUBJ = [s for _, s, _ in SHOTS]


def subject_point(name, t):
    if name in PHONE_TRACKS:
        return Vector(PHONE_TRACKS[name](t)[:3])
    if name == "ROW":
        return Vector((0.0, 0.0, 0.0))
    if name == "CARD":
        return Vector(CARD_AT)
    return Vector(EMBLEM_AT)


def subject_at(t):
    ts = SHOT_TRACK.ts
    if t <= ts[0]:
        return subject_point(SHOT_SUBJ[0], t)
    if t >= ts[-1]:
        return subject_point(SHOT_SUBJ[-1], t)
    i, s = SHOT_TRACK.seg(t)
    a, b = SHOT_SUBJ[i], SHOT_SUBJ[i + 1]
    pa = subject_point(a, t)
    return pa if a == b else pa.lerp(subject_point(b, t), smooth(s))


def view_size(lens, d):
    """Visible width/height (m) at distance d; the AUTO sensor fit puts the 36 mm on the longer image side."""
    long_side = d * 36.0 / lens
    return (long_side, long_side / ASPECT) if ASPECT >= 1 else (long_side * ASPECT, long_side)


def screen_state(t):
    cur, prev, t_cur = P1_SCREENS[0][1], P1_SCREENS[0][1], P1_SCREENS[0][0]
    for tk, name in P1_SCREENS:
        if t >= tk:
            prev, cur, t_cur = cur, name, tk
    return prev, cur, clamp((t - t_cur) / FADE)


def freeze_amt(t):
    return win(t, STOP_T - 0.004, STOP_T + 0.018) * (1 - win(t, T_AGAIN, T_AGAIN + 0.03))


def storm_amt(t):
    return win(t, STORM_T0, STORM_T0 + 0.035) * (1 - win(t, STORM_T1 - 0.012, STORM_T1 + 0.03))


def bubble_speed(t):
    v = 1.0 - win(t, STOP_T - 0.02, STOP_T + 0.004)     # decelerate into the freeze
    v += 0.6 * win(t, T_AGAIN, T_AGAIN + 0.02)           # they text again: the swarm twitches back to life
    v += 6.4 * win(t, STORM_T0, STORM_T0 + 0.035)        # the storm
    v -= 5.0 * win(t, STORM_T1 - 0.01, STORM_T1 + 0.03)
    return max(v, 0.0)


TAU_STEPS = 3000
_tau = [0.0]
for _k in range(1, TAU_STEPS + 1):
    _tau.append(_tau[-1] + bubble_speed(_k / TAU_STEPS) / TAU_STEPS)


def tau(t):
    return _tau[int(clamp(t) * TAU_STEPS)]


# ============================================================================================ scene
scene = studio.reset_scene()
studio.setup_render(scene, res=RES, samples=SAMPLES)
studio.product_studio(scene, k=1.0)
scene.render.use_persistent_data = True


def tex_path(name):
    real = os.path.join(TEX, f"{name}.png")
    return real if os.path.exists(real) else os.path.join(TEX, f"{name}_PH.png")


IMAGES = {}


def image(name):
    if name not in IMAGES:
        img = bpy.data.images.load(tex_path(name), check_existing=True)
        img.colorspace_settings.name = "sRGB"
        IMAGES[name] = img
    return IMAGES[name]


MASK = os.path.join(TEX, "screen_mask.png")


def phone(finish, label, screen):
    turn = bpy.data.objects.new(label + "_turn", None)
    scene.collection.objects.link(turn)
    root = ip.build_iphone(finish, label, screen_image=tex_path(screen), screen_mask=MASK,
                           screen_strength=SCREEN_STRENGTH)
    root.parent = turn
    root.rotation_euler = (math.radians(90.0), 0.0, 0.0)    # local +y -> world +z, the screen faces -Y
    return turn, bpy.data.materials[f"{label}_screen"]


P1, P1_screen = phone("cosmic_orange", "P1", "lock_0")
P2, P2_screen = phone("deep_blue", "P2", "msgB_dark")
P3, P3_screen = phone("silver", "P3", "msgC_dark")
ip.set_screen(P2_screen, image("msgB_dark"))
ip.set_screen(P3_screen, image("msgC_dark"))


def place(turn, v, jitter=0.0, t=0.0):
    x, y, z, pitch, roll, yaw = v
    pitch += jitter * math.sin(t * 410.0)
    roll += jitter * math.sin(t * 530.0 + 1.3)
    turn.location = (x, y, z)
    turn.rotation_euler = Euler((math.radians(pitch), math.radians(roll), math.radians(yaw)), "XYZ")


def set_visible(root, visible):
    for ob in [root] + list(root.children_recursive):
        ob.hide_render = not visible


def emission_material(name, color, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.name = "Emit"
    e.inputs["Color"].default_value = (*color, 1.0)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs["Emission"], out.inputs["Surface"])
    return mat, e


def srgb(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


ORANGE = tuple(srgb(c) for c in (245, 130, 32))
GREEN = tuple(srgb(c) for c in (48, 209, 88))


# ---------------------------------------------------------------- backdrop glow (a soft halo far behind the subject)
def glow_plane():
    import bmesh
    me = bpy.data.meshes.new("Glow")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Glow", me)
    scene.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.scale = (0.62, 0.62, 1.0)          # halo radius 0.31 m: fades out well inside the frame edges
    mat = bpy.data.materials.new("GlowMat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emi = nt.nodes.new("ShaderNodeEmission")
    see_through = nt.nodes.new("ShaderNodeBsdfTransparent")
    add = nt.nodes.new("ShaderNodeAddShader")        # additive: the page background shows through untouched
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.0, 2.0, 1.0)
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "SPHERICAL"
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 2.2
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.blend_type = "MULTIPLY"
    col.inputs[0].default_value = 1.0
    col.inputs[7].default_value = (1.0, 0.36, 0.08, 1.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], pw.inputs[0])
    nt.links.new(pw.outputs[0], col.inputs[6])
    nt.links.new(col.outputs[2], emi.inputs["Color"])
    nt.links.new(see_through.outputs[0], add.inputs[0])
    nt.links.new(emi.outputs["Emission"], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    me.materials.append(mat)
    ob.visible_shadow = False
    ob.visible_glossy = False
    ob.visible_diffuse = False
    return ob, emi, col


GLOW, GLOW_EMIT, GLOW_COL = glow_plane()


# ---------------------------------------------------------------- floating spam bubbles
BUB = json.load(open(os.path.join(HERE, "bubbles.json")))
BUB_MATS = []


def bubble_template(b):
    cu = bpy.data.curves.new(f"Bub{b['i']}", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = 0.0011
    cu.bevel_mode = "ROUND"
    cu.bevel_depth = 0.0005
    cu.bevel_resolution = 4
    sp = cu.splines.new("POLY")
    sp.points.add(len(b["outline"]) - 1)
    for k, (x, y) in enumerate(b["outline"]):
        sp.points[k].co = (x, y, 0.0, 1.0)
    sp.use_cyclic_u = True
    mat = bpy.data.materials.new(f"BubMat{b['i']}")
    mat.use_nodes = True
    nt = mat.node_tree
    p = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    x0, x1, y0, y1 = b["bbox"]
    mp.inputs["Location"].default_value = (-x0 / (x1 - x0), -y0 / (y1 - y0), 0.0)
    mp.inputs["Scale"].default_value = (1.0 / (x1 - x0), 1.0 / (y1 - y0), 1.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.extension = "EXTEND"
    tex.image = bpy.data.images.load(os.path.join(TEX, b["png"]), check_existing=True)
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = 0.55
    p.inputs["Roughness"].default_value = 0.32
    p.inputs["Coat Weight"].default_value = 0.55       # glossy, but no blown-out mirror blobs from the key light
    p.inputs["Coat Roughness"].default_value = 0.14
    cu.materials.append(mat)
    BUB_MATS.append(p)
    return cu


TEMPLATES = [bubble_template(b) for b in BUB]
ORBIT_R = (0.09, 0.42) if DESKTOP else (0.07, 0.30)
ORBIT_Z = (-0.17, 0.17) if DESKTOP else (-0.22, 0.14)   # mobile: keep the copy band at the top calmer
rng = random.Random(17)
BUBBLES = []
for k in range(46):
    b = BUB[k % 12] if k < 40 else BUB[12 + (k % 2)]       # 40 incoming spam texts, a few green STOP replies
    ob = bpy.data.objects.new(f"Bubble{k}", TEMPLATES[b["i"]])
    scene.collection.objects.link(ob)
    while True:
        ang = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(*ORBIT_R)
        z = rng.uniform(*ORBIT_Z)
        if not (math.sin(ang) * rad < 0.02 and abs(math.cos(ang) * rad) < 0.11 and abs(z) < 0.11):
            break
    BUBBLES.append(dict(ob=ob, ang=ang, rad=rad, z=z, w=rng.uniform(0.35, 0.8) * rng.choice([-1, 1]),
                        bob=rng.uniform(0.004, 0.012), ph=rng.uniform(0, 6.28), tilt=rng.uniform(-18, 18),
                        spin=rng.uniform(-25, 25), s=rng.uniform(1.25, 1.85), inward=rng.uniform(0.35, 0.6)))


def place_bubbles(t):
    T = tau(t)
    freeze = freeze_amt(t)
    push = win(t, STOP_T, STOP_T + 0.025) * (1 - win(t, T_AGAIN, STORM_T0 + 0.02))   # STOP shoves the swarm back
    storm = storm_amt(t)
    gone = win(t, 0.500, 0.548)
    c = P1_TRACK(t)
    cx, cz = c[0], c[2]
    pos = []
    for bb in BUBBLES:
        a = bb["ang"] + bb["w"] * T * 5.0
        r = bb["rad"] * (1 + 0.30 * push) * (1 - bb["inward"] * storm) * (1 + 1.8 * gone)
        x = cx + r * math.cos(a)
        sa = math.sin(a)
        y = 0.03 + r * sa * (0.9 if sa > 0 else 0.5)     # the near half of the orbit is flattened: no blobs on the lens
        z = cz + bb["z"] * (1 - 0.15 * storm) + bb["bob"] * math.sin(bb["ph"] + T * 9.0)
        if y < 0.02 and abs(x - cx) < 0.10 and abs(z - cz) < 0.11:     # never block the screen
            y = 0.02 + abs(y) * 0.5
        pos.append([x, y, z, bb["s"] * (1 - gone)])
    # bubbles that overlap on screen at nearly the same depth would cut through each other: layer them instead
    for _ in range(2):
        for i in range(len(pos)):
            xi, yi, zi, si = pos[i]
            for j in range(i + 1, len(pos)):
                xj, yj, zj, sj = pos[j]
                ox = 1 - abs(xi - xj) / (0.019 * (si + sj) + 1e-6)
                oz = 1 - abs(zi - zj) / (0.009 * (si + sj) + 1e-6)
                if ox <= 0 or oz <= 0:
                    continue
                need = 0.015 * smooth(min(ox, oz) * 3)
                dy = yj - yi
                if abs(dy) >= need:
                    continue
                nudge = (need - abs(dy)) / 2
                sgn = 1.0 if dy >= 0 else -1.0
                pos[i][1] -= nudge * sgn
                pos[j][1] += nudge * sgn
                yi = pos[i][1]
    for bb, (x, y, z, _) in zip(BUBBLES, pos):
        ob = bb["ob"]
        ob.location = (x, y, z)
        wob = 8 * math.sin(bb["ph"] + T * 4.0)
        ob.rotation_euler = Euler((math.radians(90 + bb["tilt"] * 0.4), math.radians(bb["spin"] * 0.15),
                                   math.radians(bb["tilt"] + wob)), "XYZ")
        sc = bb["s"] * (1 - gone)
        ob.scale = (sc, sc, sc)
        ob.hide_render = sc < 0.02
    for p in BUB_MATS:
        p.inputs["Emission Strength"].default_value = 0.55 * (1 - 0.45 * freeze) + 0.30 * storm


# ---------------------------------------------------------------- the STOP pulse: two green rings race outward
def ring(name):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0008
    cu.bevel_resolution = 3
    sp = cu.splines.new("POLY")
    sp.points.add(159)
    sp.use_cyclic_u = True
    mat, e = emission_material(name + "Mat", GREEN, 0.0)
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    ob.visible_shadow = False
    return ob, sp, e


RINGS = [ring("Pulse0"), ring("Pulse1")]


def stop_bubble_point():
    """Where the STOP bubble sits on the screen (fractions of the display), from the msgA_2 layout if rendered."""
    lay = load_layout("msgA_2")
    if lay:
        outs = [b for b in lay["boxes"] if "ios-b--out" in b["cls"]]
        if outs:
            b = outs[-1]
            return (b["x"] + b["w"] / 2) / 402.0, (b["y"] + b["h"] / 2) / 874.0
    return 0.86, 0.36


def pulse_setup():
    fx, fy = stop_bubble_point()
    for ob, _, _ in RINGS:
        ob.parent = P1                                   # rides on the phone, in the plane of its screen
        ob.location = ((fx - 0.5) * ip.SCREEN_W, -(ip.ZF + 0.010), (0.5 - fy) * ip.SCREEN_H)
        ob.rotation_euler = (math.radians(90.0), 0.0, 0.0)


def pulse_state(t):
    """STOP sends a ripple out of its own bubble, across the screen and through the swarm."""
    for k, (ob, sp, e) in enumerate(RINGS):
        t0 = STOP_T + 0.002 + 0.014 * k
        s = clamp((t - t0) / 0.065)
        on = 0.0 < s < 1.0
        ob.hide_render = not on
        if not on:
            continue
        R = 0.004 + 0.30 * (1 - (1 - s) ** 2.2)
        for i in range(160):
            a = 2 * math.pi * i / 160
            sp.points[i].co = (R * math.cos(a), R * math.sin(a), 0.0, 1.0)
        e.inputs["Strength"].default_value = 6.0 * (1 - s) ** 1.2


# ---------------------------------------------------------------- the screenshot card, its scan and the evidence boxes
def card_object():
    w, h = ip.SCREEN_W, ip.SCREEN_H
    pts = ip.outline(w, h, 0.0103, 0.0103)
    rings = [([(x, y) for (x, y) in pts], -0.0004), ([(x, y) for (x, y) in pts], 0.0)]
    mat = ip.screen_material("CardScreen", tex_path("msgA_5"), MASK, SCREEN_STRENGTH)
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Specular IOR Level"].default_value = 0.0      # a picture, not glass: tilted back it must not mirror
    p.inputs["Roughness"].default_value = 1.0               # the overhead light into a white sheet
    ob = ip.sweep("Card", rings, None, mat, cap_first=True, cap_last=True,
                  uv_fn=lambda co: ((co.x + w / 2) / w, (co.y + h / 2) / h))
    return ob, mat


CARD, CARD_MAT = card_object()
CARD_TURN = bpy.data.objects.new("CardTurn", None)
scene.collection.objects.link(CARD_TURN)
CARD.parent = CARD_TURN
CARD.rotation_euler = (math.radians(90.0), 0.0, 0.0)


def card_border():
    """The white border of an iOS screenshot thumbnail: a plate 1.6 mm larger than the shot, just behind it."""
    b = 0.0011
    w, h = ip.SCREEN_W + 2 * b, ip.SCREEN_H + 2 * b
    pts = ip.outline(w, h, 0.0103 + b, 0.0103 + b)
    mat, e = emission_material("CardBorderMat", (1.0, 1.0, 1.0), 0.0)
    ob = ip.sweep("CardBorder", [(list(pts), -0.0009), (list(pts), -0.0002)], CARD, mat, cap_first=True, cap_last=True)
    ob.visible_shadow = False
    return ob, e


BORDER, BORDER_EMIT = card_border()


def flat_plane(name, parent, sx, sy):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    ob.parent = parent
    ob.scale = (sx, sy, 1.0)
    ob.visible_shadow = False
    return ob


SCAN = flat_plane("Scan", CARD, ip.SCREEN_W * 1.06, 0.0016)
SCAN_MAT, SCAN_EMIT = emission_material("ScanMat", ORANGE, 0.0)
SCAN.data.materials.append(SCAN_MAT)


def trail_material():
    """The scanner's afterglow: orange at the line, fading to transparent above it."""
    mat = bpy.data.materials.new("TrailMat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 2.0
    e = nt.nodes.new("ShaderNodeEmission")
    e.name = "Emit"
    e.inputs["Color"].default_value = (*ORANGE, 1.0)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Y"], inv.inputs[1])        # generated Y is 0 at the bottom edge (the line), 1 at the top
    nt.links.new(inv.outputs[0], pw.inputs[0])
    nt.links.new(pw.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(e.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat, e


TRAIL = flat_plane("Trail", CARD, ip.SCREEN_W * 1.06, 0.010)
TRAIL_MAT, TRAIL_EMIT = trail_material()
TRAIL.data.materials.append(TRAIL_MAT)


def load_layout(name):
    for p in (os.path.join(TEX, f"{name}.layout.json"),
              os.path.join(HERE, "..", "..", "ios-ui-kit", "out", f"{name}_layout.json")):
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    return None


def evidence_boxes():
    """Orange outlines around what the reader looks for: the STOP, the date they came back, the text after it."""
    lay = load_layout("msgA_5")
    if not lay:
        print("no msgA_5 layout: the scan runs without evidence boxes")
        return []
    boxes = [b for b in lay["boxes"] if b["cls"].startswith("ios-b ") or b["cls"].startswith("ios-ts")]
    want = []
    outs = [b for b in boxes if "ios-b--out" in b["cls"]]
    ins = [b for b in boxes if "ios-b--in" in b["cls"]]
    stamps = [b for b in boxes if b["cls"].startswith("ios-ts") and "label" not in b["cls"]]
    if outs:
        want.append(outs[0])
    if stamps:
        want.append(stamps[-1])
    if ins:
        want.append(ins[-1])
    sw, sh = ip.SCREEN_W, ip.SCREEN_H
    out = []
    for k, b in enumerate(want):
        pad = 5.0
        if b["cls"].startswith("ios-ts"):              # a centered timestamp row: hug the text, not the row
            tw = len(b["text"]) * 7.4
            b = dict(b, x=201 - tw / 2, w=tw)
        x0, y0, w, h = b["x"] - pad, b["y"] - pad, b["w"] + 2 * pad, b["h"] + 2 * pad
        cx = ((x0 + w / 2) / 402.0 - 0.5) * sw
        cy = (0.5 - (y0 + h / 2) / 874.0) * sh
        wm, hm = w / 402.0 * sw, h / 874.0 * sh
        r = min(wm, hm) * 0.32
        cu = bpy.data.curves.new(f"Evi{k}", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = 0.00028
        cu.bevel_resolution = 2
        pts = ip.outline(wm, hm, r, r)
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for i, (px, py) in enumerate(pts):
            sp.points[i].co = (px, py, 0.0, 1.0)
        sp.use_cyclic_u = True
        mat, e = emission_material(f"EviMat{k}", ORANGE, 0.0)
        cu.materials.append(mat)
        ob = bpy.data.objects.new(f"Evi{k}", cu)
        scene.collection.objects.link(ob)
        ob.parent = CARD
        ob.location = (cx, cy, 0.0006)
        ob.visible_shadow = False
        out.append((ob, e, (y0 + h / 2) / 874.0))
    return out


EVIDENCE = evidence_boxes()
pulse_setup()


def card_state(t):
    """The card sits exactly on P1's screen at the flash, peels off toward us, gets read, then folds into the shield."""
    flash = bump(t, SHOT_T, SHOT_T + 0.030)
    fly = win(t, SHOT_T + 0.012, SHOT_T + 0.065)
    into = win(t, MERGE_T0, MERGE_T1)
    shown = SHOT_T + 0.010 <= t <= MERGE_T1
    for ob in [CARD, SCAN, TRAIL, BORDER] + [e[0] for e in EVIDENCE]:
        ob.hide_render = not shown
    if not shown:
        return flash
    BORDER_EMIT.inputs["Strength"].default_value = 1.3 * win(t, SHOT_T + 0.012, SHOT_T + 0.030)
    m1 = P1.matrix_world.copy()
    start = m1 @ Vector((0.0, -ip.ZF - 0.0003, 0.0))
    pos = start.lerp(Vector(CARD_AT), fly).lerp(Vector(EMBLEM_AT) + Vector((0, -0.01, 0)), into)
    CARD_TURN.location = pos
    e1 = P1.rotation_euler
    # it leaves the phone and lies back like a photo on a light table: clearly a flat picture, not a phone
    pitch = (1 - fly) * e1.x + fly * math.radians(-24.0) * (1 - into)
    yaw = (1 - fly) * e1.z + fly * math.radians(-12.0) * (1 - into)
    roll = fly * math.radians(3.0) * (1 - into)
    CARD_TURN.rotation_euler = Euler((pitch, roll, yaw), "XYZ")
    s = (1.0 - 0.36 * fly) * (1.0 - into)
    CARD_TURN.scale = (max(s, 1e-4),) * 3
    scan = clamp((t - 0.808) / 0.055)
    on = bump(t, 0.803, 0.868)
    SCAN.location = (0.0, ip.SCREEN_H * (0.5 - scan), 0.0005)
    TRAIL.location = (0.0, ip.SCREEN_H * (0.5 - scan) + 0.005, 0.0004)
    SCAN_EMIT.inputs["Strength"].default_value = 9.0 * on
    TRAIL_EMIT.inputs["Strength"].default_value = 1.6 * on
    SCAN.hide_render = TRAIL.hide_render = on < 0.01          # an unlit emitter renders black: hide it instead
    for ob, e, fy in EVIDENCE:
        lit = (win(scan, fy - 0.02, fy + 0.04) if t < 0.868 else 1.0) * (1 - into)
        e.inputs["Strength"].default_value = 5.0 * lit
        ob.hide_render = lit < 0.01
    return flash


# ---------------------------------------------------------------- the emblem (finale)
EMB = em.build_emblem(height=0.085)
EMB_TURN = bpy.data.objects.new("EmblemTurn", None)
scene.collection.objects.link(EMB_TURN)
EMB.parent = EMB_TURN


def back_out(s, c1=1.70158):
    """Ease-out with a small overshoot (the shield pops a little past full size, then settles)."""
    s = clamp(s)
    c3 = c1 + 1.0
    return 1.0 + c3 * (s - 1.0) ** 3 + c1 * (s - 1.0) ** 2


def emblem_state(t):
    """The read screenshot folds into the shield: it grows out of the card's last position with a half turn."""
    g = clamp((t - (MERGE_T1 - 0.012)) / 0.050)
    grow = back_out(g)
    EMB_TURN.location = EMBLEM_AT
    sway = 5.0 * math.sin((t - 0.94) * 14.0) * win(t, 0.94, 1.0)
    spin = -150.0 * (1 - smooth(g))
    EMB_TURN.rotation_euler = Euler((math.radians(4.0 * (1 - g)), 0.0, math.radians(spin + sway)), "XYZ")
    s = max(grow, 1e-4)
    EMB_TURN.scale = (s, s, s)
    set_visible(EMB, g > 0.0)


# ---------------------------------------------------------------- camera
CAM = studio.camera("Cam", (0, -0.6, 0), (0, 0, 0), lens=70.0, fstop=5.6, focus_target=(0, 0, 0))
scene.camera = CAM


def camera_state(t):
    S = subject_at(t)
    u, v, d, lens, fstop, rise, orbit = SHOT_TRACK(t)
    wv, hv = view_size(lens, d)
    a = math.radians(orbit)
    fwd = Vector((math.sin(a), math.cos(a), 0.0))
    right = Vector((math.cos(a), -math.sin(a), 0.0))
    up = Vector((0.0, 0.0, 1.0))
    T = S - right * ((u - 0.5) * wv) + up * ((v - 0.5) * hv)
    C = T - fwd * d + up * rise
    CAM.location = C
    studio.look_at(CAM, T)
    CAM.data.lens = lens
    CAM.data.dof.aperture_fstop = fstop
    CAM.data.dof.focus_distance = (S - C).length
    return S


def mood(t, S):
    freeze = freeze_amt(t)
    storm = storm_amt(t)
    row = win(t, 0.50, 0.55) * (1 - win(t, 0.705, 0.745))
    finale = win(t, 0.875, 0.95)
    burst = bump(t, MERGE_T1 - 0.012, MERGE_T1 + 0.035)
    strength = 0.20 + 0.34 * storm - 0.10 * freeze - 0.08 * row + 0.14 * finale + 0.35 * burst
    hot = (1.0, 0.36 - 0.16 * storm, 0.08 - 0.04 * storm)
    cool = (0.30, 0.55, 1.0)
    c = cool if freeze > 0.5 else hot                 # switch hue at the dark point: never a muddy purple
    strength *= 1.0 - 4.0 * freeze * (1.0 - freeze)
    GLOW_EMIT.inputs["Strength"].default_value = max(strength, 0.02)
    GLOW_COL.inputs[7].default_value = (*c, 1.0)
    C = CAM.location
    k = (1.10 - C.y) / max(S.y - C.y, 1e-3)              # on the camera ray through the subject: behind it on screen
    GLOW.location = C + (S - C) * k


# ============================================================================================ render loop
def apply(t):
    storm = storm_amt(t)
    place(P1, P1_TRACK(t), jitter=0.7 * storm, t=t)
    place(P2, P2_TRACK(t))
    place(P3, P3_TRACK(t))
    set_visible(P1, t < 0.935)
    set_visible(P2, 0.500 <= t <= 0.750)
    set_visible(P3, 0.505 <= t <= 0.750)
    prev, cur, mix = screen_state(t)
    bpy.context.view_layer.update()
    flash = card_state(t)
    ip.set_screen(P1_screen, image(prev), image(cur), mix=mix, flash=flash)
    CARD_MAT.node_tree.nodes["ScreenFlash"].inputs[0].default_value = flash   # the card covers the screen at the flash
    place_bubbles(t)
    pulse_state(t)
    emblem_state(t)
    S = camera_state(t)
    mood(t, S)
    bpy.context.view_layer.update()


if args.get("tfile"):          # an edit: render an explicit list of story moments, in order (the Reel ad)
    TLIST = json.load(open(os.path.join(HERE, args["tfile"]), encoding="utf-8"))
    TLIST = TLIST["t"] if isinstance(TLIST, dict) else TLIST
    jobs = [(i, float(t)) for i, t in enumerate(TLIST)]
    if ONLY is not None:
        jobs = [jobs[i] for i in ONLY]
    else:
        jobs = jobs[START:END + 1 if "end" in args else None:STEP]
else:
    jobs = [(i, i / (N - 1)) for i in (ONLY if ONLY is not None else range(START, END + 1, STEP))]
for i, t in jobs:
    path = os.path.join(OUT, f"{i:04d}.png")
    if os.path.exists(path) and not FORCE:
        continue
    apply(t)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {i} t={t:.4f}", flush=True)
print("DONE", len(jobs))
