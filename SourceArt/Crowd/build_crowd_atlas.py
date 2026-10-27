"""
Crowd atlas builder.  Reads SourceArt/Crowd/raw/Spectator_*.png (figures on a flat lavender studio backdrop, ~RGB 121,123,187),
removes the backdrop with a soft alpha matte, crops each figure, scales them to one height and packs
  - T_CrowdAtlas.png  4096x4096 RGBA: 8 columns x 4 rows of 512x1024; cells 0-9 the ten figures, 10-19 the same ten mirrored, 20-31 empty
  - T_CrowdStrip.png  2048x512  RGBA: tiling packed-crowd bust strip for the far upper stands (alpha = silhouette of heads)
  - atlas_layout.json cell geometry (used by the Unreal import script)

Run: python build_crowd_atlas.py   (needs pillow, numpy, scipy)
"""
import glob, json, os, random
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
ATLAS_W = ATLAS_H = 4096
COLS, ROWS = 8, 4
CELL_W, CELL_H = ATLAS_W / COLS, ATLAS_H / ROWS     # 512 x 1024 (figures are at most ~440 px wide at 960 px tall)
NCELLS = 20                                         # 10 figures + 10 mirrored; the other 12 cells stay empty
FIG_H = 960                                          # every figure is scaled to this pixel height
FOOT_PAD = 30                                        # transparent rows under the shoes
LO, HI = 26.0, 70.0                                  # colour distance (RGB) from the backdrop: alpha 0 below LO, 1 above HI


def matte(path):
    """Return (rgb float 0..1 with the backdrop colour removed, alpha float 0..1)."""
    im = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
    h, w, _ = im.shape
    # backdrop colour = median of a border strip
    border = np.concatenate([im[:8].reshape(-1, 3), im[-8:].reshape(-1, 3), im[:, :8].reshape(-1, 3), im[:, -8:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((im - bg) ** 2).sum(axis=2))
    a = np.clip((dist - LO) / (HI - LO), 0.0, 1.0)
    # keep only the figure: biggest connected blob of a>0.5 (+ blobs that are not tiny), and fill interior holes
    solid = a > 0.5
    lab, n = ndi.label(solid)
    if n > 1:
        sizes = ndi.sum(solid, lab, range(1, n + 1))
        keep = np.zeros(n + 1, bool)
        keep[1:] = sizes > 0.02 * sizes.max()
        solid = keep[lab]
    solid = ndi.binary_fill_holes(solid)
    near = ndi.binary_dilation(solid, iterations=3)
    a = np.where(solid, 1.0, np.where(near, a, 0.0))
    # tiny erosion of the matte to kill the lavender fringe, then a hair of feathering
    a = ndi.grey_erosion(a, size=(3, 3))
    a = ndi.gaussian_filter(a, 0.7)
    # unmix the backdrop out of the edge pixels: I = a*C + (1-a)*bg
    af = np.clip(a, 0.05, 1.0)[..., None]
    c = np.clip((im - (1 - a[..., None]) * bg) / af, 0, 255)
    # colour under fully transparent pixels: smear nearest opaque colour outward (stops dark halos in mips)
    opaque = a > 0.9
    idx = ndi.distance_transform_edt(~opaque, return_distances=False, return_indices=True)
    c_fill = c[idx[0], idx[1]]
    c = np.where((a > 0.9)[..., None], c, np.where((a > 0.02)[..., None], c, c_fill))
    return c / 255.0, a


def crop(rgb, a):
    ys, xs = np.where(a > 0.02)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return rgb[y0:y1, x0:x1], a[y0:y1, x0:x1]


def to_img(rgb, a):
    out = np.dstack([np.clip(rgb, 0, 1), np.clip(a, 0, 1)])
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')


files = sorted(glob.glob(os.path.join(RAW, 'Spectator_*.png')), key=lambda p: int(os.path.basename(p).split('_')[1].split('.')[0]))
figs = []
for f in files:
    rgb, a = crop(*matte(f))
    im = to_img(rgb, a)
    sc = FIG_H / im.height
    im = im.resize((max(1, round(im.width * sc)), FIG_H), Image.LANCZOS)
    figs.append(im)
    print(os.path.basename(f), 'cropped', rgb.shape[1], 'x', rgb.shape[0], '->', im.size)

widest = max(im.width for im in figs)
assert widest < CELL_W - 20, 'figure wider than its cell: %d' % widest

# ---- atlas
atlas = Image.new('RGBA', (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
cells = []
for i in range(NCELLS):
    im = figs[i % len(figs)]
    if i >= len(figs):
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    cx, cy = i % COLS, i // COLS
    x = int(round(cx * CELL_W + (CELL_W - im.width) / 2))
    y = int(round(cy * CELL_H + CELL_H - FOOT_PAD - im.height))
    atlas.alpha_composite(im, (x, y))
    cells.append({'cell': i, 'col': cx, 'row': cy, 'figure': i % len(figs), 'mirrored': i >= len(figs), 'x': x, 'y': y, 'w': im.width, 'h': im.height})
atlas.save(os.path.join(HERE, 'T_CrowdAtlas.png'))

# ---- far-stand strip: staggered rows of busts, tiling horizontally, silhouette alpha on top
SW, SH = 2048, 512
rng = random.Random(624)
strip = Image.new('RGBA', (SW, SH), (0, 0, 0, 0))
# dark base so gaps between bodies read as shadowed seating, not holes (only below the head line)
base = Image.new('RGBA', (SW, SH), (28, 26, 30, 0))
BUST_H = 300
busts = []
for im in figs:
    b = im.crop((0, 0, im.width, int(im.height * 0.5)))      # head + torso
    sc = BUST_H / b.height
    busts.append(b.resize((max(1, round(b.width * sc)), BUST_H), Image.LANCZOS))
row_tops = [0, 62, 124, 186]    # back row first (top of strip), front row last
for r, top in enumerate(row_tops):
    x = rng.uniform(-60, 0)
    while x < SW:
        b = rng.choice(busts)
        if rng.random() < 0.5:
            b = b.transpose(Image.FLIP_LEFT_RIGHT)
        # hue/brightness variation per person
        arr = np.asarray(b).astype(np.float32)
        tint = np.array([rng.uniform(0.8, 1.15), rng.uniform(0.8, 1.15), rng.uniform(0.8, 1.15)])
        arr[..., :3] = np.clip(arr[..., :3] * tint * (0.82 + 0.06 * r), 0, 255)   # back rows a little darker
        bb = Image.fromarray(arr.astype(np.uint8), 'RGBA')
        y = top + rng.randint(-6, 6)
        for dx in (0, -SW, SW):    # wrap so the strip tiles
            strip.alpha_composite(bb, (int(x) + dx, y)) if (0 <= int(x) + dx + bb.width and int(x) + dx < SW) else None
        x += bb.width * rng.uniform(0.55, 0.8)
# fill the lower part solid so rows read as a packed mass; pack a dark floor under the last row
a = np.asarray(strip).astype(np.float32)
alpha = a[..., 3] / 255.0
col_fill = ndi.maximum_filter(alpha, size=(1, 1))
below = np.zeros_like(alpha)
ys = np.arange(SH)[:, None]
# anything below the first opaque pixel in a column becomes opaque; transparent bits there get the dark base colour
first = np.argmax(alpha > 0.5, axis=0)
mask_below = ys >= first[None, :]
a[..., 3] = np.where(mask_below, 255.0, a[..., 3])
rgb = a[..., :3]
fill = (~(alpha > 0.5)) & mask_below
rgb[fill] = (30, 28, 32)
a[..., :3] = rgb
Image.fromarray(a.astype(np.uint8), 'RGBA').save(os.path.join(HERE, 'T_CrowdStrip.png'))

json.dump({'atlas': [ATLAS_W, ATLAS_H], 'cols': COLS, 'rows': ROWS, 'cell': [CELL_W, CELL_H], 'fig_h': FIG_H, 'foot_pad': FOOT_PAD,
           'ncells': NCELLS, 'cells': cells, 'strip': [SW, SH]}, open(os.path.join(HERE, 'atlas_layout.json'), 'w'), indent=1)
print('atlas written; widest figure', widest, 'px of cell', CELL_W)
