"""Photoreal front-view frames of the phone for the web: everything but the display, with the display area cut out
(alpha 0), so a DOM-rendered screen (the app's IosMessages) can sit under it. Exactly the body's bounds:
71.9 x 150.0 mm mapped to the whole image, the display at 66.6 x 144.8 mm centered, as PhoneFrame expects.

blender -b --factory-startup -P render_frame_png.py -- [finishes=cosmic_orange,deep_blue,silver] [pxmm=10] [samples=128]
Writes renders/frame_<finish>.png (RGBA).
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
FINISHES = args.get("finishes", "cosmic_orange,deep_blue,silver").split(",")
PXMM = float(args.get("pxmm", "10"))
SAMPLES = int(args.get("samples", "128"))
MASK = os.path.join(HERE, "textures", "screen_mask.png")

W_MM, H_MM = ip.W / ip.MM, ip.H / ip.MM
res = (round(W_MM * PXMM), round(H_MM * PXMM))
scene = studio.reset_scene()
studio.setup_render(scene, res=res, samples=SAMPLES, transparent=True)
studio.product_studio(scene, k=1.0)


def cut_out_display(mat):
    """Inside the display (the mask, in the display's UV space): Holdout. Outside it: the glossy black glass."""
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    glass = nt.nodes.new("ShaderNodeBsdfPrincipled")
    glass.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    glass.inputs["Roughness"].default_value = 0.03
    glass.inputs["IOR"].default_value = 1.52
    hold = nt.nodes.new("ShaderNodeHoldout")
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.extension = "CLIP"
    tex.interpolation = "Cubic"
    img = bpy.data.images.load(MASK, check_existing=True)
    img.colorspace_settings.name = "Non-Color"
    tex.image = img
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], mix.inputs["Fac"])
    nt.links.new(glass.outputs[0], mix.inputs[1])
    nt.links.new(hold.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


cam = studio.camera("Front", (0.0, -1.0, 0.0), (0.0, 0.0, 0.0), lens=85.0, ortho_scale=ip.H)
scene.camera = cam
os.makedirs(os.path.join(HERE, "renders"), exist_ok=True)
for finish in FINISHES:
    for ob in list(bpy.data.objects):
        if ob.name.startswith("Ph_") or ob.name == "Turn":
            bpy.data.objects.remove(ob, do_unlink=True)
    turn = bpy.data.objects.new("Turn", None)
    scene.collection.objects.link(turn)
    root = ip.build_iphone(finish, f"Ph_{finish}", screen_image=None, screen_mask=MASK)
    root.parent = turn
    root.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    cut_out_display(bpy.data.materials[f"Ph_{finish}_screen"])
    scene.render.filepath = os.path.join(HERE, "renders", f"frame_{finish}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", scene.render.filepath, res)
