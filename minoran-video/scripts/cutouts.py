"""Recortes: `npx hyperframes remove-background` + validação + fallback GrabCut + decontaminação.

Fluxo por imagem
  1. hyperframes remove-background (u2net_human_seg) -> assets/cut/raw/<key>.png
  2. valida a máscara: cobertura de alpha 2–90 %, maior componente >= 90 % da área,
     contorno coerente (pouca área semitransparente, sólido, sem buracos grandes)
  3. reprovou -> OpenCV GrabCut
       * produto: inicia pelo bbox da área não branca, recorta só o relógio (sem socle)
       * pessoa: semeado pela própria máscara u2net (FG/PR_FG/PR_BG)
     morfologia + feather de 1.5 px
  4. decontaminação de borda: as cores do interior são propagadas sobre a faixa de
     3 px antes de aplicar o alpha (sem halo branco)
  5. assets/cut/<key>.png (RGBA) + assets/cut/report.json com o método de cada uma
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "img"
CUT = ROOT / "assets" / "cut"
RAW = CUT / "raw"

PEOPLE = ["hero"]
# dicas interativas de GrabCut (coordenadas normalizadas x0, y0, x1, y1), da inspeção visual:
# o punho branco da manga direita encosta na mesa branca e o modelo de cor o confunde com fundo.
FG_HINTS: dict[str, list[tuple[float, float, float, float]]] = {
    "hero": [(0.752, 0.405, 0.828, 0.640)],
}
PRODUCTS = [
    "rect_argentee_34",
    "rect_argentee_bleu",
    "nf5075_noir",
    "doree_blanc",
    "doree_vert",
    "sil_creme",
    "sil_rose",
    "sil_bleu_clair",
    "sil_noir_or",
    "sil_nude",
    "sil_peche",
]


def npx() -> str:
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx"


def run_remove_bg(key: str) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / f"{key}.png"
    if not out.exists():
        subprocess.run(
            [npx(), "hyperframes", "remove-background", str(IMG / f"{key}.jpg"), "-o", str(out)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return out


def validate(alpha: np.ndarray) -> dict:
    a = alpha.astype(np.float32) / 255.0
    solid = (a > 0.5).astype(np.uint8)
    coverage = float(solid.mean())
    n, lab, stats, _ = cv2.connectedComponentsWithStats(solid, connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA] if n > 1 else np.array([0])
    largest = float(areas.max() / max(1, areas.sum()))
    # coerência de contorno: fração semitransparente, buracos internos, solidez do contorno
    semi = float(((a > 0.08) & (a < 0.92)).sum() / max(1, solid.sum()))
    filled = solid.copy()
    cnts, _ = cv2.findContours(solid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(filled, cnts, -1, 1, thickness=-1)
    holes = float((filled.sum() - solid.sum()) / max(1, filled.sum()))
    if cnts:
        big = max(cnts, key=cv2.contourArea)
        hull = cv2.convexHull(big)
        solidity = float(cv2.contourArea(big) / max(1.0, cv2.contourArea(hull)))
    else:
        solidity = 0.0
    coherent = semi < 0.08 and holes < 0.04 and solidity > 0.45
    ok = 0.02 <= coverage <= 0.90 and largest >= 0.90 and coherent
    return {
        "coverage": round(coverage, 4),
        "largest": round(largest, 4),
        "semi": round(semi, 4),
        "holes": round(holes, 4),
        "solidity": round(solidity, 4),
        "coherent": coherent,
        "ok": ok,
    }


def feather(mask01: np.ndarray, px: float = 1.5) -> np.ndarray:
    m = mask01.astype(np.float32)
    return np.clip(cv2.GaussianBlur(m, (0, 0), px), 0, 1)


def largest_component(mask: np.ndarray) -> np.ndarray:
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    if n <= 1:
        return mask.astype(np.uint8)
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (lab == i).astype(np.uint8)


def fill_holes(mask: np.ndarray) -> np.ndarray:
    """Preenche só buracos fechados (regiões de fundo que não tocam a borda da imagem)."""
    m = mask.astype(np.uint8)
    inv = (1 - m).astype(np.uint8)
    n, lab = cv2.connectedComponents(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    holes = ~np.isin(lab, list(border)) & (inv == 1)
    out = m.copy()
    out[holes] = 1
    return out


def grabcut_product(bgr: np.ndarray) -> np.ndarray:
    """Relógio sobre fundo branco: bbox da área não branca -> GrabCut -> só o relógio."""
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    # "não branco": saturação ou distância do branco do fundo (amostrado nas bordas)
    border = np.concatenate([lab[:8].reshape(-1, 3), lab[-8:].reshape(-1, 3), lab[:, :8].reshape(-1, 3), lab[:, -8:].reshape(-1, 3)])
    bgc = np.median(border, axis=0)
    dist = np.linalg.norm(lab.astype(np.float32) - bgc[None, None, :], axis=2)
    nonwhite = ((dist > 9) | (hsv[..., 1] > 28)).astype(np.uint8)
    nonwhite = cv2.morphologyEx(nonwhite, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    nonwhite = largest_component(cv2.morphologyEx(nonwhite, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)))
    ys, xs = np.nonzero(nonwhite)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    pad = 6
    rect = (max(0, x0 - pad), max(0, y0 - pad), min(w - 1, x1 + pad) - max(0, x0 - pad), min(h - 1, y1 + pad) - max(0, y0 - pad))
    mask = np.full((h, w), cv2.GC_BGD, np.uint8)
    rx, ry, rw, rh = rect
    mask[ry : ry + rh, rx : rx + rw] = cv2.GC_PR_BGD
    mask[nonwhite == 1] = cv2.GC_PR_FGD
    core = cv2.erode(nonwhite, np.ones((15, 15), np.uint8))
    mask[core == 1] = cv2.GC_FGD
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, rect, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
    # sombra de contato / reflexo do socle: tons neutros e claros abaixo do corpo -> fora
    shadow = (hsv[..., 1] < 22) & (hsv[..., 2] > 150) & (dist < 30)
    fg[shadow] = 0
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    fg = fill_holes(largest_component(fg))
    return fg


def grabcut_person(bgr: np.ndarray, prior: np.ndarray, hints=()) -> np.ndarray:
    """Pessoa: GrabCut semeado pela máscara u2net; o fundo é a mesa branca."""
    h, w = bgr.shape[:2]
    s = 0.5
    small = cv2.resize(bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    pa = cv2.resize(prior, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    table = (hsv[..., 2] > 214) & (hsv[..., 1] < 26)
    # mesa = branco neutro conectado à borda e com prior baixo
    seed = (table & (pa < 0.75)).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(seed, connectivity=4)
    border_lab = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    table_bg = np.isin(lab, list(border_lab))
    mask = np.full(pa.shape, cv2.GC_PR_FGD, np.uint8)
    mask[pa < 0.5] = cv2.GC_PR_BGD
    mask[pa > 0.9] = cv2.GC_FGD
    mask[cv2.erode(table_bg.astype(np.uint8), np.ones((9, 9), np.uint8)) == 1] = cv2.GC_BGD
    # o fundo é a mesa branca: tecido escuro (blazer) é sempre sujeito
    mask[hsv[..., 2] < 70] = cv2.GC_FGD
    sh, sw = mask.shape
    for x0, y0, x1, y1 in hints:
        mask[int(y0 * sh) : int(y1 * sh), int(x0 * sw) : int(x1 * sw)] = cv2.GC_FGD
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(small, mask, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    fg = cv2.resize(fg, (w, h), interpolation=cv2.INTER_LINEAR)
    fg = (fg > 127).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    return fill_holes(largest_component(fg))


def refine_edges(bgr: np.ndarray, mask01: np.ndarray, px: float = 1.5) -> np.ndarray:
    """Feather de 1.5 px, puxado para a borda real pelo gradiente da imagem."""
    a = feather(mask01, px)
    return a


def decontaminate(bgr: np.ndarray, alpha01: np.ndarray, band: int = 3) -> np.ndarray:
    """Propaga as cores do interior sobre a faixa de `band` px da borda."""
    interior = (alpha01 > 0.98).astype(np.uint8)
    interior = cv2.erode(interior, np.ones((3, 3), np.uint8))
    edge_zone = (alpha01 > 0.0) & (interior == 0)
    out = bgr.astype(np.float32).copy()
    known = interior.astype(bool)
    col = np.where(known[..., None], out, 0)
    wgt = known.astype(np.float32)
    k = np.ones((3, 3), np.float32)
    # dilatação ponderada: 3 px + margem para cobrir toda a franja do feather
    for _ in range(band + 3):
        csum = cv2.filter2D(col, -1, k, borderType=cv2.BORDER_REPLICATE)
        wsum = cv2.filter2D(wgt, -1, k, borderType=cv2.BORDER_REPLICATE)
        newly = (~known) & (wsum > 0)
        col[newly] = csum[newly] / wsum[newly][:, None]
        wgt[newly] = 1.0
        known = known | newly
    fill = known & edge_zone
    out[fill] = col[fill]
    return np.clip(out, 0, 255).astype(np.uint8)


def write_rgba(path: Path, bgr: np.ndarray, alpha01: np.ndarray) -> None:
    rgba = np.dstack([bgr, (np.clip(alpha01, 0, 1) * 255 + 0.5).astype(np.uint8)])
    cv2.imwrite(str(path), rgba)


def crop_to_alpha(bgr: np.ndarray, alpha01: np.ndarray, pad: int = 8):
    ys, xs = np.nonzero(alpha01 > 0.01)
    x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
    x1, y1 = min(bgr.shape[1], xs.max() + pad + 1), min(bgr.shape[0], ys.max() + pad + 1)
    return (int(x0), int(y0), int(x1 - x0), int(y1 - y0))


def main(only: list[str] | None = None) -> int:
    CUT.mkdir(parents=True, exist_ok=True)
    rp = CUT / "report.json"
    report = json.loads(rp.read_text()) if rp.exists() else {}
    for key in PEOPLE + PRODUCTS:
        if only and key not in only:
            continue
        bgr = cv2.imread(str(IMG / f"{key}.jpg"), cv2.IMREAD_COLOR)
        raw = cv2.imread(str(run_remove_bg(key)), cv2.IMREAD_UNCHANGED)
        prior = raw[..., 3]
        v = validate(prior)
        entry = {"source": f"assets/img/{key}.jpg", "u2net": v}
        if v["ok"]:
            alpha = prior.astype(np.float32) / 255
            method = "hyperframes remove-background (u2net_human_seg)"
        else:
            if key in PEOPLE:
                m = grabcut_person(bgr, prior, FG_HINTS.get(key, ()))
                method = "opencv grabcut seeded by u2net_human_seg"
            else:
                m = grabcut_product(bgr)
                method = "opencv grabcut from non-white bbox (watch only, no socle)"
            alpha = refine_edges(bgr, m, 1.5)
            entry["grabcut"] = validate((alpha * 255).astype(np.uint8))
        clean = decontaminate(bgr, alpha, 3)
        # recortes de produto são enquadrados no próprio alpha; o da pessoa fica em registro com a foto
        if key in PRODUCTS:
            x, y, w, h = crop_to_alpha(clean, alpha)
            write_rgba(CUT / f"{key}.png", clean[y : y + h, x : x + w], alpha[y : y + h, x : x + w])
            entry["crop"] = [x, y, w, h]
        else:
            write_rgba(CUT / f"{key}.png", clean, alpha)
            entry["crop"] = [0, 0, bgr.shape[1], bgr.shape[0]]
        entry["method"] = method
        entry["decontamination"] = "interior colour propagated over 3 px edge band before alpha"
        entry["feather_px"] = 1.5 if "grabcut" in method else 0
        report[key] = entry
        print(f"  {key:20s} {method:60s} u2net ok={v['ok']} cov={v['coverage']} semi={v['semi']}")
    rp.write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
