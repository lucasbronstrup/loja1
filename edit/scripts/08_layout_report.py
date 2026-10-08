"""Analisa edit/work/layout/*.json: áreas seguras (rostos/textos), texto sobre rosto, tamanho mínimo de texto."""
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1] / "work"
TL = json.loads((WORK / "trechos.json").read_text())
SAFE = (60, 240, 1020, 1560)
TOL = 2

# intervalos de movimento (s locais) em que objetos podem cruzar as bordas: whips, arremesso, zooms, entradas
MOTION = {
    "abertura": [(0.0, 0.7), (0.8, 2.0)],
    "a1_destaque": [(0.0, 0.5)], "a2_destaque": [(0.0, 0.5)],
    "a1_pilha": [(1.0, 1.5)], "a2_pilha": [(1.0, 1.5)],
    "a1_mosaico": [(0.0, 0.6), (2.5, 4.0)], "a2_mosaico": [(0.0, 0.6), (2.5, 4.0)],
    "a1_nome": [(1.55, 2.0)], "a2_nome": [(1.55, 2.0)],
    "pivo": [(0.0, 0.62)], "final1": [(0.0, 0.62)], "final2": [(1.0, 4.0)],
}


def inter(a, b):
    x = max(0, min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]))
    y = max(0, min(a["y1"], b["y1"]) - max(a["y0"], b["y0"]))
    return x * y


def in_motion(seg, t):
    return any(a <= t <= b for a, b in MOTION.get(seg, []))


def main():
    report = {}
    for seg in TL["trechos"]:
        sid = seg["id"]
        data = json.loads((WORK / "layout" / f"{sid}.json").read_text())
        issues = []
        min_fs = 999
        for fr in data:
            t = fr["t"]
            moving = in_motion(sid, t)
            for tx in fr["texts"]:
                min_fs = min(min_fs, tx["fs"])
                out = tx["x0"] < SAFE[0] - TOL or tx["y0"] < SAFE[1] - TOL or tx["x1"] > SAFE[2] + TOL or tx["y1"] > SAFE[3] + TOL
                if out and not moving:
                    issues.append(("texto fora da área segura", round(t, 3), tx["text"], [round(tx[k]) for k in ("x0", "y0", "x1", "y1")]))
                for fc in fr["faces"]:
                    if fc["o"] < 0.5:
                        continue
                    if "namechar" in tx["cls"]:
                        continue  # nome gigante fica atrás do recorte (o rosto continua por cima)
                    if tx["z"] > fc["z"] and inter(tx, fc) > 4:
                        issues.append(("texto sobre rosto", round(t, 3), tx["text"], fc["pid"]))
            for fc in fr["faces"]:
                if fc["o"] < 0.5 or moving:
                    continue
                # só rostos efetivamente visíveis na tela
                if fc["x1"] < 0 or fc["x0"] > 1080 or fc["y1"] < 0 or fc["y0"] > 1920:
                    continue
                out = fc["x0"] < SAFE[0] - TOL or fc["y0"] < SAFE[1] - TOL or fc["x1"] > SAFE[2] + TOL or fc["y1"] > SAFE[3] + TOL
                if out:
                    issues.append(("rosto fora da área segura", round(t, 3), fc["pid"], [round(fc[k]) for k in ("x0", "y0", "x1", "y1")]))
        # agrupa
        agg = {}
        for kind, t, what, extra in issues:
            key = (kind, what)
            agg.setdefault(key, []).append((t, extra))
        report[sid] = {"min_font_px": min_fs, "issues": {f"{k[0]} | {k[1]}": {"n": len(v), "t": [v[0][0], v[-1][0]], "ex": v[0][1]} for k, v in agg.items()}}
    (WORK / "layout_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    for sid, r in report.items():
        print(sid, "fonte mín", r["min_font_px"], "px")
        for k, v in r["issues"].items():
            print("   ", k, v)


if __name__ == "__main__":
    main()
