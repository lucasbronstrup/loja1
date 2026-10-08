"""Recorte da pessoa para a cena NOME e posição do nome gigante.

- máscara: saída da remoção de fundo do HyperFrames (u2net_human_seg, local), refinada por
  filtro guiado (bordas alinhadas à foto), limiarizada, erodida 1 px e suavizada (~2 px)
  -> PNG RGBA no MESMO tamanho da foto de origem (alinhamento ao pixel garantido pelo mesmo recorte).
- nome: mesmo tamanho de fonte para os dois (o mais largo ocupa ~88% da largura, dentro da área segura);
  linha de base = topo da cabeça + 0,75 x altura das maiúsculas (mesma regra para as duas):
  a cabeça cobre a parte de baixo das letras centrais (~18% da área) e o nome continua legível.
Saída: edit/work/hf/assets/photos/<id>_cut.png  e  edit/work/nome_layout.json
"""
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
HF = WORK / "hf"
FONT_WOFF2 = ROOT / "node_modules/@fontsource/poppins/files/poppins-latin-700-normal.woff2"
FONT_TTF = WORK / "models" / "poppins-700.ttf"

# geometria do cartão NOME (deve ser igual à usada nas composições)
NOME_INNER_W, NOME_INNER_H = 912, 1140  # borda inteira: b = 0,02/0,96 x 912 = 19 px
NOME_CX, NOME_CY = 540, 960
STROKE = 14
NAME_TARGET_W = 900  # nome mais largo + contorno: 83% da largura em repouso, 88% com a aproximação 1,06 (sempre dentro de x 60-1020)


def guided_filter(I, p, r, eps):
    mean = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1), borderType=cv2.BORDER_REFLECT)
    mI, mp = mean(I), mean(p)
    cov = mean(I * p) - mI * mp
    var = mean(I * I) - mI * mI
    a = cov / (var + eps)
    b = mp - a * mI
    return mean(a) * I + mean(b)


def refine_alpha(rgb, a):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    a = a.astype(np.float32) / 255
    g = guided_filter(gray, a, 6, 1e-3)
    hard = (g > 0.5).astype(np.uint8)
    # remove ilhas pequenas (mantém o maior componente)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(hard, 8)
    if n > 1:
        big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        hard = (lab == big).astype(np.uint8)
    # fecha pequenos buracos
    hard = cv2.morphologyEx(hard, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    hard = cv2.erode(hard, np.ones((3, 3), np.uint8), iterations=1)
    soft = cv2.GaussianBlur(hard.astype(np.float32), (0, 0), 1.0)
    return np.clip(soft, 0, 1)


def ensure_ttf():
    if not FONT_TTF.exists():
        f = TTFont(str(FONT_WOFF2))
        f.flavor = None
        f.save(str(FONT_TTF))
    return TTFont(str(FONT_TTF))


def advances(tt, text, size):
    cmap = tt.getBestCmap()
    hm = tt["hmtx"]
    upm = tt["head"].unitsPerEm
    return [hm[cmap[ord(c)]][0] / upm * size for c in text]


def main():
    sel = json.loads((WORK / "selecao.json").read_text())
    tt = ensure_ttf()
    names = {k: v["name"].upper() for k, v in sel["coordenadoras"].items()}
    widest = max(sum(advances(tt, n, 100)) for n in names.values())
    size = round(100 * (NAME_TARGET_W - 2 * STROKE) / widest, 1)
    asc = tt["hhea"].ascent / tt["head"].unitsPerEm
    cap = tt["OS/2"].sCapHeight / tt["head"].unitsPerEm
    font = ImageFont.truetype(str(FONT_TTF), round(size))
    layout = {"font_size": size, "stroke": STROKE, "cap_height": round(cap * size, 1), "names": {}}

    for key, co in sel["coordenadoras"].items():
        pid = co["plano"]["nome"]
        src = WORK / "photos" / f"{pid}.jpg"
        u2 = WORK / "cutouts" / f"{pid}_u2net.png"
        if not u2.exists():
            subprocess.run(
                [str(ROOT / "node_modules/.bin/hyperframes"), "remove-background", str(src), "-o", str(u2), "--device", "cpu"],
                check=True,
            )
        rgb = np.asarray(Image.open(src).convert("RGB"))
        a0 = np.asarray(Image.open(u2).convert("RGBA"))[:, :, 3]
        alpha = refine_alpha(rgb, a0)
        rgba = np.dstack([rgb, (alpha * 255 + 0.5).astype(np.uint8)])
        Image.fromarray(rgba, "RGBA").save(HF / "assets" / "photos" / f"{pid}_cut.png", optimize=True)

        # máscara em coordenadas de tela no quadro 0 da cena NOME
        crop = sel["crops"][pid]["nome"]
        k = NOME_INNER_W / crop["w"]
        x0 = NOME_CX - NOME_INNER_W / 2 - crop["x"] * k
        y0 = NOME_CY - NOME_INNER_H / 2 - crop["y"] * k
        M = np.float32([[k, 0, x0], [0, k, y0]])
        screen_a = cv2.warpAffine(alpha, M, (1080, 1920), flags=cv2.INTER_LINEAR)
        clip = np.zeros_like(screen_a)
        ix0, iy0 = int(NOME_CX - NOME_INNER_W / 2), int(NOME_CY - NOME_INNER_H / 2)
        clip[iy0 : iy0 + NOME_INNER_H, ix0 : ix0 + NOME_INNER_W] = 1
        screen_a *= clip
        face = crop["faces"][0]
        fx0 = NOME_CX - NOME_INNER_W / 2 + face["x"] * NOME_INNER_W
        fy0 = NOME_CY - NOME_INNER_H / 2 + face["y"] * NOME_INNER_H
        fw, fh = face["w"] * NOME_INNER_W, face["h"] * NOME_INNER_H

        name = names[key]
        adv = advances(tt, name, size)
        total = sum(adv)
        # máscara do nome (glifos + contorno) para uma linha de base em y
        def name_mask(base_y):
            im = Image.new("L", (1080, 1920), 0)
            d = ImageDraw.Draw(im)
            x = 540 - total / 2
            for ch, w in zip(name, adv):
                d.text((x, base_y), ch, font=font, fill=255, anchor="ls", stroke_width=STROKE, stroke_fill=255)
                x += w
            return np.asarray(im, dtype=np.float32) / 255

        head_top = int(np.where(screen_a.max(axis=1) > 0.5)[0].min())
        base = round(head_top + 0.75 * cap * size)
        m = name_mask(base)
        cov = float((m * screen_a).sum() / m.sum())
        best = (base, cov)
        layout["names"][key] = {
            "photo": pid,
            "text": name,
            "baseline_y": best[0],
            "coverage": round(best[1], 3),
            "letter_advances": [round(a, 2) for a in adv],
            "width": round(total, 1),
            "face_screen": [round(fx0), round(fy0), round(fw), round(fh)],
            "head_top_screen": head_top,
        }
        print(key, name, "size", size, "baseline", best[0], "coverage", round(best[1], 3), "face", [round(fx0), round(fy0), round(fw), round(fh)])

        # prévia: foto + nome + recorte
        photo = Image.open(src).convert("RGB")
        canvas = Image.new("RGB", (1080, 1920), (246, 246, 243))
        ph = photo.crop((round(crop["x"]), round(crop["y"]), round(crop["x"] + crop["w"]), round(crop["y"] + crop["h"]))).resize(
            (NOME_INNER_W, NOME_INNER_H), Image.LANCZOS
        )
        canvas.paste(ph, (ix0, iy0))
        d = ImageDraw.Draw(canvas)
        x = 540 - total / 2
        col = co["fill"]
        for ch, w in zip(name, adv):
            d.text((x, best[0]), ch, font=font, fill=col, anchor="ls", stroke_width=STROKE, stroke_fill=col)
            d.text((x, best[0]), ch, font=font, fill="white", anchor="ls")
            x += w
        cut = Image.open(HF / "assets" / "photos" / f"{pid}_cut.png").crop(
            (round(crop["x"]), round(crop["y"]), round(crop["x"] + crop["w"]), round(crop["y"] + crop["h"]))
        ).resize((NOME_INNER_W, NOME_INNER_H), Image.LANCZOS)
        canvas.paste(cut, (ix0, iy0), cut)
        canvas.save(WORK / f"preview_nome_{key}.jpg", quality=90)
    (WORK / "nome_layout.json").write_text(json.dumps(layout, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
