"""Pranchas de quadros reais de cada trecho renderizado (edit/work/qc/trecho_<id>.jpg) + nitidez em repouso."""
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
QC = WORK / "qc"
QC.mkdir(exist_ok=True)
TL = json.loads((WORK / "trechos.json").read_text())


def read_all(path, w=270, h=480):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def main():
    font = ImageFont.load_default(size=14)
    stats = {}
    for seg in TL["trechos"]:
        sid = seg["id"]
        fr = read_all(WORK / "seg" / f"{sid}.mkv")
        n = len(fr)
        idx = sorted(set([0, 1, 2] + list(range(0, n, max(1, n // 12))) + [n - 2, n - 1])) if n > 1 else [0]
        idx = [i for i in idx if 0 <= i < n]
        cols = 8
        rows = (len(idx) + cols - 1) // cols
        S = Image.new("RGB", (cols * 274 + 4, rows * 500 + 4), (30, 30, 30))
        d = ImageDraw.Draw(S)
        for k, i in enumerate(idx):
            x, y = 4 + (k % cols) * 274, 4 + (k // cols) * 500
            S.paste(Image.fromarray(fr[i]), (x, y + 18))
            g = seg["quadro_inicio"] + i
            d.text((x, y + 2), f"{sid} q{g} ({g / 60:.3f}s)", fill=(230, 230, 230), font=font)
        S.save(QC / f"trecho_{sid}.jpg", quality=82)
        # movimento x nitidez (para achar quadro parado e desfocado)
        gray = fr.mean(axis=3)
        sharp = [float(cv2.Laplacian(g.astype(np.float32), cv2.CV_32F).var()) for g in gray]
        motion = [0.0] + [float(np.abs(gray[i] - gray[i - 1]).mean()) for i in range(1, n)]
        stats[sid] = {"nitidez": sharp, "movimento": motion}
    (WORK / "qc" / "nitidez_movimento.json").write_text(json.dumps(stats))
    # quadros parados (movimento ~0 nos dois lados) com nitidez bem abaixo da mediana dos parados do trecho
    flags = []
    for sid, s in stats.items():
        sh, mo = np.array(s["nitidez"]), np.array(s["movimento"])
        still = [i for i in range(1, len(sh) - 1) if mo[i] < 0.05 and mo[i + 1] < 0.05]
        if len(still) < 3:
            continue
        # compara com quadros parados vizinhos (±12): conteúdo parecido, só o desfoque mudaria a nitidez
        for i in still:
            nb = [j for j in still if abs(j - i) <= 12 and j != i]
            if len(nb) < 3:
                continue
            med = float(np.median(sh[nb]))
            if sh[i] < 0.8 * med:
                flags.append((sid, i, round(float(sh[i]), 1), round(med, 1)))
    print("quadros parados e desfocados:", flags if flags else "nenhum")
    (WORK / "qc" / "parados_desfocados.json").write_text(json.dumps(flags))


if __name__ == "__main__":
    main()
