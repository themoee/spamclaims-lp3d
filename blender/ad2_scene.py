"""Ad 2 ("Did you mean START?"): the Deep Blue iPhone 17 Pro performs the conversation, rendered on a
transparent background (the compositor, ad2/ad2.html, paints the sunset world, the stickers and the end card).

blender -b --factory-startup -P ad2_scene.py -- [preview=1] [step=1] [only=0,100] [samples=40] [force=0] [out=frames/ad2]
Timing comes from ad2/edit.json (built from the voice performances by ad2/edit2.py); everything is in ad seconds.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

import emblem as em  # noqa: E402
import iphone17pro as ip  # noqa: E402
import studio  # noqa: E402

args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
EDIT = json.load(open(os.path.join(HERE, "..", "ad2", "edit.json"), encoding="utf-8"))
FPS = EDIT["fps"]
N = EDIT["frames"]
PREVIEW = args.get("preview", "0") == "1"
RES = (270, 480) if PREVIEW else (1080, 1920)
SAMPLES = int(args.get("samples", "12" if PREVIEW else "40"))
OUT = os.path.join(HERE, args.get("out", "frames/ad2_preview" if PREVIEW else "frames/ad2"))
FORCE = args.get("force", "0") == "1"
TEX = os.path.join(HERE, "textures", "ad2")
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def win(t, a, b):
    return smooth((t - a) / (b - a)) if b > a else float(t >= a)


def pulse(t, a, dur):
    """0 -> 1 -> 0 over [a, a + dur] (sine bump)."""
    u = (t - a) / dur
    return math.sin(math.pi * u) ** 2 if 0 <= u <= 1 else 0.0


def back_out(s, c1=1.9):
    s = clamp(s) - 1
    return 1 + (c1 + 1) * s ** 3 + c1 * s ** 2


def srgb(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


# ---------------------------------------------------------------- scene
scene = studio.reset_scene()
studio.setup_render(scene, res=RES, samples=SAMPLES, transparent=True)
scene.render.use_persistent_data = True


def warm_world(strength=1.0):
    """Reflections see a warm sunset studio (the page around the phone is orange); the film is transparent."""
    w = bpy.data.worlds.new("Warm")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    mz = nt.nodes.new("ShaderNodeMapRange")
    mz.inputs["From Min"].default_value = -1.0
    mz.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mz.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.06, 0.025, 0.012, 1)        # warm dark floor
    cr.elements[1].position, cr.elements[1].color = 1.0, (0.95, 0.80, 0.62, 1)          # bright warm sky
    e = cr.elements.new(0.50)
    e.color = (0.55, 0.20, 0.06, 1)                                                      # orange horizon
    nt.links.new(mz.outputs["Result"], ramp.inputs["Fac"])
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])


warm_world(0.9)
T0 = (0.0, 0.0, 0.0)
studio.area_light("Key", (-0.45, -0.62, 0.55), T0, size=(0.9, 0.55), power=20.0, color=(1.0, 0.93, 0.85))
studio.area_light("StripL", (-0.46, 0.18, 0.04), T0, size=(0.035, 1.2), power=12.0, color=(1.0, 0.8, 0.6))
studio.area_light("StripR", (0.46, 0.15, 0.04), T0, size=(0.035, 1.2), power=12.0, color=(1.0, 0.75, 0.55))
studio.area_light("Rim", (0.30, 0.55, 0.38), T0, size=(0.6, 0.6), power=14.0, color=(1.0, 0.62, 0.36))
studio.area_light("Fill", (0.35, -0.55, -0.30), T0, size=(0.8, 0.4), power=4.0, color=(1.0, 0.85, 0.75), visible_glossy=False)

MASK = os.path.join(HERE, "textures", "screen_mask.png")
STATES = sorted(set(b["state"] for b in EDIT["beats"] if b["kind"] == "state"))
IMG = {}


def image(k):
    if k not in IMG:
        img = bpy.data.images.load(os.path.join(TEX, f"S{k:02d}.png"), check_existing=True)
        img.colorspace_settings.name = "sRGB"
        IMG[k] = img
    return IMG[k]


TURN = bpy.data.objects.new("PhoneTurn", None)
scene.collection.objects.link(TURN)
PHONE = ip.build_iphone("deep_blue", "Ph", screen_image=os.path.join(TEX, "S00.png"), screen_mask=MASK, screen_strength=1.0)
PHONE.parent = TURN
PHONE.rotation_euler = (math.radians(90.0), 0.0, 0.0)
SCREEN = bpy.data.materials["Ph_screen"]


def set_visible(root, v):
    for ob in [root] + list(root.children_recursive):
        ob.hide_render = not v


# ---------------------------------------------------------------- evidence boxes on the final screen
def emission_mat(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1.0)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], o.inputs[0])
    return m, e


ORANGE = tuple(srgb(c) for c in (255, 122, 26))
lay = json.load(open(os.path.join(TEX, "S10.layout.json"), encoding="utf-8"))
targets = [b for b in lay["boxes"] if "ios-b--in" in b["cls"] and b["y"] > 128 and not b["text"].startswith("CrumbClub: Your")]
BOXES = []
for k, b in enumerate(targets):
    pad = 4.5
    x0, y0, w, h = b["x"] - pad, b["y"] - pad, b["w"] + 2 * pad, b["h"] + 2 * pad
    sw, sh = ip.SCREEN_W, ip.SCREEN_H
    cx, cy = ((x0 + w / 2) / 402 - 0.5) * sw, (0.5 - (y0 + h / 2) / 874) * sh
    wm, hm = w / 402 * sw, h / 874 * sh
    cu = bpy.data.curves.new(f"Box{k}", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.00032
    cu.bevel_resolution = 2
    pts = ip.outline(wm, hm, min(wm, hm) * 0.34, min(wm, hm) * 0.34)
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, (px, py) in enumerate(pts):
        sp.points[i].co = (px, py, 0.0, 1.0)
    sp.use_cyclic_u = True
    mat, emit = emission_mat(f"BoxMat{k}", ORANGE, 0.0)
    cu.materials.append(mat)
    ob = bpy.data.objects.new(f"Box{k}", cu)
    scene.collection.objects.link(ob)
    ob.parent = PHONE                                   # phone local space: +z is the screen normal
    ob.location = (cx, cy, ip.ZF + 0.0004)
    ob.visible_shadow = False
    BOXES.append((ob, emit, (y0 + h / 2) / 874))
print(f"{len(BOXES)} evidence boxes:", [t["text"][:28] for t in targets])

# ---------------------------------------------------------------- the shield (end card)
EMB = em.build_emblem(height=0.085)
EMB_TURN = bpy.data.objects.new("EmbTurn", None)
scene.collection.objects.link(EMB_TURN)
EMB.parent = EMB_TURN

# ---------------------------------------------------------------- camera: the phone big, a little low (stickers on top)
LENS = 85.0
HV = 0.150 / 0.70                                      # the phone is 70 % of the frame height
D = HV * LENS / 36.0
CAM = studio.camera("Cam", (0.0, -D, 0.0), (0.0, 0.0, 0.0), lens=LENS, fstop=8.0, focus_target=(0, 0, 0))
scene.camera = CAM
V_PHONE = 0.55                                         # phone center at 55 %: the newest text stays above the Reels UI


def camera_state(sec):
    punch = 0.0
    for b in EDIT["beats"]:                             # the shout gets a punch-in
        if b["kind"] == "state" and b.get("who") == "me" and b.get("level") == 2:
            punch = 0.10 * pulse(sec, b["at"], 0.55)
    d = D * (1 - punch)
    hv = d * 36.0 / LENS
    tz = (V_PHONE - 0.5) * hv
    CAM.location = (0.0, -d, tz + 0.004)
    studio.look_at(CAM, (0.0, 0.0, tz))
    CAM.data.dof.focus_distance = d


# ---------------------------------------------------------------- the performance
BEATS = [b for b in EDIT["beats"] if b["kind"] == "state"]
REV = EDIT["reveal"]
END = EDIT["endcard"]


def screen_at(sec):
    cur, prev, t_cur = 0, 0, 0.0
    for b in BEATS:
        if sec >= b["at"]:
            prev, cur, t_cur = cur, b["state"], b["at"]
    return prev, cur, clamp((sec - t_cur) / 0.034)       # a new message pops in (no ghosted scroll crossfade)


def performance(sec):
    """(x, y, z, pitch, roll, yaw) of the phone, in metres and degrees."""
    x = y = z = 0.0
    pitch, roll, yaw = 5.0, 0.0, -13.0
    # drop in from above, land, bounce
    if sec < 0.9:
        fall = clamp(sec / 0.5)
        z += 0.28 * (1 - fall ** 2)
        roll += -22.0 * (1 - fall) ** 2
        if sec > 0.5:
            u = (sec - 0.5) / 0.4
            z += 0.012 * math.sin(math.pi * u) * (1 - u)
            roll += 6.0 * math.sin(math.pi * u * 2) * (1 - u)
    for b in BEATS:
        a, lvl = b["at"], b.get("level", 0)
        if b.get("who") == "them":                      # an incoming text: the phone buzzes
            u = sec - a
            if 0 <= u < 0.30:
                k = (1 - u / 0.30)
                roll += 1.4 * k * math.sin(u * 2 * math.pi * 31)
                x += 0.0006 * k * math.sin(u * 2 * math.pi * 27 + 1)
                z += 0.004 * pulse(sec, a, 0.18)
        if b.get("who") == "me":                        # you send: the phone leans in, harder each time
            lean = pulse(sec, a, 0.42)
            pitch -= (2.0 + 1.2 * lvl) * lean
            y -= 0.006 * lean
            if lvl == 2:                               # "STOP!!!": a real shake
                u = sec - a
                if 0 <= u < 0.5:
                    k = 1 - u / 0.5
                    roll += 3.2 * k * math.sin(u * 2 * math.pi * 17)
                    yaw += 2.0 * k * math.sin(u * 2 * math.pi * 13 + 0.5)
    lv = {b.get("level"): b["at"] for b in BEATS if b.get("who") == "me"}
    them = {b.get("level"): b["at"] for b in BEATS if b.get("who") == "them"}
    # "Please... stop.": the phone droops until the 2 AM text perks it up (sort of)
    if 3 in lv:
        droop = win(sec, lv[3] + 0.1, lv[3] + 0.7) * (1 - win(sec, them[3], them[3] + 0.35))
        pitch += 8.0 * droop
        z -= 0.008 * droop
    # "i will throw my phone in a lake": it winds up to be thrown, rocking harder and harder
    if 4 in lv:
        u = sec - lv[4]
        wind = win(sec, lv[4], them[4] - 0.2) * (1 - win(sec, them[4] - 0.05, them[4] + 0.12))
        yaw += 13.0 * wind * math.sin(u * 2 * math.pi * 2.4) * (0.4 + 0.6 * clamp(u / 2.2))
        y += 0.03 * wind
        roll -= 4.0 * wind
        # "Did you mean START?": the confused head tilt, held through the record scratch
        tilt = win(sec, them[4] + 0.15, them[4] + 0.75)
        roll += 11.0 * tilt * (1 - win(sec, REV["spin"][0], REV["spin"][0] + 0.25))
        yaw += 6.0 * tilt * (1 - win(sec, REV["spin"][0], REV["spin"][0] + 0.25))
    # plot twist: one full spin, then it faces us square for the screenshot
    s0, s1 = REV["spin"]
    sp = smooth((sec - s0) / (s1 - s0))
    yaw += 360.0 * sp
    calm = win(sec, s0, s1)
    pitch = pitch * (1 - calm) + 2.0 * calm
    yaw = yaw - (-13.0) * calm                         # square to camera after the spin
    z += 0.015 * pulse(sec, s0, s1 - s0)
    # the end card: the phone drops out of the frame
    o0, o1 = END["phone_out"]
    out = win(sec, o0, o1)
    z -= 0.42 * out ** 1.6
    roll += 18.0 * out
    return x, y, z, pitch, roll, yaw


def jingle(sec, at):
    if sec < at:
        return 0.0, 0.0, 0.0
    u = sec - at
    d = math.exp(-1.7 * u)
    return (13.0 * d * math.sin(2 * math.pi * 2.3 * u) + 3.0 * math.sin(2 * math.pi * 0.45 * u) * min(1, u / 0.8),
            6.0 * d * math.sin(2 * math.pi * 2.3 * u + 0.9), 0.035 * math.exp(-3 * u) * abs(math.sin(2 * math.pi * 2.3 * u)))


def emblem_state(sec):
    a, b = END["shield"]
    g = clamp((sec - a) / (b - a))
    vis = sec >= a
    set_visible(EMB, vis)
    if not vis:
        return
    hv = D * 36.0 / LENS
    zc = (V_PHONE - 0.62) * hv                           # the shield at 62 % down: the end card's copy is above it
    yaw, roll, hop = jingle(sec, END["jingle"])
    EMB_TURN.location = (0.0, 0.0, zc - 0.10 * (1 - smooth(g)))
    EMB_TURN.rotation_euler = Euler((0.0, math.radians(roll), math.radians(-150 * (1 - smooth(g)) + yaw)), "XYZ")
    s = max(back_out(g) * (1 + hop), 1e-4) * 0.82
    EMB_TURN.scale = (s, s, s)


def apply(sec):
    x, y, z, pitch, roll, yaw = performance(sec)
    TURN.location = (x, y, z)
    TURN.rotation_euler = Euler((math.radians(pitch), math.radians(roll), math.radians(yaw)), "XYZ")
    set_visible(PHONE, sec < END["phone_out"][1] + 0.05)
    prev, cur, mix = screen_at(sec)
    flash = pulse(sec, REV["flash"], 0.32)
    ip.set_screen(SCREEN, image(prev), image(cur), mix=mix, flash=flash)
    for k, (ob, emit, fy) in enumerate(BOXES):          # the texts after STOP light up one by one
        t_on = REV["boxes_from"] + k * (REV["boxes_to"] - REV["boxes_from"]) / max(1, len(BOXES) - 1)
        lit = win(sec, t_on, t_on + 0.12) * (1 - win(sec, END["phone_out"][0], END["phone_out"][0] + 0.2))
        emit.inputs["Strength"].default_value = 4.5 * lit
        ob.hide_render = lit < 0.01
    emblem_state(sec)
    camera_state(sec)
    bpy.context.view_layer.update()


only = [int(v) for v in args["only"].split(",")] if args.get("only") else None
frames = only if only is not None else list(range(0, N, int(args.get("step", "1"))))
for i in frames:
    path = os.path.join(OUT, f"{i:04d}.png")
    if os.path.exists(path) and not FORCE:
        continue
    apply(i / FPS)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {i} s={i / FPS:.2f}", flush=True)
print("DONE", len(frames))
