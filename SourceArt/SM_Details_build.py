"""
Scoreboards, rim flags and floodlight towers for the Thresholds coliseum greybox.  Metres, same export rule as the other pieces.
  Blender -b /tmp/sm_bowl_work.blend --python SM_Details_build.py -- [export]
Pieces: SM_Scoreboard (front-face centre at x=0, base z=0, faces -X), SM_RimFlag (pole at origin, flag streams +X),
        SM_LightTower (centre of base, bank faces -X).   Placement table -> /tmp/detail_placements.json
"""
import bpy, bmesh, math, os, sys, json, random
from mathutils import Vector

ROOT = '/Users/todddavilla/Unreal Projects/Repositories/JCOM_624_BIU'
SRC = ROOT + '/SourceArt'
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
DO_EXPORT = 'export' in args

# reuse the Piece helper (everything above the first builder) from the peristyle script
_src = open(SRC + '/SM_Peristyle_build.py').read()
_src = _src[:_src.index('def arc(')]
exec(compile(_src, 'peri_helpers', 'exec'))
RGB.update({
    'M_ScoreHousing': (0.02, 0.02, 0.022), 'M_ScoreFace': (0.9, 0.5, 0.1), 'M_TowerSteel': (0.45, 0.46, 0.48),
    'M_LampBank': (1.0, 0.95, 0.8), 'M_FlagPole': (0.9, 0.9, 0.88),
    'M_FlagCloth': (0.8, 0.1, 0.4),
})

POD_Z = 18.0


def strut(pc, a, b, r, mat):
    a, b = Vector(a), Vector(b)
    d = (b - a)
    ref = Vector((0, 0, 1)) if abs(d.normalized().z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(ref).normalized() * r
    w = d.cross(u).normalized() * r
    ring = lambda p: [tuple(p + u + w), tuple(p - u + w), tuple(p - u - w), tuple(p + u - w)]
    ra, rb = ring(a), ring(b)
    mid = (a + b) / 2
    for i in range(4):
        j = (i + 1) % 4
        pc.face([ra[i], ra[j], rb[j], rb[i]], mat, inside=tuple(mid))


# ------------------------------------------------------------------ SM_Scoreboard
def scoreboard():
    pc = Piece('SM_Scoreboard')
    W, H, D, PLH = 20.0, 15.0, 3.0, 22.0
    pc.box(0.3, D - 0.3, -5.0, 5.0, 0.0, PLH, 'M_ScoreHousing', skip=('zm',))
    pc.box(0.0, D, -W / 2, W / 2, PLH, PLH + H, 'M_ScoreHousing')
    fy, fz0, fz1 = 9.5, PLH + 0.5, PLH + H - 0.5
    x = -0.03
    # looking from -X, screen-right is -Y: U runs +Y -> -Y
    pts = [(x, fy, fz0), (x, -fy, fz0), (x, -fy, fz1), (x, fy, fz1)]
    pc.face(pts, 'M_ScoreFace', out=(-1, 0, 0), uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    return pc.finish()


# ------------------------------------------------------------------ SM_RimFlag
def flag():
    pc = Piece('SM_RimFlag')
    PH = 10.0
    pc.cyl(0, 0, 0.10, -1.2, 0.08, PH, 8, 'M_FlagPole', caps=(False, True))
    pc.cyl(0, 0, 0.22, PH, 0.001, PH + 0.5, 8, 'M_FlagPole', caps=(True, False))
    NX, NZ = 14, 4
    L, Hh, z1 = 4.6, 3.0, PH - 0.25
    x0 = 0.12
    for i in range(NX):
        for k in range(NZ):
            xa, xb = x0 + (L - x0) * i / NX, x0 + (L - x0) * (i + 1) / NX
            za, zb = z1 - Hh * k / NZ, z1 - Hh * (k + 1) / NZ
            ua, ub = i / NX, (i + 1) / NX
            va, vb = 1 - k / NZ, 1 - (k + 1) / NZ
            pc.face([(xa, 0, za), (xb, 0, za), (xb, 0, zb), (xa, 0, zb)], 'M_FlagCloth', out=(0, -1, 0),
                    uvs=[(ua, va), (ub, va), (ub, vb), (ua, vb)])
    return pc.finish()


# ------------------------------------------------------------------ SM_LightTower
def tower():
    pc = Piece('SM_LightTower')
    Z0, Z1 = -5.0, 40.0
    hb, ht = 4.6, 1.8
    N = 8
    zs = [Z0 + (Z1 - Z0) * i / N for i in range(N + 1)]
    hw = [hb + (ht - hb) * i / N for i in range(N + 1)]
    corners = lambda h, z: [(-h, -h, z), (h, -h, z), (h, h, z), (-h, h, z)]
    levels = [corners(hw[i], zs[i]) for i in range(N + 1)]
    for c in range(4):
        for i in range(N):
            strut(pc, levels[i][c], levels[i + 1][c], 0.22, 'M_TowerSteel')
    for i in range(N + 1):
        for c in range(4):
            strut(pc, levels[i][c], levels[i][(c + 1) % 4], 0.10, 'M_TowerSteel')
    for i in range(N):
        for c in range(4):
            d = (c + 1) % 4
            if (i + c) % 2 == 0:
                strut(pc, levels[i][c], levels[i + 1][d], 0.09, 'M_TowerSteel')
            else:
                strut(pc, levels[i][d], levels[i + 1][c], 0.09, 'M_TowerSteel')
    # platform + lamp bank
    pc.box(-2.4, 2.4, -2.4, 2.4, Z1, Z1 + 0.4, 'M_TowerSteel')
    BW, BH, BZ = 13.0, 7.0, Z1 + 1.2
    bx = -2.6
    pc.box(bx - 0.2, bx + 0.7, -BW / 2 - 0.3, BW / 2 + 0.3, BZ - 0.3, BZ + BH + 0.3, 'M_TowerSteel', skip=('xm',))
    x = bx - 0.22
    pts = [(x, BW / 2, BZ), (x, -BW / 2, BZ), (x, -BW / 2, BZ + BH), (x, BW / 2, BZ + BH)]
    pc.face(pts, 'M_LampBank', out=(-1, 0, 0), uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    strut(pc, (0, 0, Z1 + 0.4), (bx + 0.2, 0, BZ - 0.3), 0.3, 'M_TowerSteel')
    strut(pc, (0, 0, Z1 + 0.4), (bx + 0.2, 0, BZ + BH * 0.5), 0.3, 'M_TowerSteel')
    return pc.finish()


objs = {}
for nm, fn in (('SM_Scoreboard', scoreboard), ('SM_RimFlag', flag), ('SM_LightTower', tower)):
    if nm in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
    ob = fn()
    objs[nm] = ob
    d = ob.dimensions
    print('PIECE %-14s faces %5d dims %.2f x %.2f x %.2f slots %s' % (nm, len(ob.data.polygons), d.x, d.y, d.z, [m.name for m in ob.data.materials]))

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

# ------------------------------------------------------------------ placement
A, B, RUN, RIM_Z, WALL_H = 100.0, 62.5, 60.0, 32.0, 4.5
X_B = 146.0
PHI1, PHI2 = math.radians(30), math.radians(46)


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def s_of(th):
    w = (th + math.pi) % (2 * math.pi) - math.pi
    return 1.0 - smooth((abs(w) - PHI1) / (PHI2 - PHI1))


def rim_pt(th, inset=0.0):
    s = s_of(th)
    tb = (X_B / math.cos(th) - A) / RUN if abs(math.cos(th)) > 0.2 else 1.0
    t = s * tb + (1 - s) * 1.0
    return Vector(((A + RUN * t) * math.cos(th) - inset * math.cos(th), (B + RUN * t) * math.sin(th) - inset * math.sin(th), 0.0))


bowl = bpy.data.objects.get('SM_Bowl')
dg = bpy.context.evaluated_depsgraph_get()


def surf_z(x, y, default=RIM_Z):
    if bowl is None:
        return default
    hit, loc, nrm, idx, ob, mat = bpy.context.scene.ray_cast(dg, (x, y, 90.0), (0, 0, -1))
    return loc.z if hit else default


# arc-length resample of the rim polyline
M = 6000
pts = [rim_pt(2 * math.pi * i / M, 0.8) for i in range(M + 1)]
cum = [0.0]
for i in range(M):
    cum.append(cum[-1] + (pts[i + 1] - pts[i]).length)
TOT = cum[-1]
n = int(TOT // 10.0)
step = TOT / n
random.seed(84)
flags = []
j = 0
for k in range(n):
    sdist = k * step
    while cum[j + 1] < sdist:
        j += 1
    f = (sdist - cum[j]) / (cum[j + 1] - cum[j])
    p = pts[j] * (1 - f) + pts[j + 1] * f
    if p.x > 120.0 and abs(p.y) < 64.0:     # peristyle / scoreboard end: no flags
        continue
    z = surf_z(p.x, p.y)
    flags.append((round(p.x, 3), round(p.y, 3), round(z, 3), round(90.0 + random.uniform(-14, 14), 1), len(flags) % 6))
print('RIM perimeter %.1f m, poles %d' % (TOT, len(flags)))

towers = []
for (tx, side) in ((-52.0, 1), (52.0, 1), (0.0, -1)):
    # find the rim point at this x on the chosen long side
    th = math.acos(max(-1, min(1, tx / (A + RUN))))
    th = th if side > 0 else -th
    p = rim_pt(th, 5.5)
    z = surf_z(p.x, p.y)
    psi = math.degrees(math.atan2(p.y, p.x))     # local -X points at the pitch centre
    towers.append((round(p.x, 3), round(p.y, 3), round(z, 3), round(psi, 2)))
print('TOWERS', towers)

boards = [('amber', 139.0, 22.0, POD_Z), ('video', 139.0, -22.0, POD_Z)]
json.dump({'flags': flags, 'towers': towers, 'boards': boards}, open('/tmp/detail_placements.json', 'w'))

bpy.ops.wm.save_as_mainfile(filepath='/tmp/sm_details_work.blend')
