from PIL import Image, ImageDraw, ImageFont
import os
HERE = os.path.dirname(os.path.abspath(__file__))
CAPS = os.path.join(HERE, '..', 'Fonts', 'LibreCaslonCondensed-Regular.ttf')
ITAL = '/System/Library/Fonts/Supplemental/Georgia Italic.ttf'
W, H = 4096, 256
CREAM = (250, 242, 205, 255)

def layout(runs, size_caps, tracking, target_w):
    """runs: (text, kind, scale, raise_px). returns list of (char, font, x, y_offset) and width"""
    fc = ImageFont.truetype(CAPS, size_caps)
    items, x = [], 0.0
    for text, kind, sc, rp in runs:
        f = fc if kind == 'caps' else ImageFont.truetype(ITAL, int(size_caps * sc))
        for ch in text:
            adv = f.getlength(ch)
            items.append((ch, f, x, rp))
            x += adv + tracking * (1.0 if kind == 'caps' else 0.25)
    return items, x

def render(runs, name):
    # find tracking so the line spans ~88% of the plate
    size = 150
    tracking = 6.0
    for _ in range(40):
        items, w = layout(runs, size, tracking, 0)
        target = W * 0.88
        if abs(w - target) < 6:
            break
        tracking += (target - w) / max(1, len(items))
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0 = (W - w) / 2
    base = H * 0.5 + size * 0.36   # caps baseline
    for ch, f, x, rp in items:
        d.text((x0 + x, base - rp), ch, font=f, fill=CREAM, anchor='ls')
    out = os.path.join(HERE, name)
    img.save(out)
    print(name, 'tracking %.1f width %.0f' % (tracking, w))

left = [('GAMES', 'caps', 1, 0), (' ', 'caps', 1, 0), ('of the', 'ital', 0.80, 0), (' ', 'caps', 1, 0), ('XXIII', 'caps', 1, 0), ('rd', 'ital', 0.55, 62), (' ', 'caps', 1, 0), ('OLYMPIAD', 'caps', 1, 0)]
right = [('LOS ANGELES CALIFORNIA 1984', 'caps', 1, 0)]
render(left, 'T_Frieze_Left.png')
render(right, 'T_Frieze_Right.png')
