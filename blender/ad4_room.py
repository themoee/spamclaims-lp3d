"""Ad 4's hero tower and the apartment where the phone lies (Blender module).

The tower stands at the origin, 24 x 24 m, 150 m tall. The apartment is on the floor at z = 95 m, its window in the
south facade (y = -12), open on the left half so the swarm and the camera can fly in. Inside: a desk facing the
window with the phone on it, a chair, a desk lamp, a laptop, a mug, books, a plant, a bookshelf, a framed print.
"""
import math
import random

import bmesh
import bpy
import mathutils

TOWER = (24.0, 24.0, 150.0)
FLOOR_Z, CEIL_Z = 95.0, 98.2
FACE_Y = -12.0                      # the south facade plane
WIN = (-1.7, 1.7, 95.55, 97.95)     # window x0, x1, z0, z1
OPEN_X = (-1.7, 0.02)               # the open half
DESK = (0.0, -9.35, 0.77)           # desk centre x, y and top height above the floor
PHONE_AT = (0.04, -9.33, FLOOR_Z + 0.77 + 0.004)


def mat(name, base, rough=0.5, metal=0.0, emit=None, emit_strength=0.0, transmission=0.0, ior=1.45, coat=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*base, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["IOR"].default_value = ior
    p.inputs["Transmission Weight"].default_value = transmission
    p.inputs["Coat Weight"].default_value = coat
    if emit:
        p.inputs["Emission Color"].default_value = (*emit, 1)
        p.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1:
        p.inputs["Alpha"].default_value = alpha
    return m


def box(name, center, size, material, parent=None, bevel=0.0, segs=2):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        b = ob.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = segs
        b.limit_method = "ANGLE"
    ob.data.materials.append(material)
    if parent:
        ob.parent = parent
    for f in ob.data.polygons:
        f.use_smooth = bool(bevel)
    return ob


def cyl(name, center, r, depth, material, segs=32, r2=None, rot=None, parent=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=segs, radius=r, depth=depth, location=center)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=segs, radius1=r, radius2=r2, depth=depth, location=center)
    ob = bpy.context.object
    ob.name = name
    if rot:
        ob.rotation_euler = rot
    ob.data.materials.append(material)
    for f in ob.data.polygons:
        f.use_smooth = True
    if parent:
        ob.parent = parent
    return ob


def wood_material(name="Oak"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (5.0, 90.0, 5.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 2.4
    wave.inputs["Distortion"].default_value = 3.5
    wave.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.22, 0.12, 0.06, 1)
    ramp.color_ramp.elements[1].color = (0.36, 0.21, 0.1, 1)
    nt.links.new(wave.outputs["Fac"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.34
    p.inputs["Coat Weight"].default_value = 0.35
    p.inputs["Coat Roughness"].default_value = 0.12
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return m


def plank_floor(name="Floor"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Brick Width"].default_value = 1.4
    brick.inputs["Row Height"].default_value = 0.19
    brick.inputs["Mortar Size"].default_value = 0.004
    brick.inputs["Color1"].default_value = (0.3, 0.18, 0.09, 1)
    brick.inputs["Color2"].default_value = (0.22, 0.12, 0.06, 1)
    brick.inputs["Mortar"].default_value = (0.05, 0.03, 0.02, 1)
    nt.links.new(tc.outputs["Object"], brick.inputs["Vector"])
    nt.links.new(brick.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.4
    p.inputs["Coat Weight"].default_value = 0.4
    p.inputs["Coat Roughness"].default_value = 0.08
    return m


def build_tower(facade_mat, glass_mat, interiors_mat):
    """The tower body (city facade shader on its own mesh) with a detailed curtain wall around the apartment."""
    W, D, H = TOWER
    root = bpy.data.objects.new("HeroTower", None)
    bpy.context.scene.collection.objects.link(root)
    # the body: four walls and a roof, with a hole where the detailed facade patch goes
    bm = bmesh.new()
    lay = {n: bm.faces.layers.float.new(n) for n in ["rnd", "lit", "tint", "glass", "bay", "wave", "hgt"]}
    attrs = {"rnd": 0.37, "lit": 0.34, "tint": 0.4, "glass": 1.0, "bay": 3.0, "wave": 13.7, "hgt": H}
    px0, px1, pz0, pz1 = -6.0, 6.0, 88.6, 105.4          # the patch on the south face
    def quad(a, b, c, d):
        f = bm.faces.new([bm.verts.new(v) for v in (a, b, c, d)])
        for k, v in attrs.items():
            f[lay[k]] = v
    x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2
    # south face split around the patch
    quad((x0, y0, 0), (x1, y0, 0), (x1, y0, pz0), (x0, y0, pz0))
    quad((x0, y0, pz1), (x1, y0, pz1), (x1, y0, H), (x0, y0, H))
    quad((x0, y0, pz0), (px0, y0, pz0), (px0, y0, pz1), (x0, y0, pz1))
    quad((px1, y0, pz0), (x1, y0, pz0), (x1, y0, pz1), (px1, y0, pz1))
    quad((x1, y0, 0), (x1, y1, 0), (x1, y1, H), (x1, y0, H))
    quad((x1, y1, 0), (x0, y1, 0), (x0, y1, H), (x1, y1, H))
    quad((x0, y1, 0), (x0, y0, 0), (x0, y0, H), (x0, y1, H))
    quad((x0, y0, H), (x1, y0, H), (x1, y1, H), (x0, y1, H))
    me = bpy.data.meshes.new("HeroTowerBody")
    bm.to_mesh(me)
    bm.free()
    body = bpy.data.objects.new("HeroTowerBody", me)
    bpy.context.scene.collection.objects.link(body)
    body.data.materials.append(facade_mat)
    body.parent = root
    # the patch: floor slabs, spandrels, mullions, glass panes, glowing interiors behind them
    alu = mat("Mullion", (0.1, 0.105, 0.11), rough=0.32, metal=1.0)
    spand = mat("Spandrel", (0.03, 0.032, 0.036), rough=0.5)
    rng = random.Random(5)
    bay = 2.0
    floors = [88.6 + 3.2 * k for k in range(6)]          # floor lines (the apartment floor is 95.0 -> k = 2)
    for fz in floors:
        box(f"Slab_{fz:.1f}", (0, FACE_Y + 0.02, fz + 0.18), (px1 - px0, 0.16, 0.36), spand, root)
    nb = int((px1 - px0) / bay)
    for k in range(nb + 1):
        x = px0 + k * bay
        box(f"Mull_{k}", (x, FACE_Y - 0.06, (pz0 + pz1) / 2), (0.07, 0.14, pz1 - pz0), alu, root)
    for fi, fz in enumerate(floors[:-1]):
        if abs(fz - FLOOR_Z) < 0.1:
            # the apartment's own floor: solid facade either side of its window (no fake rooms inside the real one)
            for xa, xb in ((px0, WIN[0] - 0.05), (WIN[1] + 0.05, px1)):
                box(f"AptSpandrel_{xa:.1f}", ((xa + xb) / 2, FACE_Y, fz + 1.7), (xb - xa, 0.1, 2.6), spand, root)
            continue
        for k in range(nb):
            xa, xb = px0 + k * bay, px0 + (k + 1) * bay
            za, zb = fz + 0.4, fz + 3.0
            box(f"Pane_{fi}_{k}", ((xa + xb) / 2, FACE_Y + 0.01, (za + zb) / 2), (xb - xa - 0.06, 0.012, zb - za), glass_mat, root)
            # a lit (or dark) room behind the glass: an emissive card with a random warm tint
            card = box(f"Room_{fi}_{k}", ((xa + xb) / 2, FACE_Y + 1.6, (za + zb) / 2), (xb - xa, 0.02, zb - za), interiors_mat, root)
            card["lit"] = 1.0 if rng.random() < 0.42 else 0.05
    # the apartment window: frame, the closed right pane, the slid-back left pane (behind it), sill
    wx0, wx1, wz0, wz1 = WIN
    for nm, c, s in [("WinTop", ((wx0 + wx1) / 2, FACE_Y, wz1), (wx1 - wx0 + 0.1, 0.12, 0.08)),
                     ("WinBot", ((wx0 + wx1) / 2, FACE_Y, wz0), (wx1 - wx0 + 0.1, 0.12, 0.08)),
                     ("WinL", (wx0, FACE_Y, (wz0 + wz1) / 2), (0.08, 0.12, wz1 - wz0)),
                     ("WinR", (wx1, FACE_Y, (wz0 + wz1) / 2), (0.08, 0.12, wz1 - wz0)),
                     ("WinMid", (0.02, FACE_Y + 0.04, (wz0 + wz1) / 2), (0.06, 0.1, wz1 - wz0))]:
        box(nm, c, s, alu, root)
    box("PaneRight", ((0.02 + wx1) / 2, FACE_Y + 0.05, (wz0 + wz1) / 2), (wx1 - 0.02 - 0.04, 0.012, wz1 - wz0 - 0.08), glass_mat, root)
    box("PaneSlid", ((0.02 + wx1) / 2 - 0.05, FACE_Y + 0.11, (wz0 + wz1) / 2), (wx1 - 0.02 - 0.04, 0.012, wz1 - wz0 - 0.08), glass_mat, root)
    box("Sill", ((wx0 + wx1) / 2, FACE_Y + 0.22, wz0 - 0.04), (wx1 - wx0 + 0.2, 0.42, 0.05), mat("SillStone", (0.6, 0.58, 0.55), 0.35), root)
    # wall around the window from the inside (so the room is closed), with the opening
    wall = mat("WallPaint", (0.74, 0.71, 0.66), rough=0.8)
    iy = FACE_Y + 0.12
    box("WallInL", ((px0 + wx0) / 2 - 0.05, iy + 0.02, (FLOOR_Z + CEIL_Z) / 2), (wx0 - px0, 0.06, CEIL_Z - FLOOR_Z), wall, root)
    box("WallInR", ((wx1 + px1) / 2 + 0.05, iy + 0.02, (FLOOR_Z + CEIL_Z) / 2), (px1 - wx1, 0.06, CEIL_Z - FLOOR_Z), wall, root)
    box("WallInBot", ((wx0 + wx1) / 2, iy + 0.02, (FLOOR_Z + wz0) / 2), (wx1 - wx0, 0.06, wz0 - FLOOR_Z), wall, root)
    box("WallInTop", ((wx0 + wx1) / 2, iy + 0.02, (wz1 + CEIL_Z) / 2), (wx1 - wx0, 0.06, CEIL_Z - wz1), wall, root)
    return root


def interiors_material():
    """Glowing rooms behind the neighbouring windows: warm, a gradient (a lamp somewhere), lit or nearly dark."""
    m = bpy.data.materials.new("Interiors")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "OBJECT"
    attr.attribute_name = "lit"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "SPHERICAL"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.9, 0.9, 0.9)
    mp.inputs["Location"].default_value = (0.0, 0.0, -0.2)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], grad.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(attr.outputs["Fac"], mul.inputs[0])
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY_ADD"
    mul2.inputs[1].default_value = 2.6
    mul2.inputs[2].default_value = 0.35
    nt.links.new(grad.outputs["Fac"], mul2.inputs[0])
    nt.links.new(mul2.outputs[0], mul.inputs[1])
    em.inputs["Color"].default_value = (1.0, 0.7, 0.42, 1)
    nt.links.new(mul.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def build_room():
    """The apartment interior: floor, walls, ceiling, the desk set, a chair, a lamp (with its light), shelf, print."""
    root = bpy.data.objects.new("Apartment", None)
    bpy.context.scene.collection.objects.link(root)
    x0, x1, y0, y1 = -3.4, 3.4, FACE_Y + 0.14, -4.6
    wall = bpy.data.materials.get("WallPaint") or mat("WallPaint", (0.74, 0.71, 0.66), rough=0.8)
    box("RoomFloor", (0, (y0 + y1) / 2, FLOOR_Z - 0.03), (x1 - x0, y1 - y0, 0.06), plank_floor(), root)
    box("RoomCeil", (0, (y0 + y1) / 2, CEIL_Z + 0.03), (x1 - x0, y1 - y0, 0.06), mat("Ceiling", (0.8, 0.79, 0.76), 0.9), root)
    box("WallBack", (0, y1, (FLOOR_Z + CEIL_Z) / 2), (x1 - x0, 0.1, CEIL_Z - FLOOR_Z), wall, root)
    box("WallLeft", (x0, (y0 + y1) / 2, (FLOOR_Z + CEIL_Z) / 2), (0.1, y1 - y0, CEIL_Z - FLOOR_Z), wall, root)
    box("WallRight", (x1, (y0 + y1) / 2, (FLOOR_Z + CEIL_Z) / 2), (0.1, y1 - y0, CEIL_Z - FLOOR_Z), wall, root)
    box("Baseboard", (0, y1 + 0.06, FLOOR_Z + 0.05), (x1 - x0, 0.02, 0.1), mat("Trim", (0.85, 0.84, 0.8), 0.5), root)
    oak = wood_material()
    steel = mat("Steel", (0.08, 0.08, 0.085), rough=0.3, metal=1.0)
    dx, dy, dh = DESK
    top_z = FLOOR_Z + dh
    box("DeskTop", (dx, dy, top_z - 0.02), (1.6, 0.78, 0.04), oak, root, bevel=0.006)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"DeskLeg{sx}{sy}", (dx + sx * 0.74, dy + sy * 0.33, FLOOR_Z + (dh - 0.04) / 2), (0.04, 0.04, dh - 0.04), steel, root, bevel=0.004)
    # chair (behind the desk, facing the window)
    fabric = mat("ChairFabric", (0.05, 0.055, 0.07), rough=0.9)
    cy = dy + 0.72
    box("ChairSeat", (dx + 0.05, cy, FLOOR_Z + 0.48), (0.5, 0.48, 0.08), fabric, root, bevel=0.03, segs=4)
    back = box("ChairBack", (dx + 0.05, cy + 0.25, FLOOR_Z + 0.82), (0.48, 0.07, 0.56), fabric, root, bevel=0.03, segs=4)
    back.rotation_euler = (math.radians(-8), 0, 0)
    cyl("ChairPost", (dx + 0.05, cy, FLOOR_Z + 0.25), 0.03, 0.42, steel, parent=root)
    for k in range(5):
        a = 2 * math.pi * k / 5
        leg = box(f"ChairFoot{k}", (dx + 0.05 + 0.17 * math.cos(a), cy + 0.17 * math.sin(a), FLOOR_Z + 0.06), (0.34, 0.04, 0.03), steel, root)
        leg.rotation_euler = (0, 0, a)
    # desk lamp: base, two arm segments, a shade with a warm light inside
    lx, ly = dx + 0.6, dy - 0.08
    cyl("LampBase", (lx, ly, top_z + 0.012), 0.08, 0.024, steel, parent=root)
    a1 = cyl("LampArm1", (lx, ly + 0.05, top_z + 0.2), 0.008, 0.38, steel, rot=(math.radians(-15), 0, 0), parent=root)
    a2 = cyl("LampArm2", (lx + 0.0, ly - 0.03, top_z + 0.42), 0.008, 0.3, steel, rot=(math.radians(62), 0, 0), parent=root)
    shade = cyl("LampShade", (lx + 0.0, ly - 0.14, top_z + 0.43), 0.075, 0.13, mat("ShadeBlack", (0.02, 0.02, 0.02), 0.45, 0.6),
                r2=0.025, rot=(math.radians(-118), 0, 0), segs=40, parent=root)
    bulb = cyl("LampBulb", (lx, ly - 0.18, top_z + 0.4), 0.03, 0.02, mat("Bulb", (1, 0.9, 0.7), emit=(1.0, 0.72, 0.42), emit_strength=40),
               parent=root)
    li = bpy.data.lights.new("LampLight", "SPOT")
    li.energy = 45.0
    li.color = (1.0, 0.7, 0.42)
    li.spot_size = math.radians(95)
    li.spot_blend = 0.6
    li.shadow_soft_size = 0.04
    lo = bpy.data.objects.new("LampLight", li)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = (lx + 0.02, ly - 0.2, top_z + 0.38)
    lo.rotation_euler = (math.radians(28), 0, 0)
    lo.parent = root
    # laptop (closed), mug, books, notebook and pen, a plant on the sill
    alu = mat("LaptopAlu", (0.55, 0.56, 0.58), rough=0.28, metal=1.0)
    box("Laptop", (dx - 0.47, dy - 0.04, top_z + 0.009), (0.31, 0.22, 0.016), alu, root, bevel=0.004)
    ceramic = mat("Ceramic", (0.86, 0.84, 0.8), rough=0.18, coat=0.4)
    cyl("Mug", (dx + 0.3, dy - 0.27, top_z + 0.05), 0.04, 0.1, ceramic, segs=40, parent=root)
    cyl("Coffee", (dx + 0.3, dy - 0.27, top_z + 0.093), 0.036, 0.004, mat("Coffee", (0.05, 0.025, 0.012), 0.08), parent=root)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.026, minor_radius=0.007, location=(dx + 0.345, dy - 0.27, top_z + 0.055),
                                     rotation=(math.radians(90), 0, 0))
    h = bpy.context.object
    h.name = "MugHandle"
    h.data.materials.append(ceramic)
    h.parent = root
    covers = [(0.45, 0.06, 0.05), (0.06, 0.18, 0.32), (0.75, 0.6, 0.2), (0.1, 0.3, 0.16)]
    zz = top_z
    for k, c in enumerate(covers[:3]):
        th = 0.028 + 0.01 * k
        b = box(f"Book{k}", (dx - 0.32 + 0.01 * k, dy + 0.18, zz + th / 2), (0.21, 0.15, th), mat(f"Cover{k}", c, 0.6), root, bevel=0.003)
        b.rotation_euler = (0, 0, math.radians(-8 + 9 * k))
        zz += th
    box("Notebook", (dx + 0.02, dy + 0.2, top_z + 0.004), (0.17, 0.22, 0.008), mat("NoteCover", (0.08, 0.08, 0.1), 0.7), root, bevel=0.002)
    pen = cyl("Pen", (dx + 0.13, dy + 0.18, top_z + 0.006), 0.004, 0.14, mat("PenBlue", (0.02, 0.05, 0.3), 0.3), rot=(0, math.radians(90), 0.4), parent=root)
    terra = mat("Terracotta", (0.42, 0.18, 0.09), 0.7)
    cyl("Pot", (1.2, FACE_Y + 0.3, WIN[2] + 0.07), 0.08, 0.14, terra, r2=0.065, parent=root)
    leaf = mat("Leaf", (0.06, 0.2, 0.06), 0.45, transmission=0.15)
    rng = random.Random(9)
    for k in range(16):
        a = 2 * math.pi * k / 16 + rng.uniform(-0.2, 0.2)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.05,
                                             location=(1.2 + 0.07 * math.cos(a), FACE_Y + 0.3 + 0.07 * math.sin(a), WIN[2] + 0.2 + rng.uniform(0, 0.12)))
        lf = bpy.context.object
        lf.name = f"Leaf{k}"
        lf.scale = (1.0, 0.35, 0.12)
        lf.rotation_euler = (rng.uniform(-0.6, 0.6), rng.uniform(-0.4, 0.4), a)
        lf.data.materials.append(leaf)
        lf.parent = root
    # bookshelf on the right wall with books; a framed print on the left wall
    shelf = mat("ShelfWood", (0.12, 0.07, 0.04), 0.5)
    for k in range(4):
        box(f"Shelf{k}", (x1 - 0.2, -7.4, FLOOR_Z + 0.4 + 0.45 * k), (0.32, 1.6, 0.03), shelf, root)
    for k in range(60):
        row = k // 15
        bh = rng.uniform(0.18, 0.3)
        c = rng.choice([(0.5, 0.07, 0.05), (0.07, 0.15, 0.35), (0.7, 0.62, 0.45), (0.12, 0.3, 0.17), (0.2, 0.2, 0.22), (0.6, 0.35, 0.08)])
        box(f"ShelfBook{k}", (x1 - 0.2, -8.12 + (k % 15) * 0.095 + rng.uniform(-0.01, 0.01), FLOOR_Z + 0.415 + 0.45 * row + bh / 2),
            (0.2, 0.07, bh), mat(f"SB{k}", c, 0.65), root)
    box("PrintFrame", (x0 + 0.06, -7.6, FLOOR_Z + 1.65), (0.03, 0.9, 0.65), mat("Frame", (0.02, 0.02, 0.02), 0.4), root)
    box("PrintArt", (x0 + 0.08, -7.6, FLOOR_Z + 1.65), (0.01, 0.8, 0.55), mat("PrintArt", (0.55, 0.3, 0.18), 0.8), root)
    return root
