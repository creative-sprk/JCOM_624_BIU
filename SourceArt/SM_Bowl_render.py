"""Workbench previews of SM_Bowl (+ context meshes). Run after SM_Bowl_build.py:
  Blender -b /tmp/sm_bowl_work.blend --python SM_Bowl_render.py -- <outdir> <view> [<view> ...]
views: mouth, finish, aerial, east
"""
import bpy, math, sys, os
from mathutils import Vector

ROOT = '/Users/todddavilla/Unreal Projects/Repositories/JCOM_624_BIU'
SRC = ROOT + '/SourceArt'
args = sys.argv[sys.argv.index('--') + 1:]
outdir, views = args[0], args[1:]
os.makedirs(outdir, exist_ok=True)

scene = bpy.context.scene
bowl = bpy.data.objects['SM_Bowl']


def tint(ob, rgba):
    me = ob.data
    if 'Col' in me.color_attributes:
        me.color_attributes.remove(me.color_attributes['Col'])
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    for d in ca.data:
        d.color = rgba


ctx = (('SM_Track', (0.55, 0.22, 0.16, 1)), ('SM_Tunnel', (0.35, 0.35, 0.34, 1)))
for name, rgba in ctx:
    if name in bpy.data.objects:
        continue
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.fbx(filepath=SRC + '/' + name + '.fbx', axis_forward='-Y', axis_up='Z')
    for n in set(bpy.data.objects.keys()) - before:
        o = bpy.data.objects[n]
        if o.type == 'MESH':
            tint(o, rgba)
            if name == 'SM_PeristyleBlock':   # preview it standing on the new podium
                o.location = (30.5, 0.0, 18.0)
            dims = o.dimensions
            if max(dims) > 1000:  # imported in centimetres
                o.scale = (0.01, 0.01, 0.01)
                bpy.context.view_layer.update()
        print('CTX', name, o.name, tuple(round(v, 1) for v in o.dimensions), tuple(round(v, 1) for v in o.location))

# world / render
w = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
scene.world = w
w.use_nodes = False
w.color = (0.45, 0.62, 0.85)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
scene.render.film_transparent = False
sh = scene.display.shading
sh.light = 'STUDIO'
sh.color_type = 'VERTEX'
sh.show_shadows = False
sh.shadow_intensity = 0.3
sh.show_cavity = False
sh.show_object_outline = False
sh.show_specular_highlight = False
scene.display.light_direction = Vector((0.35, 0.25, 0.9))
try:
    scene.render.image_settings.file_format = 'PNG'
except Exception:
    pass

cam_data = bpy.data.cameras.new('Cam')
cam = bpy.data.objects.new('Cam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def shoot(name, loc, look_at, lens=24.0):
    cam.location = loc
    cam_data.lens = lens
    cam_data.clip_start, cam_data.clip_end = 0.1, 2000
    d = Vector(look_at) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(outdir, name + '.png')
    bpy.ops.render.render(write_still=True)
    print('RENDERED', scene.render.filepath)


for v in views:
    if v == 'mouth':     # from the tunnel mouth looking east
        shoot('bowl_from_tunnel_mouth_looking_east', (-99.0, 0.0, 1.7), (140.0, 0.0, 22.0), 22.0)
    elif v == 'finish':  # from the track at the finish line looking at the east end
        shoot('bowl_from_finish_line_looking_east', (57.0, 0.0, 1.7), (140.0, 0.0, 26.0), 24.0)
    elif v == 'aerial':
        shoot('bowl_aerial_from_west', (-210.0, -150.0, 150.0), (30.0, 0.0, 0.0), 28.0)
    elif v == 'east':
        shoot('bowl_east_end_closeup', (60.0, 0.0, 30.0), (135.0, 0.0, 14.0), 30.0)
    elif v == 'peri':
        shoot('peristyle_front', (95.0, 0.0, 14.0), (140.0, 0.0, 28.0), 20.0)
    elif v == 'periside':
        shoot('peristyle_oblique', (100.0, 85.0, 38.0), (140.0, -5.0, 30.0), 28.0)
    elif v == 'northeast':
        shoot('bowl_aerial_northeast', (150.0, 140.0, 90.0), (60.0, -10.0, 8.0), 30.0)
