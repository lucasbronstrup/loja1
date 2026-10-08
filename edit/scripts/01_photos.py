"""Inventário e pré-processamento das fotos.

- aplica orientação EXIF e converte para sRGB (perfil ICC embutido -> sRGB)
- reduz para no máximo 2160 px no lado maior (nunca amplia)
- mede nitidez (variância do Laplaciano), luminância e rostos (YuNet, só para enquadrar)
- detecta duplicatas (md5 + dHash)
- grava edit/work/photos/<id>.jpg e edit/work/inventario.json

Quem aparece em cada foto vem SOMENTE da pasta ou do nome do arquivo (ver atribuir()).
"""
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageCms, ImageOps

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parents[1]          # edit/
REPO = ROOT.parent
WORK = ROOT / "work"
OUT = WORK / "photos"
MODEL = WORK / "models" / "face_detection_yunet_2023mar.onnx"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
MAX_SIDE = 2160

# Foto anexada no chat (identificada pelo usuário como Eduarda): comparada byte a byte/pixel
# a pixel com os arquivos da pasta para descobrir o NOME DO ARQUIVO correspondente.
CHAT_REF = Path("/tmp/claude-0/-home-user-loja1/415a354f-2840-5db4-8fcd-8f15a1f04578/images/1.jpg")


def find_input_dir() -> Path:
    for cand in [REPO / "fotos", REPO / "drive-download-20261008T002502Z-1-001"]:
        if cand.is_dir():
            return cand
    sys.exit("pasta de fotos ausente")


def load_srgb(path: Path) -> Image.Image:
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    icc = im.info.get("icc_profile")
    if im.mode not in ("RGB", "RGBA", "L"):
        im = im.convert("RGB")
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            dst = ImageCms.createProfile("sRGB")
            im = ImageCms.profileToProfile(im.convert("RGB"), src, dst, outputMode="RGB")
        except Exception:
            im = im.convert("RGB")
    return im.convert("RGB")


def dhash(im: Image.Image, n: int = 16) -> int:
    g = np.asarray(im.convert("L").resize((n + 1, n), Image.LANCZOS), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def sharpness(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def detect_faces(bgr: np.ndarray):
    h, w = bgr.shape[:2]
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (w, h), 0.6, 0.3, 5000)
    _, faces = det.detect(bgr)
    out = []
    if faces is not None:
        for f in faces:
            x, y, fw, fh = [float(v) for v in f[:4]]
            out.append({"x": x, "y": y, "w": fw, "h": fh, "score": float(f[-1])})
    # segunda passada em escala maior para rostos pequenos
    if not out or min(w, h) < 1400:
        big = cv2.resize(bgr, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
        det2 = cv2.FaceDetectorYN.create(str(MODEL), "", (w * 2, h * 2), 0.6, 0.3, 5000)
        _, faces2 = det2.detect(big)
        if faces2 is not None:
            for f in faces2:
                x, y, fw, fh = [float(v) / 2 for v in f[:4]]
                cand = {"x": x, "y": y, "w": fw, "h": fh, "score": float(f[-1])}
                if all(iou(cand, o) < 0.3 for o in out):
                    out.append(cand)
    out.sort(key=lambda d: -d["w"] * d["h"])
    return out


def iou(a, b):
    ax2, ay2, bx2, by2 = a["x"] + a["w"], a["y"] + a["h"], b["x"] + b["w"], b["y"] + b["h"]
    ix = max(0.0, min(ax2, bx2) - max(a["x"], b["x"]))
    iy = max(0.0, min(ay2, by2) - max(a["y"], b["y"]))
    inter = ix * iy
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0.0


def wa_seq(name: str):
    m = re.search(r"IMG-(\d{8})-WA(\d{4})", name)
    return (m.group(1), int(m.group(2))) if m else (None, None)


def atribuir(files, ref_name):
    """Atribuição pela pasta; sem subpastas, pelo nome do arquivo (data + sequência do WhatsApp).

    Regra (sem reconhecimento facial):
      1. data do nome diferente da data das fotos individuais -> lote 'final' (fotos da turma);
      2. o arquivo indicado pelo usuário (foto anexada = WA0086) pertence à Eduarda;
         o bloco CONTÍGUO de números de sequência que o contém (sem lacunas) é o lote da Eduarda;
      3. as demais fotos individuais da mesma data -> Graziela.
    """
    by_folder = {}
    for f in files:
        parent = f.parent.name.lower()
        if parent in ("graziela", "eduarda", "final"):
            by_folder[f.name] = parent
    if by_folder:
        return by_folder, "subpastas"
    dates = {}
    for f in files:
        d, _ = wa_seq(f.name)
        dates.setdefault(d, []).append(f)
    ref_date, ref_seq = wa_seq(ref_name)
    out = {}
    for d, fs in dates.items():
        if d != ref_date:
            for f in fs:
                out[f.name] = "final"
    seqs = sorted({wa_seq(f.name)[1] for f in dates[ref_date]})
    block = {ref_seq}
    s = ref_seq
    while s - 1 in seqs:
        s -= 1
        block.add(s)
    s = ref_seq
    while s + 1 in seqs:
        s += 1
        block.add(s)
    for f in dates[ref_date]:
        out[f.name] = "eduarda" if wa_seq(f.name)[1] in block else "graziela"
    return out, f"nomes de arquivo: bloco contíguo WA{min(block):04d}–WA{max(block):04d} contém o arquivo indicado ({ref_name})"


def main():
    src = find_input_dir()
    OUT.mkdir(parents=True, exist_ok=True)
    # cópias "(1)" depois do original, para que a duplicata descartada seja a cópia
    files = sorted(
        (p for p in src.rglob("*") if p.suffix.lower() in EXTS),
        key=lambda p: (re.sub(r"\(\d+\)", "", p.stem), "(" in p.name, p.name),
    )
    if not files:
        sys.exit("fotos ausentes")

    # arquivo correspondente à foto anexada no chat (comparação de pixels, não de rosto)
    ref_name = None
    if CHAT_REF.exists():
        ref = np.asarray(load_srgb(CHAT_REF).resize((64, 64)), dtype=np.int16)
        best = None
        for f in files:
            a = np.asarray(load_srgb(f).resize((64, 64)), dtype=np.int16)
            d = float(np.abs(a - ref).mean())
            if best is None or d < best[0]:
                best = (d, f.name)
        if best and best[0] < 2.0:
            ref_name = best[1]
    owners, rule = atribuir(files, ref_name)

    items, seen_md5, hashes = [], {}, []
    for f in files:
        raw = f.read_bytes()
        md5 = hashlib.md5(raw).hexdigest()
        im = load_srgb(f)
        w0, h0 = im.size
        scale = min(1.0, MAX_SIDE / max(w0, h0))
        if scale < 1.0:
            im = im.resize((round(w0 * scale), round(h0 * scale)), Image.LANCZOS)
        w, h = im.size
        arr = np.asarray(im)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        # nitidez normalizada (lado maior 1000 px)
        k = 1000 / max(w, h)
        g1000 = cv2.resize(gray, (round(w * k), round(h * k)), interpolation=cv2.INTER_AREA)
        faces = detect_faces(bgr)
        face_sharp = None
        face_luma = None
        if faces:
            fb = faces[0]
            x0, y0 = max(0, int(fb["x"])), max(0, int(fb["y"]))
            x1, y1 = min(w, int(fb["x"] + fb["w"])), min(h, int(fb["y"] + fb["h"]))
            crop = gray[y0:y1, x0:x1]
            if crop.size:
                cs = cv2.resize(crop, (200, round(200 * crop.shape[0] / max(1, crop.shape[1]))))
                face_sharp = sharpness(cs)
                face_luma = float(crop.mean())
        dh = dhash(im)
        dup_of = None
        if md5 in seen_md5:
            dup_of = seen_md5[md5]
        else:
            for other_name, other_hash in hashes:
                if bin(dh ^ other_hash).count("1") <= 12:
                    dup_of = other_name
                    break
        seen_md5.setdefault(md5, f.name)
        hashes.append((f.name, dh))
        pid = re.sub(r"[^A-Za-z0-9]+", "_", f.stem).strip("_")
        out_path = OUT / f"{pid}.jpg"
        if dup_of is None:
            im.save(out_path, quality=95, subsampling=0)
        # rostos cortados pela borda da foto?
        cut = []
        for fc in faces:
            m = 0.02 * max(w, h)
            if fc["x"] < -m or fc["y"] < -m or fc["x"] + fc["w"] > w + m or fc["y"] + fc["h"] > h + m:
                cut.append(fc)
        items.append(
            {
                "file": f.name,
                "id": pid,
                "owner": owners.get(f.name),
                "src_size": [w0, h0],
                "size": [w, h],
                "orientation": "retrato" if h > w * 1.05 else ("paisagem" if w > h * 1.05 else "quadrada"),
                "md5": md5,
                "dup_of": dup_of,
                "sharpness": round(sharpness(g1000), 1),
                "face_sharpness": round(face_sharp, 1) if face_sharp else None,
                "luma": round(float(gray.mean()), 1),
                "face_luma": round(face_luma, 1) if face_luma else None,
                "faces": faces,
                "n_faces": len(faces),
                "faces_cut": len(cut),
                "path": str(out_path.relative_to(ROOT)) if dup_of is None else None,
            }
        )
    inv = {"source_dir": str(src.relative_to(REPO)), "assignment_rule": rule, "chat_reference_file": ref_name, "photos": items}
    (WORK / "inventario.json").write_text(json.dumps(inv, indent=2, ensure_ascii=False))
    for it in items:
        print(
            f"{it['file']:30s} {it['owner']:9s} {it['size'][0]}x{it['size'][1]} {it['orientation']:9s} "
            f"sharp={it['sharpness']:8.1f} fsharp={it['face_sharpness']} luma={it['luma']:5.1f} "
            f"fluma={it['face_luma']} faces={it['n_faces']} cut={it['faces_cut']} dup={it['dup_of']}"
        )
    print("regra:", rule, "| referência:", ref_name)


if __name__ == "__main__":
    main()
