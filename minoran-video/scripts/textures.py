"""Texturas com seed fixa (Pillow/NumPy).

assets/tex/leak_gold.png     radial dourado        2560x1440
assets/tex/leak_peach.png    radial pêssego        2560x1440
assets/tex/leak_rose.png     radial rosé           2560x1440
assets/tex/leak_streak.png   streak anamórfico     2560x1440
assets/tex/bokeh_0..3.png    sprites de bokeh (RGBA 256x256)
assets/tex/paper.png         papel sutil, ladrilhável (1024x1024)
assets/tex/vignette.png      máscara de vinheta 1920x1080 (multiplicada no FFmpeg, depois do blend)
Todos os leaks são RGB sobre preto, para mix-blend-mode: screen.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "tex"
SEED = 20260214
W, H = 2560, 1440


def to8(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    # dithering triangular para gradientes sem banding
    d = (rng.random(x.shape) - rng.random(x.shape)) / 255.0
    return (np.clip(x + d, 0, 1) * 255 + 0.5).astype(np.uint8)


def blob(xx, yy, cx, cy, sx, sy, ang=0.0):
    ca, sa = np.cos(ang), np.sin(ang)
    dx, dy = xx - cx, yy - cy
    u = (dx * ca + dy * sa) / sx
    v = (-dx * sa + dy * ca) / sy
    return np.exp(-0.5 * (u * u + v * v))


def radial_leak(rng, palette, n=5):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.zeros((H, W, 3), np.float32)
    # núcleo principal fora do quadro (luz entrando pela borda)
    side = rng.choice([0, 1])
    cx = W * (0.02 if side == 0 else 0.98)
    cy = H * rng.uniform(0.25, 0.7)
    core = blob(xx, yy, cx, cy, W * 0.28, H * 0.42, rng.uniform(-0.4, 0.4))
    img += core[..., None] * np.array(palette[0], np.float32)[None, None]
    for i in range(n):
        c = palette[1 + i % (len(palette) - 1)]
        bx = cx + (rng.uniform(0.05, 0.45) * W) * (1 if side == 0 else -1)
        by = H * rng.uniform(0.05, 0.95)
        b = blob(xx, yy, bx, by, W * rng.uniform(0.08, 0.22), H * rng.uniform(0.12, 0.35), rng.uniform(0, np.pi))
        img += b[..., None] * np.array(c, np.float32)[None, None] * rng.uniform(0.25, 0.6)
    # tonemap suave
    img = 1 - np.exp(-img * 1.4)
    return img


def streak_leak(rng):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.zeros((H, W, 3), np.float32)
    cy = H * 0.46
    # linha anamórfica: muito larga em x, fina em y; núcleo quente, halo azulado-âmbar
    core = np.exp(-0.5 * ((yy - cy) / (H * 0.006)) ** 2) * np.exp(-0.5 * ((xx - W * 0.55) / (W * 0.38)) ** 2)
    halo = np.exp(-0.5 * ((yy - cy) / (H * 0.035)) ** 2) * np.exp(-0.5 * ((xx - W * 0.5) / (W * 0.45)) ** 2)
    glow = blob(xx, yy, W * 0.55, cy, W * 0.06, H * 0.08)
    img += core[..., None] * np.array([1.0, 0.86, 0.62])[None, None] * 1.3
    img += halo[..., None] * np.array([0.85, 0.62, 0.32])[None, None] * 0.55
    img += glow[..., None] * np.array([1.0, 0.9, 0.7])[None, None] * 0.7
    # fantasmas sutis
    for k in range(3):
        gx = W * (0.55 + rng.uniform(-0.3, 0.3))
        img += blob(xx, yy, gx, cy, W * 0.012, H * 0.02)[..., None] * np.array([0.9, 0.7, 0.45])[None, None] * 0.25
    return 1 - np.exp(-img * 1.2)


def bokeh_sprite(rng, size=256, rim=0.18, tint=(1.0, 0.86, 0.58)):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    c = (size - 1) / 2
    r = np.hypot(xx - c, yy - c) / (size * 0.42)
    disc = np.clip((1 - r) * 18, 0, 1)  # borda antialias
    edge = np.exp(-0.5 * ((r - 0.93) / 0.05) ** 2) * rim
    body = 0.55 + 0.12 * (1 - r) + edge
    # leve aberração: borda externa mais quente
    a = np.clip(disc * body, 0, 1)
    col = np.stack([np.full_like(a, tint[0]), np.full_like(a, tint[1]), np.full_like(a, tint[2])], -1)
    rgba = np.dstack([col, a])
    return rgba


def paper(rng, n=1024):
    # ruído filtrado em frequência (periódico -> ladrilhável) + fibras
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    rad = np.hypot(fx, fy) + 1e-4
    spec = (rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) / rad**1.15
    spec[0, 0] = 0
    base = np.real(np.fft.ifft2(spec))
    base = (base - base.mean()) / base.std()
    # fibras: ruído anisotrópico
    spec2 = (rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) * np.exp(-((fx * 1.6) ** 2 + (fy * 0.55) ** 2) * 1400)
    fib = np.real(np.fft.ifft2(spec2))
    fib = (fib - fib.mean()) / (fib.std() + 1e-6)
    grain = rng.normal(size=(n, n))
    v = 0.86 + 0.032 * base + 0.010 * fib + 0.016 * grain
    v = np.clip(v, 0, 1)
    rgb = np.stack([v * 1.0, v * 0.985, v * 0.955], -1)
    return rgb


def vignette(rng, w=1920, h=1080, depth=0.20):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 * 0.85 + ((y - h / 2) / (h / 2)) ** 2 * 0.6)
    v = 1 - depth * np.clip((r - 0.45) / 0.75, 0, 1) ** 1.8
    return np.stack([v, v, v], -1)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if "--vignette-only" in sys.argv:
        Image.fromarray(to8(vignette(np.random.default_rng(SEED + 7)), np.random.default_rng(SEED + 7))).save(OUT / "vignette.png", optimize=True)
        print("   vignette")
        return 0
    rng = np.random.default_rng(SEED)
    gold = [(1.0, 0.72, 0.30), (0.95, 0.62, 0.22), (1.0, 0.85, 0.55), (0.8, 0.5, 0.18)]
    peach = [(1.0, 0.62, 0.42), (1.0, 0.75, 0.55), (0.95, 0.5, 0.35), (1.0, 0.82, 0.68)]
    rose = [(0.98, 0.55, 0.58), (1.0, 0.7, 0.7), (0.85, 0.45, 0.55), (1.0, 0.8, 0.75)]
    for name, pal in (("leak_gold", gold), ("leak_peach", peach), ("leak_rose", rose)):
        Image.fromarray(to8(radial_leak(rng, pal), rng)).save(OUT / f"{name}.png", optimize=True)
        print("  ", name)
    Image.fromarray(to8(streak_leak(rng), rng)).save(OUT / "leak_streak.png", optimize=True)
    print("   leak_streak")
    tints = [(1.0, 0.86, 0.58), (1.0, 0.78, 0.5), (1.0, 0.92, 0.75), (0.98, 0.8, 0.62)]
    for i, t in enumerate(tints):
        rgba = bokeh_sprite(rng, 256, rim=0.12 + 0.06 * i, tint=t)
        Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(OUT / f"bokeh_{i}.png", optimize=True)
    print("   bokeh_0..3")
    Image.fromarray(to8(paper(rng), rng)).save(OUT / "paper.png", optimize=True)
    print("   paper")
    Image.fromarray(to8(vignette(np.random.default_rng(SEED + 7)), np.random.default_rng(SEED + 7))).save(OUT / "vignette.png", optimize=True)
    print("   vignette")
    return 0


if __name__ == "__main__":
    sys.exit(main())
