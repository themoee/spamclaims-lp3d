"""Ad 4 ("The Swarm"): the whole Blender scene, one continuous camera move, rendered with Cycles at 24 fps.

blender -b --factory-startup -P ad4_scene.py -- [preview=1] [samples=N] [only=0,120] [step=12] [out=frames/ad4] [force=1]

Timeline: ad4/edit.json (ad4/edit4.py). Every moving thing is a pure function of time, set by a frame-change handler
(so frames render in any order, and Cycles motion blur sees sub-frames).
"""
import json
import math
import os
import random
import sys
import time

import bpy
import mathutils
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ad4_city as city  # noqa: E402
import ad4_common as cm  # noqa: E402
import ad4_room as room  # noqa: E402
import ad4_swarm as sw  # noqa: E402
import iphone17pro as ip  # noqa: E402

args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
EDIT = json.load(open(os.path.join(HERE, "..", "ad4", "edit.json"), encoding="utf-8"))
EV = EDIT["events"]
FPS, NF = EDIT["fps"], EDIT["frames"]
PREVIEW = args.get("preview", "0") == "1"
RES = (270, 480) if PREVIEW else (1080, 1920)
OUT = os.path.join(HERE, args.get("out", "frames/ad4_preview" if PREVIEW else "frames/ad4"))
FORCE = args.get("force", "0") == "1"
TEX = os.path.join(HERE, "textures")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(44)
T_BUILD = time.time()

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS

# ============================================================================================== the city
HERO = (0.0, 0.0)
blds, tops, roofs, nb = city.build_buildings(hero=HERO, wave_t0=EV["city"], keep_clear=[(0, 0, 64)])
cm.link(blds)
FACADE = city.facade_material()
blds.data.materials.append(FACADE)
props = cm.link(city.merge_props("RoofGear", roofs, tops))
beac = cm.link(city.beacons("Beacons", tops))
cm.link(city.ground())
cm.link(city.river())
LINES = city.street_lines()
bridge, _ = city.bridges("Bridges", LINES)
cm.link(bridge)
lights, _ = city.street_lights("StreetLights", LINES)
cm.link(lights)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.7)
lamp_dot = bpy.context.object
lamp_dot.name = "LampDot"
lamp_dot.data.materials.append(cm.emission_material("Sodium", (1.0, 0.58, 0.26), 60.0))
lamp_dot.hide_render = True
cm.instance_on_points(lights, lamp_dot)
lights.visible_diffuse = lights.visible_shadow = False
TR = city.traffic_points(LINES)
cars = cm.link(cm.point_cloud("Traffic", len(TR["idx"]), {"dir": "FLOAT", "rot": "FLOAT_VECTOR"}))
bpy.ops.mesh.primitive_cube_add(size=1)
car = bpy.context.object
car.name = "CarLight"
car.scale = (3.2, 1.2, 0.6)
bpy.ops.object.transform_apply(scale=True)
cmat = bpy.data.materials.new("CarLights")
cmat.use_nodes = True
_nt = cmat.node_tree
_nt.nodes.clear()
_o = _nt.nodes.new("ShaderNodeOutputMaterial")
_e = _nt.nodes.new("ShaderNodeEmission")
_a = _nt.nodes.new("ShaderNodeAttribute"); _a.attribute_type = "INSTANCER"; _a.attribute_name = "dir"
_mr = _nt.nodes.new("ShaderNodeMapRange"); _mr.inputs["From Min"].default_value = -1; _mr.inputs["From Max"].default_value = 1
_mx = _nt.nodes.new("ShaderNodeMix"); _mx.data_type = "RGBA"
_nt.links.new(_a.outputs["Fac"], _mr.inputs["Value"]); _nt.links.new(_mr.outputs[0], _mx.inputs[0])
_mx.inputs[6].default_value = (1.0, 0.06, 0.03, 1); _mx.inputs[7].default_value = (1.0, 0.92, 0.8, 1)
_nt.links.new(_mx.outputs[2], _e.inputs["Color"]); _e.inputs["Strength"].default_value = 40
_nt.links.new(_e.outputs[0], _o.inputs["Surface"])
car.data.materials.append(cmat)
car.hide_render = True
cm.instance_on_points(cars, car, rot_attr="rot")
cars.visible_diffuse = cars.visible_shadow = False
_L = TR["L"][TR["idx"]]
CAR_ROT = np.column_stack([np.zeros(len(_L)), np.zeros(len(_L)), (np.abs(_L[:, 2] - _L[:, 0]) < 1).astype(float) * math.pi / 2])
hills = cm.link(city.hills())
city.night_world(scene, 1.0)
# moonlight: a cool, low key light so the blocks have form
sun = bpy.data.lights.new("Moon", "SUN")
sun.energy = 0.035
sun.color = (0.62, 0.72, 1.0)
sun.angle = math.radians(1.0)
moon = cm.link(bpy.data.objects.new("Moon", sun))
moon.rotation_euler = (math.radians(58), 0, math.radians(-35))

# ============================================================================================== hero tower + room
glass = room.mat("WindowGlass", (0.85, 0.9, 0.95), rough=0.015, transmission=1.0, ior=1.45)
tower = room.build_tower(FACADE, glass, room.interiors_material())
apt = room.build_room()
PHONE = ip.build_iphone("silver", "Ph", screen_image=os.path.join(TEX, "lock_5.png"),
                        screen_mask=os.path.join(TEX, "screen_mask.png"), screen_strength=1.15)
PHONE.location = room.PHONE_AT
PHONE.rotation_euler = (0, 0, math.radians(-11))
SCREEN = bpy.data.materials["Ph_screen"]
IMG = {}


def image(name):
    if name not in IMG:
        IMG[name] = bpy.data.images.load(os.path.join(TEX, name + ".png"), check_existing=True)
    return IMG[name]


# fog on every city material (not the emitter dots, not the room)
for ob in [blds, props, bridge, hills] + [o for o in bpy.data.objects if o.name in ("CityGround", "River", "HeroTowerBody")]:
    for m in ob.data.materials:
        if m and not m.get("fogged"):
            city.add_fog(m, density=0.00045 if ob is hills else 0.00028, max_fog=0.55 if ob is hills else 0.88)
            m["fogged"] = True

# ============================================================================================== bubbles
BUB = sw.bubble_mesh("BubbleMesh")
BUB.hide_render = True
BUB.data.materials.append(sw.atlas_material("BubbleAtlas"))
STOPB = sw.bubble_mesh("StopBubble", tail_side=+1)
STOPB.data.materials.append(sw.atlas_material("StopMat", os.path.join(TEX, "ad4", "stop.png"), single=True))
STOPB.hide_render = True


def system(name, n):
    ob = cm.link(cm.point_cloud(name, n, {"tile": "FLOAT", "glow": "FLOAT", "orange": "FLOAT", "rot": "FLOAT_VECTOR", "scl": "FLOAT_VECTOR"}))
    cm.instance_on_points(ob, BUB, rot_attr="rot", scale_attr="scl")
    return ob


SKY_N, ROOM_A, ROOM_B, LAN_N = 9000, 2000, 2500, 4000
SKY = system("SkySwarm", SKY_N)
ROOMS = system("RoomSwarm", ROOM_A + ROOM_B)
LANT = system("Lanterns", LAN_N)
TILES_SKY = rng.integers(0, 48, SKY_N).astype(np.float32)
TILES_ROOM = rng.integers(0, 48, ROOM_A + ROOM_B).astype(np.float32)
TILES_LAN = rng.integers(0, 48, LAN_N).astype(np.float32)

# ============================================================================================== camera
CAM = bpy.data.cameras.new("Cam")
CAMO = cm.link(bpy.data.objects.new("Cam", CAM))
scene.camera = CAMO
CAM.clip_start, CAM.clip_end = 0.01, 40000
CAM.sensor_fit = "AUTO"
PH = np.array(room.PHONE_AT)
KEYS = [  # (t, position, target, lens)
    (0.00, (-980, -2050, 560), (-110, -240, 300), 22),
    (2.80, (-700, -1520, 470), (-60, -120, 300), 23),
    (3.75, (-520, -1180, 405), (-380, -820, 620), 23),
    (4.60, (-300, -760, 285), (0, -40, 118), 25),
    (5.55, (-55, -125, 119), (0, -12.5, 96.8), 28),
    (6.10, (-0.85, -13.6, 96.85), (-0.3, -9.6, 96.2), 30),
    (6.90, (0.06, -10.08, 96.14), (0.04, -9.33, 95.78), 32),
    (7.85, (0.33, -10.25, 96.22), (0.04, -9.33, 95.84), 30),
    (EV["freeze"], None, None, 30),                       # the orbit (computed) from here ...
    (EV["shatter"], None, None, 30),                      # ... to here
    (11.40, (-0.95, -7.8, 97.75), (0.0, -9.5, 95.55), 26),
    (12.55, (-0.75, -11.25, 96.85), (-0.2, -9.1, 95.5), 26),
    (13.40, (-0.7, -19.0, 97.9), (-0.2, -7.0, 96.4), 24),
    (15.50, (-45, -270, 190), (10, 80, 150), 22),
    (19.80, (-210, -930, 430), (40, 260, 700), 22),
    (EDIT["duration"], (-185, -880, 410), (40, 260, 715), 22),
]
ORB_R, ORB_Z, ORB_A0, ORB_A1 = 0.66, 96.06, math.radians(-71), math.radians(-172)


def orbit(t):
    k = cm.smooth((t - EV["freeze"]) / (EV["shatter"] - EV["freeze"]))
    a = ORB_A0 + (ORB_A1 - ORB_A0) * k
    return np.array([PH[0] + ORB_R * math.cos(a), PH[1] + ORB_R * math.sin(a), ORB_Z]), PH + np.array([0, 0, 0.02])


for i, k in enumerate(KEYS):
    if k[1] is None:
        p, tg = orbit(k[0])
        KEYS[i] = (k[0], tuple(p), tuple(tg), k[3])
KT = np.array([k[0] for k in KEYS])
KP = np.array([k[1] for k in KEYS], dtype=float)
KG = np.array([k[2] for k in KEYS], dtype=float)
KL = np.array([k[3] for k in KEYS], dtype=float)


def pchip(t, x, y):
    """Monotone cubic (Fritsch-Carlson): no overshoot when the camera brakes from 200 m/s to a desk."""
    n = len(x)
    h = np.diff(x)
    d = np.diff(y) / h
    m = np.zeros(n)
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0], m[-1] = d[0], d[-1]
    i = int(np.clip(np.searchsorted(x, t) - 1, 0, n - 2))
    s = (t - x[i]) / h[i]
    h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    return h00 * y[i] + h10 * h[i] * m[i] + h01 * y[i + 1] + h11 * h[i] * m[i + 1]


def camera_at(t):
    if EV["freeze"] <= t <= EV["shatter"]:
        p, g = orbit(t)
        return p, g, 30.0
    p = np.array([pchip(t, KT, KP[:, k]) for k in range(3)])
    g = np.array([pchip(t, KT, KG[:, k]) for k in range(3)])
    return p, g, float(pchip(t, KT, KL))


# ============================================================================================== the sky swarm
SKY_PTS = [(200, 1400, 1500), (-300, -300, 900), (-560, -1150, 520), (-250, -560, 300), (-60, -130, 122),
           (-0.85, -13.6, 96.8), (-0.85, -11.2, 96.7)]
SKY_W = [300, 210, 125, 50, 14, 0.55, 0.25]                 # swarm radius at each control point
SKY_S = [15, 12, 8.5, 4.5, 1.6, 0.16, 0.12]               # bubble size at each control point
PATH = sw.catmull(SKY_PTS, 3000)
TAN, N1, N2 = sw.frames_along(PATH)
_ctrl_a = np.array([np.argmin(np.linalg.norm(PATH - np.array(p), axis=1)) for p in SKY_PTS]) / (len(PATH) - 1)
WIDTH = np.interp(np.linspace(0, 1, len(PATH)), _ctrl_a, SKY_W)
SIZE = np.interp(np.linspace(0, 1, len(PATH)), _ctrl_a, SKY_S)
U = rng.random((SKY_N, 6))
SKY_T0 = EV["erupt"] + 3.4 * U[:, 0]
SKY_D = 2.4 + 0.6 * U[:, 1]
SKY_R = np.sqrt(U[:, 2])
SKY_PHI = 2 * math.pi * U[:, 3]
SKY_OM = (0.7 + 0.9 * U[:, 4]) * np.where(U[:, 5] > 0.5, 1, -1)
SKY_JIT = rng.normal(0, 0.32, (SKY_N, 3))
SKY_SZ = 0.8 + 0.45 * rng.random(SKY_N)
# the lone first text: floats ahead of the camera, then joins the stream on "Then..."
_c28, _g28, _ = None, None, None


def sky_state(t, campos):
    p = (t - SKY_T0) / SKY_D
    vis = (p > 0) & (p < 1)
    a = sw.ease_out_pow(p, 1.35)
    pos, idx = sw.sample(PATH, a)
    r = WIDTH[idx] * (0.2 + 0.8 * SKY_R)
    th = SKY_PHI + SKY_OM * t * 0.35
    ex, ey = r * np.cos(th), 0.33 * r * np.sin(th)
    psi = 4.0 * math.pi * a + 0.6 * t                                   # the ribbon twists along its length
    ox, oy = ex * np.cos(psi) - ey * np.sin(psi), ex * np.sin(psi) + ey * np.cos(psi)
    ripple = np.sin(a * 19 - t * 3.2 + SKY_PHI * 0.15) * WIDTH[idx] * 0.22
    pos = pos + N1[idx] * ox[:, None] + N2[idx] * (oy + ripple)[:, None]
    scl = SIZE[idx] * SKY_SZ * vis
    # the lone first text (index 0)
    t_one, t_go = EV["one"], EV["erupt"]
    if t < t_go + 1.2:
        cp, cg, _l = camera_at(min(max(t, t_one), t_go))
        fwd = (cg - cp) / np.linalg.norm(cg - cp)
        right = np.cross(fwd, [0, 0, 1.0]); right /= np.linalg.norm(right)
        anchor = cp + fwd * 52 + right * 2.5 + np.array([0, 0, 4.0])
        pop = sw.ease_out_pow(np.array([(t - t_one) / 0.45]), 3)[0] * (1 + 0.12 * math.sin(max(0, t - t_one) * 9) * math.exp(-max(0, t - t_one) * 3))
        go = max(0.0, t - t_go)
        lone = anchor + np.array([0, 0, 0.6 * math.sin(t * 1.7)]) + (np.array(SKY_PTS[3]) - anchor) * min(1.0, (go / 1.2) ** 2)
        pos[0] = lone
        scl[0] = (9.0 * pop * (1 - min(1.0, go / 1.2) * 0.6)) if t >= t_one else 0.0
        vis[0] = t >= t_one
    rot = sw.euler_facing(campos[None, :] - pos) + SKY_JIT * 0.6
    return pos, rot, np.repeat(scl[:, None], 3, axis=1)


# ============================================================================================== the room swarm
NR = ROOM_A + ROOM_B
UR = rng.random((NR, 8))
RA_T0 = 5.55 + 2.05 * UR[:ROOM_A, 0]                       # group A enters through the window and swirls
RA_RHO = 0.42 + 1.15 * UR[:ROOM_A, 1]
RA_H = 95.86 + 1.75 * UR[:ROOM_A, 2]
RA_PHI = 2 * math.pi * UR[:ROOM_A, 3]
RA_OM = (1.2 + 1.5 * UR[:ROOM_A, 4]) * np.where(UR[:ROOM_A, 5] > 0.35, 1, -1)
WIN_IN = np.array([-0.85, -11.7, 96.75])
# the pile: a mound over the desk, spilling onto the floor toward the window
_pc = np.array([PH[0] - 0.15, PH[1] - 0.3])
_pts = []
while len(_pts) < NR:
    x, y = _pc[0] + rng.uniform(-1.95, 1.95), _pc[1] + rng.uniform(-1.95, 1.95)
    rr = math.hypot(x - _pc[0], y - _pc[1]) / 1.95
    if rr > 1 or y < room.FACE_Y + 0.35 or y > -4.9:
        continue
    on_desk = abs(x - room.DESK[0]) < 0.8 and abs(y - room.DESK[1]) < 0.39
    base = room.FLOOR_Z + (room.DESK[2] if on_desk else 0.0)
    top = room.FLOOR_Z + 0.04 + 1.05 * (1 - rr ** 1.6) + (0.0 if on_desk else -0.05)
    if top <= base + 0.03:
        continue
    _pts.append((x, y, base + 0.03 + (top - base - 0.03) * rng.random() ** 1.3))
PILE = np.array(_pts)
PILE = PILE[np.argsort(PILE[:, 2])]                        # low first: the first to land are at the bottom
order = rng.permutation(NR)
PILE_OF = np.empty(NR, int)
PILE_OF[order] = np.arange(NR)
PILE_POS = PILE[PILE_OF]
ARR = EV["shatter"] + 0.18 + 1.25 * (PILE_OF / NR) ** 0.85 + 0.1 * UR[:, 6]   # arrival: by height in the pile
RB_T0 = EV["shatter"] + 0.05 + 1.1 * (PILE_OF[ROOM_A:] / NR)
PILE_ROT = np.column_stack([rng.uniform(-1.45, -1.0, NR), rng.uniform(-0.5, 0.5, NR), rng.uniform(-math.pi, math.pi, NR)])
DPH = np.hypot(PILE_POS[:, 0] - PH[0], PILE_POS[:, 1] - PH[1])
FLIP = EV["orange"] + 0.06 + 0.95 * np.clip(DPH / 1.9, 0, 1) + 0.12 * UR[:, 7]
GRAY = rng.random(NR) < 0.07                               # a few texts from before the STOP stay gray
ROOM_SZ = 0.12 + 0.05 * rng.random(NR)
SHOCK_C = PH + np.array([0, 0, 0.09])
DOME_R = 1.38


def dome_radius(t):
    if t < EV["stop"]:
        return 0.0
    return DOME_R * float(sw.ease_out_pow(np.array([(t - EV["stop"]) / 0.2]), 2.6)[0])


def swirl_pos(t):
    """Group A before the shockwave: in through the window, then orbiting the phone."""
    u = np.clip((t - RA_T0) / 0.55, 0, 1)
    k = sw.smoothstep(u)
    ang = RA_PHI + RA_OM * t
    orb = np.column_stack([PH[0] + RA_RHO * np.cos(ang), PH[1] + RA_RHO * np.sin(ang), RA_H + 0.06 * np.sin(2.3 * t + RA_PHI)])
    return WIN_IN + (orb - WIN_IN) * k[:, None], (t >= RA_T0)


def room_state(t, campos):
    pos = np.zeros((NR, 3))
    vis = np.zeros(NR, bool)
    t_frz = EV["freeze"]
    # the effective time: bullet time runs at 3 % speed between the freeze and the shatter
    te = t if t < t_frz else (t_frz + 0.03 * (min(t, EV["shatter"]) - t_frz))
    a_pos, a_vis = swirl_pos(te)
    # the shockwave pushes everything inside the dome out to its surface
    R = dome_radius(te)
    if R > 0:
        d = a_pos - SHOCK_C
        dist = np.linalg.norm(d, axis=1)
        inside = dist < R + 0.04
        push = (R + 0.04 + 0.25 * UR[:ROOM_A, 1] * (R / DOME_R)) / np.maximum(dist, 1e-6)
        a_pos = np.where(inside[:, None], SHOCK_C + d * push[:, None], a_pos)
    pos[:ROOM_A], vis[:ROOM_A] = a_pos, a_vis
    jit = np.column_stack([UR[:ROOM_A, 1] - 0.5, UR[:ROOM_A, 3] - 0.5, UR[:ROOM_A, 4] - 0.5]) * 0.9
    to_center = sw.euler_facing(SHOCK_C[None, :] - pos[:ROOM_A] + 1e-6)
    cam_ref, _g, _l = camera_at(min(t, EV["stop"]))
    to_cam = sw.euler_facing(cam_ref[None, :] - pos[:ROOM_A] + 1e-6)
    kk = sw.smoothstep(np.array([(te - EV["stop"]) / 0.18]))[0]
    dz = np.mod(to_center[:, 2] - to_cam[:, 2] + math.pi, 2 * math.pi) - math.pi
    facing = to_cam + np.column_stack([(to_center[:, 0] - to_cam[:, 0]) * kk, np.zeros(ROOM_A), dz * kk]) + jit
    rot = np.zeros((NR, 3))
    rot[:ROOM_A] = facing
    # the flood: everyone flies to the pile; group B pours in through the window
    if t >= EV["shatter"]:
        ts = EV["shatter"]
        start = np.where(np.arange(NR) < ROOM_A, ts, np.concatenate([np.zeros(ROOM_A), RB_T0]))
        frm = np.vstack([pos[:ROOM_A], np.repeat(WIN_IN[None, :], ROOM_B, axis=0) + rng_fixed_b])
        u = np.clip((t - start) / np.maximum(ARR - start, 0.12), 0, 1)
        k = u ** 1.6                                        # falling: accelerate into the pile
        lift = (np.sin(math.pi * u) * 0.25)[:, None] * np.array([0, 0, 1.0])
        p2 = frm + (PILE_POS - frm) * k[:, None] + lift
        bounce = np.where(u >= 1, 0.03 * np.exp(-(t - ARR) * 7) * np.abs(np.sin((t - ARR) * 18)), 0.0)
        p2[:, 2] += bounce
        pos = p2
        vis = t >= start
        r_from = np.vstack([rot[:ROOM_A], np.tile([0.0, 0.0, 0.0], (ROOM_B, 1)) + rng_fixed_rb])
        rot = r_from + (PILE_ROT - r_from) * sw.smoothstep(u)[:, None]
    pos = clear_view(pos, campos, t)
    scl = np.repeat((ROOM_SZ * vis)[:, None], 3, axis=1)
    orange = np.where(GRAY, 0.0, sw.smoothstep((t - FLIP) / 0.22))
    return pos, rot, scl, orange


def clear_view(pos, campos, t, r_lens=0.55):
    """Bubbles never fill the lens: push them out of a sphere around the camera, and before the freeze also off the
    sight line from the camera to the phone (so the STOP moment shows the phone). Frozen bubbles are never moved by the
    sight-line rule (the camera orbits during the freeze)."""
    v = pos - campos[None, :]
    d = np.linalg.norm(v, axis=1)
    near = d < r_lens
    pos = np.where(near[:, None], campos[None, :] + v / np.maximum(d, 1e-6)[:, None] * r_lens, pos)
    if t < EV["freeze"]:
        seg = SHOCK_C - campos
        L2 = float(seg @ seg)
        w = pos - campos[None, :]
        s_ = np.clip((w @ seg) / max(L2, 1e-9), 0, 1)
        closest = campos[None, :] + s_[:, None] * seg[None, :]
        off = pos - closest
        od = np.linalg.norm(off, axis=1)
        lane = (od < 0.2) & (s_ > 0.05) & (s_ < 0.9)
        pos = np.where(lane[:, None], closest + off / np.maximum(od, 1e-6)[:, None] * 0.2, pos)
    return pos


rng_fixed_b = rng.normal(0, [0.25, 0.12, 0.3], (ROOM_B, 3))
rng_fixed_rb = rng.normal(0, 0.8, (ROOM_B, 3))

# ============================================================================================== lanterns -> the shield
def mask_points():
    """The shield icon (public/favicon-512.png): pixel positions of the navy body and of the orange dollar."""
    im = bpy.data.images.load(os.path.join(HERE, "..", "public", "favicon-512.png"), check_existing=True)
    w, h = im.size
    px = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[::-1]                            # Blender stores rows bottom-up
    r, g, b, a = px[..., 0], px[..., 1], px[..., 2], px[..., 3]
    body = (a > 0.5) & (b > r) & (r < 0.36)
    dollar = (a > 0.5) & (r > 0.7) & (g < 0.67) & (b < 0.47)
    return np.argwhere(body)[:, ::-1].astype(float), np.argwhere(dollar)[:, ::-1].astype(float), (w, h)


BODY_PX, DOLLAR_PX, (MW, MH) = mask_points()
SH_C = np.array([40.0, 260.0, 760.0])                       # the shield's centre in the sky above downtown
SH_H = 780.0                                                # its height (m)
_camf = KP[np.argmin(np.abs(KT - EV["shield"]))]
SH_DIR = (SH_C - _camf) / np.linalg.norm(SH_C - _camf)
SH_E1 = np.cross(SH_DIR, [0, 0, 1.0]); SH_E1 /= np.linalg.norm(SH_E1)
SH_E2 = np.array([0, 0, 1.0])
_scale = SH_H / (BODY_PX[:, 1].max() - BODY_PX[:, 1].min())
_cx, _cy = (BODY_PX[:, 0].max() + BODY_PX[:, 0].min()) / 2, (BODY_PX[:, 1].max() + BODY_PX[:, 1].min()) / 2
N_DOL = 1350
pick_b = BODY_PX[rng.choice(len(BODY_PX), LAN_N - N_DOL, replace=False)]
pick_d = DOLLAR_PX[rng.choice(len(DOLLAR_PX), N_DOL, replace=len(DOLLAR_PX) < N_DOL)]
PX = np.vstack([pick_b, pick_d]) + rng.uniform(-0.5, 0.5, (LAN_N, 2))
IS_DOL = np.arange(LAN_N) >= LAN_N - N_DOL
LAN_Q = SH_C + SH_E1 * ((PX[:, 0] - _cx) * _scale)[:, None] + SH_E2 * ((_cy - PX[:, 1]) * _scale)[:, None] \
    + SH_DIR * rng.normal(0, 9.0, LAN_N)[:, None]
# where each lantern starts: a window of a building that has already turned orange
B = np.array(city.BUILDINGS)
UL = rng.random((LAN_N, 6))
LAN_T0 = EV["lanterns"] + 2.7 * UL[:, 0] ** 1.3
_cand = [np.where(B[:, 5] <= t0 - 0.35)[0] for t0 in LAN_T0]
_bi = np.array([c[int(u * len(c))] if len(c) else int(np.argmin(B[:, 5])) for c, u in zip(_cand, UL[:, 1])])
_side = (UL[:, 2] * 4).astype(int)
_bx, _by, _bw, _bl, _bh = B[_bi, 0], B[_bi, 1], B[_bi, 2], B[_bi, 3], B[_bi, 4]
_off = (UL[:, 3] - 0.5)
LAN_P0 = np.column_stack([
    np.where(_side == 0, _bx - _bw / 2 - 1.5, np.where(_side == 1, _bx + _bw / 2 + 1.5, _bx + _off * _bw)),
    np.where(_side == 2, _by - _bl / 2 - 1.5, np.where(_side == 3, _by + _bl / 2 + 1.5, _by + _off * _bl)),
    4 + UL[:, 4] * np.maximum(_bh - 6, 2)])
LAN_D = np.maximum(EV["shield"] - LAN_T0 - 0.35 * UL[:, 5], 1.4)
LAN_LIFT = 160 + 160 * rng.random(LAN_N)
LAN_SZ = np.where(IS_DOL, 8.6, 7.4) * (0.85 + 0.3 * rng.random(LAN_N))
LAN_PH = 2 * math.pi * rng.random(LAN_N)


def lantern_state(t, campos):
    u = np.clip((t - LAN_T0) / LAN_D, 0, 1)
    k = sw.smoothstep(u)
    b0, b3 = LAN_P0, LAN_Q
    b1 = b0 + np.column_stack([np.zeros(LAN_N), np.zeros(LAN_N), LAN_LIFT])
    b2 = b3 - np.array([0, 0, 140.0]) - SH_DIR * 60
    kk = k[:, None]
    pos = (1 - kk) ** 3 * b0 + 3 * (1 - kk) ** 2 * kk * b1 + 3 * (1 - kk) * kk ** 2 * b2 + kk ** 3 * b3
    sway = np.sin(t * 1.3 + LAN_PH)[:, None] * (1 - kk) * 10.0
    pos = pos + SH_E1 * sway
    settled = np.clip((t - LAN_T0 - LAN_D) / 0.8, 0, 1)
    pos = pos + np.column_stack([np.zeros(LAN_N), np.zeros(LAN_N), 1.6 * np.sin(t * 1.1 + LAN_PH) * settled])
    v = pos - campos[None, :]
    d = np.linalg.norm(v, axis=1)
    pos = np.where((d < 70.0)[:, None], campos[None, :] + v / np.maximum(d, 1e-6)[:, None] * 70.0, pos)
    vis = t >= LAN_T0
    scl = (1.6 + (LAN_SZ - 1.6) * k) * vis
    face = sw.euler_facing(np.repeat(-SH_DIR[None, :], LAN_N, axis=0))
    wob = np.column_stack([np.sin(t * 2 + LAN_PH), np.cos(t * 1.7 + LAN_PH), np.sin(t * 1.3 + 2 * LAN_PH)]) * (0.5 * (1 - k))[:, None]
    glow = np.where(IS_DOL, 2.6, 0.7) * (1 + 0.18 * np.sin(t * 3 + LAN_PH) * settled)
    orange = np.where(IS_DOL, 0.42, 1.0)
    return pos, face + wob, np.repeat(scl[:, None], 3, axis=1), glow, orange


# ============================================================================================== the shockwave dome, shards, ring, STOP
def glass_rim_material(name, glassy=0.16):
    """A thin soap-bubble shell: mostly transparent (so the camera inside the dome still sees the room), a little
    clear glass, and a glowing green-white rim where the surface turns edge-on."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    gl = nt.nodes.new("ShaderNodeBsdfGlass")
    gl.inputs["Roughness"].default_value = 0.0
    gl.inputs["IOR"].default_value = 1.2
    gl.inputs["Color"].default_value = (0.9, 1.0, 0.94, 1)
    mx = nt.nodes.new("ShaderNodeMixShader")
    mx.inputs[0].default_value = glassy
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(gl.outputs[0], mx.inputs[2])
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.2
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 3.0
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 3.5
    mul.name = "RimStrength"
    nt.links.new(pw.outputs[0], mul.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.45, 1.0, 0.62, 1)
    nt.links.new(mul.outputs[0], em.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(mx.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m


DOMEMAT = glass_rim_material("DomeGlass")
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.0, location=tuple(SHOCK_C))
DOME = bpy.context.object
DOME.name = "Dome"
DOME.data.materials.append(DOMEMAT)
for f in DOME.data.polygons:
    f.use_smooth = True
# shards: an icosphere with every face on its own (3 unique verts), moved per frame
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0)
_ico = bpy.context.object
_v = np.array([v.co[:] for v in _ico.data.vertices])
_f = np.array([p.vertices[:] for p in _ico.data.polygons])
bpy.data.objects.remove(_ico)
SH_V0 = _v[_f]                                              # (F, 3, 3)
SH_C0 = SH_V0.mean(axis=1)
SH_N = SH_C0 / np.linalg.norm(SH_C0, axis=1, keepdims=True)
NF_SH = len(_f)
SH_SPD = 2.2 + 4.5 * rng.random(NF_SH)
SH_AX = rng.normal(0, 1, (NF_SH, 3)); SH_AX /= np.linalg.norm(SH_AX, axis=1, keepdims=True)
SH_OM = 6 + 16 * rng.random(NF_SH)
me = bpy.data.meshes.new("Shards")
me.from_pydata((SH_V0 * DOME_R).reshape(-1, 3).tolist(), [], [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(NF_SH)])
SHARDS = cm.link(bpy.data.objects.new("Shards", me))
SHARDS.data.materials.append(glass_rim_material("ShardGlass", glassy=0.55))
sol = SHARDS.modifiers.new("Solidify", "SOLIDIFY")
sol.thickness = 0.006
# the flash ring on the desk at the STOP
bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.012, major_segments=96, minor_segments=8,
                                 location=(PH[0], PH[1], room.FLOOR_Z + room.DESK[2] + 0.01))
RING = bpy.context.object
RING.name = "ShockRing"
RING.data.materials.append(cm.emission_material("RingGlow", (0.55, 1.0, 0.7), 1.0))
STOPB.hide_render = False
STOPB.parent = None


def update_fx(t):
    R = dome_radius(t)
    on = EV["stop"] <= t < EV["shatter"]
    DOME.hide_render = not on or R < 1e-3
    DOME.scale = (max(R, 1e-3),) * 3
    shimmer = 1.0 + 0.25 * math.sin(t * 11) if on else 1.0
    DOMEMAT.node_tree.nodes["RimStrength"].inputs[1].default_value = 1.6 * shimmer * (1.7 if t < EV["stop"] + 0.3 else 1.0)
    # shards
    u = t - EV["shatter"]
    SHARDS.hide_render = not (0 <= u < 1.4)
    if 0 <= u < 1.4:
        c = SHOCK_C + SH_C0 * DOME_R + SH_N * (SH_SPD * u)[:, None] + np.array([0, 0, -4.9]) * u * u
        loc = (SH_V0 - SH_C0[:, None, :]) * DOME_R * max(0.0, 1 - max(0.0, u - 0.9) / 0.5)
        rot = np.stack([sw.rodrigues(loc[:, k], SH_AX, SH_OM * u) for k in range(3)], axis=1)
        verts = (c[:, None, :] + rot).reshape(-1, 3)
        SHARDS.data.vertices.foreach_set("co", verts.astype(np.float32).ravel())
        SHARDS.data.update()
    # ring
    ur = t - EV["stop"]
    RING.hide_render = not (0 <= ur < 0.5)
    if 0 <= ur < 0.5:
        s = 0.05 + 3.2 * sw.ease_out_pow(np.array([ur / 0.5]), 2.2)[0]
        RING.scale = (s, s, 1.0)
        RING.data.materials[0].node_tree.nodes["Emission"].inputs["Strength"].default_value = 60 * (1 - ur / 0.5) ** 2
    # the STOP bubble: rises out of the screen, hangs during the freeze, pops at the shatter
    us = t - (EV["stop"] - 0.12)
    STOPB.hide_render = not (0 <= us and t < EV["shatter"] + 0.05)
    if not STOPB.hide_render:
        k = sw.ease_out_pow(np.array([us / 0.25]), 3)[0]
        STOPB.location = (PH[0] + 0.01, PH[1] - 0.01, PH[2] + 0.02 + 0.13 * k)
        s = 0.1 * (0.3 + 0.7 * k)
        STOPB.scale = (s, s, s)
        cp, cg, _l = camera_at(t)
        d = cp - np.array(STOPB.location)
        STOPB.rotation_euler = tuple(sw.euler_facing(d[None, :])[0])
    # the phone screen: notifications pile up, then the STOP conversation, then the texts after it
    if t < EV["stop"] - 0.3:
        ip.set_screen(SCREEN, image("lock_5"))
    elif t < EV["shatter"]:
        ip.set_screen(SCREEN, image("msgA_2"))
    else:
        ip.set_screen(SCREEN, image("msgA_5"))


# ============================================================================================== per frame
CITY_MATS = [FACADE, beac.data.materials[0]]


def apply(t):
    cp, cg, lens = camera_at(t)
    CAMO.location = tuple(cp)
    CAMO.rotation_euler = cm.look_at_euler(cp, cg)
    CAM.lens = lens
    CAM.clip_start = 0.01 if np.linalg.norm(cp - PH) < 40 else 0.5
    cm.set_time(CITY_MATS, t)
    p, d, ok = city.traffic_at(TR, t)
    p[~ok, 2] = -50
    cm.set_points(cars, p, dir=d, rot=CAR_ROT)
    sp, sr, ss = sky_state(t, cp)
    cm.set_points(SKY, sp, tile=TILES_SKY, glow=np.full(SKY_N, 0.9, np.float32), orange=np.zeros(SKY_N, np.float32), rot=sr, scl=ss)
    rp, rr, rs, ro = room_state(t, cp)
    cm.set_points(ROOMS, rp, tile=TILES_ROOM, glow=np.full(NR, 0.2, np.float32), orange=ro, rot=rr, scl=rs)
    lp, lr, ls, lg, lo = lantern_state(t, cp)
    cm.set_points(LANT, lp, tile=TILES_LAN, glow=lg, orange=lo, rot=lr, scl=ls)
    # hide whole systems when nothing of them is on screen (faster BVH)
    SKY.hide_render = not (EV["one"] - 0.1 <= t <= 6.6)
    ROOMS.hide_render = not (5.5 <= t <= 14.6)
    LANT.hide_render = t < EV["lanterns"] - 0.1
    update_fx(t)


def on_frame(sc, depsgraph=None):
    apply((sc.frame_current + sc.frame_subframe) / FPS)


bpy.app.handlers.frame_change_pre.clear()
bpy.app.handlers.frame_change_pre.append(on_frame)

# ============================================================================================== render settings
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "CUDA"
prefs.get_devices()
for dv in prefs.devices:
    dv.use = dv.type != "CPU"
scene.cycles.device = "GPU"
scene.cycles.use_denoising = True
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.025
scene.cycles.max_bounces = 6
scene.cycles.transparent_max_bounces = 16
scene.cycles.transmission_bounces = 8
scene.cycles.blur_glossy = 1.0
scene.cycles.sample_clamp_indirect = 8.0
scene.cycles.caustics_reflective = scene.cycles.caustics_refractive = False
scene.render.use_persistent_data = True
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.view_settings.view_transform = "Khronos PBR Neutral"
scene.view_settings.exposure = float(args.get("exposure", "0.0"))
scene.render.use_motion_blur = args.get("mblur", "1") == "1" and not PREVIEW
scene.render.motion_blur_shutter = 0.1
scene.frame_start, scene.frame_end = 0, NF - 1


def samples_at(t):
    base = int(args["samples"]) if args.get("samples") else None
    if base:
        return base
    if PREVIEW:
        return 10
    inside = 5.9 <= t <= 13.3
    return 32 if inside else 24


print(f"BUILD {time.time() - T_BUILD:.1f}s: {nb} buildings, sky {SKY_N}, room {NR}, lanterns {LAN_N}, shards {NF_SH}")
only = [int(v) for v in args["only"].split(",")] if args.get("only") else None
frames = only if only is not None else list(range(0, NF, int(args.get("step", "1"))))
for f in frames:
    path = os.path.join(OUT, f"{f:04d}.png")
    if os.path.exists(path) and not FORCE:
        continue
    t = f / FPS
    scene.cycles.samples = samples_at(t)
    scene.frame_set(f)
    scene.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {f} t={t:.2f} {time.time() - t0:.1f}s", flush=True)
print("DONE", len(frames))
