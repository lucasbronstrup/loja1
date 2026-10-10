"""Alinha "avant" em "après" com cv2.findTransformECC (euclidiano).

O ECC roda em escala reduzida, só no fundo/braço (o relógio é mascarado, porque é
exatamente o que difere entre as fotos). Se o desvio passar de 1 px, aplica o warp
em assets/img/avant*.jpg (inclusive nas versões pré-desfocadas) e registra tudo em
assets/align.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "img"
MASKS = ROOT / "assets" / "masks"


def main() -> int:
    a = cv2.imread(str(IMG / "apres.jpg"))
    b = cv2.imread(str(IMG / "avant.jpg"))
    h, w = a.shape[:2]
    s = 0.5
    ga = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY), (0, 0), 1.2).astype(np.float32) / 255
    gb = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(b, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY), (0, 0), 1.2).astype(np.float32) / 255
    # máscara: tudo menos o relógio (elipse ampliada)
    wm = cv2.imread(str(MASKS / "apres_watch.png"), cv2.IMREAD_GRAYSCALE)
    wm = cv2.resize(wm, (ga.shape[1], ga.shape[0]))
    valid = (cv2.dilate((wm > 10).astype(np.uint8), np.ones((41, 41), np.uint8)) == 0).astype(np.uint8)
    warp = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 400, 1e-7)
    cc, warp = cv2.findTransformECC(ga, gb, warp, cv2.MOTION_EUCLIDEAN, crit, valid, 5)
    full = warp.copy()
    full[:, 2] /= s
    angle = float(np.degrees(np.arctan2(full[1, 0], full[0, 0])))
    # desvio máximo nos cantos
    corners = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float32)
    moved = corners @ full.T
    dev = float(np.max(np.linalg.norm(moved - corners[:, :2], axis=1)))
    info = {"cc": float(cc), "tx": float(full[0, 2]), "ty": float(full[1, 2]), "angleDeg": angle, "maxDeviationPx": dev, "applied": False}
    if dev > 1.0:
        for suffix in ("", "_b4", "_b10", "_b20"):
            p = IMG / f"avant{suffix}.jpg"
            im = cv2.imread(str(p))
            out = cv2.warpAffine(im, full, (w, h), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
            cv2.imwrite(str(p), out, [cv2.IMWRITE_JPEG_QUALITY, 92])
        info["applied"] = True
        # verificação pós-warp
        b2 = cv2.imread(str(IMG / "avant.jpg"))
        g2 = cv2.cvtColor(cv2.resize(b2, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
        g2 = cv2.GaussianBlur(g2, (0, 0), 1.2)
        warp2 = np.eye(2, 3, dtype=np.float32)
        cc2, warp2 = cv2.findTransformECC(ga, g2, warp2, cv2.MOTION_EUCLIDEAN, crit, valid, 5)
        info["residualPx"] = float(np.hypot(warp2[0, 2] / s, warp2[1, 2] / s))
    (ROOT / "assets" / "align.json").write_text(json.dumps(info, indent=2))
    print("  align:", json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
