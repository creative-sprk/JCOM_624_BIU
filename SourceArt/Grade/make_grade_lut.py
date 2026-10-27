"""LA84 slide-film outdoor grade as a 16^3 colour-grading LUT (256x16, R along x inside a slice, G down, B across slices).
   python3 make_grade_lut.py [neutral]"""
import sys, math, colorsys, os
from PIL import Image
OUT = os.path.dirname(os.path.abspath(__file__))
P = dict(
    wb_r=0.975, wb_b=1.035,            # white balance: gamma tweaks keep black and white fixed
    red_sat=1.38, red_hue=15.0,        # reds / oranges (track, cones, red wall)
    green_sat=0.84, green_hue=105.0,
    blue_sat=0.90, blue_hue=212.0, blue_val=0.97, blue_hue_shift=-4.0,
    curve=0.30, toe=0.010,             # S-curve amount, tiny black lift
    shadow_cool=(-0.010, 0.0, 0.020),
)
for a in sys.argv[1:]:
    if '=' in a:
        k, v = a.split('=')
        P[k] = float(v)
NEUTRAL = 'neutral' in sys.argv


def bump(h, c, w):
    d = (h - c + 180.0) % 360.0 - 180.0
    return math.exp(-(d / w) ** 2)


def grade(r, g, b):
    r, g, b = r ** P['wb_r'], g, b ** P['wb_b']
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    hd = h * 360.0
    wr = bump(hd, P['red_hue'], 38.0)
    wg = bump(hd, P['green_hue'], 40.0)
    wb = bump(hd, P['blue_hue'], 32.0)
    s *= (1 + (P['red_sat'] - 1) * wr) * (1 + (P['green_sat'] - 1) * wg) * (1 + (P['blue_sat'] - 1) * wb)
    v *= 1 + (P['blue_val'] - 1) * wb
    hd += P['blue_hue_shift'] * wb
    r, g, b = colorsys.hsv_to_rgb((hd % 360.0) / 360.0, min(s, 1.0), min(v, 1.0))
    A = P['curve']
    out = []
    for c in (r, g, b):
        c = c - A * math.sin(2 * math.pi * c) / (2 * math.pi)
        out.append(P['toe'] + (1 - P['toe']) * c)
    lum = 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]
    sh = (1 - lum) ** 3
    out = [min(1.0, max(0.0, out[i] + P['shadow_cool'][i] * sh)) for i in range(3)]
    return out


img = Image.new('RGB', (256, 16))
px = img.load()
for bi in range(16):
    for gi in range(16):
        for ri in range(16):
            r, g, b = ri / 15.0, gi / 15.0, bi / 15.0
            o = (r, g, b) if NEUTRAL else grade(r, g, b)
            px[bi * 16 + ri, gi] = tuple(int(round(c * 255)) for c in o)
name = 'LUT_LA84_Neutral.png' if NEUTRAL else 'LUT_LA84_Outdoor.png'
img.save(OUT + '/' + name)
print(name, P)
