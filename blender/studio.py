"""Studio, camera and render helpers shared by the still and animation scripts (Cycles, real scale)."""
import math
import os
DEVICE_TYPE = os.environ.get("CYCLES_DEVICE", "CUDA")

import bpy
from mathutils import Vector


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    return scene


def setup_render(scene, res=(1600, 1000), samples=192, transparent=False, gpu=True, denoise=True):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.01
    scene.cycles.max_bounces = 12
    scene.cycles.glossy_bounces = 8
    scene.cycles.transmission_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.sample_clamp_indirect = 8.0
    scene.cycles.blur_glossy = 0.4
    scene.cycles.use_denoising = denoise
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = transparent
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    if gpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = DEVICE_TYPE
        prefs.refresh_devices()
        for dev in prefs.devices:
            dev.use = dev.type == DEVICE_TYPE
        scene.cycles.device = "GPU"
    vs = scene.view_settings
    try:
        vs.view_transform = "Khronos PBR Neutral"   # keeps albedo hue/saturation, rolls off only the highlights
    except TypeError:
        vs.view_transform = "AgX"
    vs.look = "None"
    vs.exposure = 0.0
    vs.gamma = 1.0


def world(scene, bg=(0.0030, 0.0042, 0.0085), top=0.55, mid=0.10, low=0.025, strength=1.0):
    """World: reflections see a soft studio dome (bright overhead, a dim horizon, a dark floor) with two
    soft vertical bands left/right; camera rays see the page background color."""
    w = bpy.data.worlds.new("World")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    # elevation ramp on z in [-1, 1]
    mz = nt.nodes.new("ShaderNodeMapRange")
    mz.inputs["From Min"].default_value = -1.0
    mz.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mz.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (low, low, low, 1.0)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (top, top, top, 1.0)
    e = cr.elements.new(0.52)
    e.color = (mid, mid, mid, 1.0)
    e2 = cr.elements.new(0.80)
    e2.color = (top * 0.75, top * 0.75, top * 0.75, 1.0)
    nt.links.new(mz.outputs["Result"], ramp.inputs["Fac"])
    # vertical soft bands at |x| ~ 0.85 (strip-light look in reflections)
    ax = nt.nodes.new("ShaderNodeMath")
    ax.operation = "ABSOLUTE"
    nt.links.new(sep.outputs["X"], ax.inputs[0])
    band = nt.nodes.new("ShaderNodeMapRange")
    band.interpolation_type = "SMOOTHSTEP"
    band.inputs["From Min"].default_value = 0.70
    band.inputs["From Max"].default_value = 0.92
    band.inputs["To Min"].default_value = 0.0
    band.inputs["To Max"].default_value = 0.45
    nt.links.new(ax.outputs[0], band.inputs["Value"])
    add = nt.nodes.new("ShaderNodeMix")
    add.data_type = "RGBA"
    add.blend_type = "ADD"
    add.inputs[0].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], add.inputs[6])
    nt.links.new(band.outputs["Result"], add.inputs[7])
    env = nt.nodes.new("ShaderNodeBackground")
    env.inputs["Strength"].default_value = strength
    nt.links.new(add.outputs[2], env.inputs["Color"])
    cam = nt.nodes.new("ShaderNodeBackground")
    cam.inputs["Color"].default_value = (*bg, 1.0)
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(env.outputs[0], mix.inputs[1])
    nt.links.new(cam.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return w


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def area_light(name, loc, target, size=(0.5, 0.3), power=50.0, color=(1, 1, 1), spread=180.0, visible_camera=False,
               visible_glossy=True):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = size
    data.energy = power
    data.color = color
    try:
        data.spread = math.radians(spread)
    except Exception:
        pass
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    look_at(ob, target)
    ob.visible_camera = visible_camera
    ob.visible_glossy = visible_glossy
    return ob


def card(name, loc, target, size=(1.0, 1.0), strength=1.0, color=(1, 1, 1), gradient=True):
    """An emissive reflection card: seen in glossy reflections, invisible to the camera."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.scale = (size[0], size[1], 1.0)
    ob.location = loc
    look_at(ob, target)
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    if gradient:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.0
        mr.inputs["From Max"].default_value = 1.0
        mr.inputs["To Min"].default_value = 0.05
        mr.inputs["To Max"].default_value = strength
        nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
        nt.links.new(sep.outputs["Y"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], em.inputs["Strength"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    me.materials.append(mat)
    ob.visible_camera = False
    ob.visible_shadow = False
    return ob


def camera(name, loc, target, lens=85.0, fstop=None, focus_target=None, ortho_scale=None, sensor=36.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = sensor
    cam.clip_start = 0.005
    cam.clip_end = 50.0
    if ortho_scale is not None:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho_scale
    if fstop is not None:
        cam.dof.use_dof = True
        cam.dof.aperture_fstop = fstop
        if focus_target is not None:
            cam.dof.focus_distance = (Vector(focus_target) - Vector(loc)).length
    ob = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    look_at(ob, target)
    return ob


def product_studio(scene, warm=(1.0, 0.62, 0.36), cool=(0.55, 0.72, 1.0), k=1.0, env=1.0):
    """Product studio, Z-up, camera on -Y looking +Y at the origin."""
    world(scene, strength=env)
    T = (0.0, 0.0, 0.0)
    area_light("Key", (-0.50, -0.60, 0.55), T, size=(0.9, 0.5), power=22.0 * k)
    area_light("StripL", (-0.46, 0.18, 0.04), T, size=(0.035, 1.2), power=12.0 * k)
    area_light("StripR", (0.46, 0.15, 0.04), T, size=(0.035, 1.2), power=12.0 * k)
    area_light("RimWarm", (0.30, 0.55, 0.38), T, size=(0.6, 0.6), power=14.0 * k, color=warm)
    area_light("FillCool", (0.32, -0.55, -0.35), T, size=(0.8, 0.4), power=2.5 * k, color=cool, visible_glossy=False)
