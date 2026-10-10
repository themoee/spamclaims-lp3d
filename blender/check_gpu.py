import bpy, sys
prefs = bpy.context.preferences.addons['cycles'].preferences
for t in ('OPTIX', 'CUDA'):
    try:
        prefs.compute_device_type = t
        prefs.refresh_devices()
        devs = [(d.name, d.type) for d in prefs.devices if d.type == t]
        print('DEVICES', t, devs)
    except Exception as e:
        print('DEVICES', t, 'error', e)
print('VERSION', bpy.app.version_string)
