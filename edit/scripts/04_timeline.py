"""Tabela de trechos (fonte única para composições, música e efeitos).

Grade: 120 BPM a 60 fps -> 30 quadros por batida, 120 por compasso; primeira batida no quadro 1.
Saída: edit/work/trechos.json e edit/work/hf/assets/timeline.js
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
FPS, BPM = 60, 120
FPB = FPS * 60 // BPM          # 30 quadros por batida
FPBAR = FPB * 4                # 120 quadros por compasso
FIRST = 1                      # quadro da primeira batida
BARS = 18
END = FIRST + BARS * FPBAR     # 2161 (exclusivo)


def bar_start(n):
    """quadro do 1º tempo do compasso n (1-based)"""
    return FIRST + (n - 1) * FPBAR


def ms(frame):
    return round(frame * 1000 / FPS, 3)


SEG = [
    # id, bloco, cena, compasso inicial, nº de compassos, transição de saída, conteúdo
    ("capa", "CAPA", "CAPA", None, None, "corte seco (quadro 1)", "Título “Graziela / & Eduarda” em caixa branca; 6 cartões (3 + 3) abaixo de y = 620"),
    ("abertura", "ABERTURA", "TIPOGRAFIA", 1, 1, "zoom-through com o riser", "“Duas coordenadoras” / “no coração.” + 6 cartões em parallax (3 da Graziela, 3 da Eduarda)"),
    ("a1_destaque", "ATO 1 · Graziela", "DESTAQUE", 2, 1, "corte seco", "Cartão da Graziela + “Graziela,” / “bem-vinda!”"),
    ("a1_pilha", "ATO 1 · Graziela", "PILHA", 3, 1, "corte seco", "3 cartões empilhados + carimbo “carinho”"),
    ("a1_mosaico", "ATO 1 · Graziela", "MOSAICO", 4, 2, "zoom-through", "Mosaico 2×2 + “Nossa história tá só começando.” + carimbo “gratidão”"),
    ("a1_nome", "ATO 1 · Graziela", "NOME", 6, 1, "whip", "GRAZIELA atrás do recorte + etiqueta “coordenadora”"),
    ("pivo", "PIVÔ", "ESPELHO", 7, 3, "corte seco", "Cartões espelhados + “Gostamos muito da Graziela” / “Nunca vamos esquecer a Eduarda.” / “Ninguém substitui ninguém.” + coração"),
    ("a2_destaque", "ATO 2 · Eduarda", "DESTAQUE", 10, 1, "corte seco", "Cartão da Eduarda + “Eduarda,” / “inesquecível!”"),
    ("a2_pilha", "ATO 2 · Eduarda", "PILHA", 11, 1, "corte seco", "3 cartões empilhados + carimbo “carinho”"),
    ("a2_mosaico", "ATO 2 · Eduarda", "MOSAICO", 12, 2, "zoom-through", "Mosaico 2×2 + “Nossas memórias ficam pra sempre.” + carimbo “gratidão”"),
    ("a2_nome", "ATO 2 · Eduarda", "NOME", 14, 1, "whip", "EDUARDA atrás do recorte + etiqueta “coordenadora”"),
    ("final1", "FINAL", "FINAL", 15, 2, "corte seco", "Foto da turma 1 + “Eduarda,” / “esse momento fica com a gente.”"),
    ("final2", "FINAL", "FINAL", 17, 2, "fim (END)", "Foto da turma 2 + confete + “Graziela, bem-vinda.” / “Eduarda, gratidão.”"),
]


def main():
    sel = json.loads((WORK / "selecao.json").read_text())
    segs = []
    for sid, block, scene, b0, nb, tout, content in SEG:
        if b0 is None:
            start, end = 0, 1
        else:
            start, end = bar_start(b0), bar_start(b0 + nb)
        segs.append(
            {
                "id": sid,
                "bloco": block,
                "cena": scene,
                "compassos": None if b0 is None else [b0, b0 + nb - 1],
                "quadro_inicio": start,
                "quadro_fim": end,
                "ms_inicio": ms(start),
                "ms_fim": ms(end),
                "quadros": end - start,
                "duracao_s": round((end - start) / FPS, 6),
                "transicao_saida": tout,
                "conteudo": content,
            }
        )
    # verificações estruturais
    assert segs[-1]["quadro_fim"] == END == 2161
    for a, b in zip(segs, segs[1:]):
        assert a["quadro_fim"] == b["quadro_inicio"]
        assert a["cena"] != b["cena"] or a["cena"] == "FINAL"
    for s in segs[1:]:
        assert (s["quadro_inicio"] - FIRST) % FPBAR == 0 and s["quadros"] % FPBAR == 0
    a1 = [s for s in segs if s["id"].startswith("a1_")]
    a2 = [s for s in segs if s["id"].startswith("a2_")]
    assert [(s["cena"], s["quadros"], s["transicao_saida"]) for s in a1] == [(s["cena"], s["quadros"], s["transicao_saida"]) for s in a2]

    chords = {
        1: "IV", 2: "I", 3: "V", 4: "vi", 5: "IV", 6: "I", 7: "vi", 8: "IV", 9: "V",
        10: "I", 11: "V", 12: "vi", 13: "IV", 14: "I", 15: "vi", 16: "IV", 17: "V", 18: "I",
    }
    data = {
        "fps": FPS,
        "bpm": BPM,
        "quadros_por_batida": FPB,
        "quadros_por_compasso": FPBAR,
        "quadro_primeira_batida": FIRST,
        "compassos": BARS,
        "END_quadro": END,
        "END_ms": ms(END),
        "tonalidade": "Ré maior",
        "acordes_por_compasso": chords,
        "cortes": [s["quadro_inicio"] for s in segs[2:]] + [END],
        "trechos": segs,
        "fotos": {
            k: v["plano"] for k, v in sel["coordenadoras"].items()
        },
        "finais": [f["id"] for f in sel["finais"]],
    }
    (WORK / "trechos.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    (WORK / "hf" / "assets" / "timeline.js").write_text("window.TIMELINE = " + json.dumps(data, ensure_ascii=False) + ";\n")
    print(f"{'id':12s} {'cena':10s} {'quadros':>12s} {'ms':>22s}  compassos")
    for s in segs:
        print(f"{s['id']:12s} {s['cena']:10s} {s['quadro_inicio']:5d}–{s['quadro_fim']:5d} {s['ms_inicio']:10.3f}–{s['ms_fim']:10.3f}  {s['compassos']}")
    print("cortes:", data["cortes"])


if __name__ == "__main__":
    main()
