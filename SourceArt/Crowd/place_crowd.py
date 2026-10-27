"""
Crowd placement.  Same seating formulas as SM_Bowl_build.py (metres, bowl centred on the origin, +X east).
Writes Saved/crowd_instances.json with three instance sets in Unreal units (cm):
  near  - individual cards, full density (0.5 m along the row, 0.8 m row pitch), lower stands
  mid   - individual cards, ~half density and slightly larger, middle stands
  strip - 3.2 m wide packed-crowd strips, upper stands (where a card would be a few pixels)
each instance = [x, y, z, yaw_deg, scale_y, scale_z]   (SM_CrowdCard is 1 m x 1 m, faces local +X)
Run with a python that has numpy:  python place_crowd.py [density_scale_for_strips ...]
"""
import json, math, random, sys
import numpy as np

A, B = 100.0, 62.5
WALL_H, RUN, RIM_Z = 4.5, 60.0, 32.0
PODIUM_Z = 18.0
SLOPE = (RIM_Z - WALL_H) / RUN
TP = (PODIUM_Z - WALL_H) / (RIM_Z - WALL_H)
X_B = 146.0
PHI1, PHI2 = math.radians(30), math.radians(46)
DOOR_HALF, STAIR_HALF = 2.25, 5.0
AISLE_SPACING, AISLE_HALF = 25.0, 0.8
VOM_SPACING, VOM_HALF_W, KP = 50.0, 2.0, 16
VOM_ROW0, VOM_ROW1 = 9, 13

# ---- tunables (the report numbers come from these)
SEAT = 0.5          # along-row spacing, near tier
ROW = 0.8           # row pitch (horizontal run), near tier
T_NEAR_END = float(sys.argv[1]) if len(sys.argv) > 1 else 0.36
T_MID_END = float(sys.argv[2]) if len(sys.argv) > 2 else 0.66
MID_SEAT, MID_ROW = float(sys.argv[3]) if len(sys.argv) > 3 else 0.85, float(sys.argv[4]) if len(sys.argv) > 4 else 1.6
STRIP_W, STRIP_H, STRIP_ROW = 3.2, 2.0, float(sys.argv[5]) if len(sys.argv) > 5 else 2.0
T_TOP = 0.955       # keep the rim clear (flags, light towers)
CARD_H = 1.75 * 1024 / 960          # cell height in metres for a 1.75 m person (figure is 960 of 1024 px)
CARD_W = CARD_H * 0.5
FOOT = 0.055 * 1.0                  # 30 px of transparent foot padding at the bottom of the cell
rng = random.Random(624)


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def s_of(th):
    return 1.0 - smooth((abs(wrap(th)) - PHI1) / (PHI2 - PHI1))


def t_out(th):
    s = s_of(th)
    tb = (X_B / math.cos(th) - A) / RUN if abs(math.cos(th)) > 0.2 else 1.0
    return s * tb + (1.0 - s) * 1.0


def z_of(t, th):
    s = s_of(th)
    return min(RIM_Z, WALL_H + (RIM_Z - WALL_H) * ((1 - s) * t + s * min(t, TP)))


def slope_factor(t, th):
    s = s_of(th)
    return (1 - s) + s * (1.0 if t < TP else 0.0)


# inner-ellipse arc length -> theta (for aisles / vomitories, as in the build script)
_N = 20000
_TH = np.linspace(0, 2 * math.pi, _N + 1)
_mid = 0.5 * (_TH[:-1] + _TH[1:])
_S = np.concatenate([[0], np.cumsum(np.hypot(A * np.sin(_mid), B * np.cos(_mid)) * (_TH[1] - _TH[0]))])
PER = _S[-1]


def theta_at(sv):
    return float(np.interp(sv % PER, _S, _TH))


aisle_th = []
for k in range(40):
    sv = AISLE_SPACING / 2 + AISLE_SPACING * k
    if sv > PER / 2:
        break
    aisle_th += [theta_at(sv), theta_at(PER - sv)]
vom = []
for quarter in (PER / 4, 3 * PER / 4):
    for m in (-1, 0, 1):
        th = theta_at(quarter + m * VOM_SPACING)
        if abs(A * math.cos(th)) > 70.0:
            continue
        vom.append(th)
T_V0, T_V1 = TP * VOM_ROW0 / KP, TP * VOM_ROW1 / KP
LIGHT_TOWERS = [(-50.2, -110.6, 8.5, 7.5), (50.2, -110.6, 8.5, 7.5), (0.0, 117.0, 7.0, 5.5)]


def speed(th, t):
    return math.hypot((A + RUN * t) * math.sin(th), (B + RUN * t) * math.cos(th))


def blocked(x, y, z, th, t, half):
    """True where a card of half-width `half` must not stand."""
    sp = speed(th, t)
    for ath in aisle_th:
        if abs(wrap(th - ath)) * sp < AISLE_HALF + half + 0.15:
            return True
    for vth in vom:
        if abs(wrap(th - vth)) * sp < VOM_HALF_W + half + 0.35 and T_V0 - 0.02 < t < T_V1 + 0.02:
            return True
    if x > 80 and abs(y) < STAIR_HALF + half + 0.3:           # central stairway
        return True
    if x < -90 and abs(y) < DOOR_HALF + 1.0 + half and z < 7.5:   # tunnel opening
        return True
    for lx, ly, hx, hy in LIGHT_TOWERS:
        if abs(x - lx) < hx and abs(y - ly) < hy:
            return True
    return False


def row_points(t, step, phase):
    """theta values spaced `step` metres apart along the ellipse of semi-axes (A+RUN t, B+RUN t)."""
    a, b = A + RUN * t, B + RUN * t
    ths = np.linspace(0, 2 * math.pi, 6001)
    m = 0.5 * (ths[:-1] + ths[1:])
    s = np.concatenate([[0], np.cumsum(np.hypot(a * np.sin(m), b * np.cos(m)) * (ths[1] - ths[0]))])
    n = int(s[-1] / step)
    return [float(np.interp((i + phase) * step, s, ths)) for i in range(n)]


def make(t0, t1, row_pitch, seat, jitter, half, scale_k, kind):
    out = []
    t = t0
    r = 0
    while t <= t1:
        pts = row_points(t, seat, 0.5 * (r % 2) + rng.random() * 0.0)
        for th in pts:
            if slope_factor(t, th) < 0.35 or t > t_out(th) - 0.004:
                continue
            a, b = A + RUN * t, B + RUN * t
            x, y = a * math.cos(th), b * math.sin(th)
            # jitter along / across the row
            nx, ny = -x / a ** 2, -y / b ** 2
            nl = math.hypot(nx, ny); nx, ny = nx / nl, ny / nl
            tx, ty = -ny, nx
            j = rng.uniform(-jitter, jitter)
            x2, y2 = x + tx * j + nx * rng.uniform(-0.1, 0.1), y + ty * j + ny * rng.uniform(-0.1, 0.1)
            z = z_of(t, th)
            if blocked(x2, y2, z, th, t, half):
                continue
            yaw = math.degrees(math.atan2(ny, nx)) + rng.uniform(-6, 6)
            k = scale_k * rng.uniform(0.94, 1.06)
            if kind == 'card':
                out.append([x2 * 100, y2 * 100, (z - FOOT * k) * 100, yaw, CARD_W * k, CARD_H * k])
            else:
                out.append([x2 * 100, y2 * 100, (z - 0.05) * 100, math.degrees(math.atan2(ny, nx)), STRIP_W + 0.15, STRIP_H * scale_k])
        t += row_pitch / RUN
        r += 1
    return out


near = make(0.012, T_NEAR_END, ROW, SEAT, 0.08, 0.35, 1.0, 'card')
mid = make(T_NEAR_END, T_MID_END, MID_ROW, MID_SEAT, 0.12, 0.45, 1.12, 'card')
strip = make(T_MID_END, T_TOP, STRIP_ROW, STRIP_W, 0.0, STRIP_W / 2, 1.0, 'strip')
json.dump({'near': near, 'mid': mid, 'strip': strip}, open('/Users/todddavilla/Unreal Projects/Repositories/JCOM_624_BIU/Saved/crowd_instances.json', 'w'))
print('near', len(near), 'mid', len(mid), 'strip', len(strip), 'total', len(near) + len(mid) + len(strip))
print('card %.2f x %.2f m, aisles %d, vomitories %d' % (CARD_W, CARD_H, len(aisle_th), len(vom)))
