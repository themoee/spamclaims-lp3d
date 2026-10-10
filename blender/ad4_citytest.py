"""Look test for ad 4's city: build it, render two views at preview size.
blender -b --factory-startup -P ad4_citytest.py -- out=frames/ad4_test res=540 samples=24 T=0"""
import math
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ad4_city as city  # noqa: E402
import ad4_common as cm  # noqa: E402

args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
OUT = os.path.join(HERE, args.get("out", "frames/ad4_test"))
os.makedirs(OUT, exist_ok=True)
W = int(args.get("res", "540"))
T = float(args.get("T", "0"))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
t0 = time.time()

blds, tops, roofs, nb = city.build_buildings(keep_clear=[(0, 0, 70)])
cm.link(blds)
fac = city.facade_material()
blds.data.materials.append(fac)
props = cm.link(city.merge_props("RoofGear", roofs, tops))
bea = cm.link(city.beacons("Beacons", tops))
cm.link(city.ground())
cm.link(city.river())
lines = city.street_lines()
br, br_pts = city.bridges("Bridges", lines)
cm.link(br)
sl, nsl = city.street_lights("StreetLights", lines)
cm.link(sl)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.7)
lamp = bpy.context.object
lamp.name = "LampDot"
lamp.data.materials.append(cm.emission_material("Sodium", (1.0, 0.58, 0.26), 60.0))
lamp.hide_render = True
cm.instance_on_points(sl, lamp)
sl.visible_diffuse = False
sl.visible_shadow = False
# traffic
tr = city.traffic_points(lines)
cars = cm.link(cm.point_cloud("Traffic", len(tr["idx"]), {"dir": "FLOAT", "rot": "FLOAT_VECTOR"}))
bpy.ops.mesh.primitive_cube_add(size=1)
car = bpy.context.object
car.name = "CarLight"
car.scale = (3.2, 1.2, 0.6)
bpy.ops.object.transform_apply(scale=True)
cmat = bpy.data.materials.new("CarLights")
cmat.use_nodes = True
nt = cmat.node_tree
nt.nodes.clear()
o = nt.nodes.new("ShaderNodeOutputMaterial")
e = nt.nodes.new("ShaderNodeEmission")
a = nt.nodes.new("ShaderNodeAttribute"); a.attribute_type = "INSTANCER"; a.attribute_name = "dir"
mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1; mr.inputs["From Max"].default_value = 1
nt.links.new(a.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs[0], mx.inputs[0])
mx.inputs[6].default_value = (1.0, 0.06, 0.03, 1); mx.inputs[7].default_value = (1.0, 0.92, 0.8, 1)
nt.links.new(mx.outputs[2], e.inputs["Color"]); e.inputs["Strength"].default_value = 40
nt.links.new(e.outputs[0], o.inputs["Surface"])
car.data.materials.append(cmat)
car.hide_render = True
cm.instance_on_points(cars, car, rot_attr="rot")
cars.visible_diffuse = False
cars.visible_shadow = False
p, d, ok = city.traffic_at(tr, T)
p[~ok, 2] = -50
L = tr["L"][tr["idx"]]
rotz = (abs(L[:, 2] - L[:, 0]) < 1).astype(float) * math.pi / 2
import numpy as np
cm.set_points(cars, p, dir=d, rot=np.column_stack([np.zeros(len(p)), np.zeros(len(p)), rotz]))
cm.link(city.hills())
city.night_world(sc, 1.0)
for ob in bpy.data.objects:
    if ob.type == "MESH" and ob.data.materials and ob.name not in ("LampDot", "CarLight", "Beacons"):
        for m in ob.data.materials:
            if m and not m.get("fogged"):
                city.add_fog(m, density=0.00045 if ob.name == "Hills" else 0.00028, max_fog=0.55 if ob.name == "Hills" else 0.88)
                m["fogged"] = True
cm.set_time([fac, bea.data.materials[0]], T)
print(f"built {nb} buildings, {nsl} street lights, {len(p)} cars in {time.time() - t0:.1f}s")

cam = bpy.data.cameras.new("Cam")
co = cm.link(bpy.data.objects.new("Cam", cam))
sc.camera = co
cam.clip_start, cam.clip_end = 0.5, 30000
sc.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "CUDA"
prefs.get_devices()
for dv in prefs.devices:
    dv.use = dv.type != "CPU"
sc.cycles.device = "GPU"
sc.cycles.samples = int(args.get("samples", "24"))
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.render.resolution_x, sc.render.resolution_y = W, int(W * 16 / 9)
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Punchy"
VIEWS = {
    "open": ((-700, -1500, 420), (40, 300, 60), 24),
    "hero": ((-30, -260, 125), (0, 0, 100), 28),
    "high": ((300, -900, 900), (0, 200, 0), 30),
    "wave": ((-200, -1100, 520), (0, 200, 40), 26),
}
for name, (loc, tgt, lens) in VIEWS.items():
    if args.get("only") and name not in args["only"].split(","):
        continue
    co.location = loc
    co.rotation_euler = cm.look_at_euler(loc, tgt)
    cam.lens = lens
    sc.render.filepath = os.path.join(OUT, f"{name}_T{T:.1f}.png")
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"VIEW {name}: {time.time() - t1:.1f}s")
