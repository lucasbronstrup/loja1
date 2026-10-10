"""Placas auxiliares derivadas dos recortes (OpenCV/Pillow).

* assets/img/hero_plate.jpg   placa limpa do hero (sujeito removido por cv2.inpaint),
                              fica sob a palavra/recorte: o parallax diferencial do
                              recorte nunca revela um "fantasma" do sujeito na foto.
* assets/cut/<produto>_b4.png / _b10.png   recortes pré-desfocados (premultiplicados),
                              para o rack focus por crossfade.
* shared/plates.js            cores de fundo amostradas nas fotos (canvas do s06 etc.).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "img"
CUT = ROOT / "assets" / "cut"
SHARED = ROOT / "shared"


def hero_plate() -> None:
    bgr = cv2.imread(str(IMG / "hero.jpg"))
    a = cv2.imread(str(CUT / "hero.png"), cv2.IMREAD_UNCHANGED)[..., 3]
    h, w = a.shape
    m = (a > 4).astype(np.uint8)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    s = 0.25
    small = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    ms = (cv2.resize(m, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST) > 0).astype(np.uint8) * 255
    inp = cv2.inpaint(small, ms, 9, cv2.INPAINT_TELEA)
    inp = cv2.GaussianBlur(inp, (0, 0), 2.0)
    inp = cv2.resize(inp, (w, h), interpolation=cv2.INTER_CUBIC)
    mf = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 6)[..., None]
    plate = bgr.astype(np.float32) * (1 - mf) + inp.astype(np.float32) * mf
    cv2.imwrite(str(IMG / "hero_plate.jpg"), np.clip(plate, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("  hero_plate.jpg")


def blurred_cutouts() -> None:
    rep = json.loads((CUT / "report.json").read_text())
    for key in rep:
        if key == "hero":
            continue
        rgba = cv2.imread(str(CUT / f"{key}.png"), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
        a = rgba[..., 3:4]
        pre = rgba[..., :3] * a
        for sig in (4, 10):
            pad = sig * 3
            P = cv2.copyMakeBorder(pre, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
            A = cv2.copyMakeBorder(a, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
            Pb = cv2.GaussianBlur(P, (0, 0), sig)
            Ab = cv2.GaussianBlur(A, (0, 0), sig)[..., None] if A.ndim == 2 else cv2.GaussianBlur(A, (0, 0), sig)
            if Ab.ndim == 2:
                Ab = Ab[..., None]
            rgb = np.where(Ab > 1e-4, Pb / np.maximum(Ab, 1e-4), 0)
            # recorta de volta ao tamanho original (mantém o registro com o PNG nítido)
            rgb = rgb[pad:-pad, pad:-pad]
            al = Ab[pad:-pad, pad:-pad]
            out = np.dstack([np.clip(rgb, 0, 1), np.clip(al, 0, 1)])
            cv2.imwrite(str(CUT / f"{key}_b{sig}.png"), (out * 255 + 0.5).astype(np.uint8))
    print("  recortes desfocados σ4/σ10")


def sample_bg(key: str, region: tuple[float, float, float, float]) -> str:
    bgr = cv2.imread(str(IMG / f"{key}.jpg"))
    h, w = bgr.shape[:2]
    x0, y0, x1, y1 = region
    patch = bgr[int(y0 * h) : int(y1 * h), int(x0 * w) : int(x1 * w)].reshape(-1, 3)
    b, g, r = np.median(patch, axis=0)
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}"


def main() -> int:
    hero_plate()
    blurred_cutouts()
    plates = {
        # fundo liso do avant/après (alto, à esquerda do braço) e base (canto inferior direito)
        "apresBgTop": sample_bg("apres", (0.02, 0.02, 0.30, 0.25)),
        "apresBgBottom": sample_bg("apres", (0.70, 0.85, 0.98, 0.98)),
        "avantBgTop": sample_bg("avant", (0.02, 0.02, 0.30, 0.25)),
        "heroTable": sample_bg("hero", (0.0, 0.0, 0.12, 0.12)),
    }
    SHARED.mkdir(exist_ok=True)
    (SHARED / "plates.js").write_text("/* gerado por scripts/plates.py — não editar */\nwindow.MINORAN_PLATES = " + json.dumps(plates) + ";\n")
    print("  plates:", plates)
    return 0


if __name__ == "__main__":
    sys.exit(main())
