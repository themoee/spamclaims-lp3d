"""Ad 6: Dre, a stylized designer-toy character built from code for Cycles: big head, big eyes, a curly top, a hoodie.

Rigid parts on a hierarchy of empties (toy joints): a pose is a dict of joint rotations. The face is parametric:
blink, eye look, brows, and a mouth decal re-shaped on the face every frame (open / wide / smile / round, with teeth and
tongue). Character-facing direction is -y; his right hand is at -x. Units are metres (toy proportions, human scale).

    dre = Character("Dre", phone=<object to put in his right hand or None>)
    dre.pose({"root_rot": (0, 0, 0), "spine": (8, 0, 0), "head": (0, 0, -5), "shoulder.R": (-40, 0, 10), ...})
    dre.face(blink=0.0, look=(0.2, 0.0), brow=(0.3, 0.3), brow_tilt=0.0, mouth=dict(open=0.4, wide=1.0, smile=0.6))
"""
import math

import bmesh
import bpy
import mathutils
import numpy as np
from mathutils.bvhtree import BVHTree

V = mathutils.Vector


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def link(ob):
    if ob.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(ob)
    return ob


def empty(name, parent=None, loc=(0, 0, 0)):
    e = link(bpy.data.objects.new(name, None))
    e.empty_display_size = 0.04
    e.parent = parent
    e.location = loc
    e.rotation_mode = "XYZ"
    return e


def mesh_obj(name, verts, faces, mat, parent=None, smooth_shade=True, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    for p in me.polygons:
        p.use_smooth = smooth_shade
    if mat is not None:
        me.materials.append(mat)
    ob = link(bpy.data.objects.new(name, me))
    ob.parent = parent
    ob.location = loc
    return ob


def bm_obj(name, bm, mat, parent=None, smooth_shade=True, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth_shade
    if mat is not None:
        me.materials.append(mat)
    ob = link(bpy.data.objects.new(name, me))
    ob.parent = parent
    ob.location = loc
    return ob


def uv_sphere(segs=48, rings=24):
    """Unit sphere vertices/faces (poles at +-z)."""
    verts, faces = [(0.0, 0.0, 1.0)], []
    for i in range(1, rings):
        th = math.pi * i / rings
        for j in range(segs):
            ph = 2 * math.pi * j / segs
            verts.append((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
    verts.append((0.0, 0.0, -1.0))
    for j in range(segs):
        faces.append((0, 1 + j, 1 + (j + 1) % segs))
    for i in range(rings - 2):
        a, b = 1 + i * segs, 1 + (i + 1) * segs
        for j in range(segs):
            faces.append((a + j, b + j, b + (j + 1) % segs, a + (j + 1) % segs))
    last = len(verts) - 1
    base = 1 + (rings - 2) * segs
    for j in range(segs):
        faces.append((base + (j + 1) % segs, base + j, last))
    return np.array(verts), faces


def ellipsoid(name, r, mat, parent=None, loc=(0, 0, 0), segs=48, rings=24):
    v, f = uv_sphere(segs, rings)
    return mesh_obj(name, v * np.array(r), f, mat, parent, loc=loc)


def capsule(name, r, length, mat, parent=None, loc=(0, 0, 0), segs=32, taper=1.0, down=True):
    """A capsule hanging from its origin along -z (down=True) or +z: radius r at the origin, r*taper at the far end."""
    verts, faces = [], []
    rings = []
    k = 10
    sgn = -1.0 if down else 1.0
    prof = []
    for i in range(k + 1):                                  # top hemisphere (at the origin)
        a = math.pi / 2 * (1 - i / k)
        prof.append((r * math.cos(a), -sgn * r * math.sin(a) * 0.999))
    for i in range(1, 7):
        t = i / 6
        prof.append((r + (r * taper - r) * t, sgn * length * t))
    for i in range(1, k + 1):                               # far hemisphere
        a = math.pi / 2 * i / k
        rr = r * taper
        prof.append((rr * math.cos(a), sgn * (length + rr * math.sin(a) * 0.999)))
    for (rad, z) in prof:
        ring = []
        for j in range(segs):
            ph = 2 * math.pi * j / segs
            ring.append(len(verts))
            verts.append((max(rad, 1e-5) * math.cos(ph), max(rad, 1e-5) * math.sin(ph), z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for j in range(segs):
            j2 = (j + 1) % segs
            faces.append((a[j], a[j2], b[j2], b[j]) if not down else (a[j], b[j], b[j2], a[j2]))
    return mesh_obj(name, verts, faces, mat, parent, loc=loc)


def tube_mesh(name, pts, radii, mat, parent=None, segs=16, closed=False, loc=(0, 0, 0), norms=None):
    """A tube through pts (parallel-transport frames) with per-point radii; open ends are capped.
    With norms (a direction per point), the cross-section is an ellipse: radii[i] = (along the normal, across)."""
    P = np.array(pts, dtype=float)
    if closed:
        T = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    else:
        T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    n = np.cross(T[0], (0.0, 0.0, 1.0))
    if np.linalg.norm(n) < 1e-6:
        n = np.cross(T[0], (1.0, 0.0, 0.0))
    n /= np.linalg.norm(n)
    verts, faces, rings = [], [], []
    for i in range(len(P)):
        if norms is not None:
            n = np.array(norms[i], dtype=float)
        n = n - np.dot(n, T[i]) * T[i]
        n /= np.linalg.norm(n)
        b = np.cross(T[i], n)
        rn, rb = radii[i] if isinstance(radii[i], (tuple, list)) else (radii[i], radii[i])
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            ring.append(len(verts))
            verts.append(tuple(P[i] + rn * math.cos(a) * n + rb * math.sin(a) * b))
        rings.append(ring)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for a, b in pairs:
        for j in range(segs):
            j2 = (j + 1) % segs
            faces.append((a[j], a[j2], b[j2], b[j]))
    if not closed:
        faces.append(tuple(reversed(rings[0])))
        faces.append(tuple(rings[-1]))
    ob = mesh_obj(name, verts, faces, mat, parent, loc=loc)
    return ob


def rounded_box_mesh(size, radius, segs=6):
    """A box with rounded edges and corners (superellipsoid-like), size = full extents, centred at the origin."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=V(size), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=radius, segments=segs, profile=0.5, affect="EDGES")
    return bm


# ============================================================================================ materials
def principled(name, base, rough=0.5, metal=0.0, sss=0.0, sss_r=(0.1, 0.05, 0.03), sheen=0.0, coat=0.0, spec=0.5,
               transmission=0.0, ior=1.45, emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*base, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Subsurface Weight"].default_value = sss
    p.inputs["Subsurface Radius"].default_value = sss_r
    p.inputs["Sheen Weight"].default_value = sheen
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Specular IOR Level"].default_value = spec
    p.inputs["Transmission Weight"].default_value = transmission
    p.inputs["IOR"].default_value = ior
    if emission is not None:
        p.inputs["Emission Color"].default_value = (*emission, 1)
        p.inputs["Emission Strength"].default_value = strength
    return m


def _bump(m, scale, strength, distance=0.002, kind="noise", detail=4.0, coord="Object"):
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tx = nt.nodes.new("ShaderNodeTexNoise" if kind == "noise" else "ShaderNodeTexVoronoi")
    tx.inputs["Scale"].default_value = scale
    if kind == "noise":
        tx.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs[coord], tx.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    bp.inputs["Distance"].default_value = distance
    nt.links.new(tx.outputs[0 if kind == "noise" else "Distance"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], p.inputs["Normal"])
    return m


def skin_material(name, base):
    m = principled(name, base, rough=0.4, sss=0.2, sss_r=(1.0, 0.4, 0.25), sheen=0.12)
    m.node_tree.nodes["Principled BSDF"].inputs["Subsurface Scale"].default_value = 0.015
    return _bump(m, 700.0, 0.12, 0.0004)


def hoodie_material(name, base):
    m = principled(name, base, rough=0.86, sheen=0.7)
    m.node_tree.nodes["Principled BSDF"].inputs["Sheen Roughness"].default_value = 0.45
    return _bump(m, 1400.0, 0.25, 0.0005, detail=2.0)


def hair_material(name):
    m = principled(name, (0.016, 0.010, 0.007), rough=0.48, sheen=0.55, spec=0.45)
    m.node_tree.nodes["Principled BSDF"].inputs["Sheen Roughness"].default_value = 0.3
    return _bump(m, 160.0, 0.8, 0.003, kind="voronoi")


def iris_material(name, iris=(0.13, 0.055, 0.018)):
    """Sclera / iris / pupil by the angle from the eyeball's forward axis (-y in the eye's object space)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Roughness"].default_value = 0.25
    p.inputs["Subsurface Weight"].default_value = 0.1
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nrm = nt.nodes.new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
    nt.links.new(tc.outputs["Object"], nrm.inputs[0])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(nrm.outputs[0], sep.inputs[0])
    fw = nt.nodes.new("ShaderNodeMath")
    fw.operation = "MULTIPLY"
    fw.inputs[1].default_value = -1.0
    nt.links.new(sep.outputs["Y"], fw.inputs[0])              # cos(angle from forward)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    # positions are cos(angle): sclera below ~0.80, limbal ring, iris, pupil above ~0.965
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.82, 0.8, 0.78, 1)
    cr.elements[1].position, cr.elements[1].color = 0.79, (0.8, 0.78, 0.76, 1)
    for pos, col in [(0.81, (0.02, 0.012, 0.008, 1)), (0.835, (iris[0] * 0.6, iris[1] * 0.6, iris[2] * 0.6, 1)),
                     (0.93, (iris[0] * 1.5, iris[1] * 1.5, iris[2] * 1.5, 1)), (0.952, (iris[0], iris[1], iris[2], 1)),
                     (0.958, (0.005, 0.004, 0.004, 1)), (1.0, (0.002, 0.002, 0.002, 1))]:
        e = cr.elements.new(pos)
        e.color = col
    nt.links.new(fw.outputs[0], ramp.inputs[0])
    # radial streaks in the iris
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 60.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.35
    nt.links.new(ramp.outputs[0], mix.inputs["A"])
    nt.links.new(nz.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])
    return m


# ============================================================================================ the character
class Character:
    def __init__(self, name="Dre", skin=(0.2, 0.095, 0.052), hoodie=(0.88, 0.42, 0.04), phone=None, opts=None):
        self.name = name
        self.opts = opts or {}
        self.m_skin = skin_material(f"{name}_skin", skin)
        self.m_hood = hoodie_material(f"{name}_hoodie", hoodie)
        self.m_hood_dark = hoodie_material(f"{name}_hoodie_rib", tuple(c * 0.78 for c in hoodie))
        self.m_hair = hair_material(f"{name}_hair")
        self.m_eye = iris_material(f"{name}_eye")
        self.m_cornea = principled(f"{name}_cornea", (1, 1, 1), rough=0.0, transmission=1.0, ior=1.336, spec=0.9)
        self.m_dark = principled(f"{name}_mouth", (0.05, 0.008, 0.012), rough=0.6)
        self.m_teeth = principled(f"{name}_teeth", (0.86, 0.84, 0.78), rough=0.25, sss=0.1)
        self.m_tongue = principled(f"{name}_tongue", (0.42, 0.06, 0.07), rough=0.45, sss=0.3)
        self.m_brow = principled(f"{name}_brow", (0.006, 0.004, 0.003), rough=0.75, sheen=0.08)
        self.m_lash = principled(f"{name}_lash", (0.008, 0.005, 0.004), rough=0.5)
        self.m_string = principled(f"{name}_string", (0.85, 0.84, 0.8), rough=0.7, sheen=0.4)
        self.m_aglet = principled(f"{name}_aglet", (0.8, 0.8, 0.82), rough=0.25, metal=1.0)
        self.m_sole = principled(f"{name}_sole", (0.9, 0.9, 0.88), rough=0.5)
        self.J = {}
        self._mouth_state = None
        self._build_rig()
        self._build_body()
        self._build_head()
        self.phone = phone
        if phone is not None:
            phone.parent = self.J["wrist.R"]

    # ------------------------------------------------------------------------------------ rig
    def _build_rig(self):
        n = self.name
        J = self.J
        J["root"] = empty(f"{n}_root")
        J["spine"] = empty(f"{n}_spine", J["root"], (0, 0, 0.0))
        J["neck"] = empty(f"{n}_neck", J["spine"], (0, 0.0, 0.445))
        J["head"] = empty(f"{n}_head", J["neck"], (0, 0, 0.025))
        for side, sx in (("L", 1.0), ("R", -1.0)):
            J[f"shoulder.{side}"] = empty(f"{n}_shoulder.{side}", J["spine"], (0.228 * sx, 0.0, 0.365))
            J[f"elbow.{side}"] = empty(f"{n}_elbow.{side}", J[f"shoulder.{side}"], (0, 0, -0.205))
            J[f"wrist.{side}"] = empty(f"{n}_wrist.{side}", J[f"elbow.{side}"], (0, 0, -0.185))
            J[f"thumb.{side}"] = empty(f"{n}_thumb.{side}", J[f"wrist.{side}"], (-0.03 * sx, -0.012, -0.03))

    # ------------------------------------------------------------------------------------ body (hoodie)
    def _build_body(self):
        n, J = self.name, self.J
        # torso: a soft rounded block, a little narrower at the waist; the hem rib at the bottom
        bm = rounded_box_mesh((0.45, 0.29, 0.45), 0.12, 7)
        for v in bm.verts:
            t = (v.co.z + 0.225) / 0.45                     # 0 at the hem, 1 at the shoulders
            v.co.x *= 0.92 + 0.08 * t + 0.03 * math.sin(math.pi * t)
            v.co.y *= 0.96 + 0.06 * math.sin(math.pi * t)
            v.co.z += 0.225
        self.torso = bm_obj(f"{n}_torso", bm, self.m_hood, J["spine"])
        sub = self.torso.modifiers.new("Sub", "SUBSURF")
        sub.levels, sub.render_levels = 1, 2
        hem = bmesh.new()
        bmesh.ops.create_cone(hem, cap_ends=False, segments=48, radius1=1.0, radius2=1.0, depth=0.035)
        for v in hem.verts:
            v.co.x *= 0.215
            v.co.y *= 0.138
        self.hem = bm_obj(f"{n}_hem", hem, self.m_hood_dark, J["spine"], loc=(0, 0, 0.02))
        sol = self.hem.modifiers.new("Thick", "SOLIDIFY")
        sol.thickness = 0.012
        # kangaroo pocket: a soft panel on the belly
        pk = rounded_box_mesh((0.25, 0.03, 0.13), 0.012, 3)
        self.pocket = bm_obj(f"{n}_pocket", pk, self.m_hood, J["spine"], loc=(0, -0.13, 0.12))
        # hood: rolled fabric around the neck and a fold at the back
        hood = bmesh.new()
        bmesh.ops.create_circle(hood, segments=48, radius=1.0)
        ring = []
        for i in range(48):
            a = 2 * math.pi * i / 48
            ring.append((math.cos(a), math.sin(a)))
        bm2 = bmesh.new()
        rings = []
        for i, (cx, cy) in enumerate(ring):
            # the hood is thicker at the back, thinner at the front opening
            back = 0.5 + 0.5 * cy                             # 1 at the back (+y), 0 at the front
            R, r = 0.112 + 0.02 * back, 0.036 + 0.034 * back
            cr = []
            for j in range(20):
                b = 2 * math.pi * j / 20
                x = (R + r * math.cos(b)) * cx
                y = (R + r * math.cos(b)) * cy
                z = r * math.sin(b) * (1.0 + 0.6 * back) + 0.03 * back
                cr.append(bm2.verts.new((x, y, z)))
            rings.append(cr)
        for i in range(48):
            a, b = rings[i], rings[(i + 1) % 48]
            for j in range(20):
                j2 = (j + 1) % 20
                bm2.faces.new((a[j], b[j], b[j2], a[j2]))
        bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces[:])
        hood.free()
        self.hood = bm_obj(f"{n}_hood", bm2, self.m_hood, J["spine"], loc=(0, 0.012, 0.432))
        sub = self.hood.modifiers.new("Sub", "SUBSURF")
        sub.levels, sub.render_levels = 1, 1
        # drawstrings with metal tips
        for sx in (1, -1):
            s = capsule(f"{n}_string{sx}", 0.0055, 0.12, self.m_string, J["spine"], loc=(0.042 * sx, -0.128, 0.418), segs=12)
            s.rotation_euler = (math.radians(-8), math.radians(4 * sx), 0)
            capsule(f"{n}_aglet{sx}", 0.0062, 0.018, self.m_aglet, s, loc=(0, 0, -0.118), segs=12)
        # neck
        capsule(f"{n}_neckmesh", 0.064, 0.07, self.m_skin, J["neck"], loc=(0, 0, 0.075), segs=32)
        # arms: sleeves, ribbed cuffs, mitten hands with a thumb
        for side, sx in (("L", 1.0), ("R", -1.0)):
            capsule(f"{n}_upper.{side}", 0.06, 0.2, self.m_hood, J[f"shoulder.{side}"], segs=32, taper=0.92)
            capsule(f"{n}_fore.{side}", 0.053, 0.17, self.m_hood, J[f"elbow.{side}"], segs=32, taper=0.95)
            cuff = bmesh.new()
            bmesh.ops.create_cone(cuff, cap_ends=False, segments=32, radius1=0.047, radius2=0.044, depth=0.03)
            cf = bm_obj(f"{n}_cuff.{side}", cuff, self.m_hood_dark, J[f"wrist.{side}"], loc=(0, 0, 0.012))
            sol = cf.modifiers.new("Thick", "SOLIDIFY")
            sol.thickness = 0.008
            hand = rounded_box_mesh((0.07, 0.038, 0.082), 0.026, 5)
            for v in hand.verts:
                v.co.z -= 0.043
                v.co.x *= 1.0 - 0.12 * smooth((-v.co.z - 0.05) / 0.04)
            h = bm_obj(f"{n}_hand.{side}", hand, self.m_skin, J[f"wrist.{side}"], loc=(0, 0, -0.005))
            sub = h.modifiers.new("Sub", "SUBSURF")
            sub.levels, sub.render_levels = 1, 2
            th = capsule(f"{n}_thumbmesh.{side}", 0.015, 0.035, self.m_skin, J[f"thumb.{side}"], segs=16)
            th.rotation_euler = (0, math.radians(-35 * sx), 0)

    # ------------------------------------------------------------------------------------ head and face
    def _build_head(self):
        n, J = self.name, self.J
        RX, RY, RZ = 0.205, 0.19, 0.2
        v, f = uv_sphere(160, 80)
        out = []
        for x, y, z in v:
            jaw = smooth((0.1 - z) / 1.05)                   # 0 above the middle, 1 at the chin
            cheek = math.exp(-((z + 0.25) / 0.28) ** 2) * max(0.0, -y)
            X = x * RX * (1 - 0.13 * jaw) * (1 + 0.08 * cheek)
            Y = y * RY * (1 - 0.06 * jaw)
            if y > 0:
                Y *= 1.05
            else:
                Y *= 1 - 0.07 * math.exp(-(z / 0.55) ** 2)   # a flatter face
            Z = z * RZ - 0.012 * jaw * max(0.0, -y)
            out.append((X, Y, Z))
        self.HC = (0.0, 0.0, 0.18)                           # head centre above the head joint
        hv = np.array(out) + np.array(self.HC)
        self.head = mesh_obj(f"{n}_headmesh", hv, f, self.m_skin, J["head"])
        self.head_bvh = BVHTree.FromPolygons([tuple(p) for p in hv], [tuple(q) for q in f])

        def surf(x, z, push=0.0):
            loc, nor, _, _ = self.head_bvh.ray_cast(V((x, -1.0, z)), V((0, 1, 0)))
            return loc + nor * push, nor

        self.surf = surf
        hc = self.HC[2]
        # ears
        for sx in (1, -1):
            e = ellipsoid(f"{n}_ear{sx}", (0.024, 0.036, 0.05), self.m_skin, J["head"], loc=(0.2 * sx, 0.012, hc - 0.018))
            e.rotation_euler = (0, 0, math.radians(12 * sx))
        # nose
        p, nor = surf(0.0, hc - 0.032, -0.007)
        self.nose = ellipsoid(f"{n}_nose", (0.03, 0.022, 0.026), self.m_skin, J["head"], loc=tuple(p))
        # eyes: eyeball (sclera/iris/pupil), cornea, upper lid with a lash line, a soft lower lid
        self.eyes, self.lids, self.lowlids = [], [], []
        RE = 0.045
        self.RE = RE
        for side, sx in (("L", 1.0), ("R", -1.0)):
            p, nor = surf(0.072 * sx, hc + 0.012)
            c = p + V((0, RE * 0.58, 0))
            piv = empty(f"{n}_eye.{side}", J["head"], tuple(c))
            ball = ellipsoid(f"{n}_ball.{side}", (RE, RE, RE), self.m_eye, piv)
            ellipsoid(f"{n}_cornea.{side}", (RE * 1.03, RE * 1.03, RE * 1.03), self.m_cornea, piv)
            # upper lid: the upper hemisphere of a shell just outside the cornea, rotated about x (see face())
            lid_piv = empty(f"{n}_lid.{side}", J["head"], tuple(c))
            vv, ff = uv_sphere(64, 32)
            keep = [i for i, q in enumerate(ff) if min(vv[k][2] for k in q) > -0.01]
            RL = RE * 1.12
            lid = mesh_obj(f"{n}_lidmesh.{side}", vv * RL, [ff[i] for i in keep], self.m_skin, lid_piv)
            sol = lid.modifiers.new("Thick", "SOLIDIFY")
            sol.thickness = 0.0035
            sol.offset = 1.0
            # lash line along the lid rim (the equator of the shell)
            ring = [(math.cos(2 * math.pi * k / 64) * (RL + 0.0035), math.sin(2 * math.pi * k / 64) * (RL + 0.0035), 0.0)
                    for k in range(64)]
            tube_mesh(f"{n}_lash.{side}", ring, [0.0019] * 64, self.m_lash, lid_piv, segs=8, closed=True)
            # lower lid: a small cap from below; it rises for smiles and squints
            low_piv = empty(f"{n}_lowlid.{side}", J["head"], tuple(c))
            keep2 = [i for i, q in enumerate(ff) if max(vv[k][2] for k in q) < -0.5]
            low = mesh_obj(f"{n}_lowmesh.{side}", vv * RE * 1.11, [ff[i] for i in keep2], self.m_skin, low_piv)
            sol = low.modifiers.new("Thick", "SOLIDIFY")
            sol.thickness = 0.003
            sol.offset = 1.0
            self.eyes.append(piv)
            self.lids.append(lid_piv)
            self.lowlids.append(low_piv)
        # brows: thick tubes that follow the forehead, inner end fuller
        self.brows = []
        for side, sx in (("L", 1.0), ("R", -1.0)):
            p, nor = surf(0.072 * sx, hc + 0.094, 0.0)
            piv = empty(f"{n}_brow.{side}", J["head"], tuple(p))
            pts, rad, nrm = [], [], []
            for k in range(13):
                u = k / 12                                   # 0 inner .. 1 outer
                x = (0.038 + 0.068 * u) * sx
                z = hc + 0.088 + 0.011 * math.sin(math.pi * u) - 0.005 * u
                q, nq = surf(x, z, 0.0022)
                pts.append(tuple(q - p))
                env = 0.35 + 0.65 * math.sin(math.pi * min(1.0, 0.1 + u * 0.95))
                rad.append((0.0042 * env, (0.0115 - 0.004 * u) * env))
                nrm.append(tuple(nq))
            tube_mesh(f"{n}_browmesh.{side}", pts, rad, self.m_brow, piv, segs=16, norms=nrm)
            piv["rest"] = tuple(p)
            self.brows.append(piv)
        # hair: one continuous volume over the scalp (a thick curly top, a short fade on the sides and back); the curls
        # are displaced in by a Voronoi texture weighted by the thickness, so the hairline and the fade stay clean
        dirs = np.asarray(v)
        nrm = np.array([vt.normal[:] for vt in self.head.data.vertices])
        outward = np.sign(np.einsum("ij,ij->i", nrm, hv - np.array(self.HC)))
        nrm = nrm * outward[:, None]
        dy, dz = dirs[:, 1], dirs[:, 2]
        hairline = 0.08 + 0.66 * np.clip(-dy, 0, 1) ** 1.2       # the hairline climbs toward the forehead
        m = smooth_np((dz - hairline) / 0.08)
        top = smooth_np((dz - 0.3) / 0.5) * smooth_np((dz - hairline) / 0.3)   # volume builds up behind the hairline
        thick = m * (0.003 + 0.052 * top)
        keepf = [q for q in f if min(m[k] for k in q) > 0.01]
        idx = sorted({k for q in keepf for k in q})
        remap = {k: i for i, k in enumerate(idx)}
        pts = hv[idx] + nrm[idx] * (thick[idx] + 0.0012)[:, None]
        self.hair = mesh_obj(f"{n}_hair", pts, [tuple(remap[k] for k in q) for q in keepf], self.m_hair, J["head"])
        vg = self.hair.vertex_groups.new(name="curl")
        for i, k in enumerate(idx):
            vg.add([i], float(top[k] * m[k]), "REPLACE")
        sub = self.hair.modifiers.new("Sub", "SUBSURF")
        sub.levels, sub.render_levels = 1, 2
        tex = bpy.data.textures.new(f"{n}_curls", "VORONOI")
        tex.noise_scale = float(self.opts.get("curl_scale", 0.02))
        tex.distance_metric = "DISTANCE"
        disp = self.hair.modifiers.new("Curls", "DISPLACE")
        disp.texture = tex
        disp.texture_coords = "LOCAL"
        disp.vertex_group = "curl"
        disp.strength = float(self.opts.get("curl_strength", 0.028))
        disp.mid_level = 0.55
        # mouth decal (dark), tongue and upper teeth: meshes rewritten by face()
        self.mouth_parts = {}
        for key, mat, push in (("mouth", self.m_dark, 0.0009), ("tongue", self.m_tongue, 0.0012), ("teeth", self.m_teeth, 0.0013)):
            ob = mesh_obj(f"{n}_{key}", [(0, 0, 0), (0.001, 0, 0), (0, 0, 0.001)], [(0, 1, 2)], mat, J["head"], smooth_shade=True)
            self.mouth_parts[key] = (ob, push)
        self.MOUTH_Z = hc - 0.1
        self.face(mouth=dict(open=0.0, wide=1.0, smile=0.3))

    # ------------------------------------------------------------------------------------ face controls
    def face(self, blink=0.0, look=(0.0, 0.0), brow=(0.0, 0.0), brow_tilt=(0.0, 0.0), squint=0.0, mouth=None):
        """blink 0 open .. 1 closed; look = (right/left, up/down) in -1..1; brow = raise per side (-1..1);
        brow_tilt = inner-end angle per side (+ worried/sad, - angry); squint raises the lower lids (smiles)."""
        for piv in self.eyes:
            piv.rotation_euler = (math.radians(-18 * look[1]), 0, math.radians(26 * look[0]))
        for lid in self.lids:
            # the lid is the upper hemisphere: rotated back (-x) it uncovers the eye, forward (+x) it closes it.
            # wide (shock) via a negative blink, down to -1
            th_open, th_closed = -34.0, 88.0
            if blink < 0:
                th = th_open + 30.0 * blink
            else:
                th = th_open + (th_closed - th_open) * blink
            th += 22.0 * squint * (1 - max(0.0, blink)) - 10.0 * look[1] * (1 - max(0.0, blink))
            lid.rotation_euler = (math.radians(th), 0, 0)
        for low in self.lowlids:
            low.rotation_euler = (math.radians(38 - 60 * squint), 0, 0)
        for k, piv in enumerate(self.brows):
            sx = 1.0 if k == 0 else -1.0
            rest = V(piv["rest"])
            piv.location = rest + V((0, 0, 0.022 * brow[k]))
            piv.rotation_euler = (0, math.radians(-14 * brow_tilt[k] * sx), 0)
        if mouth is not None:
            self.set_mouth(**mouth)

    def set_mouth(self, open=0.0, wide=1.0, smile=0.0, round=0.0, teeth=1.0):
        st = (round_(open), round_(wide), round_(smile), round_(round), round_(teeth))
        if st == self._mouth_state:
            return
        self._mouth_state = st
        a = 0.043 * wide * (1 - 0.42 * round)                 # half width
        N = 40
        xs = [a * math.cos(math.pi * (1 - i / (N - 1))) for i in range(N)]   # denser at the corners

        def base(x):
            u = x / a
            return smile * 0.011 * (u * u) - smile * 0.004

        def thick(x):
            u = x / a
            return 0.0028 * (1 - u * u) ** 0.5 + 0.0006

        op = open
        up_amt, down_amt = 0.007 * op, 0.034 * op * (1 + 0.25 * round)

        def upper(x):
            u = x / a
            return base(x) + thick(x) / 2 + up_amt * (1 - u * u) ** 0.6 + 0.004 * round * op * (1 - u * u) ** 0.5

        def lower(x):
            u = x / a
            return base(x) - thick(x) / 2 - down_amt * (1 - u * u) ** (0.7 - 0.25 * round)

        # the mouth: a strip between the upper and lower lip curves (valid for any smile curve)
        self._decal("mouth", xs, [upper(x) for x in xs], [lower(x) for x in xs])
        gap = upper(0) - lower(0)
        if op > 0.12:
            ht = min(0.009 * op + 0.002, gap * 0.42) * teeth
            tx = [x for x in xs if abs(x) < a * 0.8]
            top = [upper(x) - 0.0012 for x in tx]
            bot = [max(upper(x) - 0.0012 - ht * max(0.0, 1 - (x / a) ** 2) ** 0.3, lower(x) + 0.0012) for x in tx]
            self._decal("teeth", tx, top, bot)
        else:
            self._decal("teeth", None, None, None)
        if op > 0.25:
            tw = a * (0.62 - 0.2 * round)
            tl = [x for x in xs if abs(x) < tw]
            lo = [lower(x) + 0.0012 for x in tl]
            hi = [min(lower(x) + 0.0012 + gap * 0.42 * max(0.0, 1 - (x / tw) ** 2) ** 0.5, upper(x) - 0.004) for x in tl]
            hi = [max(h, l) for h, l in zip(hi, lo)]
            self._decal("tongue", tl, hi, lo)
        else:
            self._decal("tongue", None, None, None)

    def _decal(self, key, xs, top, bot):
        """A strip mesh between two curves (x, z offsets from the mouth centre), projected onto the face."""
        ob, push = self.mouth_parts[key]
        me = ob.data
        if xs is None or len(xs) < 2:
            verts, faces = [(0, 0, 0), (1e-6, 0, 0), (0, 0, 1e-6)], [(0, 1, 2)]
        else:
            verts = []
            for row in (top, bot):
                for x, z in zip(xs, row):
                    loc, nor, _, _ = self.head_bvh.ray_cast(V((x, -1.0, self.MOUTH_Z + z)), V((0, 1, 0)))
                    if loc is None:
                        loc, nor = V((x, -0.17, self.MOUTH_Z + z)), V((0, -1, 0))
                    verts.append(tuple(loc + nor * push))
            n = len(xs)
            faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
        me.clear_geometry()
        me.from_pydata(verts, [], faces)
        me.update()
        for p in me.polygons:
            p.use_smooth = True

    # ------------------------------------------------------------------------------------ pose
    def pose(self, p):
        """p: {"root_loc": (x, y, z), "root_rot": (deg x, y, z), joint name: (deg x, y, z), ...}"""
        for k, v in p.items():
            if k == "root_loc":
                self.J["root"].location = v
            elif k == "root_rot":
                self.J["root"].rotation_euler = tuple(math.radians(a) for a in v)
            elif k in self.J:
                self.J[k].rotation_euler = tuple(math.radians(a) for a in v)

    def head_world(self):
        return self.J["head"].matrix_world @ V(self.HC)

    def eye_world(self):
        return (self.eyes[0].matrix_world.translation + self.eyes[1].matrix_world.translation) / 2


def round_(v):
    return round(float(v), 4)


def smooth_np(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)
