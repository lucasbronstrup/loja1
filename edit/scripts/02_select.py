"""Seleção das fotos, descartes, distribuição por cena e recortes centrados nos rostos.

Entrada: edit/work/inventario.json (gerado por 01_photos.py)
Saída:   edit/work/selecao.json  e  edit/work/hf/assets/data.js (consumido pelas composições)
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
HF = WORK / "hf"

MAX_UPSCALE = 1.3          # ampliação máxima em repouso
FACE_MARGIN = 0.08         # margem mínima ao redor dos rostos dentro do recorte
BORDER = 0.02              # borda branca do cartão = 2% da largura
RADIUS = 0.03              # raio do cartão = 3% da largura

COLORS = {
    "graziela": {"fill": "#D97757", "text": "#B25730", "band": "#FBEEE8", "name": "Graziela"},
    "eduarda": {"fill": "#2F9AA8", "text": "#1F6F7D", "band": "#E6F4F6", "name": "Eduarda"},
}


def main_faces(it):
    """Rostos válidos para enquadrar: descarta falsos positivos pequenos/fracos."""
    faces = it["faces"]
    if not faces:
        return []
    big = max(f["w"] for f in faces)
    keep = [f for f in faces if f["score"] >= 0.75 or (f["w"] >= 0.4 * big and f["score"] >= 0.6)]
    if it["owner"] in ("graziela", "eduarda"):
        keep = keep[:1]  # foto individual: o rosto principal
    return keep


def crop_for(it, aspect, zoom=1.0, face_y=0.40, focus=None):
    """Maior recorte com proporção `aspect` (w/h), reduzido por `zoom`, centrado no rosto."""
    W, H = it["size"]
    faces = main_faces(it)
    if W / H > aspect:
        ch = H * zoom
        cw = ch * aspect
    else:
        cw = W * zoom
        ch = cw / aspect
    if faces:
        x0 = min(f["x"] for f in faces)
        y0 = min(f["y"] for f in faces)
        x1 = max(f["x"] + f["w"] for f in faces)
        y1 = max(f["y"] + f["h"] for f in faces)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    else:
        cx, cy = W / 2, H / 2
    if focus:
        cx, cy = focus
    x = min(max(cx - cw / 2, 0), W - cw)
    y = min(max(cy - face_y * ch, 0), H - ch)
    c = {"x": round(x, 2), "y": round(y, 2), "w": round(cw, 2), "h": round(ch, 2)}
    # rostos dentro do recorte com margem
    fr = []
    for f in faces:
        fr.append(
            {
                "x": round((f["x"] - x) / cw, 4),
                "y": round((f["y"] - y) / ch, 4),
                "w": round(f["w"] / cw, 4),
                "h": round(f["h"] / ch, 4),
            }
        )
        mx, my = FACE_MARGIN * f["w"], FACE_MARGIN * f["h"]
        inside = f["x"] - mx >= x - 0.5 and f["y"] - my >= y - 0.5 and f["x"] + f["w"] + mx <= x + cw + 0.5 and f["y"] + f["h"] + my <= y + ch + 0.5
        if not inside:
            raise SystemExit(f"rosto cortado em {it['file']} aspect={aspect} zoom={zoom}")
    c["faces"] = fr
    return c


def max_inner_width(crop, upscale=MAX_UPSCALE):
    return crop["w"] * upscale


def main():
    inv = json.loads((WORK / "inventario.json").read_text())
    photos = {it["id"]: it for it in inv["photos"]}
    discards = []

    # 1) duplicatas (mantém o arquivo original, sem sufixo "(1)")
    by_md5 = {}
    for it in inv["photos"]:
        by_md5.setdefault(it["md5"], []).append(it)
    dup_ids = set()
    for group in by_md5.values():
        if len(group) > 1:
            group.sort(key=lambda i: ("(" in i["file"], i["file"]))
            for d in group[1:]:
                dup_ids.add(d["id"])
                discards.append({"file": d["file"], "motivo": f"duplicata exata de {group[0]['file']} (mesmo md5)"})

    pool = {k: [] for k in ("graziela", "eduarda", "final")}
    for it in inv["photos"]:
        if it["id"] in dup_ids:
            continue
        pool[it["owner"]].append(it)

    # 2) fotos tremidas/escuras/rosto cortado (só fotos individuais; nitidez medida no rosto)
    ind = pool["graziela"] + pool["eduarda"]
    sharp_vals = sorted(i["face_sharpness"] or 0 for i in ind)
    median = sharp_vals[len(sharp_vals) // 2]
    for key in ("graziela", "eduarda"):
        keep = []
        for it in pool[key]:
            reason = None
            if not main_faces(it):
                reason = "nenhum rosto detectado"
            elif it["faces_cut"]:
                reason = "rosto cortado pela borda"
            elif (it["face_sharpness"] or 0) < 0.12 * median:
                reason = (
                    f"rosto desfocado/tremido (variância do Laplaciano no rosto {it['face_sharpness']} "
                    f"contra mediana {median} do conjunto)"
                )
            elif (it["face_luma"] or 0) < 55:
                reason = f"rosto escuro (luminância média {it['face_luma']})"
            if reason:
                discards.append({"file": it["file"], "motivo": reason})
            else:
                keep.append(it)
        pool[key] = keep

    n = min(len(pool["graziela"]), len(pool["eduarda"]), 10)
    if n < 4:
        raise SystemExit(f"menos de 4 fotos aproveitáveis ({n})")

    # 3) excesso: escolhe as n melhores (nitidez do rosto, tamanho do rosto, luz)
    def quality(it):
        f = main_faces(it)[0]
        face_px = f["w"]
        return (it["face_sharpness"] or 0) * 0.5 + face_px * 0.3 + min(it["face_luma"] or 0, 140) * 0.2

    for key in ("graziela", "eduarda"):
        ranked = sorted(pool[key], key=quality, reverse=True)
        for it in ranked[n:]:
            f = main_faces(it)[0]
            discards.append(
                {
                    "file": it["file"],
                    "motivo": (
                        f"excedente para igualar o número de fotos ({n} por coordenadora); menor pontuação do conjunto "
                        f"(rosto de {round(f['w'])} px, nitidez do rosto {it['face_sharpness']})"
                    ),
                }
            )
        pool[key] = sorted(ranked[:n], key=lambda i: i["file"])

    finals = sorted(pool["final"], key=lambda i: i["file"])
    notes = []
    if len(finals) > 2:
        notes.append(f"final/ tinha {len(finals)} imagens: usadas as duas primeiras em ordem de nome")
        finals = finals[:2]

    # 4) distribuição por cena (mesma estrutura nos dois atos)
    #    NOME: a foto com o maior rosto (retrato de um só rosto e boa resolução)
    plan = {}
    for key in ("graziela", "eduarda"):
        ph = pool[key]
        nome = max(ph, key=lambda i: main_faces(i)[0]["w"] * main_faces(i)[0]["h"])
        others = [p for p in ph if p["id"] != nome["id"]]
        # destaque: retrato vertical com maior rosto entre os restantes; topo da pilha: a mais "quadrada/aberta"
        vert = sorted(others, key=lambda i: (i["size"][1] / i["size"][0]), reverse=True)
        squarest = min(others, key=lambda i: abs(i["size"][0] / i["size"][1] - 1))
        rest = [p for p in others if p["id"] != squarest["id"]]
        destaque = max(rest, key=lambda i: main_faces(i)[0]["w"])
        second = [p for p in rest if p["id"] != destaque["id"]][0]
        plan[key] = {
            "nome": nome["id"],
            "destaque": destaque["id"],
            "pilha": [squarest["id"], second["id"], nome["id"]],  # topo, segundo, terceiro (parcial)
            "mosaico": [destaque["id"], nome["id"], squarest["id"], second["id"]],  # TL, TR (zoom), BL, BR
            "abertura": [destaque["id"], squarest["id"], second["id"]],
            "espelho": nome["id"],
        }

    # 5) recortes por uso
    crops = {}

    def add(pid, usage, aspect, zoom=1.0, face_y=0.40):
        c = crop_for(photos[pid], aspect, zoom, face_y)
        crops.setdefault(pid, {})[usage] = c
        return c

    for key in ("graziela", "eduarda"):
        p = plan[key]
        add(p["destaque"], "destaque", 4 / 5, zoom=0.85)
        add(p["pilha"][0], "pilha_topo", 1.0)
        add(p["pilha"][1], "pilha_segundo", 4 / 5)
        add(p["pilha"][2], "pilha_terceiro", 4 / 5)
        for pid in p["mosaico"]:
            if pid != p["nome"]:
                # enquadramento fechado (rosto ~22% da largura), sempre mais fechado que nas outras cenas
                it = photos[pid]
                fw = main_faces(it)[0]["w"]
                W, H = it["size"]
                full_w = min(W, H * 4 / 5)
                z = min(0.75, max(0.45, (fw / 0.22) / full_w))
                add(pid, "mosaico", 4 / 5, zoom=round(z, 3), face_y=0.40)
        # NOME: cabeça e ombros (zoom 0.9 nas duas), mesmo recorte na miniatura do mosaico
        add(p["nome"], "nome", 4 / 5, zoom=0.90, face_y=0.40)
        for pid in p["abertura"]:
            add(pid, "abertura", 4 / 5)
    # ESPELHO: cartões idênticos; rosto com a mesma altura relativa nos dois
    espelho_aspect = (720 - 2 * BORDER * 720) / (440 - 2 * BORDER * 720)
    fr = {}
    for key in ("graziela", "eduarda"):
        c = crop_for(photos[plan[key]["espelho"]], espelho_aspect, 1.0, 0.45)
        fr[key] = c["faces"][0]["h"]
    target = max(fr.values())
    for key in ("graziela", "eduarda"):
        add(plan[key]["espelho"], "espelho", espelho_aspect, zoom=round(fr[key] / target, 3), face_y=0.45)
    for f in finals:
        W, H = f["size"]
        crops.setdefault(f["id"], {})["final"] = {"x": 0, "y": 0, "w": W, "h": H, "faces": [
            {"x": round(a["x"] / W, 4), "y": round(a["y"] / H, 4), "w": round(a["w"] / W, 4), "h": round(a["h"] / H, 4)}
            for a in main_faces(f)
        ]}

    sel = {
        "regra_atribuicao": inv["assignment_rule"],
        "arquivo_referencia_chat": inv["chat_reference_file"],
        "n_por_coordenadora": n,
        "coordenadoras": {
            key: {**COLORS[key], "fotos": [{"id": i["id"], "file": i["file"], "size": i["size"]} for i in pool[key]], "plano": plan[key]}
            for key in ("graziela", "eduarda")
        },
        "finais": [{"id": f["id"], "file": f["file"], "size": f["size"], "n_rostos": len(main_faces(f))} for f in finals],
        "descartes": discards,
        "notas": notes,
        "crops": crops,
        "photos": {
            pid: {"file": photos[pid]["file"], "size": photos[pid]["size"], "src": f"assets/photos/{pid}.jpg"}
            for pid in crops
        },
        "constantes": {"max_upscale": MAX_UPSCALE, "border": BORDER, "radius": RADIUS},
    }
    (WORK / "selecao.json").write_text(json.dumps(sel, indent=2, ensure_ascii=False))
    (HF / "assets" / "photos").mkdir(parents=True, exist_ok=True)
    for pid in crops:
        shutil.copy(WORK / "photos" / f"{pid}.jpg", HF / "assets" / "photos" / f"{pid}.jpg")

    print("n por coordenadora:", n)
    for key in ("graziela", "eduarda"):
        print(key, [i["file"] for i in pool[key]])
        print("   plano:", plan[key])
    print("finais:", [f["file"] for f in finals])
    for d in discards:
        print("DESCARTE", d["file"], "->", d["motivo"])
    for pid, us in crops.items():
        for u, c in us.items():
            print(f"{pid:22s} {u:15s} crop={c['w']:.0f}x{c['h']:.0f}@({c['x']:.0f},{c['y']:.0f}) faces={c['faces'][:1]}")


if __name__ == "__main__":
    main()
