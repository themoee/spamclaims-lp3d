"""Ad 6: Dre's bedroom at night (Gen Z): a channel-tufted velvet headboard with a violet LED wash behind it, fairy lights
across the wall (bokeh), posters, a nightstand with a little lamp, pillows, and a duvet that is re-shaped every frame
(lying down it covers his belly, sitting up it drops to his lap).

Bed axis: the headboard is at +y, the foot at -y; Dre faces -y when sitting. Mattress top at BED_Z.
"""
import math
import os

import bmesh
import bpy
import mathutils
import numpy as np

from ad6_char import _bump, bm_obj, link, mesh_obj, principled, rounded_box_mesh, smooth, tube_mesh, uv_sphere

V = mathutils.Vector
BED_Z = 0.555
HEAD_Y = 1.05


def box(name, center, size, mat, radius=0.01, segs=3):
    bm = rounded_box_mesh(size, radius, segs)
    return bm_obj(name, bm, mat, loc=center)


def poster_image(path, kind, w=600, h=840):
    """Two abstract posters (no text, no brands), written once with Pillow-free numpy -> PNG via Blender."""
    yy, xx = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    if kind == 0:   # a retro sunset: gradient sky, a striped sun, a dark horizon
        top, bot = np.array([0.98, 0.42, 0.35]), np.array([0.25, 0.08, 0.4])
        img = top * (1 - yy[..., None]) + bot * yy[..., None]
        d = np.hypot(xx - 0.5, (yy - 0.52) * 1.0)
        sun = (d < 0.27) & ~((yy > 0.5) & (np.sin(yy * 120) > 0.3))
        img[sun] = np.array([1.0, 0.82, 0.3]) * (1 - 0.4 * yy[sun][..., None])
        img[yy > 0.72] = np.array([0.07, 0.03, 0.1])
    else:           # bold shapes: a lilac field, a pink circle, a yellow bar
        img = np.ones((h, w, 3)) * np.array([0.55, 0.5, 0.95])
        img[np.hypot(xx - 0.35, yy - 0.38) < 0.24] = np.array([1.0, 0.36, 0.65])
        img[(yy > 0.66) & (yy < 0.74)] = np.array([1.0, 0.88, 0.4])
        img[(xx > 0.62) & (yy > 0.1) & (yy < 0.55)] = np.array([0.12, 0.1, 0.3])
    rgba = np.concatenate([img, np.ones((h, w, 1))], axis=2)[::-1].astype(np.float32)
    im = bpy.data.images.new(os.path.basename(path), w, h)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    return im


def image_material(name, img, rough=0.6, emission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    if emission:
        nt.links.new(t.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emission
    return m


def plane(name, center, size, rot, mat):
    w, h = size
    verts = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for i, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = c
    me.materials.append(mat)
    ob = link(bpy.data.objects.new(name, me))
    ob.location = center
    ob.rotation_euler = rot
    return ob


class Room:
    def __init__(self, tex_dir):
        os.makedirs(tex_dir, exist_ok=True)
        wall = _bump(principled("R_wall", (0.07, 0.055, 0.13), rough=0.92), 60.0, 0.15, 0.001, detail=8)
        floor = _bump(principled("R_floor", (0.11, 0.07, 0.045), rough=0.45, coat=0.2), 30.0, 0.05, 0.001)
        plane("R_back", (0, HEAD_Y + 0.08, 1.4), (6, 2.8), (math.radians(90), 0, 0), wall)
        plane("R_side", (-1.25, 0, 1.4), (6, 2.8), (math.radians(90), 0, math.radians(90)), wall)
        plane("R_floorplane", (0, 0, 0), (6, 6), (0, 0, 0), floor)
        plane("R_ceiling", (0, 0, 2.6), (6, 6), (math.radians(180), 0, 0), wall)
        # bed: base, mattress, a channel-tufted velvet headboard
        base = principled("R_base", (0.1, 0.1, 0.12), rough=0.8, sheen=0.4)
        box("R_bedbase", (0, 0.06, 0.24), (1.72, 2.06, 0.2), base, 0.04)
        sheet = _bump(principled("R_sheet", (0.55, 0.56, 0.62), rough=0.8, sheen=0.5), 260.0, 0.1, 0.0006)
        box("R_mattress", (0, 0.05, BED_Z - 0.1), (1.62, 1.98, 0.2), sheet, 0.06, 5)
        velvet = principled("R_velvet", (0.12, 0.2, 0.17), rough=0.6, sheen=1.0)
        velvet.node_tree.nodes["Principled BSDF"].inputs["Sheen Roughness"].default_value = 0.35
        for k in range(11):
            x = -0.8 + k * 0.16
            pts = [(x, HEAD_Y, z) for z in np.linspace(0.36, 1.22, 12)]
            rad = [0.075 * (0.6 + 0.4 * math.sin(math.pi * min(1, 0.08 + 0.95 * (i / 11)))) for i in range(12)]
            tube_mesh(f"R_channel{k}", pts, rad, velvet, segs=20)
        box("R_headback", (0, HEAD_Y + 0.045, 0.79), (1.78, 0.04, 0.9), base, 0.015)
        # violet LED tape on the back of the headboard (lights the wall), and under the bed
        self.led_mat = principled("R_led", (0, 0, 0), emission=(0.55, 0.2, 1.0), strength=30.0)
        box("R_ledtape", (0, HEAD_Y + 0.07, 1.245), (1.7, 0.01, 0.012), self.led_mat, 0.003, 1)
        self.leds = []
        for name, loc, size, e in [("R_ledwash", (0, HEAD_Y + 0.075, 1.25), (1.8, 0.06), 90.0),
                                   ("R_ledunder", (0, -0.1, 0.12), (1.6, 1.8), 18.0)]:
            ld = bpy.data.lights.new(name, "AREA")
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = size
            ld.energy = e
            ld.color = (0.55, 0.22, 1.0)
            lo = link(bpy.data.objects.new(name, ld))
            lo.location = loc
            # the wash points up at the wall above the headboard; the under-bed glow points down at the floor
            lo.rotation_euler = (math.radians(-25), 0, 0) if name == "R_ledwash" else (math.radians(180), 0, 0)
            lo.visible_camera = False
            self.leds.append(lo)
        # pillows
        linen = _bump(principled("R_pillow", (0.6, 0.6, 0.66), rough=0.85, sheen=0.6), 300.0, 0.1, 0.0005)
        for k, (x, y, z, rx, rz) in enumerate([(-0.4, 0.9, BED_Z + 0.12, 62, 4), (0.4, 0.9, BED_Z + 0.12, 64, -5),
                                                (0.0, 0.8, BED_Z + 0.1, 70, 0)]):
            bm = rounded_box_mesh((0.72, 0.5, 0.17), 0.08, 5)
            for v in bm.verts:
                v.co.z *= 1.0 - 0.35 * (abs(v.co.x) / 0.36) ** 2
            p = bm_obj(f"R_pillow{k}", bm, linen, loc=(x, y, z))
            p.rotation_euler = (math.radians(rx), 0, math.radians(rz))
            sub = p.modifiers.new("Sub", "SUBSURF")
            sub.levels, sub.render_levels = 1, 2
        # fairy lights: a sagging string across the back wall, warm bulbs (bokeh)
        self.bulb_mat = principled("R_bulb", (1, 1, 1), emission=(1.0, 0.62, 0.28), strength=40.0)
        wire = principled("R_wire", (0.02, 0.02, 0.02), rough=0.5)
        for sidx, (x0, x1, zt, sag, yw) in enumerate([(-1.15, 1.2, 1.9, 0.22, HEAD_Y + 0.06), (-1.2, 1.15, 2.25, 0.16, HEAD_Y + 0.065)]):
            pts, bulbs = [], []
            for i in range(80):
                u = i / 79
                x = x0 + (x1 - x0) * u
                z = zt - sag * 4 * u * (1 - u)
                pts.append((x, yw, z))
            tube_mesh(f"R_wire{sidx}", pts, [0.0012] * 80, wire, segs=6)
            for i in range(26):
                u = (i + 0.5) / 26
                x = x0 + (x1 - x0) * u
                z = zt - sag * 4 * u * (1 - u) - 0.012
                bv, bf = uv_sphere(12, 6)
                mesh_obj(f"R_bulb{sidx}_{i}", bv * np.array((0.008, 0.008, 0.011)), bf, self.bulb_mat, loc=(x, yw - 0.006, z))
        fl = bpy.data.lights.new("R_fairyfill", "AREA")
        fl.shape = "RECTANGLE"
        fl.size, fl.size_y = 2.2, 0.4
        fl.energy = 6.0
        fl.color = (1.0, 0.65, 0.35)
        fo = link(bpy.data.objects.new("R_fairyfill", fl))
        fo.location = (0, HEAD_Y - 0.05, 2.0)
        fo.rotation_euler = (math.radians(-60), 0, 0)
        fo.visible_camera = False
        # posters on the side wall
        for k, (y, z) in enumerate([(0.25, 1.55), (-0.45, 1.45)]):
            img = poster_image(os.path.join(tex_dir, f"poster{k}.png"), k)
            plane(f"R_poster{k}", (-1.245, y, z), (0.42, 0.59), (math.radians(90), 0, math.radians(90)), image_material(f"R_poster{k}", img, 0.55))
            box(f"R_frame{k}", (-1.24, y, z), (0.012, 0.45, 0.62), principled(f"R_framemat{k}", (0.02, 0.02, 0.02), 0.4), 0.003, 1)
        # nightstand (camera right) with a mushroom lamp, glowing softly
        wood = principled("R_nightwood", (0.32, 0.22, 0.14), rough=0.45, coat=0.3)
        box("R_nightstand", (1.12, 0.85, 0.27), (0.42, 0.38, 0.54), wood, 0.02)
        shade = principled("R_lampshade", (1.0, 0.9, 0.8), rough=0.5, emission=(1.0, 0.55, 0.25), strength=3.0)
        bv, bf = uv_sphere(32, 16)
        keep = [q for q in bf if min(bv[k][2] for k in q) > -0.05]
        mesh_obj("R_lampshade", bv * np.array((0.11, 0.11, 0.08)), keep, shade, loc=(1.12, 0.85, 0.74))
        tube_mesh("R_lampstem", [(1.12, 0.85, 0.54), (1.12, 0.85, 0.74)], [0.012, 0.012], wood, segs=12)
        ll = bpy.data.lights.new("R_lamp", "POINT")
        ll.energy = 8.0
        ll.shadow_soft_size = 0.08
        ll.color = (1.0, 0.55, 0.25)
        lo = link(bpy.data.objects.new("R_lamp", ll))
        lo.location = (1.12, 0.85, 0.72)
        # the duvet (re-shaped by set_duvet)
        self.duvet_mat = _bump(principled("R_duvet", (0.42, 0.44, 0.55), rough=0.88, sheen=0.7), 180.0, 0.18, 0.0008)
        self.NX, self.NY = 100, 120
        self.duvet = mesh_obj("R_duvet", np.zeros(((self.NX + 1) * (self.NY + 1), 3)), self._grid_faces(), self.duvet_mat)
        sub = self.duvet.modifiers.new("Sub", "SUBSURF")
        sub.levels, sub.render_levels = 1, 1
        rng = np.random.default_rng(3)
        self.folds = [(rng.uniform(-0.8, 0.8), rng.uniform(-1.0, 0.4), rng.uniform(0.08, 0.2), rng.uniform(0, math.pi),
                       rng.uniform(0.006, 0.016)) for _ in range(22)]
        self._duvet_state = None

    def _grid_faces(self):
        f = []
        for j in range(self.NY):
            for i in range(self.NX):
                a = j * (self.NX + 1) + i
                f.append((a, a + 1, a + self.NX + 2, a + self.NX + 1))
        return f

    def set_duvet(self, hip_y, lie=0.0, knees=0.0):
        """hip_y: where his hips are on the bed; lie 1 = lying back (the duvet over his belly), 0 = sitting (lap).
        knees lifts the leg lump (knees up)."""
        key = (round(hip_y, 4), round(lie, 4), round(knees, 4))
        if key == self._duvet_state:
            return
        self._duvet_state = key
        NX, NY = self.NX, self.NY
        u = np.linspace(0, 1, NX + 1)
        vv = np.linspace(0, 1, NY + 1)
        U, Vv = np.meshgrid(u, vv)
        edge_y = hip_y + 0.08 + 0.12 * lie                      # the duvet's top edge (toward the headboard)
        y = -1.02 + (edge_y + 1.02) * Vv
        s = (U - 0.5) * 2.2                                       # -1.1 .. 1.1 across (beyond 0.8: hangs off the sides)
        top = BED_Z + 0.035
        ax = np.abs(s)
        over = np.clip(ax - 0.8, 0, None)
        x = np.sign(s) * (np.minimum(ax, 0.8) + 0.06 * (1 - np.exp(-over / 0.05)))
        z = top - over * 1.15
        # legs under the duvet (toward the foot), the hips, and (lying) the belly
        legs = np.exp(-((x - 0.13) / 0.16) ** 2) + np.exp(-((x + 0.13) / 0.16) ** 2)
        legs = np.minimum(legs, 1.15) / 1.15
        along = np.clip((hip_y - y) / 0.9, 0, 1)
        leg_h = (0.13 + 0.12 * knees * np.exp(-((along - 0.45) / 0.18) ** 2)) * legs * smooth_np((hip_y + 0.05 - y) / 0.15) * \
            smooth_np((y + 0.85) / 0.15)
        hips = 0.16 * np.exp(-(x / 0.3) ** 4) * np.exp(-((y - hip_y) / 0.2) ** 2)
        belly = lie * 0.26 * np.exp(-(x / 0.26) ** 4) * smooth_np((y - hip_y + 0.05) / 0.1)
        h = np.maximum(np.maximum(leg_h, hips), belly)
        z = z + h * (over == 0)
        # the top edge turns down a little; folds; a soft sag between the legs
        z = z - 0.03 * smooth_np((y - edge_y + 0.05) / 0.05)
        for (fx, fy, fw, fa, fh) in self.folds:
            d = (x - fx) * math.cos(fa) + (y - fy) * math.sin(fa)
            z = z + fh * np.exp(-(d / fw) ** 2) * (over == 0) * smooth_np((edge_y - y) / 0.1)
        verts = np.stack([x, y, z], axis=-1).reshape(-1, 3)
        self.duvet.data.vertices.foreach_set("co", verts.astype(np.float32).ravel())
        self.duvet.data.update()

    def led(self, mult=1.0, color=None):
        for lo in self.leds:
            lo.data.energy = lo.get("base", lo.data.energy) * mult if "base" in lo else lo.data.energy
        if color is not None:
            for lo in self.leds:
                lo.data.color = color
            self.led_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (*color, 1)


def smooth_np(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)
