"""Tratamento das fotos: EXIF, sRGB, grade unificado, export JPG q92 + pré-desfoques.

Saídas
  assets/img/<key>.jpg          grade aplicado, upscale Lanczos de no máx. 1.15x
  assets/img/<key>_b4.jpg       σ 4   (rack focus)
  assets/img/<key>_b10.jpg      σ 10  (fundos)
  assets/img/<key>_b20.jpg      σ 20  (fundos)
  assets/img/report.json        tamanhos e zoom máximo seguro de cada imagem

O zoom máximo seguro é medido em relação ao arquivo exportado: o arquivo já
carrega o upscale permitido (até 1.15x do original), então cada cena pode
exibir a imagem a no máximo 1.0 px de tela por px do arquivo (maxScale = 1.0),
o que equivale a 1.15x do original.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "src"
OUT = ROOT / "assets" / "img"

UPSCALE = 1.15  # teto absoluto
JPG_Q = 92
BLURS = (4, 10, 20)


def to_srgb(im: Image.Image) -> Image.Image:
    im = ImageOps.exif_transpose(im)
    icc = im.info.get("icc_profile")
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            dst = ImageCms.createProfile("sRGB")
            im = ImageCms.profileToProfile(im.convert("RGB"), src, dst, outputMode="RGB")
        except Exception:  # noqa: BLE001
            im = im.convert("RGB")
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return im.convert("RGB")


def srgb_to_lin(x: np.ndarray) -> np.ndarray:
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def grade(rgb: np.ndarray) -> np.ndarray:
    """Grade unificado sutil: curva S leve, altas luzes levemente quentes, pele natural."""
    x = rgb.astype(np.float32) / 255.0
    # curva S leve em torno de 0.5 (mistura 22% de uma smoothstep)
    s = x * x * (3 - 2 * x)
    x = x * 0.78 + s * 0.22
    # luminância para separar altas luzes
    lum = 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
    hi = np.clip((lum - 0.55) / 0.45, 0, 1) ** 1.5
    # altas luzes levemente quentes (R+, B-), sem tocar nos médios (pele)
    warm = np.stack([0.018 * hi, 0.006 * hi, -0.020 * hi], axis=-1)
    x = x + warm
    # proteção de pele: tons alaranjados de média luminância voltam 60% ao original
    orig = rgb.astype(np.float32) / 255.0
    r, g, b = orig[..., 0], orig[..., 1], orig[..., 2]
    skin = ((r > g) & (g > b) & (r - b > 0.08) & (lum > 0.25) & (lum < 0.85)).astype(np.float32)
    skin = np.asarray(Image.fromarray((skin * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), dtype=np.float32) / 255.0
    x = x * (1 - 0.6 * skin[..., None]) + orig * (0.6 * skin[..., None]) + warm * 0.25 * skin[..., None]
    # pretos ligeiramente elevados e quentes (sem esmagar)
    x = x * 0.985 + np.array([0.012, 0.010, 0.008], dtype=np.float32)
    return (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((SRC / "manifest.json").read_text())
    report: dict[str, dict] = {}
    for key in manifest:
        src = SRC / f"{key}.webp"
        im = to_srgb(Image.open(src))
        w0, h0 = im.size
        # upscale controlado: o arquivo leva 1.15x (teto), Lanczos + unsharp leve
        w1, h1 = round(w0 * UPSCALE), round(h0 * UPSCALE)
        up = im.resize((w1, h1), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.2, percent=35, threshold=2))
        graded = Image.fromarray(grade(np.asarray(up)))
        graded.save(OUT / f"{key}.jpg", quality=JPG_Q, subsampling=0, optimize=True)
        for s in BLURS:
            graded.filter(ImageFilter.GaussianBlur(s)).save(OUT / f"{key}_b{s}.jpg", quality=JPG_Q, subsampling=0, optimize=True)
        report[key] = {
            "file": f"assets/img/{key}.jpg",
            "orig": [w0, h0],
            "size": [w1, h1],
            "upscale": UPSCALE,
            # px de tela por px do arquivo; 1.0 == 1.15x do original
            "maxScale": 1.0,
            "maxDisplay": [w1, h1],
        }
        print(f"  {key:20s} {w0}x{h0} -> {w1}x{h1}")
    (OUT / "report.json").write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
