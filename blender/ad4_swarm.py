"""Ad 4's bubbles: the 3D text-bubble mesh and its atlas material, and the motion of every system, evaluated per
frame with numpy (pure functions of time, so frames render in any order).

  sky      6,000 giant bubbles: the swarm erupts behind downtown, streams past the camera, funnels into the window
  room     4,500 small bubbles: swirl around the phone, blown out by the STOP shockwave, frozen (bullet time),
           then flood in and bury the desk; the texts after STOP turn orange from the phone outward
  lantern  4,000 orange bubbles: rise from the city's windows and form the SpamClaims shield in the sky
  shards   the shockwave dome (an icosphere whose faces fly apart)
"""
import math
import os

import bmesh
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "textures", "ad4")
COLS, ROWS = 8, 6


# ---------------------------------------------------------------------------------------------- mesh + material
def bubble_mesh(name="BubbleMesh", w=1.0, h=0.5, r=0.2, depth=0.07, tail_side=-1):
    """A message bubble in the XZ plane facing -Y: a rounded rectangle with a tail at the bottom corner, extruded,
    the front face UV-mapped to the whole tile."""
    pts = []
    def arc(cx, cz, a0, a1, n=8):
        for k in range(n + 1):
            a = a0 + (a1 - a0) * k / n
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    x0, x1, z0, z1 = -w / 2, w / 2, -h / 2, h / 2
    arc(x1 - r, z1 - r, 0, math.pi / 2)
    arc(x0 + r, z1 - r, math.pi / 2, math.pi)
    if tail_side < 0:
        # bottom-left corner replaced by the tail: down and out to a point, curving back along the bottom
        pts += [(x0, z0 + r * 0.6), (x0 - 0.035, z0 - 0.045), (x0 + 0.03, z0 - 0.005), (x0 + r * 0.9, z0)]
        arc(x1 - r, z0 + r, -math.pi / 2, 0)
    else:
        arc(x0 + r, z0 + r, math.pi, 1.5 * math.pi)
        pts += [(x1 - r * 0.9, z0), (x1 - 0.03, z0 - 0.005), (x1 + 0.035, z0 - 0.045), (x1, z0 + r * 0.6)]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    front = [bm.verts.new((x, -depth / 2, z)) for x, z in pts]
    back = [bm.verts.new((x, depth / 2, z)) for x, z in pts]
    ff = bm.faces.new(front)
    bf = bm.faces.new(list(reversed(back)))
    n = len(pts)
    for k in range(n):
        bm.faces.new((front[k], front[(k + 1) % n], back[(k + 1) % n], back[k]))
    bm.normal_update()
    if ff.normal.y > 0:
        ff.normal_flip()
    for f in bm.faces:
        for lp in f.loops:
            x, _, z = lp.vert.co
            lp[uv].uv = ((x - x0) / w, (z - z0) / h)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bev = ob.modifiers.new("Bevel", "BEVEL")
    bev.width = depth * 0.42
    bev.segments = 3
    bev.limit_method = "ANGLE"
    for p in me.polygons:
        p.use_smooth = True
    return ob


def atlas_material(name="BubbleAtlas", image_path=None, single=False):
    """Light-mode bubble faces from the atlas; instancer attributes: tile (0-47), glow (emission), orange (0..1),
    fade (0..1 opacity via emission/visibility)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Roughness"].default_value = 0.32
    p.inputs["Coat Weight"].default_value = 0.6
    p.inputs["Coat Roughness"].default_value = 0.06
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(image_path or os.path.join(TEX, "atlas.png"), check_existing=True)
    img.interpolation = "Cubic"
    img.extension = "EXTEND"

    def iattr(nm):
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_type = "INSTANCER"
        a.attribute_name = nm
        return a.outputs["Fac"]

    def math_(op, a, b=None, c=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    if single:
        nt.links.new(uvn.outputs["UV"], img.inputs["Vector"])
        glow, orange = 0.0, None
    else:
        tile = iattr("tile")
        col = math_("MODULO", math_("FLOOR", tile), COLS)
        row = math_("FLOOR", math_("DIVIDE", math_("FLOOR", tile), COLS))
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(uvn.outputs["UV"], sep.inputs[0])
        # keep a hair inside the tile so neighbours never bleed
        uu = math_("MULTIPLY_ADD", sep.outputs[0], 0.985, 0.0075)
        vv = math_("MULTIPLY_ADD", sep.outputs[1], 0.985, 0.0075)
        u2 = math_("DIVIDE", math_("ADD", uu, col), COLS)
        v2 = math_("DIVIDE", math_("ADD", vv, math_("SUBTRACT", ROWS - 1, row)), ROWS)
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(u2, comb.inputs[0])
        nt.links.new(v2, comb.inputs[1])
        nt.links.new(comb.outputs[0], img.inputs["Vector"])
        glow, orange = iattr("glow"), iattr("orange")
    # orange: the face tints toward a hot orange (the text stays legible: multiply), and glows much brighter
    col_rgb = img.outputs["Color"]
    if orange is not None:
        org = nt.nodes.new("ShaderNodeRGB")
        org.outputs[0].default_value = (1.0, 0.27, 0.02, 1)
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        nt.links.new(orange, mul.inputs[0])
        nt.links.new(col_rgb, mul.inputs[6])
        nt.links.new(org.outputs[0], mul.inputs[7])
        col_rgb = mul.outputs[2]
        estr = math_("ADD", glow, math_("MULTIPLY", orange, 0.85))
    else:
        estr = 0.6
    nt.links.new(col_rgb, p.inputs["Base Color"])
    nt.links.new(col_rgb, p.inputs["Emission Color"])
    if isinstance(estr, float):
        p.inputs["Emission Strength"].default_value = estr
    else:
        nt.links.new(estr, p.inputs["Emission Strength"])
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------------------------------------- helpers
def euler_facing(dirs, roll=None):
    """Euler XYZ (radians) that turns a bubble (facing -Y) to face along -dirs (i.e. toward the viewer at +dirs)."""
    d = dirs / np.maximum(np.linalg.norm(dirs, axis=1, keepdims=True), 1e-9)
    yaw = np.arctan2(-d[:, 0], d[:, 1]) + math.pi          # rotate about Z so -Y points along d
    pitch = np.arcsin(np.clip(d[:, 2], -1, 1))
    rx = -pitch
    rz = yaw
    ry = roll if roll is not None else np.zeros(len(d))
    return np.column_stack([rx, ry, rz])


def catmull(points, n=2000):
    """A centripetal-ish Catmull-Rom path through points, resampled by arc length: returns (n, 3) samples."""
    P = np.array(points, dtype=np.float64)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, 200, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    out = np.array(out)
    seg = np.linalg.norm(np.diff(out, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    s = np.linspace(0, cum[-1], n)
    res = np.column_stack([np.interp(s, cum, out[:, k]) for k in range(3)])
    return res


def frames_along(path):
    """Unit tangent and two normals along a sampled path (for offsets around it)."""
    t = np.gradient(path, axis=0)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    up = np.array([0, 0, 1.0])
    n1 = np.cross(t, up)
    bad = np.linalg.norm(n1, axis=1) < 1e-6
    n1[bad] = np.array([1.0, 0, 0])
    n1 /= np.linalg.norm(n1, axis=1, keepdims=True)
    n2 = np.cross(n1, t)
    return t, n1, n2


def sample(path, a):
    """Positions on a sampled path at fractions a (0..1), plus the sample indices."""
    idx = np.clip((a * (len(path) - 1)).astype(int), 0, len(path) - 1)
    return path[idx], idx


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def ease_out_pow(x, p=1.7):
    x = np.clip(x, 0, 1)
    return 1 - (1 - x) ** p


def rodrigues(v, axis, ang):
    """Rotate vectors v (n x 3) about unit axes (n x 3) by angles (n)."""
    c, s = np.cos(ang)[:, None], np.sin(ang)[:, None]
    return v * c + np.cross(axis, v) * s + axis * np.sum(axis * v, axis=1, keepdims=True) * (1 - c)
