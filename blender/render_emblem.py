import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import studio, emblem
HERE = os.path.dirname(os.path.abspath(__file__))
scene = studio.reset_scene()
studio.setup_render(scene, res=(900, 900), samples=128)
studio.product_studio(scene)
e = emblem.build_emblem(height=0.09)
turn = bpy.data.objects.new("Turn", None); scene.collection.objects.link(turn); e.parent = turn
turn.rotation_euler = (math.radians(6), 0, math.radians(-18))
cam = studio.camera("Cam", (0, -0.42, 0.02), (0, 0, 0), lens=85)
scene.camera = cam
scene.render.filepath = os.path.join(HERE, "renders", "emblem_test.png")
bpy.ops.render.render(write_still=True)
print("RENDERED", scene.render.filepath)
