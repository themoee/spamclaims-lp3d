"""Ad 5 ("2:13 AM"): a photoreal bedroom at night. A phone on a walnut nightstand wakes up to spam texts after STOP;
the camera rises over the screen as the evidence is counted, then the phone screenshots it and opens spamclaims.com.

blender -b --factory-startup -P ad5_scene.py -- [preview=1] [samples=N] [only=0,120] [step=8] [out=frames/ad5] [force=1]
Few objects, all about realism: walnut, a braided cable, a glass of water, books, an earbuds case, a linen lamp, the
bed, moonlight through blinds, the screen as the main light, a 50-70 mm lens at f/2, a little handheld drift.
"""
import json
import math
import os
import random
import sys
import time

import bmesh
import bpy
import mathutils
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import iphone17pro as ip  # noqa: E402

args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
EDIT = json.load(open(os.path.join(HERE, "..", "ad5", "edit.json"), encoding="utf-8"))
EV = EDIT["events"]
FPS, NF = EDIT["fps"], EDIT["frames"]
PREVIEW = args.get("preview", "0") == "1"
RES = (270, 480) if PREVIEW else (1080, 1920)
OUT = os.path.join(HERE, args.get("out", "frames/ad5_preview" if PREVIEW else "frames/ad5"))
FORCE = args.get("force", "0") == "1"
TEX = os.path.join(HERE, "textures", "ad5")
os.makedirs(OUT, exist_ok=True)
T_BUILD = time.time()

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
TOP_Z = 0.60                                   # the nightstand's top surface


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def link(ob):
    if ob.name not in scene.collection.objects:
        scene.collection.objects.link(ob)
    return ob


def principled(name, base, rough=0.5, metal=0.0, coat=0.0, coat_rough=0.05, transmission=0.0, ior=1.45, sheen=0.0, sss=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*base, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Coat Roughness"].default_value = coat_rough
    p.inputs["Transmission Weight"].default_value = transmission
    p.inputs["IOR"].default_value = ior
    p.inputs["Sheen Weight"].default_value = sheen
    p.inputs["Subsurface Weight"].default_value = sss
    return m


def add_bump(m, scale=300.0, strength=0.06, detail=6.0, kind="noise"):
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tx = nt.nodes.new("ShaderNodeTexNoise" if kind == "noise" else "ShaderNodeTexVoronoi")
    tx.inputs["Scale"].default_value = scale
    if kind == "noise":
        tx.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs["Object"], tx.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    nt.links.new(tx.outputs[0 if kind == "noise" else "Distance"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], p.inputs["Normal"])
    return m


def walnut():
    m = bpy.data.materials.new("Walnut")
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (6.0, 60.0, 6.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.inputs["Scale"].default_value = 3.0
    wv.inputs["Distortion"].default_value = 2.2
    wv.inputs["Detail"].default_value = 8.0
    wv.inputs["Detail Scale"].default_value = 1.5
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 140.0
    nz.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.inputs[0].default_value = 0.25
    nt.links.new(wv.outputs["Fac"], mix.inputs[2])
    nt.links.new(nz.outputs["Fac"], mix.inputs[3])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.2, (0.075, 0.038, 0.02, 1)
    cr.elements[1].position, cr.elements[1].color = 0.9, (0.16, 0.085, 0.042, 1)
    nt.links.new(mix.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.42
    p.inputs["Coat Weight"].default_value = 0.55
    p.inputs["Coat Roughness"].default_value = 0.11
    # pores and a few fine scratches in the varnish
    sc = nt.nodes.new("ShaderNodeTexNoise")
    sc.inputs["Scale"].default_value = 900.0
    sc.inputs["Detail"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], sc.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.03
    nt.links.new(sc.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], p.inputs["Normal"])
    cb = nt.nodes.new("ShaderNodeBump")
    cb.inputs["Strength"].default_value = 0.08
    nt.links.new(wv.outputs["Fac"], cb.inputs["Height"])
    nt.links.new(cb.outputs["Normal"], p.inputs["Coat Normal"])
    return m


def rounded_box(name, center, size, mat, bevel, segs=6):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    b = ob.modifiers.new("Bevel", "BEVEL")
    b.width = bevel
    b.segments = segs
    b.limit_method = "NONE"
    ob.data.materials.append(mat)
    for f in ob.data.polygons:
        f.use_smooth = True
    return ob


def cylinder(name, center, r, depth, mat, segs=64, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=segs, radius=r, depth=depth, location=center)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=segs, radius1=r, radius2=r2, depth=depth, location=center)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(mat)
    for f in ob.data.polygons:
        f.use_smooth = True
    return ob


# ============================================================================================== the set
WAL = walnut()
rounded_box("NightTop", (0, 0.0, TOP_Z - 0.015), (0.52, 0.40, 0.03), WAL, 0.006)
rounded_box("NightBody", (0, 0.01, TOP_Z - 0.03 - 0.27), (0.5, 0.37, 0.54), WAL, 0.004)
drawer_gap = principled("DrawerGap", (0.01, 0.006, 0.004), 0.8)
rounded_box("DrawerFront", (0, -0.176, TOP_Z - 0.13), (0.46, 0.012, 0.15), WAL, 0.003)
rounded_box("DrawerShadow", (0, -0.171, TOP_Z - 0.13), (0.468, 0.006, 0.158), drawer_gap, 0.001)
brass = principled("Brass", (0.78, 0.56, 0.3), rough=0.28, metal=1.0)
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.012, location=(0, -0.19, TOP_Z - 0.13))
knob = bpy.context.object
knob.name = "Knob"
knob.scale = (1, 0.7, 1)
knob.data.materials.append(brass)
for f in knob.data.polygons:
    f.use_smooth = True
# wall (plaster) and floor
plaster = add_bump(principled("Plaster", (0.36, 0.35, 0.34), rough=0.9), scale=80.0, strength=0.12, detail=10)
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0.33, 1.2), rotation=(math.radians(90), 0, 0))
bpy.context.object.name = "Wall"
bpy.context.object.data.materials.append(plaster)
floor = add_bump(principled("FloorBoards", (0.09, 0.06, 0.04), rough=0.5, coat=0.3), scale=40.0, strength=0.05)
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
bpy.context.object.name = "Floor"
bpy.context.object.data.materials.append(floor)

# the bed to the right: mattress, a rumpled duvet, a pillow (mostly out of focus)
linen = principled("Duvet", (0.62, 0.62, 0.6), rough=0.85, sheen=0.6)
linen.node_tree.nodes["Principled BSDF"].inputs["Sheen Roughness"].default_value = 0.4
rounded_box("Mattress", (1.3, -0.65, 0.4), (2.0, 2.0, 0.34), principled("Mattress", (0.7, 0.7, 0.68), 0.9), 0.06)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=80, y_subdivisions=80, size=2.1, location=(1.32, -0.62, 0.6))
duvet = bpy.context.object
duvet.name = "Duvet"
tex = bpy.data.textures.new("DuvetFolds", "CLOUDS")
tex.noise_scale = 0.32
tex.noise_depth = 2
dsp = duvet.modifiers.new("Folds", "DISPLACE")
dsp.texture = tex
dsp.strength = 0.07
dsp.mid_level = 0.3
sub = duvet.modifiers.new("Smooth", "SUBSURF")
sub.levels = 1
sub.render_levels = 2
duvet.data.materials.append(linen)
for f in duvet.data.polygons:
    f.use_smooth = True
pillow = rounded_box("Pillow", (0.75, 0.12, 0.66), (0.6, 0.32, 0.14), linen, 0.06, 8)
pillow.rotation_euler = (0, math.radians(-4), math.radians(5))

# the phone, its cable, a glass of water, books, an earbuds case, a lamp (off)
PHONE = ip.build_iphone("cosmic_orange", "Ph", screen_image=os.path.join(TEX, "lock1.png"),
                        screen_mask=os.path.join(HERE, "textures", "screen_mask.png"), screen_strength=0.0)
PH_AT = mathutils.Vector((-0.02, -0.035, TOP_Z + 0.0043))
PH_YAW = math.radians(-8)
PHONE.location = PH_AT
PHONE.rotation_euler = (0, 0, PH_YAW)
SCREEN = bpy.data.materials["Ph_screen"]
IMG = {}


def image(name):
    if name not in IMG:
        IMG[name] = bpy.data.images.load(os.path.join(TEX, name + ".png"), check_existing=True)
    return IMG[name]


# braided USB-C cable from the phone's bottom port, over the back edge
port = PH_AT + mathutils.Vector((math.sin(-PH_YAW) * -0.0745 * -1, -math.cos(PH_YAW) * 0.0745, 0.0))
pts = [port + mathutils.Vector(v) for v in [(0, -0.012, 0), (0.0, -0.05, -0.002), (0.05, -0.085, -0.0035), (0.13, -0.06, -0.0035),
                                             (0.19, 0.05, -0.0035), (0.2, 0.15, -0.0035), (0.205, 0.205, -0.004), (0.21, 0.24, -0.06),
                                             (0.21, 0.26, -0.3)]]
cu = bpy.data.curves.new("Cable", "CURVE")
cu.dimensions = "3D"
cu.bevel_depth = 0.0019
cu.bevel_resolution = 4
spl = cu.splines.new("NURBS")
spl.points.add(len(pts) - 1)
for k, v in enumerate(pts):
    spl.points[k].co = (v.x, v.y, v.z + 0.002, 1.0)
spl.order_u = 4
spl.use_endpoint_u = True
cable = link(bpy.data.objects.new("Cable", cu))
braid = principled("Braid", (0.82, 0.8, 0.76), rough=0.75, sheen=0.3)
add_bump(braid, scale=2400.0, strength=0.25, kind="voronoi")
cable.data.materials.append(braid)
plug = rounded_box("Plug", (port.x, port.y - 0.012, PH_AT.z), (0.0085, 0.022, 0.0065), principled("PlugWhite", (0.86, 0.85, 0.82), 0.35), 0.0025)
plug.rotation_euler = (0, 0, PH_YAW)
# a tumbler of water: glass shell + water with a meniscus-ish top
glass = principled("Glass", (1, 1, 1), rough=0.0, transmission=1.0, ior=1.5)
water = principled("Water", (0.9, 0.96, 1.0), rough=0.0, transmission=1.0, ior=1.333)
gx, gy = -0.13, -0.11
outer = cylinder("GlassOuter", (gx, gy, TOP_Z + 0.05), 0.034, 0.1, glass, segs=96, r2=0.037)
inner = cylinder("GlassInner", (gx, gy, TOP_Z + 0.055), 0.0315, 0.094, glass, segs=96, r2=0.0345)
bool_ = outer.modifiers.new("Hollow", "BOOLEAN")
bool_.operation = "DIFFERENCE"
bool_.object = inner
inner.hide_render = True
inner.hide_viewport = True
cylinder("Water", (gx, gy, TOP_Z + 0.035), 0.0314, 0.062, water, segs=96, r2=0.0332)
# books (hardcovers with page blocks), an earbuds case, a lamp with a linen shade
cloth = add_bump(principled("BookCloth", (0.06, 0.09, 0.16), rough=0.8), scale=900.0, strength=0.1)
cloth2 = add_bump(principled("BookCloth2", (0.32, 0.12, 0.08), rough=0.8), scale=900.0, strength=0.1)
pages = principled("Pages", (0.78, 0.74, 0.64), rough=0.85)
for k, (c, dz, rot) in enumerate([(cloth, 0.0, 6), (cloth2, 0.026, -3)]):
    bk = rounded_box(f"Book{k}", (0.15, 0.085, TOP_Z + 0.0125 + dz), (0.16, 0.235, 0.025), c, 0.0015, 2)
    bk.rotation_euler = (0, 0, math.radians(rot))
    pg = rounded_box(f"Pages{k}", (0.153, 0.085, TOP_Z + 0.0125 + dz), (0.152, 0.226, 0.021), pages, 0.0005, 1)
    pg.rotation_euler = (0, 0, math.radians(rot))
case = rounded_box("EarbudsCase", (0.165, -0.115, TOP_Z + 0.0115), (0.062, 0.05, 0.023), principled("CaseWhite", (0.88, 0.88, 0.86), 0.22, coat=0.6), 0.011, 8)
case.rotation_euler = (0, 0, math.radians(22))
ceramic = principled("LampCeramic", (0.55, 0.5, 0.44), rough=0.3, coat=0.5)
cylinder("LampBase", (-0.15, 0.18, TOP_Z + 0.09), 0.055, 0.18, ceramic, segs=64, r2=0.04)
shade = principled("LinenShade", (0.85, 0.8, 0.7), rough=0.9, sss=0.0, transmission=0.0)
shade.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.0
sh = cylinder("LampShade", (-0.15, 0.18, TOP_Z + 0.27), 0.12, 0.18, shade, segs=64, r2=0.09)
sol = sh.modifiers.new("Thick", "SOLIDIFY")
sol.thickness = 0.002

# ============================================================================================== light
w = bpy.data.worlds.new("Night")
scene.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.002, 0.0025, 0.004, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
# moonlight through blinds: a cool area light off to the left, slats between it and the set
moon = bpy.data.lights.new("Moon", "SPOT")
moon.spot_size = math.radians(55)
moon.spot_blend = 0.3
moon.shadow_soft_size = 0.02
moon.energy = 1000.0
moon.color = (0.55, 0.68, 1.0)
mo = link(bpy.data.objects.new("Moon", moon))
mo.location = (-2.2, -1.0, 1.9)
d = mathutils.Vector((0.0, 0.1, 0.7)) - mo.location
mo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
slat_mat = principled("Slat", (0.2, 0.2, 0.2), 0.6)
for k in range(27):
    z = 1.05 + k * 0.046
    s = rounded_box(f"Slat{k}", (-1.15, -0.55, z), (0.02, 1.4, 0.024), slat_mat, 0.002, 1)
    s.rotation_euler = (math.radians(25), 0, math.radians(-12))
    s.visible_camera = False
# a faint warm hallway spill from the right, far away (separates the bed from the dark)
hall = bpy.data.lights.new("Hall", "AREA")
hall.size = 0.6
hall.energy = 14.0
hall.color = (1.0, 0.7, 0.45)
ho = link(bpy.data.objects.new("Hall", hall))
ho.location = (2.6, -1.8, 1.3)
d = mathutils.Vector((0.6, 0.0, 0.5)) - ho.location
ho.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

# ============================================================================================== camera
CAM = bpy.data.cameras.new("Cam")
CO = link(bpy.data.objects.new("Cam", CAM))
scene.camera = CO
CAM.sensor_fit = "AUTO"
CAM.dof.use_dof = True
CAM.clip_start = 0.01
SCR = PH_AT + mathutils.Vector((0, 0, 0.004))
KEYS = [  # (t, position, target, lens, f-stop)
    (0.0, (0.05, -0.44, 0.80), (-0.025, -0.03, 0.607), 60, 4.0),
    (EV["thread"] - 0.2, (0.035, -0.35, 0.82), (-0.025, -0.032, 0.607), 60, 4.5),
    (EV["badges"][0] - 0.3, (-0.01, -0.175, 0.865), (-0.02, -0.038, 0.606), 50, 6.3),
    (EV["money"] + 0.6, (-0.015, -0.142, 0.82), (-0.02, -0.036, 0.606), 50, 6.3),
    (EV["shot"] + 0.6, (-0.02, -0.15, 0.835), (-0.02, -0.036, 0.606), 50, 6.3),
    (EV["end"] + 0.1, (-0.02, -0.165, 0.85), (-0.02, -0.036, 0.606), 50, 6.3),
    (EDIT["duration"], (0.1, -0.5, 0.84), (-0.01, -0.03, 0.62), 42, 4.0),
]
KT = np.array([k[0] for k in KEYS])
KV = [np.array([k[i] for k in KEYS], dtype=float) for i in (1, 2, 3, 4)]


def pchip(t, x, y):
    n = len(x)
    h = np.diff(x)
    dd = np.diff(y) / h
    m = np.zeros(n)
    for i in range(1, n - 1):
        if dd[i - 1] * dd[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dd[i - 1] + w2 / dd[i])
    m[0], m[-1] = dd[0], dd[-1]
    i = int(np.clip(np.searchsorted(x, t) - 1, 0, n - 2))
    s = (t - x[i]) / h[i]
    h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    return h00 * y[i] + h10 * h[i] * m[i] + h01 * y[i + 1] + h11 * h[i] * m[i + 1]


def hand(t, amp):
    """Handheld drift: a few incommensurate sines (deterministic)."""
    return np.array([math.sin(t * 1.3 + 0.4) * 0.6 + math.sin(t * 2.9 + 1.1) * 0.3,
                     math.sin(t * 1.1 + 2.0) * 0.5 + math.sin(t * 3.3) * 0.2,
                     math.sin(t * 1.7 + 0.9) * 0.5 + math.sin(t * 2.3 + 0.3) * 0.25]) * amp


def camera_at(t):
    p = np.array([pchip(t, KT, KV[0][:, k]) for k in range(3)]) + hand(t, 0.0011)
    g = np.array([pchip(t, KT, KV[1][:, k]) for k in range(3)]) + hand(t + 5.0, 0.0005)
    return p, g, float(pchip(t, KT, KV[2])), float(pchip(t, KT, KV[3]))


# ============================================================================================== per frame
SEQ = [(0.0, "lock1"), (EV["buzz"][1], "lock2"), (EV["buzz"][2], "lock3"), (EV["thread"], "thread"),
       (EV["badges"][0], "ev1"), (EV["badges"][1], "ev2"), (EV["badges"][2], "ev3"), (EV["evidence"], "evidence"),
       (EV["web"], "web")]


def screen_at(t):
    cur, prev, t_cur = SEQ[0][1], SEQ[0][1], 0.0
    for t0, name in SEQ:
        if t >= t0:
            prev, cur, t_cur = cur, name, t0
    return prev, cur, clamp((t - t_cur) / 0.09)


def apply(t):
    cp, cg, lens, fstop = camera_at(t)
    CO.location = tuple(cp)
    d = mathutils.Vector(cg) - mathutils.Vector(cp)
    CO.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    CAM.lens = lens
    CAM.dof.aperture_fstop = fstop
    # focus: on the notifications (the lower screen) while the lock screen fills up, then the screen's centre
    k = smooth((t - (EV["thread"] - 0.3)) / 0.9)
    f_pt = SCR + mathutils.Vector((0.006, -0.045, 0.0)) * (1 - k)
    CAM.dof.focus_distance = (mathutils.Vector(cp) - f_pt).length
    # the screen: dark, wakes with the first text, flashes on the screenshot
    on = smooth((t - EV["wake"]) / 0.14)
    flash = clamp(1 - abs(t - EV["shot"] - 0.06) / 0.12) if EV["shot"] - 0.06 <= t <= EV["shot"] + 0.18 else 0.0
    prev, cur, mix = screen_at(t)
    ip.set_screen(SCREEN, image(prev), image(cur), mix=mix, flash=flash, strength=1.05 * on)
    # the buzz: the phone rattles on the walnut for a moment with each text
    jx = jy = jr = 0.0
    for b in EV["buzz"]:
        u = t - b
        if 0 <= u < 0.42:
            k = 1 - u / 0.42
            jx += 0.0007 * k * math.sin(u * 2 * math.pi * 43)
            jy += 0.0005 * k * math.sin(u * 2 * math.pi * 37 + 1.0)
            jr += 0.35 * k * math.sin(u * 2 * math.pi * 41 + 0.5)
    PHONE.location = (PH_AT.x + jx, PH_AT.y + jy, PH_AT.z)
    PHONE.rotation_euler = (0, 0, PH_YAW + math.radians(jr))


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
scene.cycles.adaptive_threshold = 0.02
scene.cycles.samples = int(args.get("samples", "10" if PREVIEW else "56"))
scene.cycles.max_bounces = 8
scene.cycles.transmission_bounces = 12
scene.cycles.transparent_max_bounces = 12
scene.cycles.blur_glossy = 0.6
scene.cycles.sample_clamp_indirect = 6.0
scene.cycles.caustics_reflective = scene.cycles.caustics_refractive = False
scene.render.use_persistent_data = True
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Base Contrast"
scene.view_settings.exposure = float(args.get("exposure", "0.75"))
scene.render.use_motion_blur = not PREVIEW
scene.render.motion_blur_shutter = 0.15
scene.frame_start, scene.frame_end = 0, NF - 1
print(f"BUILD {time.time() - T_BUILD:.1f}s")
only = [int(v) for v in args["only"].split(",")] if args.get("only") else None
frames = only if only is not None else list(range(0, NF, int(args.get("step", "1"))))
for f in frames:
    path = os.path.join(OUT, f"{f:04d}.png")
    if os.path.exists(path) and not FORCE:
        continue
    scene.frame_set(f)
    scene.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {f} t={f / FPS:.2f} {time.time() - t0:.1f}s", flush=True)
print("DONE", len(frames))
