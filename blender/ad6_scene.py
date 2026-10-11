"""Ad 6 ("Storytime"): the 3D shots of Dre in his room, rendered at their place in the ad timeline (ad6/edit.json).

blender -b --factory-startup -P ad6_scene.py -- [shots=hook,real] [only=0,50] [step=4] [samples=40] [preview=1] [force=1]
  frames -> blender/frames/ad6/<global frame>.png (the compositor picks them up by frame number)

Every frame is a pure function of time (frame_change_pre), so motion blur and any render order work. Arms are posed
with two-bone IK (a target for the wrist and a direction for the phone screen), the face with a few controls, and
the mouth follows the voice (energy + the letters being said) when Dre talks to the camera.
"""
import json
import math
import os
import sys
import time
import wave

import bpy
import mathutils
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import iphone17pro as ip  # noqa: E402
from ad6_char import Character  # noqa: E402
from ad6_room import BED_Z, Room  # noqa: E402

V = mathutils.Vector
M = mathutils.Matrix
args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
AD6 = os.path.join(HERE, "..", "ad6")
EDIT = json.load(open(os.path.join(AD6, "edit.json"), encoding="utf-8"))
EV = EDIT["events"]
FPS = EDIT["fps"]
PREVIEW = args.get("preview", "0") == "1"
OUT = os.path.join(HERE, args.get("out", "frames/ad6_preview" if PREVIEW else "frames/ad6"))
os.makedirs(OUT, exist_ok=True)
FORCE = args.get("force", "0") == "1"
T_BUILD = time.time()
VO = {v["line"]: v for v in EDIT["voice"]}

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
TEX5 = os.path.join(HERE, "textures", "ad5")


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease(x):
    x = clamp(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def back_out(x, c=1.7):
    x = clamp(x) - 1
    return 1 + (c + 1) * x ** 3 + c * x ** 2


def lerp(a, b, k):
    if isinstance(a, (tuple, list)):
        return tuple(lerp(x, y, k) for x, y in zip(a, b))
    return a + (b - a) * k


def track(keys, t, fn=ease):
    """keys: [(t, value)], eased between neighbours (values: floats or tuples)."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return lerp(v0, v1, fn((t - t0) / max(1e-6, t1 - t0)))
    return keys[-1][1]


def wobble(t, amp, seed=0.0):
    return (math.sin(t * 1.7 + seed) * 0.6 + math.sin(t * 3.1 + 1.3 * seed) * 0.4) * amp


# ============================================================================================== build
phone = ip.build_iphone("deep_blue", "Ph", screen_image=os.path.join(HERE, "textures", "ad6", "lock.png"),
                        screen_mask=os.path.join(HERE, "textures", "screen_mask.png"), screen_strength=1.0)
SCREEN = bpy.data.materials["Ph_screen"]
room = Room(os.path.join(HERE, "textures", "ad6"))
dre = Character("Dre", phone=phone)
J = dre.J
phone.location = (0.0, -0.03, -0.062)
phone.rotation_euler = (math.radians(90), math.radians(180), 0)      # screen away from the palm, top toward the fingers

kl = bpy.data.lights.new("PhoneKey", "AREA")
kl.shape = "RECTANGLE"
kl.size, kl.size_y = 0.08, 0.16
kl.color = (0.78, 0.87, 1.0)
KEY = bpy.data.objects.new("PhoneKey", kl)
scene.collection.objects.link(KEY)
KEY.parent = phone
KEY.location = (0, 0, 0.02)
KEY.rotation_euler = (math.radians(180), 0, 0)
KEY.visible_camera = False
LIGHTS = {}
for name, loc, tgt, e, col, size in [("Rim", (0.4, 1.0, 1.8), (0.0, 0.45, 1.2), 70.0, (0.6, 0.3, 1.0), 0.6),
                                     ("RimR", (-0.6, 0.95, 1.6), (0.0, 0.45, 1.2), 30.0, (1.0, 0.35, 0.7), 0.5),
                                     ("Fill", (-0.9, -0.6, 1.5), (0.0, 0.45, 1.2), 3.0, (0.45, 0.55, 1.0), 1.0)]:
    ld = bpy.data.lights.new(name, "AREA")
    ld.size = size
    ld.energy = e
    ld.color = col
    lo = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(lo)
    lo.location = loc
    lo.rotation_euler = (V(tgt) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    lo.visible_camera = False
    lo["base"] = e
    LIGHTS[name] = lo
for lo in room.leds:
    lo["base"] = lo.data.energy
w = bpy.data.worlds.new("Night")
scene.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.004, 0.009, 1)

CAM = bpy.data.cameras.new("Cam")
CO = bpy.data.objects.new("Cam", CAM)
scene.collection.objects.link(CO)
scene.camera = CO
CAM.sensor_fit = "AUTO"
CAM.dof.use_dof = True
CAM.clip_start = 0.01

FACEFILL = bpy.data.lights.new("FaceFill", "AREA")
FACEFILL.size = 0.9
FACEFILL.energy = float(args.get("facefill", "9"))
FACEFILL.color = (1.0, 0.9, 0.82)
FF = bpy.data.objects.new("FaceFill", FACEFILL)
scene.collection.objects.link(FF)
FF.parent = CO
FF.location = (0.25, 0.3, 0.05)
FF.visible_camera = False
FF.visible_glossy = False

IMG = {}


def image(path):
    if path not in IMG:
        IMG[path] = bpy.data.images.load(path, check_existing=True)
    return IMG[path]


TEX6 = os.path.join(HERE, "textures", "ad6")
SCREENS = {"thread": os.path.join(TEX6, "thread.png"), "lock": os.path.join(TEX6, "lock.png"),
           "web": os.path.join(TEX6, "web.png")}

# ============================================================================================== rig helpers
A_UP, A_FORE = 0.205, 0.185 + 0.045         # upper arm; forearm + the hand to the grip point


def ik_arm(side, target, hint, palm_n=None, fingers=None):
    """Two-bone IK in spine space. target: where the hand grips (spine space), hint: where the elbow points.
    palm_n / fingers: directions for the hand (palm normal outward, finger direction). Sets the joint rotations."""
    S = V(J[f"shoulder.{side}"].location)
    T = V(target)
    a, b = A_UP, A_FORE
    d = min((T - S).length, a + b - 1e-4)
    dT = (T - S).normalized()
    cos_a = clamp((a * a + d * d - b * b) / (2 * a * d), -1, 1)
    alpha = math.acos(cos_a)
    h = V(hint)
    hp = (h - dT * h.dot(dT))
    hp = hp.normalized() if hp.length > 1e-6 else V((0, 0, -1))
    u = (dT * math.cos(alpha) + hp * math.sin(alpha)).normalized()      # upper arm direction
    E = S + u * a
    wv = (S + dT * d - E).normalized()                                  # forearm direction
    cos_b = clamp(u.dot(wv), -1, 1)
    beta = math.acos(cos_b)                                             # bend angle
    col_z = -u
    perp = wv - u * wv.dot(u)
    col_y = -(perp.normalized() if perp.length > 1e-6 else V((0, 1, 0)))
    col_x = col_y.cross(col_z)
    Rs = M((col_x, col_y, col_z)).transposed()
    J[f"shoulder.{side}"].rotation_euler = Rs.to_euler("XYZ")
    J[f"elbow.{side}"].rotation_euler = (-beta, 0, 0)
    if palm_n is not None and fingers is not None:
        Rf = Rs @ M.Rotation(-beta, 3, "X")
        fz = -V(fingers).normalized()
        fy = -(V(palm_n) - V(fingers).normalized() * V(palm_n).dot(V(fingers).normalized())).normalized()
        fx = fy.cross(fz)
        Rh = M((fx, fy, fz)).transposed()
        J[f"wrist.{side}"].rotation_euler = (Rf.transposed() @ Rh).to_euler("XYZ")


def spine_point(world):
    """World point -> spine space (for IK targets defined in the world)."""
    bpy.context.view_layer.update()
    return J["spine"].matrix_world.inverted() @ V(world)


def aim_head(target_world, amount=1.0, extra=(0, 0, 0)):
    """Turn neck+head toward a world point (split between them), plus extra degrees."""
    bpy.context.view_layer.update()
    hw = dre.head_world()
    d = (V(target_world) - hw)
    sp = J["spine"].matrix_world.to_3x3().inverted() @ d
    yaw = math.degrees(math.atan2(sp.x, -sp.y)) * amount
    pitch = math.degrees(math.atan2(sp.z, math.hypot(sp.x, sp.y))) * amount
    J["neck"].rotation_euler = tuple(math.radians(v) for v in (-pitch * 0.4 + extra[0] * 0.5, 0, yaw * 0.4))
    J["head"].rotation_euler = tuple(math.radians(v) for v in (-pitch * 0.6 + extra[0] * 0.5, extra[1], yaw * 0.6 + extra[2]))


# ============================================================================================== lip sync
ENV = {}


def envelope(line):
    if line not in ENV:
        with wave.open(os.path.join(AD6, "audio", "fast", f"{line}.wav")) as wf:
            x = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768
            sr = wf.getframerate()
        h = sr // 100
        n = len(x) // h
        r = np.sqrt((x[: n * h].reshape(n, h) ** 2).mean(axis=1))
        r = r / (np.percentile(r, 92) + 1e-9)
        out, y = np.zeros_like(r), 0.0
        for i, v in enumerate(r):                    # attack 25 ms, release 70 ms
            c = 0.33 if v > y else 0.13
            y += (v - y) * c
            out[i] = y
        ENV[line] = out
    return ENV[line]


ROUND, WIDE, CLOSE = set("ouwq"), set("eiy"), set("mbp")


def mouth_for(t, lines, base=None):
    """Mouth from the voice: open by energy, round/wide by the letter being said, shut on m/b/p."""
    base = dict(base or {"open": 0.0, "wide": 1.0, "smile": 0.2, "round": 0.0})
    for line in lines:
        at = VO[line]["at"]
        if not (at - 0.05 <= t <= at + VO[line]["dur"] + 0.05):
            continue
        env = envelope(line)
        i = int((t - at) * 100)
        e = float(env[i]) if 0 <= i < len(env) else 0.0
        op = clamp((e - 0.12) / 0.75) ** 0.85 * 0.8
        ch = [c for c in EDIT["chars"][line] if c[1] - 0.02 <= t <= c[2] + 0.02 and c[0].isalpha()]
        rnd, wd = 0.0, 1.0
        if ch:
            c = ch[0][0].lower()
            if c in ROUND:
                rnd, wd = 0.65, 0.85
            elif c in WIDE:
                wd = 1.12
            elif c in CLOSE:
                op *= 0.2
        base["open"] = max(base.get("open", 0.0), op)
        base["round"] = max(base.get("round", 0.0), rnd * min(1.0, op * 2.5))
        base["wide"] = base.get("wide", 1.0) * (wd if op > 0.1 else 1.0)
    return base


def blinks(t, times):
    v = 0.0
    for b in times:
        u = (t - b) / 0.16
        if 0 <= u <= 1:
            v = max(v, math.sin(math.pi * u))
    return v


# ============================================================================================== shots
SIT = (0.0, 0.42, BED_Z + 0.035)
LIE = (0.0, 0.28, BED_Z + 0.115)


def eyes_world():
    bpy.context.view_layer.update()
    return dre.eye_world()


def set_camera(loc, target, lens, fstop, focus=None, shake=0.0, t=0.0):
    loc = V(loc) + V((wobble(t, shake, 0.3), wobble(t, shake * 0.6, 1.9), wobble(t, shake * 0.8, 3.7)))
    target = V(target) + V((wobble(t + 4, shake * 0.5, 2.2), 0, wobble(t + 4, shake * 0.5, 0.7)))
    CO.location = loc
    CO.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    CAM.lens = lens
    CAM.dof.aperture_fstop = fstop
    f = V(focus) if focus is not None else eyes_world()
    CAM.dof.focus_distance = max(0.05, (f - loc).length)


KEY_MULT = float(args.get("keymult", "0.34"))   # the screen faces his face now: its light is close, keep it a glow


def lights(key=2.2, rim=1.0, led=1.0, led_col=(0.55, 0.22, 1.0), rim_col=None):
    KEY.data.energy = key * KEY_MULT
    for nm in ("Rim", "RimR"):
        LIGHTS[nm].data.energy = LIGHTS[nm]["base"] * rim
    if rim_col is not None:
        LIGHTS["Rim"].data.color = rim_col
    for lo in room.leds:
        lo.data.energy = lo["base"] * led
        lo.data.color = led_col
    room.led_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (*led_col, 1)
    room.led_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 30.0 * led


def screen(name, strength=1.0):
    ip.set_screen(SCREEN, image(SCREENS[name]), image(SCREENS[name]), mix=0.0, flash=0.0, strength=strength)


def phone_in_front(t, dist=0.3, drop=0.1, side_off=-0.02, tilt=0.0, buzz=0.0):
    """Right hand holds the phone in front of his face, screen toward his eyes."""
    bpy.context.view_layer.update()
    eye = dre.eye_world()
    sp_eye = J["spine"].matrix_world.inverted() @ eye
    tgt = sp_eye + V((side_off, -dist, -drop))
    tgt += V((buzz * 0.003 * math.sin(t * 2 * math.pi * 40), 0, buzz * 0.002 * math.sin(t * 2 * math.pi * 33)))
    to_eye = (sp_eye - tgt).normalized()
    up = V((0, 0.25 + tilt, 1.0)).normalized()
    fingers = (up - to_eye * up.dot(to_eye)).normalized()
    # the palm faces his eyes and the phone lies in it, screen toward him (the back of the phone toward us)
    ik_arm("R", tgt, hint=(-0.6, 0.3, -0.75), palm_n=to_eye, fingers=fingers)


def left_rest(lap=True):
    ik_arm("L", (0.14, -0.2, 0.12) if lap else (0.2, -0.05, 0.1), hint=(0.8, 0.2, -0.6), palm_n=(0.0, 0.2, -1.0), fingers=(-0.3, -1.0, 0.0))


def shot_hook(t):
    """0 .. V2: lying in bed scrolling, the text lands, he bolts upright and stares; EACH: he looks up at us."""
    up = EV["boltup"]
    k = back_out((t - up) / 0.36, 1.2) if t > up else 0.0
    kk = clamp(k, 0, 1.15)
    lie = 1 - kk
    root_rot = (-88 * lie + (-4 * (1 - smooth((t - up - 0.25) / 0.5)) if t > up else 0), 0, 0)
    loc = lerp(LIE, SIT, clamp(kk))
    dre.pose({"root_loc": loc, "root_rot": root_rot, "spine": (-4 * lie, 0, 0)})
    room.set_duvet(lerp(LIE[1], SIT[1], clamp(kk)), lie=clamp(lie), knees=0.25 * clamp(kk))
    # head: lying it rests on the pillow, chin a little down; after the bolt he stares at the phone
    J["neck"].rotation_euler = (math.radians(lerp(22, 8, clamp(kk))), 0, 0)
    J["head"].rotation_euler = (math.radians(lerp(10, 4, clamp(kk))), 0, 0)
    buzz = 1.0 if any(0 <= t - b < 0.4 for b in EV["buzz"]) else 0.0
    phone_in_front(t, dist=lerp(0.3, 0.3, clamp(kk)), drop=lerp(0.04, 0.12, clamp(kk)), side_off=lerp(-0.13, -0.03, clamp(kk)), buzz=buzz)
    left_rest(lap=kk > 0.5)
    look_up = smooth((t - EV["each"] + 0.12) / 0.14)
    bl = blinks(t, [0.6])
    wide = smooth((t - up + 0.05) / 0.12)
    face = dict(blink=lerp(0.32 * (1 - smooth((t - 1.2) / 0.3)), -0.9, wide) + bl,
                look=(lerp(0.0, 0.0, look_up), lerp(-0.45, 0.05, look_up)),
                brow=(lerp(0.15, 0.95, wide), lerp(0.15, 0.95, wide)), brow_tilt=(0.25 * wide, 0.25 * wide),
                mouth=dict(open=lerp(0.0, 0.75, wide) + 0.15 * look_up, wide=lerp(1.0, 0.82, wide), smile=lerp(0.1, -0.1, wide),
                           round=0.6 * wide))
    dre.face(**face)
    if look_up > 0:
        aim_head(CO.location, 0.5 * look_up, extra=(4 * (1 - look_up), 0, 0))
    screen("lock", 1.0)
    lights(key=lerp(1.6, 2.4, clamp(kk)), rim=lerp(0.35, 1.0, clamp(kk)))   # lying: the rim would rake across his hair
    hair_look(clamp(kk))
    # camera: high over the bed looking down at him lying, then it drops to the front as he bolts up; punch-in on EACH
    c_hi = ((0.06, 0.4, 1.58), (0.0, 0.98, 0.8), 36)
    c_lo = ((0.14, -0.78, 1.28), (0.0, 0.42, 1.14), 45)
    m = ease((t - up + 0.06) / 0.62)
    pin = back_out((t - EV["each"]) / 0.22, 1.4) if t > EV["each"] else 0.0
    loc = lerp(c_hi[0], c_lo[0], m)
    tgt = lerp(c_hi[1], c_lo[1], m)
    loc = lerp(loc, (0.06, -0.12, 1.24), 0.22 * pin)
    tgt = lerp(tgt, (0.0, 0.42, 1.2), 0.5 * pin)
    set_camera(loc, tgt, lerp(c_hi[2], c_lo[2], m), 2.4, shake=0.004 + 0.01 * (1 - smooth((t - up - 0.2) / 0.4)) * (t > up), t=t)


HAIR = bpy.data.materials["Dre_hair"].node_tree.nodes["Principled BSDF"]
HAIR_BUMP = [n for n in bpy.data.materials["Dre_hair"].node_tree.nodes if n.type == "BUMP"][0]
HAIR_REST = {k: HAIR.inputs[k].default_value for k in ("Specular IOR Level", "Sheen Weight", "Roughness")}


def hair_look(k):
    """Seen from above (lying in bed) the curls catch the purple room light like foil: matte them down there.
    k = 1 is the normal look (every other shot)."""
    HAIR.inputs["Specular IOR Level"].default_value = lerp(0.18, HAIR_REST["Specular IOR Level"], k)
    HAIR.inputs["Sheen Weight"].default_value = lerp(0.15, HAIR_REST["Sheen Weight"], k)
    HAIR.inputs["Roughness"].default_value = lerp(0.7, HAIR_REST["Roughness"], k)
    HAIR_BUMP.inputs["Strength"].default_value = lerp(0.45, 0.8, k)


def shot_annoyed(t):
    """The phone keeps buzzing in his hand; he stares at us, unimpressed."""
    hair_look(1.0)
    t0 = EV["annoyed"]
    dre.pose({"root_loc": SIT, "root_rot": (0, 0, 0), "spine": (-6, 0, 0)})
    room.set_duvet(SIT[1], lie=0.0, knees=0.25)
    buzz = 1.0 if (t - t0) % 0.55 < 0.35 else 0.0
    phone_in_front(t, dist=0.24, drop=0.24, side_off=-0.04, buzz=buzz)
    left_rest()
    aim_head(CO.location, 0.8)
    dre.face(blink=0.42, look=(0.0, 0.0), brow=(-0.25, -0.25), brow_tilt=(-0.15, -0.15),
             mouth=dict(open=0.0, wide=0.92, smile=-0.45))
    screen("thread", 1.0)
    lights(key=1.6)
    k = smooth((t - t0) / 1.0)
    set_camera(lerp((0.1, -0.82, 1.25), (0.08, -0.72, 1.25), k), (0.0, 0.42, 1.15), 45, 2.2, shake=0.003, t=t)


def shot_twoam(t):
    """2 AM: hunched over the phone in the dark, typing; face lit by the screen."""
    hair_look(1.0)
    t0 = EV["twoam"]
    dre.pose({"root_loc": SIT, "root_rot": (0, 0, 0), "spine": (14, 0, 0)})
    room.set_duvet(SIT[1], lie=0.0, knees=0.55)
    phone_in_front(t, dist=0.22, drop=0.16, side_off=-0.01, tilt=0.4)
    left_rest()
    J["neck"].rotation_euler = (math.radians(14), 0, 0)
    J["head"].rotation_euler = (math.radians(12), 0, math.radians(-4))
    J["thumb.R"].rotation_euler = (math.radians(18 * abs(math.sin(t * 2 * math.pi * 3.2))), 0, 0)
    dre.face(blink=0.2 + blinks(t, [t0 + 0.9]), look=(-0.1, -0.55), brow=(-0.1, 0.25), brow_tilt=(0.25, 0.1), squint=0.15,
             mouth=dict(open=0.05, wide=0.9, smile=-0.1))
    screen("thread", 1.15)
    lights(key=2.1, rim=0.55, led=0.45)
    k = ease((t - t0) / 1.8)
    set_camera(lerp((-0.46, -0.82, 1.16), (-0.4, -0.72, 1.17), k), (0.0, 0.3, 1.12), 45, 2.0, shake=0.003, t=t)


def shot_shock(t):
    """After the $500: he recoils, eyes huge, mouth open; a crash zoom."""
    hair_look(1.0)
    t0 = EV["shock"]
    k = back_out((t - t0) / 0.25, 1.6)
    dre.pose({"root_loc": SIT, "root_rot": (0, 0, 0), "spine": (-6 - 8 * clamp(k), 0, 0)})
    room.set_duvet(SIT[1], lie=0.0, knees=0.25)
    phone_in_front(t, dist=0.3, drop=0.16, side_off=-0.06)
    left_rest()
    aim_head(CO.location, 0.9, extra=(-8 * clamp(k), 0, 0))
    dre.face(blink=-1.0, look=(0.0, 0.05), brow=(1.0, 1.0), brow_tilt=(0.35, 0.35),
             mouth=dict(open=0.95, wide=0.78, round=0.75, smile=-0.15))
    screen("thread", 1.0)
    lights(key=2.4, rim=1.2, led=1.2)
    z = back_out((t - t0) / 0.2, 1.2)
    set_camera(lerp((0.05, -1.0, 1.26), (0.03, -0.42, 1.25), clamp(z, 0, 1.05)), (0.0, 0.42, 1.2), 45, 2.4, shake=0.006, t=t)


def shot_skeptic(t):
    """To camera: 'Obviously, I thought it was a scam.' (sarcastic), then a laugh: 'So did the group chat.'"""
    hair_look(1.0)
    t0 = EV["skeptic"]
    scam = EV["scam"]
    laugh = smooth((t - scam - 0.35) / 0.25)
    tilt = math.sin(clamp((t - t0) / 1.6) * math.pi) * 6
    dre.pose({"root_loc": SIT, "root_rot": (0, 0, 0), "spine": (-4, 0, 2 * laugh)})
    room.set_duvet(SIT[1], lie=0.0, knees=0.25)
    phone_in_front(t, dist=0.25, drop=0.3, side_off=-0.08)
    left_rest()
    aim_head(CO.location, 0.85, extra=(-3 * laugh, tilt * (1 - laugh), 4 * laugh * math.sin(t * 14)))
    m = mouth_for(t, ["V5"], {"open": 0.0, "wide": 1.0, "smile": lerp(-0.25, 0.9, laugh), "round": 0.0})
    dre.face(blink=lerp(0.28, 0.0, laugh) + blinks(t, [t0 + 1.3]), look=(lerp(-0.25, 0.0, smooth((t - t0 - 0.6) / 0.3)), 0.0),
             brow=(lerp(0.85, 0.4, laugh), lerp(-0.3, 0.4, laugh)), brow_tilt=(0.0, lerp(-0.35, 0.0, laugh)),
             squint=0.45 * laugh, mouth=m)
    screen("thread", 0.9)
    lights(key=1.8)
    set_camera((0.1, -0.8, 1.26), (0.0, 0.42, 1.16), 45, 2.2, shake=0.004, t=t)


def shot_real(t):
    """'It's a hundred percent real. A hundred percent legal. For real, for real.' Confident, punches on the beats."""
    hair_look(1.0)
    t0 = EV["real3d"]
    beats = [EV["real"], EV["legal"], EV["frfr"] + 0.13, EV["frfr"] + 0.5]
    lean = smooth((t - t0) / 0.4)
    dre.pose({"root_loc": SIT, "root_rot": (0, 0, 0), "spine": (6 * lean, 0, 0)})
    room.set_duvet(SIT[1], lie=0.0, knees=0.25)
    phone_in_front(t, dist=0.18, drop=0.42, side_off=-0.12)
    # left hand: an open palm toward us on "legal", two chops on "for real, for real"
    chop = 0.0
    for b in beats[2:]:
        u = (t - b + 0.12) / 0.3
        if 0 <= u <= 1:
            chop = max(chop, math.sin(math.pi * u))
    g = smooth((t - EV["legal"] + 0.35) / 0.25)
    hand = lerp((0.14, -0.2, 0.12), (0.12, -0.42, 0.34 - 0.08 * chop), g)
    ik_arm("L", hand, hint=(0.9, 0.3, -0.5), palm_n=lerp((0.0, 0.2, -1.0), (0.0, -1.0, 0.25), g), fingers=lerp((-0.3, -1.0, 0.0), (0.0, 0.1, 1.0), g))
    nod = sum(math.sin(math.pi * clamp((t - b + 0.05) / 0.22)) for b in beats)
    aim_head(CO.location, 0.9, extra=(6 * nod, 0, 0))
    m = mouth_for(t, ["V6"], {"open": 0.0, "wide": 1.02, "smile": 0.55, "round": 0.0})
    dre.face(blink=blinks(t, [t0 + 1.25]), look=(0.0, 0.0), brow=(0.35 + 0.3 * min(1.0, nod), 0.35 + 0.3 * min(1.0, nod)),
             squint=0.15, mouth=m)
    screen("thread", 0.8)
    pulse = max([0.0] + [math.exp(-max(0.0, t - b) / 0.18) * (t >= b - 0.02) for b in beats])
    lights(key=1.7, rim=1.0 + 0.6 * pulse, led=1.0 + 1.6 * pulse, led_col=lerp((0.55, 0.22, 1.0), (1.0, 0.25, 0.62), min(1.0, pulse * 1.3)))
    pin = sum(0.05 * back_out(clamp((t - b) / 0.16), 1.5) for b in beats)
    loc = lerp((0.12, -0.98, 1.22), (0.08, -0.84, 1.23), smooth((t - t0) / 3.0))
    loc = V(loc) + V((0, pin, 0))
    set_camera(loc, (0.0, 0.42, 1.1), 42, 2.4, shake=0.004, t=t)


def shot_close(t):
    """'They ignored your STOP. The law didn't.' A knowing smile; then he lies back as the end card comes in."""
    hair_look(1.0)
    t0 = EV["close"]
    back = ease((t - EV["end"] - 0.15) / 1.1)
    dre.pose({"root_loc": lerp(SIT, LIE, back * 0.35), "root_rot": (-30 * back, 0, 0), "spine": (-4, 0, 0)})
    room.set_duvet(lerp(SIT[1], LIE[1], back * 0.35), lie=0.3 * back, knees=0.25)
    phone_in_front(t, dist=0.26, drop=0.36, side_off=-0.06)
    left_rest()
    aim_head(CO.location, 0.85 * (1 - 0.5 * back), extra=(-4, 0, 0))
    m = mouth_for(t, ["V9"], {"open": 0.0, "wide": 1.05, "smile": lerp(0.35, 0.95, smooth((t - EV["law"] + 0.2) / 0.4)), "round": 0.0})
    dre.face(blink=blinks(t, [t0 + 0.6, EV["end"] + 0.5]), look=(0.0, 0.0), brow=(0.2, 0.45), brow_tilt=(0.0, -0.1),
             squint=0.3 * smooth((t - EV["law"]) / 0.4), mouth=m)
    screen("web", 0.9)
    warm = smooth((t - EV["end"]) / 0.8)
    lights(key=1.8, rim=1.0, led=1.0 + 0.3 * warm, led_col=lerp((0.55, 0.22, 1.0), (1.0, 0.45, 0.6), warm))
    k = smooth((t - t0) / 2.6)
    loc = lerp((0.1, -0.86, 1.25), (0.07, -0.76, 1.25), k)
    loc = lerp(loc, (0.25, -1.35, 1.62), ease((t - EV["end"]) / 1.6))
    set_camera(loc, (0.0, 0.42, 1.12), 45, 2.6, shake=0.003, t=t)


SHOT_FN = {"hook": shot_hook, "annoyed": shot_annoyed, "twoam": shot_twoam, "shock": shot_shock,
           "skeptic": shot_skeptic, "real": shot_real, "close": shot_close}
SHOT_AT = {s["name"]: (s["start"], s["end"]) for s in EDIT["shots3d"]}


def shot_at(t):
    for name, (a, b) in SHOT_AT.items():
        if a - 1e-6 <= t < b + 1e-6:
            return name
    return None


CURRENT = {"shot": None}


def apply(t):
    name = CURRENT["shot"] or shot_at(t)
    if name:
        SHOT_FN[name](t)          # pass 1 places the camera; pass 2 aims the head at it and focuses on the eyes
        SHOT_FN[name](t)


def on_frame(sc, depsgraph=None):
    apply((sc.frame_current + sc.frame_subframe) / FPS)


bpy.app.handlers.frame_change_pre.clear()
bpy.app.handlers.frame_change_pre.append(on_frame)

# ============================================================================================== render
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "CUDA"
prefs.get_devices()
for dv in prefs.devices:
    dv.use = dv.type != "CPU"
scene.cycles.device = "GPU"
scene.cycles.use_denoising = True
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.samples = int(args.get("samples", "12" if PREVIEW else "40"))
scene.cycles.max_bounces = 8
scene.cycles.transmission_bounces = 8
scene.cycles.sample_clamp_indirect = 8.0
scene.cycles.blur_glossy = 0.5
scene.render.use_persistent_data = True
scene.render.resolution_x, scene.render.resolution_y = (270, 480) if PREVIEW else (1080, 1920)
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Base Contrast"
scene.view_settings.exposure = float(args.get("exposure", "0.62"))
scene.render.use_motion_blur = not PREVIEW
scene.render.motion_blur_shutter = float(args.get("shutter", "0.22"))
scene.frame_start, scene.frame_end = 0, EDIT["frames"] - 1
print(f"BUILD {time.time() - T_BUILD:.1f}s")

shots = args.get("shots", ",".join(SHOT_AT)).split(",")
frames = []
for s in shots:
    a, b = SHOT_AT[s]
    fr = list(range(int(round(a * FPS)), int(round(b * FPS))))
    if args.get("step"):
        fr = fr[:: int(args["step"])]
    frames += [(s, f) for f in fr]
if args.get("only"):
    want = {int(v) for v in args["only"].split(",")}
    frames = [(s, f) for s, f in frames if f in want]
for s, f in frames:
    path = os.path.join(OUT, f"{f:04d}.png")
    if os.path.exists(path) and not FORCE:
        continue
    CURRENT["shot"] = s
    scene.frame_set(f)
    scene.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {s} {f} t={f / FPS:.2f} {time.time() - t0:.1f}s", flush=True)
print("DONE", len(frames))
