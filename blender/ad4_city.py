"""Ad 4's night city (Blender module): thousands of buildings in one mesh with procedural lit windows, rooftop gear,
street lights, moving traffic, a river with bridges, distant hills and a starry sky.

Every building carries attributes the facade shader reads: rnd (its own random), lit (how many windows are on),
tint (warm to cool light), glass (curtain-wall tower or not), bay (window width) and wave (when it turns orange:
the city-wide "every text after STOP" beat). The shader's T node is the scene time, set every frame by the scene.

Units are meters, Z up. The hero tower stands at the origin (the scene builds it); the city leaves its block empty.
"""
import math
import random

import bmesh
import bpy
import numpy as np

PITCH, BLOCK, STREET = 108.0, 90.0, 18.0
RADIUS = 2600.0
DOWNTOWN = (40.0, 420.0)          # the skyline sits behind the hero tower as the camera comes in from the south
RIVER_W = 130.0
BUILDINGS = []                    # (cx, cy, w, l, h, wave) of every building, filled by build_buildings()


def river_x(y):
    """The river's centerline (x at a given y): a long S-curve east of downtown."""
    return 520.0 + 260.0 * math.sin(y / 620.0) + 90.0 * math.sin(y / 230.0 + 1.3)


def in_river(x, y, pad=0.0):
    return abs(x - river_x(y)) < RIVER_W / 2 + pad


def _node(nt, kind, loc, **kw):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in kw.items():
        if k == "op":
            n.operation = v
        else:
            setattr(n, k, v)
    return n


def _math(nt, op, a, b=None, c=None, clamp=False):
    n = _node(nt, "ShaderNodeMath", (0, 0), op=op)
    n.use_clamp = clamp
    for i, v in enumerate((a, b, c)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


# ---------------------------------------------------------------------------------------------- buildings
def _box(bm, lay, x0, y0, x1, y1, z0, z1, attrs):
    vs = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                    (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for f in ((4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):     # no floor face
        fc = bm.faces.new([vs[k] for k in f])
        for name, v in attrs.items():
            fc[lay[name]] = v


def _cyl(bm, lay, cx, cy, r, z0, z1, attrs, segs=20):
    ring0 = [bm.verts.new((cx + r * math.cos(2 * math.pi * k / segs), cy + r * math.sin(2 * math.pi * k / segs), z0)) for k in range(segs)]
    ring1 = [bm.verts.new((cx + r * math.cos(2 * math.pi * k / segs), cy + r * math.sin(2 * math.pi * k / segs), z1)) for k in range(segs)]
    faces = [bm.faces.new((ring0[k], ring0[(k + 1) % segs], ring1[(k + 1) % segs], ring1[k])) for k in range(segs)]
    faces.append(bm.faces.new(ring1))
    for fc in faces:
        for name, v in attrs.items():
            fc[lay[name]] = v


def build_buildings(seed=7, hero=(0.0, 0.0), wave_speed=900.0, wave_t0=13.6, keep_clear=None):
    """keep_clear: list of (x, y, r) discs with no buildings (the hero block, the camera's path at low height)."""
    rng = random.Random(seed)
    bm = bmesh.new()
    names = ["rnd", "lit", "tint", "glass", "bay", "wave", "hgt"]
    lay = {n: bm.faces.layers.float.new(n) for n in names}
    tops = []                      # (x, y, z, height) of tall roofs: antennas, beacons
    roofs = []                     # (x, y, z, w, l) roof rectangles: rooftop gear
    n_b = 0
    nb = int(RADIUS / PITCH) + 1
    for bi in range(-nb, nb + 1):
        for bj in range(-nb, nb + 1):
            cx, cy = bi * PITCH, bj * PITCH
            if math.hypot(cx, cy) > RADIUS + rng.uniform(-200, 120):
                continue
            if in_river(cx, cy, pad=BLOCK / 2):
                continue
            if keep_clear and any(math.hypot(cx - kx, cy - ky) < kr for kx, ky, kr in keep_clear):
                continue
            dd = math.hypot(cx - DOWNTOWN[0], cy - DOWNTOWN[1])
            core = math.exp(-(dd / 620.0) ** 2)
            ring = math.exp(-(math.hypot(cx, cy) / 1500.0) ** 2)
            park = rng.random() < 0.035 and dd > 500
            if park:
                continue
            # lots inside the block
            lots = rng.choice([1, 1, 2, 2, 3, 4]) if core < 0.5 else rng.choice([1, 1, 2])
            half = BLOCK / 2
            splits = sorted(rng.uniform(-half * 0.6, half * 0.6) for _ in range(lots - 1))
            edges = [-half] + splits + [half]
            for k in range(lots):
                a, b = edges[k] + 2.0, edges[k + 1] - 2.0
                if b - a < 10:
                    continue
                vertical = rng.random() < 0.5
                x0, x1 = (cx + a, cx + b) if vertical else (cx - half + 3, cx + half - 3)
                y0, y1 = (cy - half + 3, cy + half - 3) if vertical else (cy + a, cy + b)
                if not vertical and lots > 1:
                    pass
                base_h = 9 + 30 * ring + 240 * core * rng.random() ** 1.6
                h = max(7.0, rng.gauss(1.0, 0.28) * base_h)
                glass = 1.0 if (h > 70 and rng.random() < 0.55) else 0.0
                u_ = rng.random()
                lit = rng.uniform(0.03, 0.16) if u_ < 0.58 else (rng.uniform(0.16, 0.38) if u_ < 0.9 else rng.uniform(0.45, 0.82))
                attrs = {"rnd": rng.random(), "lit": lit,
                         "tint": rng.random(), "glass": glass, "bay": rng.choice([2.6, 3.0, 3.4, 4.2]),
                         "wave": wave_t0 + math.hypot(cx - hero[0], cy - hero[1]) / wave_speed + rng.uniform(-0.12, 0.12),
                         "hgt": h}
                w, l = x1 - x0, y1 - y0
                if False:
                    r = min(w, l) / 2 - 2
                    _cyl(bm, lay, (x0 + x1) / 2, (y0 + y1) / 2, r, 0, h, attrs)
                    tops.append(((x0 + x1) / 2, (y0 + y1) / 2, h, h))
                elif h > 60 and rng.random() < 0.7:
                    # setbacks: two or three stacked boxes, each narrower
                    steps = rng.choice([2, 3])
                    z = 0.0
                    for s in range(steps):
                        frac = [0.55, 0.3, 0.15][s] if steps == 3 else [0.62, 0.38][s]
                        hh = h * frac
                        ins = s * min(w, l) * 0.13
                        _box(bm, lay, x0 + ins, y0 + ins, x1 - ins, y1 - ins, z, z + hh, attrs)
                        roofs.append(((x0 + x1) / 2, (y0 + y1) / 2, z + hh, w - 2 * ins, l - 2 * ins))
                        z += hh
                    tops.append(((x0 + x1) / 2, (y0 + y1) / 2, z, h))
                else:
                    _box(bm, lay, x0, y0, x1, y1, 0, h, attrs)
                    roofs.append(((x0 + x1) / 2, (y0 + y1) / 2, h, w, l))
                    if h > 45:
                        tops.append(((x0 + x1) / 2, (y0 + y1) / 2, h, h))
                BUILDINGS.append(((x0 + x1) / 2, (y0 + y1) / 2, w, l, h, attrs["wave"]))
                n_b += 1
    me = bpy.data.meshes.new("CityBuildings")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("CityBuildings", me)
    return ob, tops, roofs, n_b


def facade_material(name="CityFacade"):
    """Lit windows on a floor/bay grid, warm to cool, some TV-blue flicker; turns orange after the building's wave
    time; glass towers are darker and glossier. Node 'T' = scene time (seconds)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = _node(nt, "ShaderNodeOutputMaterial", (1800, 0))
    T = _node(nt, "ShaderNodeValue", (-1400, -700))
    T.name = T.label = "T"
    geo = _node(nt, "ShaderNodeNewGeometry", (-1400, 0))
    pos = _node(nt, "ShaderNodeSeparateXYZ", (-1200, 100))
    nt.links.new(geo.outputs["Position"], pos.inputs[0])
    nrm = _node(nt, "ShaderNodeSeparateXYZ", (-1200, -150))
    nt.links.new(geo.outputs["Normal"], nrm.inputs[0])

    def attr(n, y):
        a = _node(nt, "ShaderNodeAttribute", (-1400, y), attribute_name=n)
        return a.outputs["Fac"]
    rnd, lit, tint, glass, bay, wave = (attr(n, -250 - 90 * i) for i, n in enumerate(["rnd", "lit", "tint", "glass", "bay", "wave"]))
    # facade coordinate: x on faces that look along y, y on faces that look along x
    ax = _math(nt, "ABSOLUTE", nrm.outputs[0])
    ay = _math(nt, "ABSOLUTE", nrm.outputs[1])
    u = _math(nt, "ADD", _math(nt, "MULTIPLY", pos.outputs[0], ay), _math(nt, "MULTIPLY", pos.outputs[1], ax))
    uu = _math(nt, "DIVIDE", u, bay)
    zz = _math(nt, "DIVIDE", pos.outputs[2], 3.6)
    fu, fz = _math(nt, "FRACT", uu), _math(nt, "FRACT", zz)
    win_u = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", fu, 0.14), _math(nt, "LESS_THAN", fu, 0.86))
    win_z = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", fz, 0.22), _math(nt, "LESS_THAN", fz, 0.84))
    win = _math(nt, "MULTIPLY", win_u, win_z)
    vert = _math(nt, "LESS_THAN", _math(nt, "ABSOLUTE", nrm.outputs[2]), 0.5)          # facades only, not roofs
    win = _math(nt, "MULTIPLY", win, vert)
    # per-window random: white noise on (floor, bay, building)
    comb = _node(nt, "ShaderNodeCombineXYZ", (-400, 300))
    nt.links.new(_math(nt, "FLOOR", uu), comb.inputs[0])
    nt.links.new(_math(nt, "FLOOR", zz), comb.inputs[1])
    nt.links.new(_math(nt, "MULTIPLY", rnd, 917.0), comb.inputs[2])
    wn = _node(nt, "ShaderNodeTexWhiteNoise", (-200, 300), noise_dimensions="3D")
    nt.links.new(comb.outputs[0], wn.inputs["Vector"])
    wn2 = _node(nt, "ShaderNodeTexWhiteNoise", (-200, 100), noise_dimensions="4D")
    nt.links.new(comb.outputs[0], wn2.inputs["Vector"])
    wn2.inputs["W"].default_value = 3.7
    # orange after the wave (smooth over 0.6 s), and more windows come on
    og = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", T.outputs[0], wave), 1.6, clamp=True)
    og = _math(nt, "MULTIPLY", og, _math(nt, "SUBTRACT", 3.0, _math(nt, "MULTIPLY", og, 2.0)))
    og = _math(nt, "MULTIPLY", og, _math(nt, "MULTIPLY", og, 1.0))     # smoothstep-ish ramp
    fl = _node(nt, "ShaderNodeCombineXYZ", (-400, 500))
    nt.links.new(_math(nt, "FLOOR", zz), fl.inputs[0])
    nt.links.new(_math(nt, "MULTIPLY", rnd, 331.0), fl.inputs[1])
    fn = _node(nt, "ShaderNodeTexWhiteNoise", (-200, 500), noise_dimensions="3D")
    nt.links.new(fl.outputs[0], fn.inputs["Vector"])
    floor_k = _math(nt, "MULTIPLY_ADD", fn.outputs["Value"], 1.9, 0.15)        # 0.15 .. 2.05 per floor
    lit_now = _math(nt, "ADD", _math(nt, "MULTIPLY", lit, floor_k), _math(nt, "MULTIPLY", og, 0.06))
    on = _math(nt, "LESS_THAN", wn.outputs["Value"], lit_now)
    em_mask = _math(nt, "MULTIPLY", win, on)
    # colour: warm..cool per window, a few TV-blue windows flicker
    warm = _node(nt, "ShaderNodeRGB", (0, 600)); warm.outputs[0].default_value = (1.0, 0.66, 0.36, 1)
    cool = _node(nt, "ShaderNodeRGB", (0, 450)); cool.outputs[0].default_value = (0.78, 0.88, 1.0, 1)
    mixc = _node(nt, "ShaderNodeMix", (250, 520), data_type="RGBA")
    k = _math(nt, "MULTIPLY", wn2.outputs["Value"], _math(nt, "ADD", tint, 0.25))
    nt.links.new(_math(nt, "MINIMUM", k, 1.0), mixc.inputs[0])
    nt.links.new(warm.outputs[0], mixc.inputs[6]); nt.links.new(cool.outputs[0], mixc.inputs[7])
    orange = _node(nt, "ShaderNodeRGB", (250, 350)); orange.outputs[0].default_value = (1.0, 0.34, 0.05, 1)
    mixo = _node(nt, "ShaderNodeMix", (500, 450), data_type="RGBA")
    nt.links.new(og, mixo.inputs[0])
    nt.links.new(mixc.outputs[2], mixo.inputs[6]); nt.links.new(orange.outputs[0], mixo.inputs[7])
    bright = _math(nt, "MULTIPLY_ADD", wn2.outputs["Value"], 2.4, 1.2)
    bright = _math(nt, "MULTIPLY", bright, _math(nt, "MULTIPLY_ADD", og, 2.2, 1.0))
    strength = _math(nt, "MULTIPLY", em_mask, bright)
    emis = _node(nt, "ShaderNodeEmission", (800, 300))
    nt.links.new(mixo.outputs[2], emis.inputs["Color"])
    nt.links.new(strength, emis.inputs["Strength"])
    # the building body: concrete or dark glass, unlit windows a little glossier
    bsdf = _node(nt, "ShaderNodeBsdfPrincipled", (800, -200))
    body = _node(nt, "ShaderNodeMix", (500, -100), data_type="RGBA")
    nt.links.new(glass, body.inputs[0])
    body.inputs[6].default_value = (0.032, 0.03, 0.033, 1)
    body.inputs[7].default_value = (0.012, 0.016, 0.026, 1)
    nt.links.new(body.outputs[2], bsdf.inputs["Base Color"])
    rough = _math(nt, "SUBTRACT", 0.7, _math(nt, "MULTIPLY", _math(nt, "MAXIMUM", glass, win), 0.55))
    nt.links.new(rough, bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    add = _node(nt, "ShaderNodeAddShader", (1200, 0))
    nt.links.new(bsdf.outputs[0], add.inputs[0]); nt.links.new(emis.outputs[0], add.inputs[1])
    # street-light spill on the lowest floors
    spill = _node(nt, "ShaderNodeEmission", (1000, -350))
    spill.inputs["Color"].default_value = (1.0, 0.5, 0.2, 1)
    low = _math(nt, "SUBTRACT", 1.0, _math(nt, "DIVIDE", pos.outputs[2], 22.0), clamp=True)
    nt.links.new(_math(nt, "MULTIPLY", _math(nt, "MULTIPLY", low, low), 0.05), spill.inputs["Strength"])
    add2 = _node(nt, "ShaderNodeAddShader", (1400, 0))
    nt.links.new(add.outputs[0], add2.inputs[0]); nt.links.new(spill.outputs[0], add2.inputs[1])
    nt.links.new(add2.outputs[0], out.inputs["Surface"])
    return m


def add_fog(m, color=(0.055, 0.036, 0.05), density=0.00028, max_fog=0.88, strength=1.0):
    """Aerial haze inside a material: mix the surface toward a glowing haze colour by the camera distance
    (1 - exp(-d * density)), so distant blocks fade into the light-polluted air without a volume pass."""
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    src = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None
    if src is None:
        return m
    cam = nt.nodes.new("ShaderNodeCameraData")
    d = _math(nt, "MULTIPLY", cam.outputs["View Distance"], -density)
    f = _math(nt, "SUBTRACT", 1.0, _math(nt, "EXPONENT", d))
    f = _math(nt, "MULTIPLY", f, max_fog)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(f, mix.inputs[0])
    nt.links.new(src, mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------------------------------------- rooftop gear, beacons
def merge_props(name, roofs, tops, seed=11):
    """Water towers, AC boxes, roof huts on roofs; antennas with a beacon ball on tall tops (the balls are a second
    object with the blinking material)."""
    rng = random.Random(seed)
    bm = bmesh.new()
    for x, y, z, w, l in roofs:
        if w < 12 or l < 12:
            continue
        n = rng.choice([0, 1, 2, 3, 4])
        for _ in range(n):
            px, py = x + rng.uniform(-w / 2 + 3, w / 2 - 3), y + rng.uniform(-l / 2 + 3, l / 2 - 3)
            kind = rng.random()
            if kind < 0.25 and z < 120:
                # water tower: a short cylinder on legs
                r, h = rng.uniform(1.6, 2.6), rng.uniform(3, 4.5)
                bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r, radius2=r, depth=h,
                                      matrix=__import__("mathutils").Matrix.Translation((px, py, z + 2.2 + h / 2)))
                bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r * 1.05, radius2=0.2, depth=1.4,
                                      matrix=__import__("mathutils").Matrix.Translation((px, py, z + 2.2 + h + 0.7)))
            else:
                sx, sy, sz = rng.uniform(2, 6), rng.uniform(2, 5), rng.uniform(1.2, 3.2)
                bmesh.ops.create_cube(bm, size=1.0, matrix=__import__("mathutils").Matrix.LocRotScale(
                    (px, py, z + sz / 2), None, (sx, sy, sz)))
    for x, y, z, h in tops:
        if h > 110 and rng.random() < 0.7:
            ah = rng.uniform(8, 26)
            bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.45, radius2=0.12, depth=ah,
                                  matrix=__import__("mathutils").Matrix.Translation((x, y, z + ah / 2)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    mat = bpy.data.materials.new(name + "Mat")
    mat.use_nodes = True
    p = mat.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.03, 0.03, 0.032, 1)
    p.inputs["Roughness"].default_value = 0.6
    ob.data.materials.append(mat)
    return ob


def beacons(name, tops, seed=13):
    rng = random.Random(seed)
    bm = bmesh.new()
    lay = bm.faces.layers.float.new("ph")
    import mathutils
    for x, y, z, h in tops:
        if h < 70:
            continue
        ph = rng.random()
        top = z + (rng.uniform(8, 26) if h > 110 else 1.0)
        res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.9, matrix=mathutils.Matrix.Translation((x, y, top)))
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f[lay] = ph
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    m = bpy.data.materials.new(name + "Mat")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = _node(nt, "ShaderNodeOutputMaterial", (600, 0))
    T = _node(nt, "ShaderNodeValue", (-600, -200)); T.name = T.label = "T"
    ph = _node(nt, "ShaderNodeAttribute", (-600, 0), attribute_name="ph")
    s = _math(nt, "FRACT", _math(nt, "ADD", _math(nt, "MULTIPLY", T.outputs[0], 0.8), ph.outputs["Fac"]))
    blink = _math(nt, "LESS_THAN", s, 0.18)
    em = _node(nt, "ShaderNodeEmission", (300, 0))
    em.inputs["Color"].default_value = (1.0, 0.08, 0.04, 1)
    nt.links.new(_math(nt, "MULTIPLY_ADD", blink, 160.0, 4.0), em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(m)
    ob.visible_diffuse = False
    ob.visible_shadow = False
    return ob


# ---------------------------------------------------------------------------------------------- streets, lights, traffic
def street_lines():
    """Street centerlines (x0, y0, x1, y1) between blocks, clipped to the city radius, skipping the river."""
    nb = int(RADIUS / PITCH) + 1
    lines = []
    for k in range(-nb, nb + 1):
        c = (k + 0.5) * PITCH
        span = math.sqrt(max(0.0, RADIUS ** 2 - c ** 2))
        if span < 200:
            continue
        lines.append((c, -span, c, span))           # north-south at x = c
        lines.append((-span, c, span, c))           # east-west at y = c
    return lines


def street_lights(name, lines, spacing=34.0, seed=17):
    rng = random.Random(seed)
    pts = []
    for x0, y0, x1, y1 in lines:
        L = math.hypot(x1 - x0, y1 - y0)
        n = int(L / spacing)
        dx, dy = (x1 - x0) / L, (y1 - y0) / L
        for i in range(n):
            s = i * spacing + rng.uniform(-2, 2)
            for side in (-1, 1):
                x = x0 + dx * s - dy * side * (STREET / 2 - 1)
                y = y0 + dy * s + dx * side * (STREET / 2 - 1)
                if in_river(x, y, 4):
                    continue
                pts.append((x, y, 9.0))
    me = bpy.data.meshes.new(name)
    me.from_pydata(pts, [], [])
    ob = bpy.data.objects.new(name, me)
    return ob, len(pts)


def traffic_points(lines, n=3200, seed=19):
    """Cars: (line index, offset, speed, direction) arrays; positions are evaluated per frame by traffic_at()."""
    rng = np.random.default_rng(seed)
    L = np.array([[x0, y0, x1, y1] for x0, y0, x1, y1 in lines], dtype=np.float64)
    lengths = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1])
    idx = rng.choice(len(L), size=n, p=lengths / lengths.sum())
    return {"L": L, "len": lengths, "idx": idx, "off": rng.uniform(0, 1, n), "spd": rng.uniform(9, 17, n),
            "dir": rng.choice([-1.0, 1.0], size=n), "lane": rng.uniform(2.0, 5.5, n)}


def traffic_at(tr, sec):
    L, idx = tr["L"][tr["idx"]], tr["idx"]
    length = tr["len"][idx]
    s = np.mod(tr["off"] * length + tr["dir"] * tr["spd"] * sec, length)
    d = (L[:, 2:4] - L[:, 0:2]) / length[:, None]
    p = L[:, 0:2] + d * s[:, None]
    side = tr["dir"][:, None] * tr["lane"][:, None]
    p += np.stack([-d[:, 1], d[:, 0]], axis=1) * side
    ok = ~np.array([in_river(x, y, 2) for x, y in p])
    return np.column_stack([p, np.full(len(p), 0.8)]), tr["dir"], ok


# ---------------------------------------------------------------------------------------------- ground, river, bridges, hills
def ground(name="CityGround"):
    bpy.ops.mesh.primitive_plane_add(size=60000, location=(0, 0, 0))
    ob = bpy.context.object
    ob.name = name
    m = bpy.data.materials.new(name + "Mat")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = _node(nt, "ShaderNodeOutputMaterial", (900, 0))
    geo = _node(nt, "ShaderNodeNewGeometry", (-1000, 0))
    sep = _node(nt, "ShaderNodeSeparateXYZ", (-800, 0))
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    # distance to the nearest street line, from the block grid: streets glow warm (sodium light pollution)
    def street_d(c):
        f = _math(nt, "FRACT", _math(nt, "DIVIDE", c, PITCH))
        return _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", f, 0.5))
    dx, dy = street_d(sep.outputs[0]), street_d(sep.outputs[1])
    dmin = _math(nt, "MINIMUM", dx, dy)
    streetness = _math(nt, "LESS_THAN", dmin, STREET / PITCH / 2)
    r = _math(nt, "SQRT", _math(nt, "ADD", _math(nt, "MULTIPLY", sep.outputs[0], sep.outputs[0]),
                                  _math(nt, "MULTIPLY", sep.outputs[1], sep.outputs[1])))
    inside = _math(nt, "LESS_THAN", r, RADIUS)
    glow = _math(nt, "MULTIPLY", streetness, inside)
    em = _node(nt, "ShaderNodeEmission", (400, 200))
    em.inputs["Color"].default_value = (1.0, 0.5, 0.18, 1)
    patch = _node(nt, "ShaderNodeTexNoise", (0, 400))
    patch.inputs["Scale"].default_value = 0.004
    patch.inputs["Detail"].default_value = 3.0
    nt.links.new(geo.outputs["Position"], patch.inputs["Vector"])
    pk = _math(nt, "POWER", patch.outputs["Fac"], 2.5)
    nt.links.new(_math(nt, "MULTIPLY", _math(nt, "MULTIPLY", glow, pk), 0.09), em.inputs["Strength"])
    bsdf = _node(nt, "ShaderNodeBsdfPrincipled", (400, -150))
    bsdf.inputs["Base Color"].default_value = (0.018, 0.018, 0.02, 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    add = _node(nt, "ShaderNodeAddShader", (700, 0))
    nt.links.new(bsdf.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(m)
    return ob


def river(name="River"):
    ys = np.linspace(-RADIUS - 1200, RADIUS + 1200, 400)
    verts, faces = [], []
    for i, y in enumerate(ys):
        x = river_x(y)
        dy = (river_x(y + 1) - river_x(y - 1)) / 2
        n = np.array([1.0, -dy]) / math.hypot(1.0, dy)
        for s in (-1, 1):
            verts.append((x + s * n[0] * RIVER_W / 2, y + s * n[1] * RIVER_W / 2, 0.15))
        if i:
            a = 2 * (i - 1)
            faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new(name, me)
    m = bpy.data.materials.new(name + "Mat")
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.004, 0.006, 0.01, 1)
    p.inputs["Roughness"].default_value = 0.06
    p.inputs["Specular IOR Level"].default_value = 0.8
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 0.08; noise.inputs["Detail"].default_value = 6
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.18
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    ob.data.materials.append(m)
    return ob


def bridges(name, lines):
    bm = bmesh.new()
    import mathutils
    pts = []
    for x0, y0, x1, y1 in lines:
        if abs(y1 - y0) > 1:          # east-west streets cross the river
            continue
        y = y0
        x = river_x(y)
        if abs(y) > RADIUS - 150:
            continue
        L = RIVER_W + 40
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.LocRotScale((x, y, 7.0), None, (L, 16, 2.0)))
        for k in range(-4, 5):
            pts.append((x + k * L / 9, y - 7.5, 9.5))
            pts.append((x + k * L / 9, y + 7.5, 9.5))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    m = bpy.data.materials.new(name + "Mat"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.03, 0.03, 0.035, 1)
    ob.data.materials.append(m)
    return ob, pts


def hills(name="Hills", seed=23):
    rng = np.random.default_rng(seed)
    n_ang, n_rad = 360, 10
    verts, faces = [], []
    for i in range(n_ang):
        a = 2 * math.pi * i / n_ang
        hmax = 160 + 260 * (0.5 + 0.5 * math.sin(3 * a + 1.0)) * (0.6 + 0.4 * math.sin(7 * a)) + rng.uniform(0, 40)
        for j in range(n_rad):
            r = 5200 + 3200 * j / (n_rad - 1)
            h = hmax * math.sin(math.pi * j / (n_rad - 1)) ** 0.8
            verts.append((r * math.cos(a), r * math.sin(a), h - 5))
    for i in range(n_ang):
        for j in range(n_rad - 1):
            a, b = i * n_rad + j, ((i + 1) % n_ang) * n_rad + j
            faces.append((a, b, b + 1, a + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new(name, me)
    m = bpy.data.materials.new(name + "Mat"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.006, 0.006, 0.009, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    ob.data.materials.append(m)
    return ob


def night_world(scene, strength=1.0):
    """Deep blue zenith, a warm light-pollution glow at the horizon, stars."""
    w = bpy.data.worlds.new("NightWorld")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = _node(nt, "ShaderNodeOutputWorld", (900, 0))
    tc = _node(nt, "ShaderNodeTexCoord", (-900, 0))
    sep = _node(nt, "ShaderNodeSeparateXYZ", (-700, 0))
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])            # on the world, Generated = the ray direction
    z = _math(nt, "MULTIPLY_ADD", sep.outputs[2], 0.5, 0.5)            # -1..1 -> 0..1, the horizon at 0.5
    ramp = _node(nt, "ShaderNodeValToRGB", (-400, 0))
    nt.links.new(z, ramp.inputs[0])
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.006, 0.004, 0.006, 1)
    cr.elements[1].position = 0.52
    cr.elements[1].color = (0.11, 0.05, 0.05, 1)
    e = cr.elements.new(0.58); e.color = (0.035, 0.03, 0.07, 1)
    e = cr.elements.new(0.8); e.color = (0.007, 0.011, 0.03, 1)
    e = cr.elements.new(1.0); e.color = (0.003, 0.005, 0.015, 1)
    # stars: sparse white noise above the horizon
    vor = _node(nt, "ShaderNodeTexVoronoi", (-400, -300))
    vor.inputs["Scale"].default_value = 420.0
    nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
    st = _math(nt, "LESS_THAN", vor.outputs["Distance"], 0.045)
    hz = _math(nt, "GREATER_THAN", z, 0.56)
    starv = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", st, hz), 2.5)
    add = _node(nt, "ShaderNodeMix", (200, 0), data_type="RGBA", blend_type="ADD")
    add.inputs[0].default_value = 1.0
    nt.links.new(ramp.outputs[0], add.inputs[6])
    sc = _node(nt, "ShaderNodeCombineColor", (0, -300))
    for i in range(3):
        nt.links.new(starv, sc.inputs[i])
    nt.links.new(sc.outputs[0], add.inputs[7])
    bg = _node(nt, "ShaderNodeBackground", (500, 0))
    bg.inputs["Strength"].default_value = strength
    nt.links.new(add.outputs[2], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return w
