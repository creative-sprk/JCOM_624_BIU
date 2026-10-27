"""
Track, infield, curb, lane lines, apron, runways (SM_Track) + SM_TrafficCone.  Metres.  Same export rule as the other pieces.
  Blender -b --factory-startup --python SM_Track_build.py -- [export]
SM_Track slots: M_Track, M_Infield, M_LaneLine, M_CurbAluminum, M_Apron, M_Runway, M_Sand
Stadium oval: straights x in [-L, L], inner radius R0, 8 lanes of LW.  Runner's straight is Blender -Y (UE +Y).
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector

ROOT = '/Users/todddavilla/Unreal Projects/Repositories/JCOM_624_BIU'
SRC = ROOT + '/SourceArt'
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
DO_EXPORT = 'export' in args

_src = open(SRC + '/SM_Peristyle_build.py').read()
_src = _src[:_src.index('def arc(')]
exec(compile(_src, 'peri_helpers', 'exec'))
RGB.update({
    'M_Track': (0.66, 0.35, 0.30), 'M_Infield': (0.38, 0.50, 0.25), 'M_LaneLine': (0.95, 0.95, 0.93),
    'M_CurbAluminum': (0.9, 0.9, 0.88), 'M_Apron': (0.58, 0.59, 0.51), 'M_Runway': (0.7, 0.2, 0.15), 'M_Sand': (0.8, 0.72, 0.52),
    'M_ConeOrange': (1.0, 0.35, 0.05), 'M_ConeBlack': (0.03, 0.03, 0.03), 'M_ConeWhite': (0.95, 0.95, 0.95),
})

L, R0, NL = 42.19, 36.5, 8
LW = (46.26 - 36.5) / 8.0           # 1.2203 m
WIDTH = LW * NL
WALL_A, WALL_B = 100.0, 62.5
FINISH_X = 42.195
LINE_W, LINE_Z = 0.05, 0.010
STEP_S, STEP_A = 3.0, 3.0           # station spacing on straights (m) / on the curves (deg)


def stations():
    """list of (centre(x,y), unit outward normal) around the loop, starting on the south straight (y<0) going +X, closed."""
    st = []
    nS = int(round(2 * L / STEP_S))
    for i in range(nS):                    # south straight, x -L..L
        st.append(((-L + 2 * L * i / nS, 0.0), (0.0, -1.0), 'S'))
    n = int(round(180 / STEP_A))
    for i in range(n):                     # east semicircle: angle -90 -> +90
        a = math.radians(-90 + 180 * i / n)
        st.append(((L, 0.0), (math.cos(a), math.sin(a)), 'E'))
    for i in range(nS):                    # north straight x L..-L
        st.append(((L - 2 * L * i / nS, 0.0), (0.0, 1.0), 'N'))
    for i in range(n):                     # west semicircle 90 -> 270
        a = math.radians(90 + 180 * i / n)
        st.append(((-L, 0.0), (math.cos(a), math.sin(a)), 'W'))
    return st


ST = stations()
NS = len(ST)


def P(i, d, z=0.0):
    (cx, cy), (nx, ny), _ = ST[i % NS]
    return (cx + nx * (R0 + d), cy + ny * (R0 + d), z)


def uvp(p):
    return (p[0], p[1])


def strip(pc, d0, d1, z, mat, i0=0, i1=None, flat_up=True):
    i1 = NS if i1 is None else i1
    for i in range(i0, i1):
        a, b = P(i, d0, z), P(i + 1, d0, z)
        c, e = P(i + 1, d1, z), P(i, d1, z)
        pc.face([a, b, c, e], mat, out=(0, 0, 1), uvs=[uvp(a), uvp(b), uvp(c), uvp(e)])


def build_track():
    pc = Piece('SM_Track')
    pc.slot('M_Track'); pc.slot('M_Infield')       # keep the original slot order
    # --- track surface, 8 lanes
    strip(pc, 0.0, WIDTH, 0.0, 'M_Track')
    # --- infield: fan from the centre to the inner edge
    for i in range(NS):
        a, b = P(i, 0.0), P(i + 1, 0.0)
        pc.face([(0, 0, 0), a, b], 'M_Infield', out=(0, 0, 1), uvs=[(0, 0), uvp(a), uvp(b)])
    # --- apron: outer track edge -> wall ellipse, by polar angle
    def outer_pt(th):
        dx, dy = math.cos(th), math.sin(th)
        lo, hi = 0.0, 200.0
        for _ in range(60):
            t = 0.5 * (lo + hi)
            x, y = dx * t, dy * t
            ex = max(abs(x) - L, 0.0)
            if math.hypot(ex, y) < R0 + WIDTH:
                lo = t
            else:
                hi = t
        return (dx * lo, dy * lo, 0.003)
    NA = 360
    for k in range(NA):
        t0, t1 = 2 * math.pi * k / NA, 2 * math.pi * (k + 1) / NA
        o0, o1 = outer_pt(t0), outer_pt(t1)
        w0 = (WALL_A * math.cos(t0), WALL_B * math.sin(t0), 0.003)
        w1 = (WALL_A * math.cos(t1), WALL_B * math.sin(t1), 0.003)
        pc.face([o0, o1, w1, w0], 'M_Apron', out=(0, 0, 1), uvs=[uvp(o0), uvp(o1), uvp(w1), uvp(w0)])
    # --- lane lines
    for k in range(NL + 1):
        d = k * LW
        d0, d1 = (d - LINE_W / 2, d + LINE_W / 2)
        if k == 0:
            d0, d1 = 0.0, LINE_W
        if k == NL:
            d0, d1 = WIDTH - LINE_W, WIDTH
        strip(pc, d0, d1, LINE_Z, 'M_LaneLine')
    # --- finish line across all lanes (south straight)
    for (x0, x1) in ((FINISH_X - LINE_W / 2, FINISH_X + LINE_W / 2),):
        y0, y1 = -(R0), -(R0 + WIDTH)
        pts = [(x0, y0, LINE_Z), (x1, y0, LINE_Z), (x1, y1, LINE_Z), (x0, y1, LINE_Z)]
        pc.face(pts, 'M_LaneLine', out=(0, 0, 1), uvs=[uvp(p) for p in pts])
    # --- staggered start marks on the two curves: a bar across each lane, moved on by a lane-dependent angle
    for centre, a0, sgn in ((L, 24.0, 1.0), (-L, 24.0, 1.0)):
        for lane in range(1, NL + 1):
            r0 = R0 + (lane - 1) * LW + LINE_W
            r1 = R0 + lane * LW - LINE_W
            ang = math.radians(a0 + (lane - 1) * 2.6)
            for base in (0.0,):
                th = ang
                if centre > 0:           # east curve, leaving the south straight
                    th = -math.pi / 2 + ang
                else:                    # west curve, leaving the north straight
                    th = math.pi / 2 + ang
                dir_ = Vector((math.cos(th), math.sin(th)))
                tan_ = Vector((-dir_.y, dir_.x))
                c0 = Vector((centre, 0)) + dir_ * r0
                c1 = Vector((centre, 0)) + dir_ * r1
                hw = tan_ * (LINE_W / 2)
                pts = [tuple(c0 - hw) + (LINE_Z,), tuple(c0 + hw) + (LINE_Z,), tuple(c1 + hw) + (LINE_Z,), tuple(c1 - hw) + (LINE_Z,)]
                pc.face(pts, 'M_LaneLine', out=(0, 0, 1), uvs=[uvp(p) for p in pts])
    # --- aluminium inner curb: 7.5 cm wide, 5 cm tall, just inside the inner edge
    CW, CH = 0.075, 0.05
    for i in range(NS):
        (cx, cy), (nx, ny), _ = ST[i]
        (cx2, cy2), (nx2, ny2), _ = ST[(i + 1) % NS]
        n_mid = Vector((nx + nx2, ny + ny2, 0)).normalized()
        a_t, b_t = P(i, -CW, CH), P(i + 1, -CW, CH)
        c_t, e_t = P(i + 1, 0.0, CH), P(i, 0.0, CH)
        pc.face([a_t, b_t, c_t, e_t], 'M_CurbAluminum', out=(0, 0, 1), uvs=[(0, 0)] * 4)
        a_b, b_b = P(i, 0.0, 0.0), P(i + 1, 0.0, 0.0)
        pc.face([a_b, b_b, c_t, e_t], 'M_CurbAluminum', out=tuple(n_mid), uvs=[(0, 0)] * 4)
        a_i, b_i = P(i, -CW, 0.0), P(i + 1, -CW, 0.0)
        pc.face([a_i, b_i, b_t, a_t], 'M_CurbAluminum', out=tuple(-n_mid), uvs=[(0, 0)] * 4)
    # --- jump runways + pit on the north infield
    for yc in (24.0, 27.0):
        x0, x1 = -34.0, 8.0
        pts = [(x0, yc - 0.61, 0.006), (x1, yc - 0.61, 0.006), (x1, yc + 0.61, 0.006), (x0, yc + 0.61, 0.006)]
        pc.face(pts, 'M_Runway', out=(0, 0, 1), uvs=[uvp(p) for p in pts])
    pts = [(8.0, 22.6, 0.006), (17.0, 22.6, 0.006), (17.0, 25.35, 0.006), (8.0, 25.35, 0.006)]
    pc.face(pts, 'M_Sand', out=(0, 0, 1), uvs=[uvp(p) for p in pts])
    return pc.finish()


def cone():
    pc = Piece('SM_TrafficCone')
    pc.box(-0.19, 0.19, -0.19, 0.19, 0.0, 0.03, 'M_ConeBlack')
    seg = 14
    def rad(z):
        return 0.155 - 0.13 * (z - 0.03) / 0.67
    bands = [(0.03, 0.30, 'M_ConeOrange'), (0.30, 0.41, 'M_ConeWhite'), (0.41, 0.47, 'M_ConeOrange'), (0.47, 0.55, 'M_ConeWhite'), (0.55, 0.70, 'M_ConeOrange')]
    for z0, z1, m in bands:
        pc.cyl(0, 0, rad(z0), z0, rad(z1), z1, seg, m, caps=(False, m == 'M_ConeOrange' and z1 > 0.69))
    return pc.finish()


objs = {}
for nm, fn in (('SM_Track', build_track), ('SM_TrafficCone', cone)):
    if nm in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
    ob = fn()
    objs[nm] = ob
    d = ob.dimensions
    print('PIECE %-16s faces %6d dims %.2f x %.2f x %.3f slots %s' % (nm, len(ob.data.polygons), d.x, d.y, d.z, [m.name for m in ob.data.materials]))

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

# ------------------------------------------------------------------ cone placements along the runner's path (UE units in, cm)
import json


def hermite(p0, t0, p1, t1, u):
    h00, h10, h01, h11 = 2*u**3 - 3*u**2 + 1, u**3 - 2*u**2 + u, -2*u**3 + 3*u**2, u**3 - u**2
    return (h00*p0[0] + h10*t0[0] + h01*p1[0] + h11*t1[0], h00*p0[1] + h10*t0[1] + h01*p1[1] + h11*t1[1])


pts = [[-22793.03, 0.0], [-9993.03, 0.0], [-7595.36257353524, 1541.1271474489135], [-4965.700165372674, 3635.203751263166],
       [-3470.3274476666084, 3711.0], [4219.5, 3711.0], [5719.5, 3711.0]]
tang = [[[12800.0, 0.0], [12800.0, 0.0]], [[12800.0, 0.0], [3096.0447788496144, 0.0]], [[1285.744720668986, 2816.443464000971], [1476.0610148637302, 3233.3342155327205]],
        [[3481.726051746044, 714.695718140274], [1107.7515995517656, 227.38874718924416]], [[2521.479004904384, 0.0], [7689.827447666608, 0.0]],
        [[7689.827447666608, 0.0], [1500.0, 0.0]], [[1500.0, 0.0], [1500.0, 0.0]]]
poly = []
for i in range(len(pts) - 1):
    for k in range(200):
        poly.append(hermite(pts[i], tang[i][1], pts[i + 1], tang[i + 1][0], k / 200.0))
poly.append(tuple(pts[-1]))
cum = [0.0]
for i in range(len(poly) - 1):
    cum.append(cum[-1] + math.hypot(poly[i + 1][0] - poly[i][0], poly[i + 1][1] - poly[i][1]))
start = next(i for i, p in enumerate(poly) if p[0] >= -9993.03)        # tunnel mouth
s0, s1 = cum[start], cum[-1]
OFF = 0.5 * LW * 100.0 + 0.0                                            # outer edge of lane 1 = half a lane off the lane-1 centre line
cones = []
s = s0 + 150.0
j = start
while s <= s1:
    while cum[j + 1] < s:
        j += 1
    f = (s - cum[j]) / (cum[j + 1] - cum[j])
    px = poly[j][0] * (1 - f) + poly[j + 1][0] * f
    py = poly[j][1] * (1 - f) + poly[j + 1][1] * f
    tx, ty = poly[j + 1][0] - poly[j][0], poly[j + 1][1] - poly[j][1]
    tl = math.hypot(tx, ty)
    nx, ny = ty / tl, -tx / tl           # right-hand normal in UE (X fwd, Y right)... pick the side away from the infield (+Y of the path)
    if ny < 0:
        nx, ny = -nx, -ny
    # outside of the oval is +Y (UE); on the entry diagonal this keeps cones on the downstream side
    cones.append([round(px + nx * OFF, 1), round(py + ny * OFF, 1), round(math.degrees(math.atan2(ty, tx)), 1)])
    s += 300.0
print('CONES', len(cones), cones[0], cones[-1])
json.dump(cones, open('/tmp/cone_placements.json', 'w'))
bpy.ops.wm.save_as_mainfile(filepath='/tmp/sm_track_work.blend')
