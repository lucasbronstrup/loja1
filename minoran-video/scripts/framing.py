"""Enquadramento (OpenCV): rostos, ponto focal, localização do relógio e máscaras de glint.

Para cada imagem de assets/img:
  * Haar frontal + perfil (cv2.data.haarcascades), perfil também espelhado
  * ponto focal = centro ponderado dos rostos; sem rosto -> centroide do alpha do recorte;
    sem alpha -> centroide da energia Sobel
  * relógio: HSV (dourado / prateado) + componentes conectados; o resultado de cada
    foto foi conferido visualmente (assets/masks/_inspect_<img>.jpg)
  * assets/masks/<img>_watch.png = elipse suave sobre o relógio (para glints)
Saída: assets/framing.json (coordenadas normalizadas 0–1 no arquivo da imagem)
       shared/framing.js (window.MINORAN_FRAMING)
Regras gravadas junto: nunca cortar olhos, nunca texto sobre rosto,
todo push-in com transform-origin no ponto focal.
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
MASKS = ROOT / "assets" / "masks"
SHARED = ROOT / "shared"

# correções da inspeção visual (assets/masks/_inspect_*.jpg): onde a detecção automática
# pegou a região errada (pele entre pulseira e braço, furo da pulseira, aro achatado)
VISUAL_OVERRIDES: dict[str, list[dict]] = {
    "hero": [{"cx": 0.503, "cy": 0.451, "rx": 0.067, "ry": 0.066}],
    "sil_nude": [{"cx": 0.472, "cy": 0.420, "rx": 0.218, "ry": 0.240}],
    "sil_creme": [{"cx": 0.505, "cy": 0.415, "rx": 0.235, "ry": 0.215}],
}

PHOTOS = {
    # chave: metal(is) do relógio presente(s) na foto
    "hero": ["gold"],
    "apres": ["silver"],
    "avant": [],
    "story_home": ["gold", "silver"],
    "doree_noir_9093": ["gold"],
}


def detect_faces(gray: np.ndarray) -> list[dict]:
    base = cv2.data.haarcascades
    frontal = cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml")
    profile = cv2.CascadeClassifier(base + "haarcascade_profileface.xml")
    h, w = gray.shape
    eq = cv2.equalizeHist(gray)
    min_side = max(40, int(min(h, w) * 0.06))
    faces = []
    for kind, casc, img, flip in (
        ("frontal", frontal, eq, False),
        ("profile", profile, eq, False),
        ("profile", profile, cv2.flip(eq, 1), True),
    ):
        rects = casc.detectMultiScale(img, scaleFactor=1.08, minNeighbors=7, minSize=(min_side, min_side))
        for x, y, fw, fh in rects if len(rects) else []:
            if flip:
                x = w - x - fw
            faces.append({"kind": kind, "x": x / w, "y": y / h, "w": fw / w, "h": fh / h, "weight": float(fw * fh)})
    return faces


def verify_faces(bgr: np.ndarray, faces: list[dict]) -> tuple[list[dict], list[dict]]:
    """Descarta falsos positivos do Haar (texturas de pulseira/mostrador):
    exige pele (YCrCb) e, no frontal, ao menos um olho detectado dentro do retângulo."""
    h, w = bgr.shape[:2]
    eye = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    keep, rejected = [], []
    for f in faces:
        x0, y0 = int(f["x"] * w), int(f["y"] * h)
        x1, y1 = int((f["x"] + f["w"]) * w), int((f["y"] + f["h"]) * h)
        roi = ycc[y0:y1, x0:x1]
        cr, cb = roi[..., 1], roi[..., 2]
        skin = float(((cr > 135) & (cr < 175) & (cb > 85) & (cb < 130)).mean()) if roi.size else 0.0
        eyes = eye.detectMultiScale(gray[y0:y1, x0:x1], 1.1, 6, minSize=(max(8, (x1 - x0) // 8),) * 2)
        f = dict(f, skin=round(skin, 3), eyes=int(len(eyes)))
        ok = skin > 0.35 and (f["kind"] == "profile" or len(eyes) >= 1)
        (keep if ok else rejected).append(f)
    return keep, rejected


def sobel_centroid(gray: np.ndarray) -> tuple[float, float]:
    g = cv2.GaussianBlur(gray, (0, 0), 2).astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    e = np.sqrt(gx * gx + gy * gy)
    h, w = e.shape
    ys, xs = np.mgrid[0:h, 0:w]
    s = e.sum() + 1e-6
    return float((e * xs).sum() / s / w), float((e * ys).sum() / s / h)


def alpha_centroid(a: np.ndarray) -> tuple[float, float]:
    h, w = a.shape
    ys, xs = np.mgrid[0:h, 0:w]
    af = a.astype(np.float32)
    s = af.sum() + 1e-6
    return float((af * xs).sum() / s / w), float((af * ys).sum() / s / h)


def metal_masks(bgr: np.ndarray) -> dict[str, np.ndarray]:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hh, ss, vv = hsv[..., 0], hsv[..., 1] / 255, hsv[..., 2] / 255
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    # energia especular local: metal polido tem contraste local alto
    mu = cv2.GaussianBlur(gray, (0, 0), 3)
    var = cv2.GaussianBlur(gray * gray, (0, 0), 3) - mu * mu
    std = np.sqrt(np.maximum(var, 0)) / 255
    gold = (hh >= 12) & (hh <= 32) & (ss > 0.38) & (vv > 0.35) & (std > 0.035)
    silver = (ss < 0.12) & (vv > 0.30) & (std > 0.09)
    return {"gold": gold.astype(np.uint8), "silver": silver.astype(np.uint8)}


def locate_watches(bgr: np.ndarray, metals: list[str]) -> list[dict]:
    h, w = bgr.shape[:2]
    mm = metal_masks(bgr)
    found = []
    for metal in metals:
        m = mm[metal]
        k = max(5, int(min(h, w) * 0.012)) | 1
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k * 3, k * 3)))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        n, lab, stats, cent = cv2.connectedComponentsWithStats(m, connectivity=8)
        best = None
        for i in range(1, n):
            x, y, bw, bh, area = stats[i]
            if area < 0.002 * h * w:
                continue
            # densidade: relógio = blob compacto e denso, não fiapos espalhados
            dens = area / float(bw * bh)
            touches = x <= 1 or y <= 1 or x + bw >= w - 1 or y + bh >= h - 1
            score = area * dens * (0.5 if touches else 1.0)
            if best is None or score > best[0]:
                best = (score, i)
        if best is None:
            continue
        i = best[1]
        x, y, bw, bh, area = stats[i]
        comp = (lab == i).astype(np.uint8)
        # caixa do relógio: linhas mais largas do componente (o mostrador é mais largo que a pulseira)
        widths = comp.sum(axis=1).astype(np.float32)
        rows = np.nonzero(widths > 0.8 * widths.max())[0]
        cy = float(rows.mean())
        xs = np.nonzero(comp[rows].sum(axis=0) > 0)[0]
        cx = float(xs.mean())
        found.append(
            {
                "metal": metal,
                "bbox": [x / w, y / h, bw / w, bh / h],
                "case": {"cx": cx / w, "cy": cy / h, "rx": (xs.max() - xs.min()) / 2 / w, "ry": (rows.max() - rows.min() + 1) / 2 / h},
            }
        )
    return found


def find_dials(bgr: np.ndarray, n_max: int, alpha: np.ndarray | None = None) -> list[dict]:
    """Mostrador = região fechada (buraco) dentro do anel de metal da caixa."""
    h, w = bgr.shape[:2]
    mm = metal_masks(bgr)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hh, ss, vv = hsv[..., 0], hsv[..., 1] / 255, hsv[..., 2] / 255
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mu = cv2.GaussianBlur(gray, (0, 0), 3)
    std = np.sqrt(np.maximum(cv2.GaussianBlur(gray * gray, (0, 0), 3) - mu * mu, 0)) / 255
    rose = (((hh <= 20) | (hh >= 165)) & (ss > 0.22) & (ss < 0.65) & (vv > 0.45) & (std > 0.03)).astype(np.uint8)
    metal = (mm["gold"] | mm["silver"] | rose).astype(np.uint8)
    if alpha is not None:
        metal &= (alpha > 127).astype(np.uint8)
    k = max(3, int(min(h, w) * 0.006)) | 1
    metal = cv2.morphologyEx(metal, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    inv = (1 - metal).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    cands = []
    for i in range(1, n):
        if i in border:
            continue
        x, y, bw, bh, area = stats[i]
        if area < 0.004 * h * w or area > 0.25 * h * w:
            continue
        aspect = bw / float(bh)
        fill = area / float(bw * bh)
        if not (0.45 < aspect < 2.2) or fill < 0.55:
            continue
        cands.append((area * fill, x, y, bw, bh))
    cands.sort(reverse=True)
    dials = []
    for _, x, y, bw, bh in cands[:n_max]:
        # caixa = mostrador + aro (~18 %)
        dials.append({"cx": (x + bw / 2) / w, "cy": (y + bh / 2) / h, "rx": bw / 2 * 1.18 / w, "ry": bh / 2 * 1.18 / h, "dial": [x / w, y / h, bw / w, bh / h]})
    dials.sort(key=lambda d: d["cx"])
    return dials


def case_from_alpha(a: np.ndarray) -> dict:
    """Produto recortado: a caixa é a faixa de linhas mais largas do alpha."""
    h, w = a.shape
    solid = (a > 127).astype(np.uint8)
    widths = solid.sum(axis=1).astype(np.float32)
    sm = np.convolve(widths, np.ones(9) / 9, mode="same")
    rows = np.nonzero(sm > 0.86 * sm.max())[0]
    # maior trecho contínuo
    splits = np.split(rows, np.nonzero(np.diff(rows) > 3)[0] + 1)
    rows = max(splits, key=len)
    xs = np.nonzero(solid[rows].sum(axis=0) > 0)[0]
    return {
        "cx": float(xs.mean() / w),
        "cy": float(rows.mean() / h),
        "rx": float((xs.max() - xs.min()) / 2 / w),
        "ry": float((rows.max() - rows.min() + 1) / 2 / h),
    }


def soft_ellipse(h: int, w: int, case: dict, grow: float = 1.25) -> np.ndarray:
    m = np.zeros((h, w), np.float32)
    center = (int(case["cx"] * w), int(case["cy"] * h))
    axes = (max(2, int(case["rx"] * w * grow)), max(2, int(case["ry"] * h * grow)))
    cv2.ellipse(m, center, axes, 0, 0, 360, 1.0, -1)
    sig = max(3.0, 0.25 * min(axes))
    m = cv2.GaussianBlur(m, (0, 0), sig)
    return np.clip(m / max(1e-6, m.max()), 0, 1)


def main() -> int:
    MASKS.mkdir(parents=True, exist_ok=True)
    SHARED.mkdir(parents=True, exist_ok=True)
    report = json.loads((IMG / "report.json").read_text())
    cut_report = json.loads((CUT / "report.json").read_text()) if (CUT / "report.json").exists() else {}
    out: dict[str, dict] = {}
    for key, meta in report.items():
        bgr = cv2.imread(str(IMG / f"{key}.jpg"))
        h, w = bgr.shape[:2]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        faces, rejected = verify_faces(bgr, detect_faces(gray))
        entry: dict = {"size": [w, h], "faces": faces, "facesRejected": rejected, "maxScale": meta["maxScale"]}
        cut_path = CUT / f"{key}.png"
        alpha_full = None
        if cut_path.exists():
            rgba = cv2.imread(str(cut_path), cv2.IMREAD_UNCHANGED)
            crop = cut_report.get(key, {}).get("crop", [0, 0, w, h])
            alpha_full = np.zeros((h, w), np.uint8)
            x, y, cw, ch = crop
            alpha_full[y : y + ch, x : x + cw] = rgba[..., 3]
            entry["cut"] = {"file": f"assets/cut/{key}.png", "crop": [x / w, y / h, cw / w, ch / h], "cropPx": crop}
        if faces:
            tw = sum(f["weight"] for f in faces)
            fx = sum((f["x"] + f["w"] / 2) * f["weight"] for f in faces) / tw
            fy = sum((f["y"] + f["h"] * 0.42) * f["weight"] for f in faces) / tw  # linha dos olhos
            entry["focal"] = {"x": fx, "y": fy, "source": "faces"}
        elif alpha_full is not None:
            fx, fy = alpha_centroid(alpha_full)
            entry["focal"] = {"x": fx, "y": fy, "source": "alpha"}
        else:
            fx, fy = sobel_centroid(gray)
            entry["focal"] = {"x": fx, "y": fy, "source": "sobel"}
        # relógio
        if key in PHOTOS:
            n_w = len(PHOTOS[key])
            dials = find_dials(bgr, n_w) if n_w else []
            if len(dials) == n_w:
                watches = [{"metal": m, "case": d, "method": "dial-hole"} for m, d in zip(sorted(PHOTOS[key]), dials)]
            else:
                watches = [dict(wt, method="metal-blob") for wt in locate_watches(bgr, PHOTOS[key])]
        elif alpha_full is not None:
            dials = find_dials(bgr, 1, alpha_full)
            if dials:
                watches = [{"metal": "product", "case": dials[0], "method": "dial-hole"}]
            else:
                watches = [{"metal": "product", "case": case_from_alpha(alpha_full), "method": "alpha-rows"}]
        else:
            watches = []
        if key in VISUAL_OVERRIDES:
            auto = watches
            watches = [{"metal": (auto[i]["metal"] if i < len(auto) else "product"), "case": c, "method": "visual inspection", "auto": (auto[i]["case"] if i < len(auto) else None)} for i, c in enumerate(VISUAL_OVERRIDES[key])]
        entry["watches"] = watches
        # rosto cujo centro cai sobre um relógio é textura de mostrador/pulseira, não pessoa
        for f in list(entry["faces"]):
            fcx, fcy = f["x"] + f["w"] / 2, f["y"] + f["h"] / 2
            for wt in watches:
                c = wt["case"]
                if ((fcx - c["cx"]) / (c["rx"] * 1.6)) ** 2 + ((fcy - c["cy"]) / (c["ry"] * 1.6)) ** 2 <= 1:
                    entry["faces"].remove(f)
                    entry["facesRejected"].append(dict(f, reason="on watch"))
                    break
        if not entry["faces"] and entry["focal"]["source"] == "faces":
            if alpha_full is not None:
                fx, fy = alpha_centroid(alpha_full)
                entry["focal"] = {"x": fx, "y": fy, "source": "alpha"}
            else:
                fx, fy = sobel_centroid(gray)
                entry["focal"] = {"x": fx, "y": fy, "source": "sobel"}
        if watches:
            m = np.zeros((h, w), np.float32)
            for wt in watches:
                m = np.maximum(m, soft_ellipse(h, w, wt["case"]))
            # RGBA (branco + alpha = elipse suave) para mask-image em modo alpha
            a8 = (m * 255).astype(np.uint8)
            cv2.imwrite(str(MASKS / f"{key}_watch.png"), np.dstack([np.full_like(a8, 255)] * 3 + [a8]))
            entry["watchMask"] = f"assets/masks/{key}_watch.png"
            # o ponto de interesse do produto é o relógio: push-in centrado nele
            entry["watch"] = {k: watches[0]["case"][k] for k in ("cx", "cy", "rx", "ry")}
            insp = bgr.copy()
            for wt in watches:
                c = wt["case"]
                cv2.ellipse(insp, (int(c["cx"] * w), int(c["cy"] * h)), (int(c["rx"] * w), int(c["ry"] * h)), 0, 0, 360, (255, 0, 255), 3)
            cv2.circle(insp, (int(entry["focal"]["x"] * w), int(entry["focal"]["y"] * h)), 10, (0, 255, 0), -1)
            cv2.imwrite(str(MASKS / f"_inspect_{key}.jpg"), cv2.resize(insp, (w // 2, h // 2)), [cv2.IMWRITE_JPEG_QUALITY, 80])
        entry["rules"] = {"neverCropEyes": True, "noTextOverFaces": True, "pushInOrigin": "focal"}
        out[key] = entry
        print(f"  {key:20s} faces={len(faces)} focal=({entry['focal']['x']:.3f},{entry['focal']['y']:.3f}) {entry['focal']['source']:6s} watches={[(round(x['case']['cx'],3), round(x['case']['cy'],3)) for x in watches]}")
    (ROOT / "assets" / "framing.json").write_text(json.dumps(out, indent=2))
    (SHARED / "framing.js").write_text("/* gerado por scripts/framing.py — não editar */\nwindow.MINORAN_FRAMING = " + json.dumps(out, separators=(",", ":")) + ";\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
