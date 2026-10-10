"""Review stills of the iPhone 17 Pro model (Z-up world; the camera looks along +Y at the origin).

blender -b --factory-startup -P render_stills.py -- [views=...] [finish=cosmic_orange] [screen=textures/_placeholder.png]
  [samples=160] [res=1600x1000] [strength=1.6] [k=1.0]
Writes renders/<finish>_<view>.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402

import iphone17pro as ip  # noqa: E402
import studio  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
views = args.get("views", "front34,back34,backflat,frontflat,macro,side").split(",")
finish = args.get("finish", "cosmic_orange")
screen = os.path.join(HERE, args.get("screen", "textures/_placeholder.png"))
mask = os.path.join(HERE, "textures/screen_mask.png")
samples = int(args.get("samples", "160"))
res = tuple(int(v) for v in args.get("res", "1600x1000").split("x"))
strength = float(args.get("strength", "1.6"))
k = float(args.get("k", "1.0"))

scene = studio.reset_scene()
studio.setup_render(scene, res=res, samples=samples)
studio.product_studio(scene, k=k)

turn = bpy.data.objects.new("Turn", None)
scene.collection.objects.link(turn)
phone = ip.build_iphone(finish, "Phone", screen_image=screen, screen_mask=mask, screen_strength=strength)
phone.parent = turn
phone.rotation_euler = (math.radians(90.0), 0.0, 0.0)   # local +y -> world +z, screen faces -Y (the camera)

VIEWS = {
    # name: (camera location, target, lens, turn rotation in degrees (pitch about X, roll about Y, yaw about Z), ortho scale)
    "front34": ((0.0, -0.64, 0.03), (0, 0, 0), 85.0, (4.0, 0.0, 26.0), None),
    "frontflat": ((0.0, -1.2, 0.0), (0, 0, 0), 85.0, (0.0, 0.0, 0.0), 0.165),
    "back34": ((0.0, -0.64, 0.04), (0, 0, 0), 85.0, (6.0, 0.0, 206.0), None),
    "backflat": ((0.0, -1.2, 0.0), (0, 0, 0), 85.0, (0.0, 0.0, 180.0), 0.165),
    "macro": ((0.0, -0.22, 0.075), (0, 0, 0.048), 100.0, (10.0, 0.0, 202.0), None),
    "side": ((0.0, -0.64, 0.0), (0, 0, 0), 85.0, (0.0, 0.0, 90.0), None),
}

out_dir = os.path.join(HERE, "renders")
os.makedirs(out_dir, exist_ok=True)
for v in views:
    loc, tgt, lens, rot, ortho = VIEWS[v]
    scene.render.resolution_x, scene.render.resolution_y = (res[1], res[0]) if v.endswith("flat") else res
    turn.rotation_euler = tuple(math.radians(a) for a in rot)
    cam = studio.camera(f"Cam_{v}", loc, tgt, lens=lens, ortho_scale=ortho)
    scene.camera = cam
    scene.render.filepath = os.path.join(out_dir, f"{finish}_{v}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", scene.render.filepath)
