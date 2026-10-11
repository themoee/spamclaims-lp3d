"""Ad 6 look development: Dre sitting up in bed at night, phone in hand; renders a few expressions and a wide shot.

blender -b --factory-startup -P ad6_lookdev.py -- out=<dir> [samples=48] [res=720x1280] [only=neutral,shock]
"""
import math
import os
import sys
import time

import bpy
import mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import iphone17pro as ip  # noqa: E402
from ad6_char import Character  # noqa: E402
from ad6_room import BED_Z, Room  # noqa: E402

args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
OUT = args.get("out", os.path.join(HERE, "frames", "ad6_lookdev"))
os.makedirs(OUT, exist_ok=True)
V = mathutils.Vector
T0 = time.time()

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
TEX5 = os.path.join(HERE, "textures", "ad5")
phone = ip.build_iphone("deep_blue", "Ph", screen_image=os.path.join(TEX5, "thread.png"),
                        screen_mask=os.path.join(HERE, "textures", "screen_mask.png"), screen_strength=1.0)
room = Room(os.path.join(HERE, "textures", "ad6"))
dre = Character("Dre", phone=phone)

# key light from the phone screen, toward his face
kl = bpy.data.lights.new("PhoneKey", "AREA")
kl.shape = "RECTANGLE"
kl.size, kl.size_y = 0.066, 0.145
kl.energy = float(args.get("key", "5"))
kl.color = (0.78, 0.87, 1.0)
ko = bpy.data.objects.new("PhoneKey", kl)
scene.collection.objects.link(ko)
ko.parent = phone
ko.location = (0, 0, 0.012)
ko.rotation_euler = (math.radians(180), 0, 0)          # area lights emit along -z: flip to emit out of the screen
ko.visible_camera = False
# a violet rim from behind-above (the LED side) and a dim cool fill
for name, loc, tgt, e, col, size in [("Rim", (0.35, 1.0, 1.75), (0.0, 0.45, 1.25), float(args.get("rim", "45")), (0.6, 0.3, 1.0), 0.5),
                                     ("Fill", (-0.9, -0.6, 1.5), (0.0, 0.45, 1.2), float(args.get("fill", "4")), (0.45, 0.55, 1.0), 1.0)]:
    ld = bpy.data.lights.new(name, "AREA")
    ld.size = size
    ld.energy = e
    ld.color = col
    lo = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(lo)
    lo.location = loc
    lo.rotation_euler = (V(tgt) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    lo.visible_camera = False

w = bpy.data.worlds.new("Night")
scene.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.004, 0.009, 1)

# pose: sitting up against the pillows, phone held low in his right hand, looking at the camera
HIP = (0.0, 0.42, BED_Z + 0.03)
dre.pose({"root_loc": HIP, "root_rot": (0, 0, 0), "spine": (-8, 0, 0), "neck": (6, 0, 0), "head": (2, 0, 0),
          "shoulder.R": (-38, 0, 16), "elbow.R": (-78, 0, 0), "wrist.R": (-10, 0, 0),
          "shoulder.L": (-20, 0, -14), "elbow.L": (-40, 0, 0), "wrist.L": (0, 0, 0)})
phone.location = (0.0, -0.025, -0.07)
phone.rotation_euler = (math.radians(-100), 0, math.radians(180))
room.set_duvet(HIP[1], lie=0.0, knees=0.3)
bpy.context.view_layer.update()

cam = bpy.data.cameras.new("Cam")
co = bpy.data.objects.new("Cam", cam)
scene.collection.objects.link(co)
scene.camera = co
cam.sensor_fit = "AUTO"
cam.dof.use_dof = True
cam.clip_start = 0.01

scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "CUDA"
prefs.get_devices()
for dv in prefs.devices:
    dv.use = dv.type != "CPU"
scene.cycles.device = "GPU"
scene.cycles.samples = int(args.get("samples", "48"))
scene.cycles.use_denoising = True
scene.cycles.use_adaptive_sampling = True
scene.cycles.max_bounces = 8
scene.cycles.transmission_bounces = 8
scene.cycles.sample_clamp_indirect = 8.0
rx, ry = (int(v) for v in args.get("res", "720x1280").split("x"))
scene.render.resolution_x, scene.render.resolution_y = rx, ry
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Base Contrast"
scene.view_settings.exposure = float(args.get("exposure", "0.6"))
print(f"BUILD {time.time() - T0:.1f}s")

EXPR = {
    "neutral": dict(blink=0.0, look=(0.0, 0.05), brow=(0.0, 0.0), mouth=dict(open=0.0, wide=1.0, smile=0.45)),
    "talk": dict(blink=0.0, look=(0.0, 0.05), brow=(0.35, 0.25), mouth=dict(open=0.55, wide=1.0, smile=0.4)),
    "shock": dict(blink=-1.0, look=(0.0, 0.1), brow=(1.0, 1.0), brow_tilt=(0.3, 0.3), mouth=dict(open=0.9, wide=0.8, round=0.7, smile=-0.1)),
    "smile": dict(blink=0.0, look=(0.0, 0.05), brow=(0.25, 0.25), squint=0.45, mouth=dict(open=0.35, wide=1.15, smile=1.0)),
    "skeptic": dict(blink=0.15, look=(-0.2, 0.0), brow=(0.9, -0.35), brow_tilt=(0.0, -0.4), mouth=dict(open=0.05, wide=0.9, smile=-0.35)),
}
SHOTS = {  # name: (expression, camera offset from the head, lens, f-stop)
    "neutral": ("neutral", (0.12, -0.95, -0.02), 55, 2.4),
    "talk": ("talk", (0.12, -0.95, -0.02), 55, 2.4),
    "shock": ("shock", (0.06, -0.8, -0.03), 55, 2.4),
    "smile": ("smile", (0.12, -0.95, -0.02), 55, 2.4),
    "skeptic": ("skeptic", (0.12, -0.95, -0.02), 55, 2.4),
    "wide": ("neutral", (0.55, -2.3, -0.25), 35, 4.0),
}
only = args.get("only", ",".join(SHOTS)).split(",")
for name in only:
    ex, off, lens, fs = SHOTS[name]
    dre.face(**EXPR[ex])
    bpy.context.view_layer.update()
    hw = dre.head_world()
    eye = dre.eye_world()
    co.location = hw + V(off)
    co.rotation_euler = (hw - co.location + V((0, 0, -0.04 if name == "wide" else 0.0))).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    cam.dof.aperture_fstop = fs
    cam.dof.focus_distance = (eye - co.location).length - 0.03
    scene.render.filepath = os.path.join(OUT, f"{name}.png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"SHOT {name} {time.time() - t0:.1f}s", flush=True)
