"""T_Scoreboard_AmberMask (192x144 bulb on/off) and T_Scoreboard_VideoPlaceholder (64x48 red/white/blue)."""
from PIL import Image, ImageDraw
import math, os
OUT = os.path.dirname(os.path.abspath(__file__))
F = {
 'A': ["01110","10001","10001","11111","10001","10001","10001"],
 'D': ["11110","10001","10001","10001","10001","10001","11110"],
 'E': ["11111","10000","10000","11110","10000","10000","11111"],
 'F': ["11111","10000","10000","11110","10000","10000","10000"],
 'G': ["01110","10001","10000","10111","10001","10001","01111"],
 'H': ["10001","10001","10001","11111","10001","10001","10001"],
 'I': ["11111","00100","00100","00100","00100","00100","11111"],
 'L': ["10000","10000","10000","10000","10000","10000","11111"],
 'M': ["10001","11011","10101","10101","10001","10001","10001"],
 'O': ["01110","10001","10001","10001","10001","10001","01110"],
 'P': ["11110","10001","10001","11110","10000","10000","10000"],
 'S': ["01111","10000","10000","01110","00001","00001","11110"],
 'T': ["11111","00100","00100","00100","00100","00100","00100"],
 'X': ["10001","10001","01010","00100","01010","10001","10001"],
 'Y': ["10001","10001","01010","00100","00100","00100","00100"],
 'r': ["00000","00000","10110","11001","10000","10000","10000"],
 'd': ["00001","00001","01101","10011","10001","10011","01101"],
 ' ': ["00000"]*7,
}
W, H, SC = 192, 144, 2
img = Image.new('L', (W, H), 0)
px = img.load()
lines = ["GAMES OF THE", "XXIIIrd", "OLYMPIAD"]
ytop, gap = 22, 14
for li, t in enumerate(lines):
    adv = 6 * SC
    w = len(t) * adv - SC
    x0 = (W - w) // 2
    y0 = ytop + li * (7 * SC + gap)
    for ci, ch in enumerate(t):
        for r, row in enumerate(F[ch]):
            for c, v in enumerate(row):
                if v == '1':
                    for dy in range(SC):
                        for dx in range(SC):
                            px[x0 + ci * adv + c * SC + dx, y0 + r * SC + dy] = 255
# a row of border bulbs
for x in range(4, W - 4):
    for y in (4, H - 5):
        if x % 2 == 0:
            px[x, y] = 255
for y in range(4, H - 4):
    for x in (4, W - 5):
        if y % 2 == 0:
            px[x, y] = 255
img.save(OUT + '/T_Scoreboard_AmberMask.png')

# 1984 video-board placeholder: blue field, white star, red/white stripes
w, h = 64, 48
v = Image.new('RGB', (w, h), (20, 40, 150))
d = ImageDraw.Draw(v)
for i in range(0, h, 6):
    d.rectangle([0, i, w, i + 2], fill=(215, 25, 40) if (i // 6) % 2 == 0 else (240, 240, 240))
d.rectangle([0, 0, 26, 25], fill=(20, 40, 150))
cx, cy, ro, ri = 13, 12, 9.5, 3.9
pts = []
for k in range(10):
    a = -math.pi / 2 + k * math.pi / 5
    r = ro if k % 2 == 0 else ri
    pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
d.polygon(pts, fill=(245, 245, 245))
d.rectangle([30, 28, 62, 46], fill=(20, 40, 150))
for k in range(5):
    d.rectangle([32 + k * 6, 31, 35 + k * 6, 43], fill=(240, 240, 240) if k % 2 == 0 else (215, 25, 40))
v.save(OUT + '/T_Scoreboard_VideoPlaceholder.png')
print('ok')
