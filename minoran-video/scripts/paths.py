"""Contornos reais dos produtos -> paths SVG (shared/paths.js) para o DrawSVG.

findContours no alpha de cada recorte + approxPolyDP; os vértices viram curvas
cúbicas (Catmull-Rom -> Bézier) para o traço ficar contínuo. As coordenadas
estão no espaço de pixels do PNG recortado (viewBox = 0 0 w h).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CUT = ROOT / "assets" / "cut"
SHARED = ROOT / "shared"


def catmull_rom_path(pts: np.ndarray) -> str:
    n = len(pts)
    d = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = p1 + (p2 - p0) / 6.0
        c2 = p2 - (p3 - p1) / 6.0
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return "".join(d) + "Z"


def main() -> int:
    report = json.loads((CUT / "report.json").read_text())
    out = {}
    for key in report:
        if key == "hero":
            continue
        rgba = cv2.imread(str(CUT / f"{key}.png"), cv2.IMREAD_UNCHANGED)
        a = rgba[..., 3]
        h, w = a.shape
        m = (a > 110).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cnts, key=cv2.contourArea)
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.0018 * peri, True).reshape(-1, 2).astype(np.float64)
        # começa no ponto mais alto à esquerda: o traço nasce no topo da caixa
        start = int(np.argmin(approx[:, 1] * 10 + approx[:, 0] * 0.01))
        approx = np.roll(approx, -start, axis=0)
        # contorno deslocado para fora (~14 px no arquivo): o traço ouro corre junto à peça, sem cobri-la
        pad = 14
        mo = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * pad + 1, 2 * pad + 1)))
        co, _ = cv2.findContours(mo, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        co = max(co, key=cv2.contourArea)
        ao = cv2.approxPolyDP(co, 0.0018 * cv2.arcLength(co, True), True).reshape(-1, 2).astype(np.float64)
        ao = np.roll(ao, -int(np.argmin(ao[:, 1] * 10 + ao[:, 0] * 0.01)), axis=0)
        out[key] = {"w": w, "h": h, "d": catmull_rom_path(approx), "offset": catmull_rom_path(ao), "offsetPx": pad, "points": int(len(approx)), "perimeter": round(float(peri), 1)}
        print(f"  {key:20s} {len(c):5d} px contour -> {len(approx):3d} vertices")
    SHARED.mkdir(parents=True, exist_ok=True)
    (SHARED / "paths.js").write_text("/* gerado por scripts/paths.py — não editar */\nwindow.MINORAN_PATHS = " + json.dumps(out, separators=(",", ":")) + ";\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
