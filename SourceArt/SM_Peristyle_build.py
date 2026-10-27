"""
Peristyle (modular) for the Thresholds Coliseum greybox.  Metres.  Local origin of every piece = centre of its
front face at its base; +X = depth (away from the field), -X = front, +Y/-Y across, Z up.  (Blender +Y -> Unreal -Y.)

  Blender -b /tmp/sm_bowl_work.blend --python SM_Peristyle_build.py -- [export]
Pieces: SM_PeriColumn, SM_PeriArchBay, SM_PeriFrieze, SM_PeriTower, SM_Torch, SM_EndPylon, SM_PalmTree
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector

ROOT = '/Users/todddavilla/Unreal Projects/Repositories/JCOM_624_BIU'
SRC = ROOT + '/SourceArt'
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
DO_EXPORT = 'export' in args

# ------------------------------------------------------------------ dimensions
POD_Z = 18.0
FRONT_X = 132.0
P = 5.6                       # bay pitch (column centre to column centre)
NB = 7                        # bays each side of the tower
COL_R, COL_H = 0.6, 14.0
BAY_D = 5.0                   # depth of the colonnade
TOWER_W, TOWER_D, TOWER_H = 18.0, 12.0, 30.0   # top = 48 m above the field
FRIEZE_H = 3.55
PYL_W, PYL_D = 5.2, 5.0

RGB = {
    'M_PeriWhite': (0.93, 0.92, 0.88), 'M_PeriAqua': (0.12, 0.72, 0.74), 'M_PeriOrange': (0.96, 0.42, 0.08),
    'M_PeriMagenta': (0.82, 0.12, 0.50), 'M_PeriLavender': (0.66, 0.56, 0.86), 'M_ArchRed': (0.80, 0.14, 0.06),
    'M_FriezeText': (0.36, 0.30, 0.25), 'M_EmblemPlaceholder': (0.90, 0.88, 0.82), 'M_TorchMetal': (0.07, 0.07, 0.075),
    'M_PalmTrunk': (0.35, 0.24, 0.14), 'M_PalmFrond': (0.16, 0.38, 0.12),
}


class Piece:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.cache = {}
        self.mats = []
        self.uv = self.bm.loops.layers.uv.new('UVMap')
        self.col = self.bm.loops.layers.float_color.new('Col')

    def slot(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def v(self, p):
        key = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
        vv = self.cache.get(key)
        if vv is None:
            vv = self.bm.verts.new(key)
            self.cache[key] = vv
        return vv

    def face(self, pts, mat, out=None, inside=None, uvs=None):
        pairs = []
        for i, p in enumerate(pts):
            vv = self.v(p)
            if pairs and pairs[-1][0] is vv:
                continue
            pairs.append((vv, uvs[i] if uvs else (0.0, 0.0)))
        while len(pairs) > 1 and pairs[0][0] is pairs[-1][0]:
            pairs.pop()
        if len(set(id(a) for a, _ in pairs)) < 3:
            return None
        n = Vector((0, 0, 0))
        for i in range(len(pairs)):
            a, b = pairs[i][0].co, pairs[(i + 1) % len(pairs)][0].co
            n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
        if n.length < 1e-9:
            return None
        if out is not None:
            flip = n.dot(Vector(out)) < 0
        elif inside is not None:
            c = sum((a.co for a, _ in pairs), Vector((0, 0, 0))) / len(pairs)
            flip = n.dot(c - Vector(inside)) < 0
        else:
            flip = False
        if flip:
            pairs.reverse()
        try:
            f = self.bm.faces.new([a for a, _ in pairs])
        except ValueError:
            return None
        f.material_index = self.slot(mat)
        r, g, b = RGB[mat]
        for lp, (_, uv) in zip(f.loops, pairs):
            lp[self.uv].uv = uv
            lp[self.col] = (r, g, b, 1.0)
        return f

    # ---- primitives
    def box(self, x0, x1, y0, y1, z0, z1, mat, skip=()):
        c = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        F = {
            'xm': [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
            'xp': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
            'ym': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            'yp': [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
            'zm': [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
            'zp': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        }
        for k, pts in F.items():
            if k not in skip:
                self.face(pts, mat, inside=c)

    def frustum(self, cx, cy, hx0, hy0, z0, hx1, hy1, z1, mat, bottom=True):
        b = [(cx - hx0, cy - hy0, z0), (cx + hx0, cy - hy0, z0), (cx + hx0, cy + hy0, z0), (cx - hx0, cy + hy0, z0)]
        t = [(cx - hx1, cy - hy1, z1), (cx + hx1, cy - hy1, z1), (cx + hx1, cy + hy1, z1), (cx - hx1, cy + hy1, z1)]
        c = (cx, cy, (z0 + z1) / 2)
        for i in range(4):
            j = (i + 1) % 4
            self.face([b[i], b[j], t[j], t[i]], mat, inside=c)
        self.face(t, mat, out=(0, 0, 1))
        if bottom:
            self.face(b, mat, out=(0, 0, -1))

    def cyl(self, cx, cy, r0, z0, r1, z1, seg, mat, caps=(True, True), invert=False):
        c = (cx, cy, (z0 + z1) / 2)
        pb = [(cx + r0 * math.cos(2 * math.pi * i / seg), cy + r0 * math.sin(2 * math.pi * i / seg), z0) for i in range(seg)]
        pt = [(cx + r1 * math.cos(2 * math.pi * i / seg), cy + r1 * math.sin(2 * math.pi * i / seg), z1) for i in range(seg)]
        made = []
        for i in range(seg):
            j = (i + 1) % seg
            made.append(self.face([pb[i], pb[j], pt[j], pt[i]], mat, inside=c))
        if invert:
            for f in made:
                if f is not None:
                    f.normal_flip()
        if caps[1]:
            for i in range(seg):
                self.face([(cx, cy, z1), pt[i], pt[(i + 1) % seg]], mat, out=(0, 0, 1))
        if caps[0]:
            for i in range(seg):
                self.face([(cx, cy, z0), pb[i], pb[(i + 1) % seg]], mat, out=(0, 0, -1))

    def finish(self):
        me = bpy.data.meshes.new(self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            mt = bpy.data.materials.get(m) or bpy.data.materials.new(m)
            mt.use_nodes = True
            rgba = RGB[m] + (1.0,)
            next(n for n in mt.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = rgba
            mt.diffuse_color = rgba
            me.materials.append(mt)
        if 'Col' in me.color_attributes:
            me.color_attributes.active_color = me.color_attributes['Col']
            me.color_attributes.render_color_index = list(me.color_attributes.keys()).index('Col')
        for p in me.polygons:
            p.use_smooth = False
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def arc(yc, zc, r, n):
    return [(yc + r * math.cos(math.pi - math.pi * k / n), zc + r * math.sin(math.pi * k / n)) for k in range(n + 1)]


# ------------------------------------------------------------------ SM_PeriColumn
def column():
    pc = Piece('SM_PeriColumn')
    pc.cyl(0, 0, 0.72, 0.0, 0.72, 0.45, 24, 'M_PeriWhite', caps=(True, False))       # base ring
    pc.cyl(0, 0, COL_R, 0.45, COL_R, 13.0, 24, 'M_PeriWhite', caps=(False, False))     # shaft
    for z in (10.1, 10.85, 11.6):                                                       # three aqua bands
        pc.cyl(0, 0, COL_R + 0.03, z, COL_R + 0.03, z + 0.4, 24, 'M_PeriAqua', caps=(False, False))
        pc.cyl(0, 0, COL_R + 0.03, z, COL_R + 0.03, z + 0.4, 24, 'M_PeriAqua', caps=(False, False)) if False else None
    pc.box(-0.78, 0.78, -0.78, 0.78, 13.0, 14.0, 'M_PeriOrange')                        # capital block
    return pc.finish()


# ------------------------------------------------------------------ SM_PeriArchBay
def archbay():
    pc = Piece('SM_PeriArchBay')
    Wo = P - 2 * COL_R
    r = Wo / 2
    zs = COL_H - r
    n = 18
    pts = arc(0, zs, r, n)
    for xp, out in ((0.0, (-1, 0, 0)), (BAY_D, (1, 0, 0))):
        pc.face([(xp, -P / 2, 0), (xp, -r, 0), (xp, -r, COL_H), (xp, -P / 2, COL_H)], 'M_PeriWhite', out)
        pc.face([(xp, r, 0), (xp, P / 2, 0), (xp, P / 2, COL_H), (xp, r, COL_H)], 'M_PeriWhite', out)
        for k in range(n):
            (y0, z0), (y1, z1) = pts[k], pts[k + 1]
            pc.face([(xp, y0, z0), (xp, y1, z1), (xp, y1, COL_H), (xp, y0, COL_H)], 'M_PeriWhite', out)
    pc.face([(0, -r, 0), (BAY_D, -r, 0), (BAY_D, -r, zs), (0, -r, zs)], 'M_ArchRed', (0, 1, 0))
    pc.face([(0, r, 0), (BAY_D, r, 0), (BAY_D, r, zs), (0, r, zs)], 'M_ArchRed', (0, -1, 0))
    for k in range(n):
        (y0, z0), (y1, z1) = pts[k], pts[k + 1]
        c = (0, 0, zs)
        pc.face([(0, y0, z0), (BAY_D, y0, z0), (BAY_D, y1, z1), (0, y1, z1)], 'M_ArchRed', inside=(0, 0, 0.4 * zs + 0.6 * COL_H - 99) if False else None, out=(0, -(y0 + y1) / 2, zs - (z0 + z1) / 2))
    pc.face([(0, -P / 2, COL_H), (BAY_D, -P / 2, COL_H), (BAY_D, P / 2, COL_H), (0, P / 2, COL_H)], 'M_PeriWhite', (0, 0, 1))
    return pc.finish()


# ------------------------------------------------------------------ SM_PeriFrieze  (one wing, 7 bays long)
def frieze():
    pc = Piece('SM_PeriFrieze')
    L = NB * P
    x0, x1 = -0.3, BAY_D + 0.3
    pc.box(x0, x1, -L / 2, L / 2, 0.0, FRIEZE_H, 'M_PeriWhite')
    pc.box(x0 - 0.06, x0, -L / 2, L / 2, 0.25, 0.70, 'M_PeriAqua')                      # aqua band along the bottom
    pc.box(x0 - 0.05, x0 + 0.45, -L / 2, L / 2, FRIEZE_H - 0.12, FRIEZE_H + 0.16, 'M_PeriMagenta')  # thin magenta stripe along the front top edge
    # text plate on the front face: u runs to the viewer's right (-Y in Blender), v down
    z0, z1 = 0.95, 3.15
    xt = x0 - 0.08
    ya, yb = L / 2 - 0.8, -L / 2 + 0.8
    pc.face([(xt, ya, z0), (xt, yb, z0), (xt, yb, z1), (xt, ya, z1)], 'M_FriezeText', (-1, 0, 0),
            uvs=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
    return pc.finish()


# ------------------------------------------------------------------ SM_PeriTower
def star(pc, yc, zc, ro, x, mat):
    ri = ro * 0.4
    ptsx = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = ro if i % 2 == 0 else ri
        ptsx.append((x, yc + rr * math.cos(a), zc + rr * math.sin(a)))
    for i in range(10):
        pc.face([(x, yc, zc), ptsx[i], ptsx[(i + 1) % 10]], mat, (-1, 0, 0))


def tower():
    pc = Piece('SM_PeriTower')
    W2, D, H = TOWER_W / 2, TOWER_D, TOWER_H
    r = 3.5
    crown = 15.0
    zs = crown - r
    n = 20
    pts = arc(0, zs, r, n)
    for xp, out in ((0.0, (-1, 0, 0)), (D, (1, 0, 0))):
        pc.face([(xp, -W2, 0), (xp, -r, 0), (xp, -r, H), (xp, -W2, H)], 'M_PeriWhite', out)
        pc.face([(xp, r, 0), (xp, W2, 0), (xp, W2, H), (xp, r, H)], 'M_PeriWhite', out)
        for k in range(n):
            (y0, z0), (y1, z1) = pts[k], pts[k + 1]
            pc.face([(xp, y0, z0), (xp, y1, z1), (xp, y1, H), (xp, y0, H)], 'M_PeriWhite', out)
    pc.face([(0, -r, 0), (D, -r, 0), (D, -r, zs), (0, -r, zs)], 'M_ArchRed', (0, 1, 0))
    pc.face([(0, r, 0), (D, r, 0), (D, r, zs), (0, r, zs)], 'M_ArchRed', (0, -1, 0))
    for k in range(n):
        (y0, z0), (y1, z1) = pts[k], pts[k + 1]
        pc.face([(0, y0, z0), (D, y0, z0), (D, y1, z1), (0, y1, z1)], 'M_ArchRed', out=(0, -(y0 + y1) / 2, zs - (z0 + z1) / 2))
    # sides (the tower is a solid block)
    pc.face([(0, -W2, 0), (D, -W2, 0), (D, -W2, H), (0, -W2, H)], 'M_PeriWhite', (0, -1, 0))
    pc.face([(0, W2, 0), (D, W2, 0), (D, W2, H), (0, W2, H)], 'M_PeriWhite', (0, 1, 0))
    pc.face([(0, -W2, H), (D, -W2, H), (D, W2, H), (0, W2, H)], 'M_PeriWhite', (0, 0, 1))
    pc.box(-0.6, D + 0.6, -W2 - 0.6, W2 + 0.6, H - 0.9, H, 'M_PeriWhite')                 # cornice
    # aqua trim around the arch (front)
    tw, xo = 0.55, -0.18
    inner = [(-r, 0.0)] + [(-r, zs)] + [(y, z) for (y, z) in pts[1:-1]] + [(r, zs), (r, 0.0)]
    outer = [(-r - tw, 0.0), (-r - tw, zs)] + [((r + tw) * (y / r), zs + (r + tw) * ((z - zs) / r)) for (y, z) in pts[1:-1]] + [(r + tw, zs), (r + tw, 0.0)]
    for i in range(len(inner) - 1):
        a, b, c, d = inner[i], inner[i + 1], outer[i + 1], outer[i]
        pc.face([(xo, a[0], a[1]), (xo, b[0], b[1]), (xo, c[0], c[1]), (xo, d[0], d[1])], 'M_PeriAqua', (-1, 0, 0))
        pc.face([(0, d[0], d[1]), (xo, d[0], d[1]), (xo, c[0], c[1]), (0, c[0], c[1])], 'M_PeriAqua', out=(0, d[0] - 0, d[1] - zs))
    # magenta band with a row of white stars, upper face
    bz0, bz1 = 24.0, 26.6
    pc.box(-0.14, 0.0, -W2, W2, bz0, bz1, 'M_PeriMagenta', skip=('xp',))
    for yc in (-7.5, -5.0, -2.5, 0.0, 2.5, 5.0, 7.5):
        star(pc, yc, (bz0 + bz1) / 2, 0.95, -0.15, 'M_PeriWhite')
    # flat plate for the rings, below the band
    pc.box(-0.22, 0.0, -4.2, 4.2, 18.8, 23.4, 'M_EmblemPlaceholder', skip=('xp',))
    return pc.finish()


# ------------------------------------------------------------------ SM_Torch
def torch():
    pc = Piece('SM_Torch')
    pc.frustum(0, 0, 1.6, 1.6, 0.0, 0.9, 0.9, 15.0, 'M_PeriWhite', bottom=False)
    pc.box(-1.1, 1.1, -1.1, 1.1, 15.0, 15.45, 'M_PeriOrange')
    # dark metal bowl: outer, rim, inner, floor
    seg = 20
    pc.cyl(0, 0, 0.8, 15.45, 1.9, 16.9, seg, 'M_TorchMetal', caps=(True, False))
    pc.cyl(0, 0, 1.9, 16.9, 1.7, 17.05, seg, 'M_TorchMetal', caps=(False, False))
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        o0 = (1.9 * math.cos(a0), 1.9 * math.sin(a0), 16.9)
        o1 = (1.9 * math.cos(a1), 1.9 * math.sin(a1), 16.9)
        i0 = (1.7 * math.cos(a0), 1.7 * math.sin(a0), 17.05)
        i1 = (1.7 * math.cos(a1), 1.7 * math.sin(a1), 17.05)
        pc.face([o0, o1, i1, i0], 'M_TorchMetal', (0, 0, 1))
    pc.cyl(0, 0, 0.7, 16.3, 1.7, 17.05, seg, 'M_TorchMetal', caps=(True, False), invert=True)   # inner surface, facing in
    return pc.finish()


# ------------------------------------------------------------------ SM_EndPylon
def pylon():
    pc = Piece('SM_EndPylon')
    hw, D = PYL_W / 2, PYL_D
    BH = 18.6
    pc.box(0.0, D, -hw, hw, 0.0, BH, 'M_PeriWhite', skip=('zm',))
    pc.box(-0.12, 0.0, -1.9, 1.9, 9.6, 12.8, 'M_EmblemPlaceholder', skip=('xp',))        # flat face plate for the emblem
    cx = D / 2
    pc.box(cx - 2.3, cx + 2.3, -2.3, 2.3, BH, BH + 3.0, 'M_PeriAqua')
    pc.box(cx - 1.9, cx + 1.9, -1.9, 1.9, BH + 3.0, BH + 6.0, 'M_PeriLavender')
    pc.box(cx - 1.5, cx + 1.5, -1.5, 1.5, BH + 6.0, BH + 9.0, 'M_PeriOrange')
    return pc.finish()


# ------------------------------------------------------------------ SM_PalmTree (low poly)
def palm():
    pc = Piece('SM_PalmTree')
    seg, rings = 7, 9
    prev = None
    for i in range(rings + 1):
        z = 8.0 * i / rings
        lean = 0.035 * z * z
        r = 0.38 - 0.16 * (i / rings)
        ring = [(lean + r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z) for k in range(seg)]
        if prev:
            for k in range(seg):
                j = (k + 1) % seg
                pc.face([prev[k], prev[j], ring[j], ring[k]], 'M_PalmTrunk', inside=(sum(p[0] for p in ring) / seg, 0, z - 0.5))
        prev = ring
    top = (0.035 * 64, 0.0, 8.0)
    nfr = 11
    for f in range(nfr):
        a = 2 * math.pi * f / nfr + 0.2
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-math.sin(a), math.cos(a), 0))
        L = 4.2 + 0.5 * math.sin(f * 2.1)
        N = 5
        left, right = [], []
        for j in range(N + 1):
            u = j / N
            h = 1.5 * math.sin(math.pi * 0.55 * u) - 2.1 * u * u
            w = 0.75 * (1 - u) ** 0.6 + 0.05
            c = Vector(top) + d * (L * u) + Vector((0, 0, h + 0.3))
            left.append(c + side * w)
            right.append(c - side * w)
        for j in range(N):
            pc.face([tuple(left[j]), tuple(right[j]), tuple(right[j + 1]), tuple(left[j + 1])], 'M_PalmFrond', out=(0, 0, 1))
    return pc.finish()


builders = [column, archbay, frieze, tower, torch, pylon, palm]
objs = {}
for b in builders:
    nm = {'column': 'SM_PeriColumn', 'archbay': 'SM_PeriArchBay', 'frieze': 'SM_PeriFrieze', 'tower': 'SM_PeriTower',
          'torch': 'SM_Torch', 'pylon': 'SM_EndPylon', 'palm': 'SM_PalmTree'}[b.__name__]
    if nm in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
    ob = b()
    objs[nm] = ob
    d = ob.dimensions
    vs = ob.data.vertices
    print('PIECE %-16s faces %5d  dims %.2f x %.2f x %.2f  slots %s' % (nm, len(ob.data.polygons), d.x, d.y, d.z, [m.name for m in ob.data.materials]))
    ob.hide_viewport = False

# ------------------------------------------------------------------ export (each piece at the origin, per the export rule)
if DO_EXPORT:
    for nm, ob in objs.items():
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        path = SRC + '/' + nm + '.fbx'
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0,
                                 apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Y', axis_up='Z',
                                 bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type='FACE', add_leaf_bones=False,
                                 path_mode='AUTO')
        print('EXPORTED', path, os.path.getsize(path))

# ------------------------------------------------------------------ assemble on the podium (preview copies + placement table)
bowl = bpy.data.objects.get('SM_Bowl')
dg = bpy.context.evaluated_depsgraph_get()


def surf_z(x, y):
    if bowl is None:
        return POD_Z
    hit, loc, nrm, idx, ob, mat = bpy.context.scene.ray_cast(dg, (x, y, 80.0), (0, 0, -1))
    return loc.z if hit else POD_Z


placements = []   # (piece, x, y, z, yaw_deg, scale, variant)
placements.append(('SM_PeriTower', FRONT_X, 0.0, POD_Z, 0, 1.0, ''))
for sgn in (1, -1):
    for k in range(NB):
        placements.append(('SM_PeriArchBay', FRONT_X, sgn * (TOWER_W / 2 + P / 2 + P * k), POD_Z, 0, 1.0, ''))
    for j in range(1, NB):
        placements.append(('SM_PeriColumn', FRONT_X - 0.3, sgn * (TOWER_W / 2 + P * j), POD_Z, 0, 1.0, ''))
    placements.append(('SM_PeriFrieze', FRONT_X, sgn * (TOWER_W / 2 + NB * P / 2), POD_Z + COL_H, 0, 1.0, 'left' if sgn > 0 else 'right'))
    placements.append(('SM_EndPylon', FRONT_X, sgn * (TOWER_W / 2 + NB * P + PYL_W / 2), POD_Z, 0, 1.0, ''))
    for dy, sc, yaw in ((PYL_W / 2 + 3.4, 1.0, 20), (PYL_W / 2 + 7.2, 0.82, 140)):
        yy = sgn * (TOWER_W / 2 + NB * P + dy)
        placements.append(('SM_PalmTree', FRONT_X + 2.0, yy, surf_z(FRONT_X + 2.0, yy), yaw, sc, ''))
placements.append(('SM_Torch', FRONT_X + TOWER_D / 2, 0.0, POD_Z + TOWER_H, 0, 1.0, ''))

for (nm, x, y, z, yaw, sc, var) in placements:
    o = objs[nm].copy()
    o.data = objs[nm].data
    o.name = 'ASM_' + nm + ('_' + var if var else '')
    o.location = (x, y, z)
    o.rotation_euler = (0, 0, math.radians(yaw))
    o.scale = (sc, sc, sc)
    bpy.context.scene.collection.objects.link(o)
for nm in objs:
    objs[nm].hide_viewport = True
    objs[nm].hide_render = True

import json
json.dump([(p[0], round(p[1], 3), round(p[2], 3), round(p[3], 3), p[4], p[5], p[6]) for p in placements], open('/tmp/peri_placements.json', 'w'))
print('PLACEMENTS', len(placements))
for p in placements:
    if p[0] in ('SM_EndPylon', 'SM_PalmTree'):
        print('PLACE', p[0], round(p[1], 2), round(p[2], 2), 'z=%.2f' % p[3])
bpy.ops.wm.save_as_mainfile(filepath='/tmp/sm_full_work.blend')
