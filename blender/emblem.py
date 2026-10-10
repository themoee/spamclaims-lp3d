"""The SpamClaims shield emblem in 3D, from the outlines traced out of the real logo (shield_outline.json):
a glossy navy enamel shield (with the speech-bubble tail) and a raised, polished orange-metal dollar sign
with the logo's top-to-bottom gradient. Z-up world; the emblem faces -Y (the default camera side)."""
import json
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))


def _srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _curve_from_poly(name, pts, height, depth, bevel, parent, mat, y_offset=0.0):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = depth / 2
    cu.bevel_mode = "ROUND"
    cu.bevel_depth = bevel
    cu.bevel_resolution = 6
    cu.offset = 0.0
    cu.resolution_u = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, (x, y) in enumerate(pts):
        sp.points[i].co = (x * height, y * height, 0.0, 1.0)
    sp.use_cyclic_u = True
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.data.materials.append(mat)
    return ob


def build_emblem(name="Emblem", height=0.09):
    data = json.load(open(os.path.join(HERE, "shield_outline.json")))
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)

    navy = tuple(_srgb_to_lin(c) for c in (36, 52, 86))
    m_shield = bpy.data.materials.new(name + "_navy")
    m_shield.use_nodes = True
    p = m_shield.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*navy, 1.0)
    p.inputs["Roughness"].default_value = 0.22
    p.inputs["Coat Weight"].default_value = 1.0
    p.inputs["Coat Roughness"].default_value = 0.035

    m_dollar = bpy.data.materials.new(name + "_orange")
    m_dollar.use_nodes = True
    nt = m_dollar.node_tree
    q = nt.nodes.get("Principled BSDF")
    # glossy orange enamel over a metal base: bare metal mirrors the dark studio and reads brown, the logo's
    # dollar is a bright orange gradient, so mostly dielectric, a clear coat for the highlights, a little glow
    q.inputs["Metallic"].default_value = 0.25
    q.inputs["Roughness"].default_value = 0.22
    q.inputs["Coat Weight"].default_value = 1.0
    q.inputs["Coat Roughness"].default_value = 0.04
    q.inputs["Emission Strength"].default_value = 0.28
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -0.3 * height
    mr.inputs["From Max"].default_value = 0.3 * height
    nt.links.new(sep.outputs["Y"], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*(_srgb_to_lin(c) for c in (238, 106, 31)), 1.0)
    ramp.color_ramp.elements[1].color = (*(_srgb_to_lin(c) for c in (248, 162, 58)), 1.0)
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], q.inputs["Base Color"])
    nt.links.new(ramp.outputs["Color"], q.inputs["Emission Color"])

    shield = _curve_from_poly(name + "_shield", data["points"], height, depth=0.16 * height, bevel=0.028 * height,
                              parent=root, mat=m_shield)
    for i, pts in enumerate(data["dollar"]):
        dob = _curve_from_poly(f"{name}_dollar{i}", pts, height, depth=0.07 * height, bevel=0.012 * height,
                               parent=root, mat=m_dollar)
        dob.location = (0.0, 0.0, 0.08 * height + 0.03 * height)
    # curves are built in the XY plane facing +Z; stand the emblem up facing -Y
    root.rotation_euler = (1.5707963, 0.0, 0.0)
    shield.location = (0.0, 0.0, 0.0)
    return root
