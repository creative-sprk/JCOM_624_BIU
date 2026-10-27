"""Tileable T_TrackGrain_N (fine rubber-grain normal) and T_TrackNoise (R macro, G mid, B fine) via numpy FFT noise.
  Blender -b --factory-startup --python make_track_textures.py"""
import bpy, numpy as np, os
OUT = '/Users/todddavilla/Unreal Projects/Repositories/JCOM_624_BIU/SourceArt/Track'
N = 512
rng = np.random.default_rng(1984)
fx = np.fft.fftfreq(N)[:, None]
fy = np.fft.fftfreq(N)[None, :]
fr = np.sqrt(fx * fx + fy * fy)


def band(lo, hi):
    w = rng.standard_normal((N, N))
    F = np.fft.fft2(w)
    mask = np.exp(-((fr - 0.5 * (lo + hi)) / (0.5 * (hi - lo) + 1e-6)) ** 2)
    a = np.real(np.fft.ifft2(F * mask))
    a = (a - a.mean()) / (a.std() + 1e-9)
    return a


def save(name, arr):          # arr HxWx4 float 0..1
    img = bpy.data.images.new(name, N, N, alpha=True, float_buffer=False)
    flat = np.flipud(arr).reshape(-1)
    img.pixels.foreach_set(flat.astype(np.float32))
    img.file_format = 'PNG'
    img.filepath_raw = OUT + '/' + name + '.png'
    img.colorspace_settings.name = 'Non-Color'
    img.save()


# rubber grain height: mostly fine speckle with a little mid-scale
h = band(0.18, 0.45) * 1.0 + band(0.05, 0.12) * 0.35
gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
S = 0.55
nx, ny, nz = -gx * S, gy * S, np.ones_like(h)       # +Y green = up in UE's DirectX-style tangent space
l = np.sqrt(nx * nx + ny * ny + nz * nz)
nrm = np.stack([nx / l * 0.5 + 0.5, ny / l * 0.5 + 0.5, nz / l * 0.5 + 0.5, np.ones_like(h)], -1)
save('T_TrackGrain_N', nrm)


def unit(a):
    a = a / 3.0 * 0.5 + 0.5
    return np.clip(a, 0, 1)


noise = np.stack([unit(band(0.01, 0.04)), unit(band(0.04, 0.12)), unit(band(0.2, 0.5)), np.ones((N, N))], -1)
save('T_TrackNoise', noise)
print('textures ok')
