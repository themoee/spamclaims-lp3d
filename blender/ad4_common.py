"""Shared helpers for ad 4's Blender scene: geometry-nodes instancing from point clouds whose positions and attributes
are rewritten every frame with numpy, emission materials, and small math."""
import math

import bpy
import numpy as np


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def win(t, a, b):
    return smooth((t - a) / (b - a)) if b != a else float(t >= a)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def link(ob, coll=None):
    c = coll or bpy.context.scene.collection
    if ob.name not in c.objects:
        c.objects.link(ob)
    return ob


def point_cloud(name, n, attrs=None):
    """A vertex-only mesh with n points and float/vector attributes on the points (POINT domain)."""
    me = bpy.data.meshes.new(name)
    me.vertices.add(n)
    for aname, kind in (attrs or {}).items():
        me.attributes.new(aname, kind, "POINT")
    ob = bpy.data.objects.new(name, me)
    return ob


def set_points(ob, pos, **attrs):
    """Rewrite positions (n x 3) and attributes (n or n x 3) of a point cloud built by point_cloud()."""
    me = ob.data
    n = len(me.vertices)
    p = np.asarray(pos, dtype=np.float32).reshape(n, 3)
    me.vertices.foreach_set("co", p.ravel())
    for aname, val in attrs.items():
        a = me.attributes[aname]
        v = np.asarray(val, dtype=np.float32)
        key = "vector" if a.data_type == "FLOAT_VECTOR" else "value"
        a.data.foreach_set(key, v.ravel())
    me.update()


def instance_on_points(points_ob, inst_ob, name=None, rot_attr=None, scale_attr=None, collection_instance=False):
    """Geometry-nodes modifier: instance inst_ob (or a collection) on every point; rotation (Euler, radians) and
    scale (vector) come from named point attributes if given. Point attributes reach the instance as instancer
    attributes, which materials read with an Attribute node of type INSTANCER."""
    ng = bpy.data.node_groups.new(name or (points_ob.name + "GN"), "GeometryNodeTree")
    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi = ng.nodes.new("NodeGroupInput")
    go = ng.nodes.new("NodeGroupOutput")
    iop = ng.nodes.new("GeometryNodeInstanceOnPoints")
    if collection_instance:
        info = ng.nodes.new("GeometryNodeCollectionInfo")
        info.inputs["Collection"].default_value = inst_ob
        info.inputs["Separate Children"].default_value = True
        info.inputs["Reset Children"].default_value = True
        ng.links.new(info.outputs[0], iop.inputs["Instance"])
        iop.inputs["Pick Instance"].default_value = True
        idx = ng.nodes.new("GeometryNodeInputNamedAttribute")
        idx.data_type = "INT"
        idx.inputs["Name"].default_value = "pick"
        ng.links.new(idx.outputs["Attribute"], iop.inputs["Instance Index"])
    else:
        info = ng.nodes.new("GeometryNodeObjectInfo")
        info.inputs["Object"].default_value = inst_ob
        info.transform_space = "ORIGINAL"
        ng.links.new(info.outputs["Geometry"], iop.inputs["Instance"])
    ng.links.new(gi.outputs[0], iop.inputs["Points"])
    if rot_attr:
        ra = ng.nodes.new("GeometryNodeInputNamedAttribute")
        ra.data_type = "FLOAT_VECTOR"
        ra.inputs["Name"].default_value = rot_attr
        ng.links.new(ra.outputs["Attribute"], iop.inputs["Rotation"])
    if scale_attr:
        sa = ng.nodes.new("GeometryNodeInputNamedAttribute")
        sa.data_type = "FLOAT_VECTOR"
        sa.inputs["Name"].default_value = scale_attr
        ng.links.new(sa.outputs["Attribute"], iop.inputs["Scale"])
    ng.links.new(iop.outputs["Instances"], go.inputs[0])
    mod = points_ob.modifiers.new("Instances", "NODES")
    mod.node_group = ng
    return mod


def emission_material(name, color, strength=1.0, attr_strength=None, attr_type="INSTANCER"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    if attr_strength:
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_type = attr_type
        a.attribute_name = attr_strength
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = strength
        nt.links.new(a.outputs["Fac"], mul.inputs[0])
        nt.links.new(mul.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def set_time(materials, sec):
    """Every material with a Value node named 'T' gets the scene time."""
    for m in materials:
        n = m.node_tree.nodes.get("T")
        if n:
            n.outputs[0].default_value = sec


def look_at_euler(cam_loc, target, roll=0.0):
    import mathutils
    d = mathutils.Vector(target) - mathutils.Vector(cam_loc)
    q = d.to_track_quat("-Z", "Y")
    if roll:
        q = q @ mathutils.Quaternion((0, 0, 1), math.radians(roll))
    return q.to_euler()
