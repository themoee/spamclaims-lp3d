"""
Builds the 3D assets for the SpamClaims 3D landing page and exports them to
public/models/scene.glb.

Run headless from the repo root:

    blender -b -P tools/build_assets.py            # export GLB
    blender -b -P tools/build_assets.py -- --render tools/preview.png   # also render a preview

Meshes (named so three.js can pick them up by name):
    Phone        dark rounded slab, bevelled edges
    Screen       slightly inset plane (emissive; textured at runtime in three.js)
    CameraBump   rounded square bump + two lenses on the back
    StopSign     octagon, bevelled
    StopRim      yellow octagon ring around the sign
    StopInner    thin white ring (like a real stop sign)
    StopText     extruded "STOP" (text object converted to mesh, bevelled)
    Bubble1..3   rounded speech bubbles with a tail

Modelled Z-up; the glTF exporter converts to Y-up (export_yup=True), so the
phone's front face (-Y here) ends up facing +Z in three.js (toward the camera).
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "public", "models", "scene.glb")

argv = sys.argv
extra = argv[argv.index("--") + 1:] if "--" in argv else []
RENDER_PATH = None
if "--render" in extra:
    RENDER_PATH = extra[extra.index("--render") + 1]


# ---------------------------------------------------------------- helpers
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.fonts):
        for item in list(block):
            try:
                block.remove(item)
            except Exception:
                pass


def srgb_to_linear(c):
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def make_material(name, rgb, roughness=0.5, metallic=0.0, emission=None, emission_strength=0.0):
    """Simple PBR material. rgb is sRGB 0..1; converted to linear for the shader."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    lin = srgb_to_linear(rgb)
    bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None:
        elin = srgb_to_linear(emission)
        for key in ("Emission Color", "Emission"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = (*elin, 1.0)
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def rounded_rect_outline(w, h, r, seg=8, cx=0.0, cz=0.0):
    """2D rounded rectangle outline in the XZ plane (Blender Z-up), CCW when seen from -Y."""
    hw, hh = w / 2.0, h / 2.0
    r = min(r, hw, hh)
    corners = [
        (cx + hw - r, cz + hh - r, 0.0),            # top-right
        (cx - hw + r, cz + hh - r, math.pi / 2),    # top-left
        (cx - hw + r, cz - hh + r, math.pi),        # bottom-left
        (cx + hw - r, cz - hh + r, 3 * math.pi / 2) # bottom-right
    ]
    pts = []
    for (x, z, a0) in corners:
        for i in range(seg + 1):
            a = a0 + (math.pi / 2) * (i / seg)
            pts.append((x + r * math.cos(a), z + r * math.sin(a)))
    # drop duplicates where arcs meet
    out = []
    for p in pts:
        if not out or (abs(out[-1][0] - p[0]) > 1e-6 or abs(out[-1][1] - p[1]) > 1e-6):
            out.append(p)
    if abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


def prism_from_outlines(name, outlines, depth, y0=0.0, bevel=0.0, bevel_segments=3, material=None, smooth_angle=40.0):
    """Create a mesh object: each outline (list of (x, z)) becomes a face at y=y0,
    extruded along +Y by `depth`. Optional bevel modifier on edges."""
    bm = bmesh.new()
    faces = []
    for outline in outlines:
        verts = [bm.verts.new((x, y0, z)) for (x, z) in outline]
        faces.append(bm.faces.new(verts))
    bm.faces.ensure_lookup_table()
    res = bmesh.ops.extrude_face_region(bm, geom=faces)
    moved = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=moved, vec=(0.0, depth, 0.0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if material is not None:
        obj.data.materials.append(material)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = bevel_segments
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(30)
        try:
            mod.harden_normals = True
        except Exception:
            pass
    shade_smooth(obj, smooth_angle)
    return obj


def shade_smooth(obj, angle_deg=40.0):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for op, kwargs in (
        ("shade_smooth_by_angle", {"angle": math.radians(angle_deg)}),
        ("shade_auto_smooth", {"angle": math.radians(angle_deg)}),
        ("shade_smooth", {}),
    ):
        fn = getattr(bpy.ops.object, op, None)
        if fn is None:
            continue
        try:
            fn(**kwargs)
            return
        except Exception:
            continue


def apply_modifiers_and_triangulate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as e:
            print("modifier_apply failed", obj.name, mod.name, e)
    tri = obj.modifiers.new("Triangulate", "TRIANGULATE")
    try:
        tri.quad_method = "BEAUTY"
        tri.ngon_method = "BEAUTY"
    except Exception:
        pass
    try:
        bpy.ops.object.modifier_apply(modifier=tri.name)
    except Exception as e:
        print("triangulate apply failed", obj.name, e)


def load_font():
    for path in (
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\ariblk.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if os.path.exists(path):
            try:
                return bpy.data.fonts.load(path), path
            except Exception:
                pass
    return None, "Bfont (built-in)"


# ---------------------------------------------------------------- build
clear_scene()

# Palette (sRGB). Matches the SpamClaims "genz" theme.
MAT_BODY = make_material("PhoneBody", (0.09, 0.07, 0.14), roughness=0.35, metallic=0.6)
MAT_SCREEN = make_material("Screen", (0.02, 0.02, 0.04), roughness=0.2, emission=(0.18, 0.12, 0.45), emission_strength=1.5)
MAT_LENS = make_material("Lens", (0.02, 0.02, 0.03), roughness=0.08, metallic=0.2)
MAT_SIGN = make_material("StopSign", (0.93, 0.13, 0.36), roughness=0.45)       # hot red-pink
MAT_RIM = make_material("StopRim", (1.0, 0.86, 0.25), roughness=0.4, metallic=0.1)  # highlight yellow
MAT_WHITE = make_material("StopWhite", (0.98, 0.98, 1.0), roughness=0.5)
MAT_B1 = make_material("BubbleGray", (0.62, 0.60, 0.72), roughness=0.55)
MAT_B2 = make_material("BubblePink", (1.0, 0.36, 0.66), roughness=0.5)
MAT_B3 = make_material("BubbleViolet", (0.55, 0.45, 1.0), roughness=0.5)

# --- Phone
PHONE_W, PHONE_H, PHONE_D, PHONE_R = 0.72, 1.50, 0.08, 0.10
phone = prism_from_outlines(
    "Phone", [rounded_rect_outline(PHONE_W, PHONE_H, PHONE_R, seg=10)],
    depth=PHONE_D, y0=-PHONE_D / 2, bevel=0.012, bevel_segments=4, material=MAT_BODY, smooth_angle=45,
)

# Screen: inset plane just in front of the front face (front face is at y = -PHONE_D/2)
SCREEN_W, SCREEN_H = 0.655, 1.415
bm = bmesh.new()
verts = [bm.verts.new((x, -PHONE_D / 2 - 0.0015, z)) for (x, z) in rounded_rect_outline(SCREEN_W, SCREEN_H, 0.075, seg=10)]
f = bm.faces.new(verts)
bmesh.ops.recalc_face_normals(bm, faces=[f])
# make sure the screen faces -Y (toward the viewer)
if f.normal.y > 0:
    bmesh.ops.reverse_faces(bm, faces=[f])
# UVs: map the rounded rect to 0..1 so three.js can drop a canvas texture on it
uv_layer = bm.loops.layers.uv.new("UVMap")
for loop in f.loops:
    x, _, z = loop.vert.co
    loop[uv_layer].uv = ((x / SCREEN_W) + 0.5, (z / SCREEN_H) + 0.5)
mesh = bpy.data.meshes.new("Screen")
bm.to_mesh(mesh)
bm.free()
screen = bpy.data.objects.new("Screen", mesh)
bpy.context.collection.objects.link(screen)
screen.data.materials.append(MAT_SCREEN)

# Camera bump on the back (back face is at y = +PHONE_D/2), top-left
bump = prism_from_outlines(
    "CameraBump",
    [rounded_rect_outline(0.22, 0.22, 0.06, seg=8, cx=-0.21, cz=0.56)],
    depth=0.022, y0=PHONE_D / 2 - 0.002, bevel=0.006, bevel_segments=3, material=MAT_BODY, smooth_angle=45,
)
# two lenses
lens_outlines = []
for (lx, lz) in ((-0.255, 0.605), (-0.165, 0.515)):
    ring = [(lx + 0.042 * math.cos(a), lz + 0.042 * math.sin(a)) for a in [i * 2 * math.pi / 24 for i in range(24)]]
    lens_outlines.append(ring)
lenses = prism_from_outlines("CameraLens", lens_outlines, depth=0.014, y0=PHONE_D / 2 + 0.018, material=MAT_LENS, smooth_angle=60)
# join bump + lenses into one object named CameraBump
bpy.ops.object.select_all(action="DESELECT")
bump.select_set(True)
lenses.select_set(True)
bpy.context.view_layer.objects.active = bump
bpy.ops.object.join()
bump.name = "CameraBump"

# --- STOP sign (octagon with flats at top/bottom/sides)
SIGN_R, SIGN_D = 1.0, 0.12
def octagon(radius, offset=math.pi / 8):
    return [(radius * math.cos(offset + i * math.pi / 4), radius * math.sin(offset + i * math.pi / 4)) for i in range(8)]

sign = prism_from_outlines("StopSign", [octagon(SIGN_R)], depth=SIGN_D, y0=-SIGN_D / 2, bevel=0.03, bevel_segments=4, material=MAT_SIGN, smooth_angle=45)

# yellow rim: ring between r=1.0 and r=1.08, slightly thicker than the sign
def ring_object(name, r_in, r_out, depth, y0, material, bevel=0.012):
    bm = bmesh.new()
    outer = [bm.verts.new((x, y0, z)) for (x, z) in octagon(r_out)]
    inner = [bm.verts.new((x, y0, z)) for (x, z) in octagon(r_in)]
    faces = []
    for i in range(8):
        j = (i + 1) % 8
        faces.append(bm.faces.new((outer[i], outer[j], inner[j], inner[i])))
    res = bmesh.ops.extrude_face_region(bm, geom=faces)
    moved = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=moved, vec=(0.0, depth, 0.0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(30)
        try:
            mod.harden_normals = True
        except Exception:
            pass
    shade_smooth(obj, 45)
    return obj

rim = ring_object("StopRim", 0.99, 1.08, SIGN_D + 0.04, -(SIGN_D + 0.04) / 2, MAT_RIM, bevel=0.012)
inner = ring_object("StopInner", 0.86, 0.91, 0.02, -SIGN_D / 2 - 0.018, MAT_WHITE, bevel=0.004)

# STOP text: Blender text object -> mesh, extruded + bevelled
font, font_path = load_font()
bpy.ops.object.text_add(location=(0, 0, 0))
txt = bpy.context.active_object
txt.name = "StopText"
txt.data.body = "STOP"
txt.data.align_x = "CENTER"
txt.data.align_y = "CENTER"
txt.data.size = 0.62
txt.data.extrude = 0.04
txt.data.bevel_depth = 0.006
txt.data.bevel_resolution = 2
txt.data.space_character = 1.02
if font is not None:
    txt.data.font = font
# face -Y: text is built in XY facing +Z; rotate 90deg about X
txt.rotation_euler = (math.radians(90), 0, 0)
txt.location = (0, -SIGN_D / 2 - 0.045, -0.02)
bpy.ops.object.select_all(action="DESELECT")
txt.select_set(True)
bpy.context.view_layer.objects.active = txt
bpy.ops.object.convert(target="MESH")
txt = bpy.context.active_object
txt.name = "StopText"
txt.data.name = "StopText"
txt.data.materials.append(MAT_WHITE)
# scale to fit the sign width (1.5 units of the 2.0 diameter)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bb = [txt.matrix_world @ Vector(c) for c in txt.bound_box]
w = max(v.x for v in bb) - min(v.x for v in bb)
target = 1.48
if w > 0:
    s = target / w
    txt.scale = (s, s, s)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bb = [txt.matrix_world @ Vector(c) for c in txt.bound_box]
cz = (max(v.z for v in bb) + min(v.z for v in bb)) / 2
cx = (max(v.x for v in bb) + min(v.x for v in bb)) / 2
txt.location.x -= cx
txt.location.z -= cz
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
shade_smooth(txt, 35)

# --- Speech bubbles (rounded rect + tail), three variants
def bubble(name, w, h, r, depth, material, tail_side=-1):
    body = rounded_rect_outline(w, h, r, seg=8)
    hw, hh = w / 2, h / 2
    tx = tail_side * (hw - r * 1.1)
    tail = [(tx - 0.07 * tail_side, -hh + 0.02), (tx + 0.09 * tail_side, -hh + 0.02), (tx + 0.02 * tail_side, -hh - 0.14)]
    if tail_side > 0:
        tail = list(reversed(tail))
    obj = prism_from_outlines(name, [body, tail], depth=depth, y0=-depth / 2, bevel=0.028, bevel_segments=4, material=material, smooth_angle=45)
    return obj

b1 = bubble("Bubble1", 0.62, 0.36, 0.17, 0.14, MAT_B1, tail_side=-1)
b2 = bubble("Bubble2", 0.46, 0.42, 0.2, 0.14, MAT_B2, tail_side=1)
b3 = bubble("Bubble3", 0.78, 0.30, 0.15, 0.14, MAT_B3, tail_side=-1)

# --- Apply modifiers + triangulate everything
for obj in list(bpy.context.scene.objects):
    if obj.type == "MESH":
        apply_modifiers_and_triangulate(obj)

# --- Export
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
export_kwargs = dict(filepath=OUT, export_format="GLB", export_apply=True, export_yup=True, use_selection=True)
try:
    bpy.ops.export_scene.gltf(**export_kwargs)
except TypeError:
    export_kwargs.pop("use_selection", None)
    bpy.ops.export_scene.gltf(**export_kwargs)

# --- Report
tris = 0
verts = 0
for obj in bpy.context.scene.objects:
    if obj.type == "MESH":
        ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        m = ev.to_mesh()
        t = sum(len(p.vertices) - 2 for p in m.polygons)
        tris += t
        verts += len(m.vertices)
        print(f"  {obj.name:12s} verts={len(m.vertices):6d} tris={t:6d}")
        ev.to_mesh_clear()
size = os.path.getsize(OUT)
print(f"FONT_USED: {font_path}")
print(f"POLYCOUNT: {tris} triangles, {verts} vertices")
print(f"GLB_SIZE: {size} bytes ({size / 1024:.1f} KB)")
print(f"GLB_PATH: {OUT}")

# Layout for the preview render only, applied AFTER the export so the GLB nodes stay at the origin
# (three.js positions everything itself).
if RENDER_PATH:
    sign.location = (0.9, -0.9, 1.0)
    rim.location = sign.location
    inner.location = sign.location
    txt.location = txt.location + Vector(sign.location)
    for o in (sign, rim, inner, txt):
        o.rotation_euler = (0, math.radians(-18), math.radians(12))
    phone.rotation_euler = (0, math.radians(14), 0)
    for o in (screen, bump):
        o.rotation_euler = phone.rotation_euler
    b1.location = (-1.1, 0.4, 0.9)
    b2.location = (-0.9, 0.2, -0.5)
    b3.location = (1.3, 0.6, -0.9)
    b1.rotation_euler = (0, math.radians(18), math.radians(-10))
    b2.rotation_euler = (0, math.radians(-22), 0)

# --- Optional preview render
if RENDER_PATH:
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0.3, -5.2, 0.4)
    cam.rotation_euler = (math.radians(86), 0, math.radians(3))
    cam_data.lens = 50
    scene.camera = cam

    def light(name, kind, loc, color, energy):
        ld = bpy.data.lights.new(name, kind)
        ld.color = color
        ld.energy = energy
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.location = loc
        return lo

    light("Key", "POINT", (2.5, -3, 2.5), (0.75, 0.55, 1.0), 900)
    light("Fill", "POINT", (-3, -2.5, -1), (1.0, 0.45, 0.75), 500)
    light("Rim", "POINT", (1.5, 2.5, 2.5), (1.0, 0.9, 0.35), 1200)
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*srgb_to_linear((0.09, 0.05, 0.18)), 1.0)
    bg.inputs[1].default_value = 1.0

    scene.render.resolution_x = 1200
    scene.render.resolution_y = 630
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = RENDER_PATH
    rendered = False
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = engine
            if engine == "CYCLES":
                scene.cycles.samples = 48
                scene.cycles.device = "CPU"
                try:
                    scene.cycles.use_denoising = True
                except Exception:
                    pass
            else:
                try:
                    scene.eevee.taa_render_samples = 32
                except Exception:
                    pass
            bpy.ops.render.render(write_still=True)
            rendered = True
            print(f"RENDERED with {engine}: {RENDER_PATH}")
            break
        except Exception as e:
            print(f"render with {engine} failed: {e}")
    if not rendered:
        print("RENDER FAILED")
