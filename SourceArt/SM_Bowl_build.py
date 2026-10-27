"""
SM_Bowl (Thresholds greybox) -- rebuilds the whole bowl, closed at the east end.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b --python SM_Bowl_build.py -- [export] [render]

Units: metres. +X = east (peristyle end), tunnel door at -X. Track at Z = 0.
Slots: 0 M_Concrete, 1 M_ConcreteAisle, 2 M_Vomitory, 3 M_StairStripes
"""
import bpy, bmesh, math, os, sys, shutil, bisect
from mathutils import Vector

ROOT = '/Users/todddavilla/Unreal Projects/Repositories/JCOM_624_BIU'
SRC = ROOT + '/SourceArt'
REF = SRC + '/Reference/BowlRevision'
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
DO_EXPORT = 'export' in args
DO_RENDER = 'render' in args

# ------------------------------------------------------------------ parameters
A, B = 100.0, 62.5                    # inner (track wall) ellipse semi-axes
WALL_H, RUN, RIM_Z = 4.5, 60.0, 32.0  # wall height, outward run of the stands, rim height
PODIUM_Z = 18.0
SLOPE = (RIM_Z - WALL_H) / RUN
TP = (PODIUM_Z - WALL_H) / (RIM_Z - WALL_H)  # t where the east stands reach the podium
X_B = 146.0                           # straight back edge of the podium
PHI1, PHI2 = math.radians(30), math.radians(46)  # east sector fully podium / back to normal stands
KP, KS = 16, 22                       # rows: below the podium crease / above it
DOOR_HALF, DOOR_H = 2.25, 3.5         # tunnel opening (unchanged)
STAIR_HALF = 5.0                      # 10 m stairway
AISLE_SPACING, AISLE_HALF, AISLE_RISE = 25.0, 0.8, 0.25
VOM_SPACING, VOM_HALF_W = 50.0, 2.0   # 4 m wide openings
VOM_ROW0, VOM_ROW1 = 9, 13            # grid rows (of KP) the recess spans: ~7 m deep, a third of the way up
NBASE = 288

SLOT = {'concrete': 0, 'aisle': 1, 'vom': 2, 'stripe': 3}
COL = {
    'concrete': (0.45, 0.45, 0.43, 1), 'aisle': (0.30, 0.30, 0.29, 1),
    'vom': (0.015, 0.015, 0.015, 1),
}
STRIPES = [(0.90, 0.10, 0.55, 1), (1.00, 0.45, 0.05, 1), (1.00, 0.85, 0.10, 1), (0.05, 0.75, 0.80, 1)]  # magenta orange yellow aqua


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def s_of(th):
    return 1.0 - smooth((abs(wrap(th)) - PHI1) / (PHI2 - PHI1))


def t_out(th):
    s = s_of(th)
    tb = (X_B / math.cos(th) - A) / RUN if abs(math.cos(th)) > 0.2 else 1.0   # reaches the straight back edge x = X_B
    return s * tb + (1.0 - s) * 1.0


def z_of(t, th):
    s = s_of(th)
    return min(RIM_Z, WALL_H + (RIM_Z - WALL_H) * ((1 - s) * t + s * min(t, TP)))


def P(th, t, z=None):
    return Vector(((A + RUN * t) * math.cos(th), (B + RUN * t) * math.sin(th), z_of(t, th) if z is None else z))


def tangent(th, t):
    v = Vector((-(A + RUN * t) * math.sin(th), (B + RUN * t) * math.cos(th), 0))
    return v.normalized()


# ------------------------------------------------------------------ arc length of the inner ellipse
_N = 20000
_TH = [2 * math.pi * i / _N for i in range(_N + 1)]
_S = [0.0]
for _i in range(_N):
    _m = 0.5 * (_TH[_i] + _TH[_i + 1])
    _S.append(_S[-1] + math.hypot(A * math.sin(_m), B * math.cos(_m)) * (_TH[1] - _TH[0]))
PER = _S[-1]


def theta_at(sv):
    sv %= PER
    k = bisect.bisect_left(_S, sv)
    k = max(1, min(_N, k))
    f = (sv - _S[k - 1]) / max(1e-12, _S[k] - _S[k - 1])
    return _TH[k - 1] + f * (_TH[k] - _TH[k - 1])


# ------------------------------------------------------------------ feature placement
aisle_th = []
for k in range(40):
    sv = AISLE_SPACING / 2 + AISLE_SPACING * k
    if sv > PER / 2:
        break
    aisle_th.append(theta_at(sv))
    aisle_th.append(theta_at(PER - sv))
aisle_th = sorted(set(round(a, 9) for a in aisle_th))

vom = []  # (theta_c, dtheta)
for quarter in (PER / 4, 3 * PER / 4):
    for m in (-1, 0, 1):
        th = theta_at(quarter + m * VOM_SPACING)
        if abs(A * math.cos(th)) > 70.0:
            continue
        t_mid = TP * 0.5 * (VOM_ROW0 + VOM_ROW1) / KP
        speed = math.hypot((A + RUN * t_mid) * math.sin(th), (B + RUN * t_mid) * math.cos(th))
        vom.append((th, VOM_HALF_W / speed))

door_d = math.asin(DOOR_HALF / B)
stair_d = math.asin(STAIR_HALF / B)

# ------------------------------------------------------------------ theta columns
special = [math.pi - door_d, math.pi + door_d, stair_d, -stair_d]
for th, d in vom:
    special += [th - d, th + d]
cols = [2 * math.pi * i / NBASE for i in range(NBASE)] + [s % (2 * math.pi) for s in special]
cols = sorted(set(round(c, 10) for c in cols))
merged = []
for c in cols:
    if merged and c - merged[-1] < 1e-7:
        continue
    merged.append(c)
cols = merged
NC = len(cols)


def col_index(th):
    th = th % (2 * math.pi)
    best = min(range(NC), key=lambda i: abs(cols[i] - th))
    assert abs(cols[best] - th) < 1e-6, (th, cols[best])
    return best


# ------------------------------------------------------------------ mesh building helpers
bm = bmesh.new()
cache = {}
col_layer = bm.loops.layers.float_color.new('Col')
uv_layer = bm.loops.layers.uv.new('UVMap')   # stripe id lives in U for M_StairStripes: u = (index + 0.5) / 4


def V(x, y, z):
    key = (round(x, 4), round(y, 4), round(z, 4))
    v = cache.get(key)
    if v is None:
        v = bm.verts.new((x, y, z))
        cache[key] = v
    return v


def VV(p):
    return V(p.x, p.y, p.z)


def face(vs, mat, hint, color=None, stripe=None):
    out = []
    for v in vs:
        if not out or out[-1] is not v:
            out.append(v)
    while len(out) > 1 and out[0] is out[-1]:
        out.pop()
    if len(set(id(v) for v in out)) < 3:
        return None
    n = Vector((0, 0, 0))
    for i in range(len(out)):
        a, b = out[i].co, out[(i + 1) % len(out)].co
        n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    if n.length < 1e-9:
        return None
    if hint is not None and n.dot(hint) < 0:
        out.reverse()
    try:
        f = bm.faces.new(out)
    except ValueError:
        return None
    f.material_index = SLOT[mat]
    c = color if color is not None else COL[mat]
    for lp in f.loops:
        lp[col_layer] = c
        if stripe is not None:
            lp[uv_layer].uv = ((stripe + 0.5) / 4.0, 0.5)
    return f


UP = Vector((0, 0, 1))


def ell_out(p):
    return Vector((p.x / (A + RUN) ** 2, p.y / (B + RUN) ** 2, 0))


# ------------------------------------------------------------------ stand grid
rows_t = []
for i in range(NC):
    to = t_out(cols[i])
    rows = [TP * k / KP for k in range(KP + 1)] + [TP + (to - TP) * m / KS for m in range(1, KS + 1)]
    rows_t.append(rows)
NR = KP + KS + 1

grid = [[VV(P(cols[i], rows_t[i][j])) for j in range(NR)] for i in range(NC)]

# vomitory holes (cell ranges)
holes = set()
vom_cols = []
for th, d in vom:
    ia, ib = col_index(th - d), col_index(th + d)
    if ib < ia:
        ib += NC
    vom_cols.append((ia, ib, th))
    for i in range(ia, ib):
        for j in range(VOM_ROW0, VOM_ROW1):
            holes.add((i % NC, j))

for i in range(NC):
    i2 = (i + 1) % NC
    for j in range(NR - 1):
        if (i, j) in holes:
            continue
        face([grid[i][j], grid[i2][j], grid[i2][j + 1], grid[i][j + 1]], 'concrete', UP)

# vomitory recesses
for ia, ib, thc in vom_cols:
    rad = lambda p: Vector((p.x, p.y, 0)).normalized()
    t0, t1 = rows_t[ia % NC][VOM_ROW0], rows_t[ia % NC][VOM_ROW1]
    z0 = z_of(t0, thc)
    for i in range(ia, ib):
        ca, cb = i % NC, (i + 1) % NC
        for j in range(VOM_ROW0, VOM_ROW1):
            fa = V(*P(cols[ca], rows_t[ca][j], z0))
            fb = V(*P(cols[cb], rows_t[cb][j], z0))
            fc = V(*P(cols[cb], rows_t[cb][j + 1], z0))
            fd = V(*P(cols[ca], rows_t[ca][j + 1], z0))
            face([fa, fb, fc, fd], 'concrete', UP)
        # back wall: the dark opening
        b0 = V(*P(cols[ca], rows_t[ca][VOM_ROW1], z0))
        b1 = V(*P(cols[cb], rows_t[cb][VOM_ROW1], z0))
        face([b0, b1, grid[cb][VOM_ROW1], grid[ca][VOM_ROW1]], 'vom', -Vector((P(cols[ca], t1).x, P(cols[ca], t1).y, 0)).normalized())
    centre = P(thc, 0.5 * (t0 + t1), z0)
    for side_col, sgn in ((ia % NC, 0), (ib % NC, 1)):
        for j in range(VOM_ROW0, VOM_ROW1):
            fa = V(*P(cols[side_col], rows_t[side_col][j], z0))
            fb = V(*P(cols[side_col], rows_t[side_col][j + 1], z0))
            face([fa, fb, grid[side_col][j + 1], grid[side_col][j]], 'concrete', Vector((centre.x - fa.co.x, centre.y - fa.co.y, 0)))

# outer skirt down to the ground.  The tunnel runs through the west stands, so the skirt is open below TUN_CLEAR over the
# door columns (it used to close the tunnel at x = -160 m and hide the far opening from inside the tunnel).
TUN_CLEAR = 5.0
sk_a, sk_b = col_index(math.pi - door_d), col_index(math.pi + door_d)
for i in range(NC):
    i2 = (i + 1) % NC
    a, b = grid[i][NR - 1], grid[i2][NR - 1]
    mid = (a.co + b.co) * 0.5
    if sk_a <= i < sk_b:
        a0, b0 = V(a.co.x, a.co.y, TUN_CLEAR), V(b.co.x, b.co.y, TUN_CLEAR)
    else:
        a0, b0 = V(a.co.x, a.co.y, 0.0), V(b.co.x, b.co.y, 0.0)
    face([a, b, b0, a0], 'concrete', ell_out(mid))

# track wall (kept low), with the tunnel door at -X and the stair opening at +X
wall_rows = [0.0, DOOR_H, WALL_H]
wall_v = [[V(*P(cols[i], 0.0, z)) for z in wall_rows] for i in range(NC)]
door_a, door_b = col_index(math.pi - door_d), col_index(math.pi + door_d)
st_a, st_b = col_index(-stair_d), col_index(stair_d)
for i in range(NC):
    i2 = (i + 1) % NC
    for r in range(2):
        if r == 0 and door_a <= i < door_b:
            continue  # tunnel opening: 4.5 m wide, 3.5 m high, from Z = 0
        if (i >= st_a or i < 0) and False:
            pass
        in_stair = (i >= st_a or i < st_b) if st_a > st_b else (st_a <= i < st_b)
        if in_stair:
            continue
        mid = (wall_v[i][r].co + wall_v[i2][r + 1].co) * 0.5
        face([wall_v[i][r], wall_v[i2][r], wall_v[i2][r + 1], wall_v[i][r + 1]], 'concrete', Vector((-mid.x / A ** 2, -mid.y / B ** 2, 0)))

# ------------------------------------------------------------------ central stairway (10 m, striped runway)
X0 = 100.0 - WALL_H / SLOPE                      # where the slope line is at track level
X1 = 100.0 + (PODIUM_Z - WALL_H) / SLOPE         # podium front edge on the centre line
NSTEP = 48
RISE_S = PODIUM_Z / NSTEP
TREAD = (X1 - X0) / NSTEP
ycuts = [-STAIR_HALF, -2.0, -1.0, 0.0, 1.0, 2.0, STAIR_HALF]
stripe_idx = {1: 0, 2: 1, 3: 2, 4: 3}  # interval index -> colour
for k in range(NSTEP):
    xa, xb = X0 + k * TREAD, X0 + (k + 1) * TREAD
    zt = RISE_S * (k + 1)
    zb = RISE_S * k
    for q in range(len(ycuts) - 1):
        ya, yb = ycuts[q], ycuts[q + 1]
        stripe = q in (1, 2, 3, 4)
        mat = 'stripe' if stripe else 'concrete'
        colr = STRIPES[stripe_idx[q] if stripe else 0] if stripe else None
        sid = stripe_idx[q] if stripe else None
        face([V(xa, ya, zt), V(xb, ya, zt), V(xb, yb, zt), V(xa, yb, zt)], mat, UP, colr, sid)             # tread
        face([V(xa, ya, zb), V(xa, yb, zb), V(xa, yb, zt), V(xa, ya, zt)], mat, Vector((-1, 0, 0)), colr, sid)  # riser (faces the field)
    for ys, hint in ((-STAIR_HALF, Vector((0, -1, 0))), (STAIR_HALF, Vector((0, 1, 0)))):
        face([V(xa, ys, 0.0), V(xb, ys, 0.0), V(xb, ys, zt), V(xa, ys, zt)], 'concrete', hint)

# ------------------------------------------------------------------ radial aisles (thin, stepped, darker concrete)
for th in aisle_th:
    to = t_out(th)
    ts = [to * k / 3000 for k in range(3001)]
    zs = [z_of(t, th) for t in ts]
    ztop = zs[-1]

    def t_for(zv):
        k = bisect.bisect_left(zs, zv - 1e-9)
        k = max(0, min(len(ts) - 1, k))
        if k == 0:
            return ts[0]
        f = (zv - zs[k - 1]) / max(1e-12, zs[k] - zs[k - 1])
        return ts[k - 1] + f * (ts[k] - ts[k - 1])

    n = int(math.ceil((ztop - WALL_H) / AISLE_RISE - 1e-9))
    for j in range(n):
        zlo = WALL_H + AISLE_RISE * j
        zhi = min(WALL_H + AISLE_RISE * (j + 1), ztop)
        tlo, thi = t_for(zlo), t_for(zhi)
        if thi - tlo < 1e-6:
            continue
        ulo, uhi = tangent(th, tlo) * AISLE_HALF, tangent(th, thi) * AISLE_HALF
        plo, phi = P(th, tlo, 0), P(th, thi, 0)

        def pt(p, u, z):
            return V(p.x + u.x, p.y + u.y, z)
        face([pt(plo, -ulo, zhi), pt(plo, ulo, zhi), pt(phi, uhi, zhi), pt(phi, -uhi, zhi)], 'aisle', UP)                # tread
        rad = Vector((math.cos(th), math.sin(th), 0))
        face([pt(plo, -ulo, zlo), pt(plo, ulo, zlo), pt(plo, ulo, zhi), pt(plo, -ulo, zhi)], 'aisle', -rad)           # riser
        face([pt(plo, ulo, zlo), pt(phi, uhi, zhi), pt(plo, ulo, zhi)], 'aisle', tangent(th, tlo))                      # side +
        face([pt(plo, -ulo, zlo), pt(phi, -uhi, zhi), pt(plo, -ulo, zhi)], 'aisle', -tangent(th, tlo))                  # side -

# ------------------------------------------------------------------ finish mesh
bm.normal_update()
me = bpy.data.meshes.new('SM_Bowl')
bm.to_mesh(me)
nfaces = len(bm.faces)
bm.free()
for n in ('SM_Bowl',):
    if n in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
ob = bpy.data.objects.new('SM_Bowl', me)
bpy.context.scene.collection.objects.link(ob)


def mat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = rgba
    m.diffuse_color = rgba
    return m


if 'Col' in me.color_attributes:
    me.color_attributes.active_color = me.color_attributes['Col']
    me.color_attributes.render_color_index = list(me.color_attributes.keys()).index('Col')
for name, rgba in (('M_Concrete', COL['concrete']), ('M_ConcreteAisle', COL['aisle']), ('M_Vomitory', COL['vom']), ('M_StairStripes', (1, 1, 1, 1))):
    me.materials.append(mat(name, rgba))
for p in me.polygons:
    p.use_smooth = False
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

vs = [v.co for v in me.vertices]
print('RESULT faces', nfaces, 'verts', len(vs), 'slots', len(me.materials))
print('RESULT bbox X %.3f..%.3f Y %.3f..%.3f Z %.3f..%.3f' % (min(v.x for v in vs), max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs), min(v.z for v in vs), max(v.z for v in vs)))
print('RESULT aisles', len(aisle_th), 'vomitories', len(vom), 'cols', NC, 'PER %.2f' % PER)
print('RESULT east podium: stairs X0 %.2f X1 %.2f tread %.3f rise %.3f' % (X0, X1, TREAD, RISE_S))
for th in (0.0, math.radians(15), math.radians(20)):
    to = t_out(th)
    print('RESULT podium th=%.0f: front x=%.2f y=%.2f ; back x=%.2f y=%.2f' % (math.degrees(th), P(th, TP).x, P(th, TP).y, P(th, to).x, P(th, to).y))
for (px,py) in ((132,53.4),(132,-53.4),(146,40),(137,53.4),(144,9)):
    pass
print('RESULT vom centres', [(round(A * math.cos(t), 1), round(B * math.sin(t), 1)) for t, d in vom])

# door check (unchanged position)
door_pts = [v for v in vs if v.x < -90 and abs(v.y) <= DOOR_HALF + 1e-4 and v.z <= DOOR_H + 1e-4]
print('RESULT door verts x %.4f y %.4f..%.4f z %.2f..%.2f' % (min(v.x for v in door_pts), min(v.y for v in door_pts), max(v.y for v in door_pts), min(v.z for v in door_pts), max(v.z for v in door_pts)))

if DO_EXPORT:
    os.makedirs(REF, exist_ok=True)
    old = SRC + '/SM_Bowl.fbx'
    bak = REF + '/SM_Bowl_before_revision.fbx'
    if os.path.exists(old) and not os.path.exists(bak):
        shutil.copy2(old, bak)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=old, use_selection=True, object_types={'MESH'}, global_scale=1.0,
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Y', axis_up='Z',
                             bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type='FACE', add_leaf_bones=False,
                             path_mode='AUTO')
    print('RESULT exported', old, os.path.getsize(old))
bpy.ops.wm.save_as_mainfile(filepath='/tmp/sm_bowl_work.blend')
