"""iPhone 17 Pro model for Blender (Cycles), built procedurally to the measured spec in
docs/IPHONE17PRO_IOS_SPEC.md. Real scale: 1 Blender unit = 1 m.

Local axes: x across the width (+x = the right edge seen from the front), y along the height (+y = top),
z through the thickness (+z = the screen side). Origin = the body's center.

build_iphone(finish, name, screen_image=None, screen_mask=None) -> the root Empty; every part is parented to it.
"""
import math

import bmesh
import bpy

MM = 0.001
W, H, D = 71.9 * MM, 150.0 * MM, 8.75 * MM
ZB, ZF = -D / 2, D / 2                      # back face, front face
SCREEN_W, SCREEN_H = 66.6 * MM, 144.8 * MM  # active display (2622 x 1206 px at 460 ppi)
BODY_R = 13.3 * MM                          # circle-equivalent body corner radius (front outline)
SE_N = 3.0                                  # superellipse exponent -> continuous-curvature corners
SE_K = 1.42                                 # superellipse half-size per unit circle-equivalent radius (45 deg inset match)

PLATEAU_DEPTH = 1.9 * MM
PLATEAU_BOTTOM = 43.5 * MM                  # measured from the top edge
PLATEAU_LOWER_R = 7.0 * MM

FINISHES = {
    # linear-space base colors
    "cosmic_orange": dict(metal=(0.86, 0.235, 0.062), panel=(0.52, 0.135, 0.038), ring=(0.92, 0.32, 0.10), rough=0.28),
    "deep_blue": dict(metal=(0.046, 0.066, 0.125), panel=(0.040, 0.056, 0.102), ring=(0.075, 0.095, 0.16), rough=0.30),
    "silver": dict(metal=(0.80, 0.80, 0.785), panel=(0.82, 0.82, 0.81), ring=(0.88, 0.88, 0.87), rough=0.26),
}


# ============================================================================================ 2D shapes
def _quadrant(a, n=SE_N, m=40):
    pts = []
    for i in range(m):
        t = (math.pi / 2) * i / (m - 1)
        c, s = math.cos(t), math.sin(t)
        pts.append((a * (c ** (2.0 / n)) if c > 1e-12 else 0.0, a * (s ** (2.0 / n)) if s > 1e-12 else 0.0))
    return pts


def _lerp(p, q, k):
    return [(p[0] + (q[0] - p[0]) * i / (k + 1), p[1] + (q[1] - p[1]) * i / (k + 1)) for i in range(1, k + 1)]


def outline(w, h, r_top, r_bot=None, m=40, k_long=36, k_short=18):
    """CCW outline (seen from +z) of a w x h rounded rectangle centered at the origin, continuous-curvature
    corners (superellipse n=3). r_* are circle-equivalent radii. Constant vertex count for given m/k."""
    r_bot = r_top if r_bot is None else r_bot
    at = min(SE_K * r_top, w / 2 - 1e-7, h / 2 - 1e-7)
    ab = min(SE_K * r_bot, w / 2 - 1e-7, h / 2 - 1e-7)
    hw, hh = w / 2, h / 2
    qt, qb = _quadrant(at, m=m), _quadrant(ab, m=m)
    pts = []
    pts += [(hw - at + x, hh - at + y) for (x, y) in qt]                     # top-right corner
    pts += _lerp((hw - at, hh), (-(hw - at), hh), k_short)                     # top edge
    pts += [(-(hw - at) - x, hh - at + y) for (x, y) in reversed(qt)]        # top-left corner
    pts += _lerp((-hw, hh - at), (-hw, -(hh - ab)), k_long)                    # left edge
    pts += [(-(hw - ab) - x, -(hh - ab) - y) for (x, y) in qb]               # bottom-left corner
    pts += _lerp((-(hw - ab), -hh), (hw - ab, -hh), k_short)                   # bottom edge
    pts += [(hw - ab + x, -(hh - ab) - y) for (x, y) in reversed(qb)]        # bottom-right corner
    pts += _lerp((hw, -(hh - ab)), (hw, hh - at), k_long)                      # right edge
    return pts


def inset(w, h, r_top, r_bot, d, **kw):
    return outline(w - 2 * d, h - 2 * d, max(r_top - d, 0.05 * MM), max(r_bot - d, 0.05 * MM), **kw)


def stadium(w, h, segs=16, k=6):
    """CCW stadium (pill) w x h, w >= h, with true semicircular ends, centered at the origin."""
    r = h / 2
    cx = w / 2 - r
    pts = []
    for i in range(segs + 1):                       # right end, from bottom to top
        a = -math.pi / 2 + math.pi * i / segs
        pts.append((cx + r * math.cos(a), r * math.sin(a)))
    pts += _lerp((cx, r), (-cx, r), k)
    for i in range(segs + 1):                       # left end, from top to bottom
        a = math.pi / 2 + math.pi * i / segs
        pts.append((-cx + r * math.cos(a), r * math.sin(a)))
    pts += _lerp((-cx, -r), (cx, -r), k)
    return pts


def circle(r, segs=96):
    return [(r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs)) for i in range(segs)]


# ============================================================================================ meshes
def _finish_object(name, bm, parent, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    if mat is not None:
        me.materials.append(mat)
    return ob


def sweep(name, rings, parent, mat, cap_first=False, cap_last=False, uv_fn=None, recalc=True):
    """rings: ordered list of (points_2d, z) along a profile; consecutive rings are bridged with quads.
    Side faces smooth; caps flat with sharp borders. Normals are made consistent (outward for closed shells)."""
    bm = bmesh.new()
    vr = [[bm.verts.new((x, y, z)) for (x, y) in pts] for pts, z in rings]
    n = len(vr[0])
    for r in range(len(vr) - 1):
        a, b = vr[r], vr[r + 1]
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f.smooth = True
    caps = []
    if cap_first:
        caps.append(bm.faces.new(list(reversed(vr[0]))))
    if cap_last:
        caps.append(bm.faces.new(vr[-1]))
    for f in caps:
        f.smooth = False
        for e in f.edges:
            e.smooth = False
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if uv_fn is not None:
        uv = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            for loop in f.loops:
                loop[uv].uv = uv_fn(loop.vert.co)
    return _finish_object(name, bm, parent, mat)


def revolve(name, profile, parent, mat, center=(0.0, 0.0), segs=96, cap_first=False, cap_last=False):
    """profile: ordered [(radius, z)]; returns a surface of revolution around the z axis at center."""
    rings = [([(center[0] + x, center[1] + y) for (x, y) in circle(r, segs)], z) for (r, z) in profile]
    return sweep(name, rings, parent, mat, cap_first=cap_first, cap_last=cap_last)


def flat_face(name, pts, z, parent, mat, facing=+1, uv_fn=None):
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, z)) for (x, y) in pts]
    f = bm.faces.new(vs if facing > 0 else list(reversed(vs)))
    f.smooth = False
    if uv_fn is not None:
        uv = bm.loops.layers.uv.new("UVMap")
        for loop in f.loops:
            loop[uv].uv = uv_fn(loop.vert.co)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    return _finish_object(name, bm, parent, mat)


def arc(n, f):
    """[f(phi)] for phi from 0 to pi/2 inclusive in n segments."""
    return [f((math.pi / 2) * k / n) for k in range(n + 1)]


# ============================================================================================ materials
def _set(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def principled(name, base=(0.8, 0.8, 0.8), metallic=0.0, rough=0.5, ior=1.5, coat=0.0, coat_rough=0.03,
               thin_film=0.0, thin_film_ior=1.38, spec_level=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    p = mat.node_tree.nodes.get("Principled BSDF")
    _set(p, "Base Color", (*base, 1.0))
    _set(p, "Metallic", metallic)
    _set(p, "Roughness", rough)
    _set(p, "IOR", ior)
    _set(p, "Coat Weight", coat)
    _set(p, "Coat Roughness", coat_rough)
    _set(p, "Thin Film Thickness", thin_film)
    _set(p, "Thin Film IOR", thin_film_ior)
    if spec_level is not None:
        _set(p, "Specular IOR Level", spec_level)
    return mat


def anodized_metal(name, base, rough):
    """Bead-blasted anodized aluminum: metallic tint + a fine roughness variation (no bump: it aliases)."""
    mat = principled(name, base=base, metallic=1.0, rough=rough)
    nt = mat.node_tree
    p = nt.nodes.get("Principled BSDF")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1400.0
    noise.inputs["Detail"].default_value = 3.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.7
    mr.inputs["To Min"].default_value = rough - 0.025
    mr.inputs["To Max"].default_value = rough + 0.025
    nt.links.new(noise.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], p.inputs["Roughness"])
    return mat


def screen_material(name, image_path=None, mask_path=None, strength=1.0):
    """The front glass top face: a glossy black dielectric that emits the screen image inside the display rect.
    Two images (ScreenTexA / ScreenTexB) crossfade by the ScreenMix node's factor; ScreenFlash adds white
    (the screenshot flash). UVs map the active display to [0,1]; outside it the image is clipped to black,
    and the mask rounds the display corners."""
    mat = principled(name, base=(0.0, 0.0, 0.0), rough=0.03, ior=1.52, spec_level=0.5)
    nt = mat.node_tree
    p = nt.nodes.get("Principled BSDF")
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"

    def img_node(label):
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.name = label
        tex.extension = "CLIP"
        tex.interpolation = "Cubic"
        nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        return tex

    ta, tb = img_node("ScreenTexA"), img_node("ScreenTexB")
    if image_path:
        img = bpy.data.images.load(image_path, check_existing=True)
        img.colorspace_settings.name = "sRGB"
        ta.image = img
        tb.image = img
    mix = nt.nodes.new("ShaderNodeMix")
    mix.name = "ScreenMix"
    mix.data_type = "RGBA"
    mix.inputs[0].default_value = 0.0
    nt.links.new(ta.outputs["Color"], mix.inputs[6])
    nt.links.new(tb.outputs["Color"], mix.inputs[7])
    flash = nt.nodes.new("ShaderNodeMix")
    flash.name = "ScreenFlash"
    flash.data_type = "RGBA"
    flash.inputs[0].default_value = 0.0
    flash.inputs[7].default_value = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(mix.outputs[2], flash.inputs[6])
    color = flash.outputs[2]
    if mask_path:
        mtex = img_node("ScreenMask")
        mimg = bpy.data.images.load(mask_path, check_existing=True)
        mimg.colorspace_settings.name = "Non-Color"
        mtex.image = mimg
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(color, mul.inputs[6])
        nt.links.new(mtex.outputs["Color"], mul.inputs[7])
        color = mul.outputs[2]
    nt.links.new(color, p.inputs["Emission Color"])
    _set(p, "Emission Strength", strength)
    return mat


def set_screen(mat, img_a, img_b=None, mix=0.0, flash=0.0, strength=None):
    """Point a phone's screen material at images (bpy.types.Image) and set the crossfade / flash."""
    nt = mat.node_tree
    nt.nodes["ScreenTexA"].image = img_a
    nt.nodes["ScreenTexB"].image = img_b or img_a
    nt.nodes["ScreenMix"].inputs[0].default_value = mix
    nt.nodes["ScreenFlash"].inputs[0].default_value = flash
    if strength is not None:
        nt.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = strength


# ============================================================================================ the phone
def _root(name):
    root = bpy.data.objects.new(name, None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.05
    bpy.context.scene.collection.objects.link(root)
    return root


def _back_xy(bx_mm, by_mm):
    """Back-view coordinates (mm from the left/top as you look at the back) -> local (x, y)."""
    return (W / 2 - bx_mm * MM, H / 2 - by_mm * MM)


def build_iphone(finish="cosmic_orange", name="iPhone", screen_image=None, screen_mask=None, screen_strength=1.0):
    fin = FINISHES[finish]
    root = _root(name)
    m_metal = anodized_metal(f"{name}_metal", fin["metal"], fin["rough"])
    m_ring = principled(f"{name}_ring", base=fin["ring"], metallic=1.0, rough=0.09)
    m_panel = principled(f"{name}_panel", base=fin["panel"], rough=0.36, ior=1.5)
    m_glass = principled(f"{name}_glass", base=(0.0, 0.0, 0.0), rough=0.03, ior=1.52, spec_level=0.5)
    m_screen = screen_material(f"{name}_screen", screen_image, screen_mask, screen_strength)
    m_cover = principled(f"{name}_lens_cover", base=(0.98, 0.98, 0.98), rough=0.0, ior=1.62, thin_film=300.0)
    _set(m_cover.node_tree.nodes.get("Principled BSDF"), "Transmission Weight", 1.0)
    m_inner = principled(f"{name}_lens_inner", base=(0.006, 0.007, 0.011), metallic=0.3, rough=0.12,
                         thin_film=430.0, thin_film_ior=1.45)
    m_black = principled(f"{name}_black", base=(0.005, 0.005, 0.006), rough=0.5)
    m_flash = principled(f"{name}_flash", base=(0.93, 0.86, 0.68), rough=0.5, ior=1.45)
    m_lidar = principled(f"{name}_lidar", base=(0.003, 0.003, 0.004), rough=0.04, ior=1.6, thin_film=300.0)
    m_cc = principled(f"{name}_camera_control", base=(0.012, 0.012, 0.014), rough=0.07, ior=1.77)

    # ---------------------------------------------------------------- body (aluminum unibody)
    # profile from the back face up: back edge round (r 2.2 mm) -> straight side -> front lip (1.2 mm in,
    # ending 0.35 mm below the glass top) -> a hidden cap under the glass.
    rb, rf = 2.2 * MM, 1.2 * MM
    z_lip_end = ZF - 0.35 * MM
    prof = []
    prof += arc(12, lambda p: (rb * (1 - math.sin(p)), ZB + rb * (1 - math.cos(p))))
    prof += arc(10, lambda p: (rf * (1 - math.cos(p)), (ZF - rf) + (z_lip_end - (ZF - rf)) * math.sin(p)))[1:]
    rings = [(inset(W, H, BODY_R, BODY_R, d), z) for (d, z) in prof]
    sweep(f"{name}_body", rings, root, m_metal, cap_first=True, cap_last=True)

    # ---------------------------------------------------------------- front glass (inset 1.3 mm, 0.7 mm thick)
    gi, gr = 1.3 * MM, 0.3 * MM
    gprof = [(gi, ZF - 0.7 * MM)] + arc(8, lambda p: (gi + gr * (1 - math.cos(p)), (ZF - gr) + gr * math.sin(p)))
    sweep(f"{name}_glass_edge", [(inset(W, H, BODY_R, BODY_R, d), z) for (d, z) in gprof], root, m_glass)

    def screen_uv(co):
        return ((co.x + SCREEN_W / 2) / SCREEN_W, (co.y + SCREEN_H / 2) / SCREEN_H)

    flat_face(f"{name}_screen", inset(W, H, BODY_R, BODY_R, gi + gr), ZF, root, m_screen, facing=+1, uv_fn=screen_uv)

    # ---------------------------------------------------------------- camera plateau (top 43.5 mm, 1.9 mm proud)
    ph = PLATEAU_BOTTOM
    pw = W + 0.03 * MM
    pcy = H / 2 - ph / 2
    zp = ZB - PLATEAU_DEPTH
    rp = 1.6 * MM

    def p_out(d):
        return [(x, y + pcy) for (x, y) in outline(pw - 2 * d, ph - 2 * d, max(BODY_R - d, 0.05 * MM),
                                                     max(PLATEAU_LOWER_R - d, 0.05 * MM))]

    pprof = arc(10, lambda p: (rp * (1 - math.sin(p)), zp + rp * (1 - math.cos(p)))) + [(0.0, ZB + rb + 0.3 * MM)]
    sweep(f"{name}_plateau", [(p_out(d), z) for (d, z) in pprof], root, m_metal, cap_first=True, cap_last=True)

    # ---------------------------------------------------------------- back glass panel (flush, 0.03 mm proud)
    px0, px1, py0, py1 = 3.9, 68.0, 48.5, 146.5
    pc_y = H / 2 - (py0 + py1) / 2 * MM
    pwid, phgt = (px1 - px0) * MM, (py1 - py0) * MM
    grr = 0.12 * MM

    def g_out(d):
        return [(x, y + pc_y) for (x, y) in outline(pwid - 2 * d, phgt - 2 * d, 9.4 * MM - d, 9.4 * MM - d)]

    gpp = arc(5, lambda p: (grr * (1 - math.sin(p)), (ZB - 0.03 * MM) + grr * (1 - math.cos(p)))) + [(0.0, ZB + 0.25 * MM)]
    sweep(f"{name}_panel", [(g_out(d), z) for (d, z) in gpp], root, m_panel, cap_first=True)

    # ---------------------------------------------------------------- lenses
    for i, (bx, by) in enumerate([(14.4, 14.0), (14.3, 33.4), (32.5, 23.7)]):
        c = _back_xy(bx, by)
        ro, ri, rr = 8.2 * MM, 7.0 * MM, 0.45 * MM
        z_top = zp - 1.2 * MM                       # outermost (most negative z) face of the ring
        ring_prof = [(ro, zp + 0.25 * MM), (ro, z_top + rr)]
        ring_prof += arc(6, lambda p: (ro - rr * (1 - math.cos(p)), (z_top + rr) - rr * math.sin(p)))[1:]
        ring_prof += [(ri + 0.2 * MM, z_top), (ri, z_top + 0.22 * MM)]
        revolve(f"{name}_lens{i}_ring", ring_prof, root, m_ring, center=c)
        z_cover = z_top + 0.22 * MM
        revolve(f"{name}_lens{i}_cover", [(0.0, z_cover + 0.3 * MM), (ri, z_cover + 0.3 * MM), (ri, z_cover), (0.0, z_cover)],
                root, m_cover, center=c)
        # inside: a dark barrel with stepped annuli and a domed element (seen through the cover glass)
        inner = [(6.6, 0.55), (6.6, 0.9), (5.3, 0.9), (5.3, 1.35), (3.8, 1.35), (3.8, 1.9)]
        revolve(f"{name}_lens{i}_barrel", [(r * MM, z_cover + dz * MM) for (r, dz) in inner], root, m_inner, center=c,
                cap_last=True)
        dome = []
        dome += arc(10, lambda p: (3.4 * MM * math.cos(p), z_cover + 1.55 * MM - 0.9 * MM * math.sin(p)))
        revolve(f"{name}_lens{i}_dome", dome, root, m_inner, center=c)

    # flash / mic / LiDAR, right column of the back
    def recessed_disc(label, bx, by, r, mat, rim=0.35 * MM):
        c = _back_xy(bx, by)
        revolve(f"{name}_{label}", [(r, zp + 0.25 * MM), (r, zp - 0.02 * MM)], root, mat, center=c, cap_last=True, segs=64)
        if rim:
            revolve(f"{name}_{label}_rim", [(r + rim, zp + 0.1 * MM), (r + rim, zp - 0.08 * MM), (r, zp - 0.08 * MM), (r, zp + 0.1 * MM)],
                    root, m_ring, center=c, segs=64)

    recessed_disc("flash", 57.5, 14.0, 3.5 * MM, m_flash)
    recessed_disc("mic", 57.5, 23.7, 0.6 * MM, m_black, rim=0.0)
    recessed_disc("lidar", 57.5, 33.4, 3.5 * MM, m_lidar)

    # ---------------------------------------------------------------- side buttons
    z_mid = ((ZB + rb) + (ZF - rf)) / 2

    def button(label, side, y_top_mm, y_bot_mm, mat, proud=0.5 * MM, tz=2.6 * MM):
        length = (y_bot_mm - y_top_mm) * MM
        cy = H / 2 - (y_top_mm + y_bot_mm) / 2 * MM
        rr = min(0.22 * MM, proud * 0.5)
        steps = [(W / 2 - 0.6 * MM, 0.0), (W / 2 + proud - rr, 0.0)]
        steps += arc(4, lambda p: (W / 2 + proud - rr + rr * math.sin(p), rr * (1 - math.cos(p))))[1:]
        bm = bmesh.new()
        vr = []
        for xx, dd in steps:
            pts = stadium(length - 2 * dd, tz - 2 * dd)       # (y, z) in the stadium's (x, y)
            vr.append([bm.verts.new((side * xx, cy + a, z_mid + b)) for (a, b) in pts])
        n = len(vr[0])
        for r in range(len(vr) - 1):
            for i2 in range(n):
                j2 = (i2 + 1) % n
                f = bm.faces.new((vr[r][i2], vr[r][j2], vr[r + 1][j2], vr[r + 1][i2]))
                f.smooth = True
        cap = bm.faces.new(vr[-1])
        cap.smooth = False
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return _finish_object(f"{name}_{label}", bm, root, mat)

    button("action", -1, 29.7, 35.4, m_metal)
    button("vol_up", -1, 42.5, 51.0, m_metal)
    button("vol_down", -1, 55.8, 64.2, m_metal)
    button("side", +1, 45.0, 59.0, m_metal)
    button("camera_control", +1, 90.0, 107.0, m_cc, proud=0.06 * MM)

    # ---------------------------------------------------------------- bottom: USB-C and grilles (dark inlays)
    def bottom_inlay(label, x_mm, w_mm, h_mm, mat):
        pts = stadium(w_mm * MM, h_mm * MM, segs=12, k=3)
        bm = bmesh.new()
        vs = [bm.verts.new((x_mm * MM + a, -H / 2 - 0.012 * MM, z_mid + b)) for (a, b) in pts]
        f = bm.faces.new(vs)
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()
        f.smooth = False
        _finish_object(f"{name}_{label}", bm, root, mat)

    bottom_inlay("usbc", 0.0, 9.0, 3.2, m_black)
    for k in range(6):
        bottom_inlay(f"grille_l{k}", -9.5 - k * 2.0, 1.15, 1.15, m_black)
        bottom_inlay(f"grille_r{k}", 9.5 + k * 2.0, 1.15, 1.15, m_black)

    root["finish"] = finish
    return root
