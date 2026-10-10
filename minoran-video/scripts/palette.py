"""Paleta: cv2.kmeans nos produtos + tokens do capture -> shared/palette.css (+ assets/palette.json).

* Cores fixas da marca (marfim, tinta, ouro, prata, verde).
* Tokens do capture (capture/extracted/tokens.json): acento #C6A663 etc.
* Pulseiras: medidas nas próprias fotos — k-means (k=4) só nos pixels de pulseira
  (alpha do recorte, fora da elipse da caixa), cluster dominante não-metálico.
* Mostradores: cluster dominante dentro da elipse da caixa.
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

BRAND = {
    "ivory": "#F5F0E8",
    "ivory-flash": "#FFF8EE",
    "ink": "#12100E",
    "ink-deep": "#0E0C0A",
    "green": "#1E4A3A",
    "gold-1": "#8C6A2E",
    "gold-2": "#D9B76A",
    "gold-3": "#F6E7B8",
    "gold-4": "#B8893B",
    "silver-1": "#8E959E",
    "silver-2": "#E6E9EE",
    "silver-3": "#A9AFB8",
}
STRAPS = {
    "creme": "sil_creme",
    "rose": "sil_rose",
    "bleu-clair": "sil_bleu_clair",
    "noir-or": "sil_noir_or",
    "nude": "sil_nude",
    "peche": "sil_peche",
}
DIALS = {
    "dial-bleu": "rect_argentee_bleu",
    "dial-noir": "nf5075_noir",
    "dial-blanc": "doree_blanc",
    "dial-vert": "doree_vert",
}


def hexc(bgr) -> str:
    b, g, r = [int(round(float(v))) for v in bgr]
    return f"#{r:02X}{g:02X}{b:02X}"


def kmeans_dominant(pixels: np.ndarray, k: int = 4, avoid_metal: bool = True) -> tuple[str, list]:
    px = pixels.reshape(-1, 3).astype(np.float32)
    if len(px) > 60000:
        idx = np.random.default_rng(7).choice(len(px), 60000, replace=False)
        px = px[idx]
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 60, 0.2)
    cv2.setRNGSeed(7)
    _, labels, centers = cv2.kmeans(px, k, None, crit, 5, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.ravel(), minlength=k)
    order = np.argsort(-counts)
    clusters = [{"hex": hexc(centers[i]), "share": round(float(counts[i] / counts.sum()), 3)} for i in order]
    # cor percebida = média ponderada dos dois clusters dominantes (face iluminada + meio-tom)
    i0, i1 = order[0], order[1]
    w0, w1 = counts[i0], counts[i1]
    if avoid_metal:
        hsv = cv2.cvtColor(centers.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_BGR2HSV)[0]
        # o segundo cluster só entra se tiver o mesmo matiz (não é ferragem/especular)
        dh = abs(int(hsv[i0][0]) - int(hsv[i1][0]))
        if min(dh, 180 - dh) > 18 and hsv[i0][1] > 40:
            w1 = 0
    mean = (centers[i0] * w0 + centers[i1] * w1) / (w0 + w1)
    return hexc(mean), clusters


def main() -> int:
    fr = json.loads((ROOT / "assets" / "framing.json").read_text())
    tokens = json.loads((ROOT / "capture" / "extracted" / "tokens.json").read_text())
    measured = {"straps": {}, "dials": {}}
    for name, key in STRAPS.items():
        rgba = cv2.imread(str(CUT / f"{key}.png"), cv2.IMREAD_UNCHANGED)
        h, w = rgba.shape[:2]
        crop = fr[key]["cut"]["cropPx"]
        W, H = fr[key]["size"]
        c = fr[key]["watch"]
        cx, cy = c["cx"] * W - crop[0], c["cy"] * H - crop[1]
        rx, ry = c["rx"] * W * 1.08, c["ry"] * H * 1.08
        yy, xx = np.mgrid[0:h, 0:w]
        outside_case = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 > 1
        sel = (rgba[..., 3] > 240) & outside_case
        col, clusters = kmeans_dominant(rgba[..., :3][sel], 4)
        measured["straps"][name] = {"hex": col, "clusters": clusters, "source": key}
    for name, key in DIALS.items():
        rgba = cv2.imread(str(CUT / f"{key}.png"), cv2.IMREAD_UNCHANGED)
        h, w = rgba.shape[:2]
        crop = fr[key]["cut"]["cropPx"]
        W, H = fr[key]["size"]
        c = fr[key]["watch"]
        cx, cy = c["cx"] * W - crop[0], c["cy"] * H - crop[1]
        rx, ry = c["rx"] * W * 0.7, c["ry"] * H * 0.7
        yy, xx = np.mgrid[0:h, 0:w]
        inside = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
        col, clusters = kmeans_dominant(rgba[..., :3][inside & (rgba[..., 3] > 240)], 4)
        measured["dials"][name] = {"hex": col, "clusters": clusters, "source": key}
    capture = {"accent": None, "colors": tokens.get("colors", [])}
    for cname in tokens.get("colors", []):
        if cname.upper() == "#C6A663":
            capture["accent"] = cname
    pal = {"brand": BRAND, "capture": capture, "measured": measured}
    (ROOT / "assets" / "palette.json").write_text(json.dumps(pal, indent=2))

    def mix(a: str, b: str, t: float) -> str:
        ca = np.array([int(a[i : i + 2], 16) for i in (1, 3, 5)], float)
        cb = np.array([int(b[i : i + 2], 16) for i in (1, 3, 5)], float)
        m = ca * (1 - t) + cb * t
        return "#" + "".join(f"{int(round(v)):02X}" for v in m)

    lines = ["/* gerado por scripts/palette.py — não editar */", ":root {"]
    for k, v in BRAND.items():
        lines.append(f"  --mn-{k}: {v};")
    lines.append(f"  --mn-gold: linear-gradient(100deg, {BRAND['gold-1']} 0%, {BRAND['gold-2']} 38%, {BRAND['gold-3']} 55%, {BRAND['gold-4']} 100%);")
    lines.append(f"  --mn-silver: linear-gradient(100deg, {BRAND['silver-1']} 0%, {BRAND['silver-2']} 50%, {BRAND['silver-3']} 100%);")
    lines.append(f"  --mn-capture-accent: {capture['accent'] or '#C6A663'};")
    lines.append("  --mn-capture-ink: #171717;")
    lines.append("  --mn-capture-buy: #166D00;")
    for name, d in measured["straps"].items():
        lines.append(f"  --mn-strap-{name}: {d['hex']};")
        lines.append(f"  --mn-strap-{name}-bg: {mix(d['hex'], BRAND['ivory'], 0.30)};")
    for name, d in measured["dials"].items():
        lines.append(f"  --mn-{name}: {d['hex']};")
    lines.append("}")
    SHARED.mkdir(parents=True, exist_ok=True)
    (SHARED / "palette.css").write_text("\n".join(lines) + "\n")
    # versão JS para as cenas (fundo do s05 = cor da pulseira misturada 30% com marfim: 70 % pulseira + 30 % marfim)
    js = {
        "brand": BRAND,
        "straps": {k: {"hex": v["hex"], "bg": mix(v["hex"], BRAND["ivory"], 0.30)} for k, v in measured["straps"].items()},
        "dials": {k: v["hex"] for k, v in measured["dials"].items()},
    }
    (SHARED / "palette.js").write_text("/* gerado por scripts/palette.py — não editar */\nwindow.MINORAN_PALETTE = " + json.dumps(js, separators=(",", ":")) + ";\n")
    for k, v in measured["straps"].items():
        print(f"  strap {k:11s} {v['hex']}  bg {js['straps'][k]['bg']}")
    for k, v in measured["dials"].items():
        print(f"  {k:17s} {v['hex']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
