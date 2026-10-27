"""SM_CrowdCard: 1 m x 1 m upright quad, pivot at bottom centre, facing local +X, UV (0,0) top-left of the image.
Normals are tilted up (0.55, 0, 0.83) so sunlit cards read evenly whichever way they face.
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --python SM_CrowdCard_build.py
"""
import bpy, bmesh, math
from mathutils import Vector
ROOT = '/Users/todddavilla/Unreal Projects/Repositories/JCOM_624_BIU'
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('SM_CrowdCard')
bm = bmesh.new()
vs = [bm.verts.new(p) for p in ((0, -0.5, 0), (0, 0.5, 0), (0, 0.5, 1), (0, -0.5, 1))]
f = bm.faces.new(vs)
uv = bm.loops.layers.uv.new('UVMap')
for lp, (u, v) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):   # blender v up == top of image
    lp[uv].uv = (u, v)
bm.normal_update()
if f.normal.x < 0:
    f.normal_flip()
bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new('SM_CrowdCard', me)
bpy.context.scene.collection.objects.link(ob)
n = Vector((0.55, 0.0, 0.83)).normalized()
me.normals_split_custom_set([n] * len(me.loops))
m = bpy.data.materials.new('M_CrowdCard')
me.materials.append(m)
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.fbx(filepath=ROOT + '/SourceArt/SM_CrowdCard.fbx', use_selection=True, object_types={'MESH'}, global_scale=1.0,
                         apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Y', axis_up='Z',
                         bake_space_transform=False, mesh_smooth_type='OFF', add_leaf_bones=False, path_mode='AUTO')
print('RESULT exported', [tuple(round(c, 2) for c in v.co) for v in me.vertices], f.normal)
