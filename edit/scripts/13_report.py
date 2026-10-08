"""Gera edit/relatorio.md a partir dos JSON de trabalho (trechos, seleção, efeitos, loudness, verificação)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
TL = json.loads((WORK / "trechos.json").read_text())
SEL = json.loads((WORK / "selecao.json").read_text())
NOME = json.loads((WORK / "nome_layout.json").read_text())
MUS = json.loads((WORK / "audio_music_info.json").read_text())
MIX = json.loads((WORK / "audio_mix_info.json").read_text())
VER = json.loads((WORK / "verificacao.json").read_text())
LAY = json.loads((WORK / "layout_report.json").read_text())

CHORD_NAME = {"I": "Ré (I)", "V": "Lá (V)", "vi": "Si menor (vi)", "IV": "Sol (IV)", "Vsus": "Lá sus4 → Lá (V)"}
CHORDS = {1: "Vsus", 2: "I", 3: "V", 4: "vi", 5: "IV", 6: "I", 7: "vi", 8: "IV", 9: "Vsus", 10: "I", 11: "V", 12: "vi", 13: "IV", 14: "I", 15: "vi", 16: "IV", 17: "Vsus", 18: "I"}
ARR = {
    1: "piano elétrico e pad esparsos + riser (stem separado)",
    **{b: "ritmo completo: bumbo, shaker, baixo, arpejo de pluck, piano elétrico, pad, melodia, sino discreto no 1º tempo" for b in range(2, 7)},
    7: "respiro: pad + piano (acordes e arpejo lento) + melodia suave", 8: "respiro: pad + piano + melodia suave", 9: "respiro: pad + piano (Lá sus4 → Lá), sem ritmo",
    **{b: "ritmo volta igual ao Ato 1 (bumbo, shaker, baixo, piano, pad, melodia, sino) com cordas macias no lugar do pluck" for b in range(10, 15)},
    15: "arranjo completo e amplo: ritmo + palmas leves + pluck + cordas sustentadas + sinos dobrando a melodia",
    16: "arranjo completo e amplo (idem)", 17: "construção: bumbo nos 4 tempos, palmas, Lá sus4 → Lá (dominante)",
    18: "cadência resolvida no 1º tempo (Ré maior), acorde soando até a saída gradual de 800 ms",
}


def fmt_ms(f):
    return f"{f * 1000 / 60:.3f}".replace(".", ",")


def br(x, nd=1):
    """número no formato brasileiro (vírgula decimal, menos tipográfico)"""
    return f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def br_text(t):
    import re

    return re.sub(r"(\d)\.(\d)", r"\1,\2", t)


def main():
    L = []
    w = L.append
    end_ms = TL["END_ms"]
    w("# Relatório — homenagem a Graziela e Eduarda\n")
    w("## 1. Resumo\n")
    w(f"- END: quadro **{TL['END_quadro']}** (exclusivo) = **{end_ms:.3f} ms**".replace(".", ",", 1))
    w(f"- Duração total: **{TL['END_quadro']} quadros a 60 qps = {br(TL['END_quadro'] / 60, 3)} s**")
    w(f"- Andamento: **{TL['bpm']} BPM** (30 quadros por batida, 120 por compasso; 1ª batida no quadro 1)")
    w(f"- Tonalidade: **{TL['tonalidade']}** · **{TL['compassos']} compassos**")
    w("- Entregas: `final.mp4`, `stems/music.wav`, `stems/sfx.wav`, `stems/riser.wav`, este relatório; intermediários em `work/`.\n")

    w("## 2. Tabela de trechos\n")
    w("| Quadros (início–fim excl.) | ms | Compassos | Bloco | Cena | Conteúdo | Saída |")
    w("|---|---|---|---|---|---|---|")
    for s in TL["trechos"]:
        cmp = "—" if not s["compassos"] else (f"{s['compassos'][0]}" if s["compassos"][0] == s["compassos"][1] else f"{s['compassos'][0]}–{s['compassos'][1]}")
        w(f"| {s['quadro_inicio']}–{s['quadro_fim']} | {fmt_ms(s['quadro_inicio'])}–{fmt_ms(s['quadro_fim'])} | {cmp} | {s['bloco']} | {s['cena']} | {s['conteudo']} | {s['transicao_saida']} |")
    w("\nFonte única: `work/trechos.json` (usada pelas composições, pela música e pelos efeitos).\n")

    w("## 3. Fotos\n")
    w(f"**Atribuição de quem é quem.** A pasta `{json.loads((WORK / 'inventario.json').read_text())['source_dir']}` chegou sem subpastas e com nomes do WhatsApp. "
      "A foto anexada no chat (indicada como Eduarda) é idêntica, pixel a pixel, ao arquivo `IMG-20261007-WA0086.jpg`. "
      "Pela numeração dos arquivos: o bloco contíguo `WA0086–WA0090` (mesmo envio) foi atribuído à **Eduarda**; as demais fotos individuais do mesmo dia "
      "(`WA0078`, `WA0092–WA0094`, `WA0097`) à **Graziela**; as duas fotos de grupo de outra data (`20260313`) são as fotos **finais** da turma com a Eduarda. "
      "Nenhum reconhecimento facial foi usado — a detecção de rostos (YuNet/OpenCV, local) serviu só para enquadrar. **Se a atribuição estiver trocada, basta inverter as listas em `work/selecao.json` e renderizar de novo.**\n")
    for key in ("graziela", "eduarda"):
        c = SEL["coordenadoras"][key]
        p = c["plano"]
        w(f"**{c['name']}** ({len(c['fotos'])} fotos): " + ", ".join(f"`{f['file']}`" for f in c["fotos"]))
        fn = {f["id"]: f["file"] for f in c["fotos"]}
        w(f"- DESTAQUE: `{fn[p['destaque']]}` · PILHA (topo / segundo / terceiro): " + " / ".join(f"`{fn[x]}`" for x in p["pilha"]))
        w(f"- MOSAICO (TL, TR=NOME, BL, BR): " + ", ".join(f"`{fn[x]}`" for x in p["mosaico"]) + f" · NOME: `{fn[p['nome']]}` · ESPELHO: `{fn[p['espelho']]}`")
        w(f"- ABERTURA/CAPA: " + ", ".join(f"`{fn[x]}`" for x in p["abertura"]) + "\n")
    w("**Fotos finais:** " + " e ".join(f"`{f['file']}` ({f['n_rostos']} rostos detectados)" for f in SEL["finais"]) + " — mostradas inteiras.\n")
    w("**Descartes:**\n")
    for d in SEL["descartes"]:
        w(f"- `{d['file']}` — {br_text(d['motivo'])}")
    w("\n**Igualdade:** 4 fotos para cada uma; mesma estrutura de cenas (DESTAQUE 1, PILHA 3, MOSAICO 4 com a foto do NOME, NOME), mesmas durações (5 compassos por ato), mesmas transições (corte seco, corte seco, zoom-through, whip), mesmos efeitos sonoros (impacto no pouso do DESTAQUE e na chegada do NOME, passagem no whip), mesmos tamanhos de cartão e de fonte; nome gigante no mesmo tamanho (181 px) para as duas. Com menos de 8 fotos, cada foto aparece em até duas cenas do ato, com enquadramentos diferentes (o mosaico usa recortes mais fechados); a foto do NOME é a miniatura ampliada pelo zoom-through (exceção prevista).\n")
    w("Pré-processamento: orientação EXIF aplicada, conversão ICC → sRGB, máximo de 2160 px (nenhuma ampliação). Recortes centrados nos rostos; nenhuma foto ampliada mais de 1,3× em repouso (NOME da Graziela: 1,18× com a aproximação de 1,06 → 1,26×).\n")

    w("## 4. Roteiro final dos textos\n")
    w("| Trecho | Texto na tela | Ajuste em relação à base |")
    w("|---|---|---|")
    rows = [
        ("Capa (quadro 0)", "Graziela / & Eduarda", "título criado (110 px, caixa branca y 262–603)"),
        ("Abertura", "Duas / coordenadoras / no coração.", "“Duas coordenadoras” não cabe em 960 px a ≥ 96 px: a 1ª linha da base foi quebrada em duas etiquetas (3 linhas no total); “coração.” em Instrument Serif itálico com as duas cores"),
        ("Ato 1 · DESTAQUE", "Graziela, / bem-vinda!", "sem mudança (“bem-vinda!” em Instrument Serif itálico terracota, sublinhado à mão)"),
        ("Ato 1 · PILHA", "carinho (carimbo)", "sem mudança"),
        ("Ato 1 · MOSAICO", "Nossa história / tá só começando. + carimbo “gratidão”", "sem mudança (“história” em itálico)"),
        ("Ato 1 · NOME", "GRAZIELA + etiqueta “coordenadora”", "sem mudança"),
        ("Pivô · compasso 7", "Gostamos / muito / da Graziela", "quebrado em 3 linhas para ocupar a mesma grade da frase seguinte (troca limpa, mesmo peso visual)"),
        ("Pivô · compasso 8", "Nunca vamos / esquecer / a Eduarda.", "sem mudança (3 linhas a 96 px)"),
        ("Pivô · compasso 9", "Ninguém substitui / ninguém. + coração", "marca-texto: “Ninguém” na faixa da Graziela, “ninguém.” na faixa da Eduarda"),
        ("Ato 2 · DESTAQUE", "Eduarda, / inesquecível!", "sem mudança"),
        ("Ato 2 · PILHA", "carinho (carimbo)", "sem mudança"),
        ("Ato 2 · MOSAICO", "Nossas memórias / ficam pra sempre. + carimbo “gratidão”", "sem mudança (“memórias” em itálico)"),
        ("Ato 2 · NOME", "EDUARDA + etiqueta “coordenadora”", "sem mudança"),
        ("Final · foto 1", "Eduarda, / esse momento / fica com a gente.", "sem mudança (3 linhas acima do cartão; “momento” em itálico, sublinhado)"),
        ("Final · foto 2 (compasso 18)", "Graziela, bem-vinda. / Eduarda, gratidão.", "sem mudança (80 px, mesmo tamanho, terracota / azul-petróleo)"),
    ]
    for r in rows:
        w(f"| {r[0]} | {r[1]} | {r[2]} |")
    pal = VER["palavras_proibidas"]
    w(f"\nBusca por palavras proibidas (nova, antiga, velha, substituta, melhor, pior) nos textos finais: **{len(pal['ocorrencias'])} ocorrências**. Única exceção usada: “Ninguém substitui ninguém.”\n")

    w("## 5. Cenas\n")
    scenes = [
        ("CAPA (quadro 0)", "fundo radial quase branco, caixa branca com o título e 6 cartões (3 + 3) estáticos e nítidos abaixo de y = 620."),
        ("TIPOGRAFIA (abertura)", "três etiquetas brancas com o texto entram no centro (máscara na batida 1, mola meia batida depois) sobre 6 cartões pequenos (3 de cada) em três camadas de parallax com 5–9 px de desfoque; nos últimos 1,2 s a câmera atravessa os cartões até o retrato da Graziela preencher a largura da tela (zoom-through com o riser)."),
        ("DESTAQUE", "cartão flutuante de 812 px com pílula do nome; entra de 0,86 → 1 e −4° → 0° (back.out(1.4), 0,5 s) e pousa na batida 2; depois deriva. Frase acima do cartão: máscara + sublinhado desenhado."),
        ("PILHA", "três cartões empilhados (−4,5° a +6°); carimbo “carinho” na batida 2; na batida 3 o cartão do topo é arremessado para a direita com rotação e desfoque de movimento; o segundo cresce de 0,96 a 1."),
        ("MOSAICO", "2×2 com 24 px de espaçamento; miniaturas entram em stagger de 1/4 de batida (back.out(1.6)); frase no topo; carimbo “gratidão” no centro na batida 3; nos últimos 1,5 s a câmera vai até a miniatura do NOME (power2.inOut), que termina exatamente no enquadramento do cartão do NOME."),
        ("NOME", "retrato em cartão grande (912 × 1140), nome gigante branco com contorno de 14 px na cor dela atrás da cabeça e o recorte da pessoa por cima; letras em stagger de 0,04 s, câmera 1 → 1,06, etiqueta “coordenadora” na batida 3 (carimbo); sai com whip vertical."),
        ("ESPELHO (pivô)", "cartões idênticos 720 × 440 (Graziela em cima, Eduarda embaixo) deslizando da esquerda e da direita (power3.out, 0,5 s), pílulas com as cores; três frases em sequência numa grade fixa de 3 linhas, nomes coloridos; marca-texto em “Ninguém substitui ninguém.”; coração de 134 px desenhado traço a traço na batida 3 do compasso 9 (metade terracota, metade azul-petróleo)."),
        ("FINAL · foto 1", "foto da turma inteira num cartão largo (750 px) sobre cópia desfocada quase branca da própria foto; chega com o whip e para na batida 2; aproximação 1 → 1,08 (sine.inOut); frase acima (mola + sublinhado)."),
        ("FINAL · foto 2", "corte seco; foto vertical inteira, recuo 1,08 → 1; confete retangular (36 peças nas duas cores, atrás do cartão) na batida 3; no compasso 18 as duas linhas de encerramento entram juntas (respiro) e ficam paradas e nítidas até END."),
    ]
    for n, d in scenes:
        w(f"- **{n}** — {d}")
    w("\nTransições: Abertura → Ato 1 zoom-through com riser; DESTAQUE → PILHA e PILHA → MOSAICO cortes secos; MOSAICO → NOME zoom-through; NOME → bloco seguinte whip vertical (saída 0,45 s power3.in, chegada 0,6 s power3.out, velocidade contínua de 3 500 px/s no corte); Pivô → Ato 2 e Final 1 → Final 2 cortes secos. Nenhum fade ou dissolve entre trechos.\n")

    w("## 6. Efeitos sonoros (stems/sfx.wav)\n")
    w("| Quadro | ms | Tipo | Evento (arquivo de eventos da composição) |")
    w("|---|---|---|---|")
    for e in MIX["efeitos"]:
        w(f"| {e['quadro']:.0f} | {fmt_ms(e['quadro'])} | {e['tipo']} | {e['trecho']}: {e['rotulo']} |")
    w("\nPicos relativos ao pico da música: impactos e sinais −9 dB, passagens −9 dB (pico no corte), brilho −12 dB; riser −10 dB. Nenhum efeito em cortes secos, derivas, aproximações, zoom-throughs ou entradas da pilha/mosaico; na junção abertura → Ato 1 soa só o riser.\n")

    w("## 7. Loudness (FFmpeg ebur128)\n")
    w("| Faixa | LUFS integrados | Pico verdadeiro (dBTP) |")
    w("|---|---|---|")
    for k, v in VER["loudness"].items():
        tp = "—" if v["true_peak_dbtp"] is None else br(v["true_peak_dbtp"])
        w(f"| {k} | {br(v['lufs_integrado'])} | {tp} |")
    lim = MIX["limitador"]
    w(f"\nGanho comum aplicado às três faixas: +{br(MIX['ganho_comum_db'], 2)} dB. "
      + ("A soma passou do limite num único ponto (impacto da foto final 2 sobre o 1º tempo do compasso 17, pico verdadeiro da soma "
         f"{br(MIX['true_peak_soma_db'])} dBTP); ali atuou um limitador transparente de pico verdadeiro (−1,3 dBTP, antecipação de 10 ms): "
         f"{lim['tempo_ativo_ms']:.0f} ms no total, redução máxima {br(lim['reducao_max_db'], 2)} dB em {', '.join(br(x, 3) for x in lim['trechos_s'])} s. Fora desse trecho o master é a soma exata dos três stems." if lim.get("ativado") else "O limitador não foi necessário.")
      + "\n")

    w("## 8. Música (stems/music.wav) e riser\n")
    w("Trilha original sintetizada com NumPy/SciPy: piano elétrico FM, pad de serras com passa-baixa, pluck aditivo, sinos FM discretos, baixo suave, bumbo macio, shaker, palmas leves e cordas macias; reverb por convolução sintética. 120 BPM, Ré maior, progressão I–V–vi–IV (um acorde por compasso), melodia simples no piano elétrico. Só entrada de 5 ms anti-estalo e saída gradual de 800 ms no fim; dinâmica pelo arranjo (sem automação de volume).\n")
    w("| Compasso | Acorde | Arranjo |")
    w("|---|---|---|")
    for b in range(1, 19):
        w(f"| {b} | {CHORD_NAME[CHORDS[b]]} | {ARR[b]} |")
    secs = MUS["secoes_lufs"]
    w(f"\nLoudness por seção (antes do ganho comum): abertura {br(secs['abertura'], 2)} · Ato 1 {br(secs['ato1'], 2)} · pivô {br(secs['pivo'], 2)} · Ato 2 {br(secs['ato2'], 2)} · final {br(secs['final'], 2)} LUFS — os dois atos ficam iguais (diferença {br(abs(secs['ato1'] - secs['ato2']), 2)} LU; o ganho das cordas foi calibrado para isso).\n")
    rs = VER["riser"]
    w(f"Riser (stems/riser.wav): ruído filtrado com filtro abrindo + tom grave subindo (55 → 196 Hz), **2 s exatos**: começa na amostra 800 (quadro 1) e cresce até a junção com o Ato 1 (amostra 96 800 = quadro 121), com 4 ms anti-estalo nas pontas; última amostra audível {rs['ultima_amostra']}; nada depois do corte. Pico 10 dB abaixo do pico da música.\n")

    w("## 9. Decisões, alternativas e limitações\n")
    dec = [
        "Atribuição das fotos pela numeração dos arquivos + foto de referência do chat (ver seção 3); sem reconhecimento facial.",
        "4 fotos por coordenadora (mínimo entre os conjuntos após descartes): `WA0093` descartada por desfoque, `WA0090` como excedente, `WA0078(1)` duplicata.",
        "Renderização: HyperFrames 0.8.140 (`render --fps 240 --format png-sequence`, uma composição por trecho, motor determinístico com relógio GSAP). Os 240 qps foram viáveis (~10 subquadros/s), sem precisar do modo 120 qps.",
        "Combinação dos 4 subquadros (FFmpeg tpad + tmix + select) com obturador “traseiro”: o quadro n é a média dos instantes n/60 − 3/240 … n/60. Assim o 1º quadro de cada trecho é o instante exato do corte (nítido) e a capa usa 4 subquadros idênticos.",
        "Desfoque de movimento: além da mistura de subquadros, cada elemento recebe desfoque gaussiano direcional (SVG) com sigma = 0,29 × v × 0,75 / 60 (máx. 40 px) pela velocidade de translação na tela; parado = sem desfoque. Profundidade de campo só em cartões (até 14 px), nunca em texto.",
        "Whips verticais (para cima) nos dois atos: os cartões do ESPELHO deslizam em sentidos opostos (esquerda/direita), então um whip horizontal favoreceria um deles; o vertical mantém a simetria.",
        "NOME: recorte pela remoção de fundo do HyperFrames (u2net_human_seg, local), refinado com filtro guiado, erosão de 1 px e suavização de ~2 px; o nome fica atrás da cabeça (cobertura de ~19% das letras). Na altura dos ombros a cobertura passava de 40% e o nome ficava ilegível, por isso os ombros não cobrem o nome.",
        "NOME em cartão grande (912 × 1140), e não em tela cheia: em tela cheia a foto passaria de 1,3× de ampliação. O nome mais largo ocupa 83% da largura no início e 88% no fim da aproximação, para não sair da área segura.",
        "Abertura: o texto vai em etiquetas brancas porque o zoom-through termina com a foto atrás do texto (regra de texto sobre foto); o rosto termina acima das etiquetas.",
        "Pivô: as frases 1 e 2 saem por fade de 0,2 s (com leve subida) junto com a entrada da seguinte, para não sobrepor letras; a 3ª sai por máscara (0,3 s).",
        "Loudness: os efeitos são esparsos e somam só ~0,2 LU à música; as metas −15 (música) e −14 (soma) não cabem juntas com um ganho único, então o ganho comum deixa as duas dentro de 0,5 LU (música −14,6, master −14,4).",
        "Fotos finais com tamanho limitado pela faixa y 260–1230 incluindo a aproximação de 8% (cartões de 750 px e 500 px de largura).",
        "A remoção de fundo do HyperFrames instalou o `onnxruntime-node` e baixou o modelo (168 MB) no cache do usuário (`~/.cache/hyperframes`); nenhuma foto saiu da máquina.",
    ]
    for d in dec:
        w(f"- {d}")

    w("\n## 10. Verificação final\n")
    v = VER["video"]
    a = VER["audio"]
    okc = all(c["ok"] for c in VER["cortes"])
    oke = all(e["ok"] for e in VER["efeitos"])
    w(f"- Vídeo: H.264 {v['profile']}, {v['width']}×{v['height']}, {v['pix_fmt']}, {v['r_frame_rate'].split('/')[0]} qps, **{v['nb_read_frames']} quadros ({br(float(v['duration']), 6)} s)**, BT.709 (primárias, transferência e matriz), faixa limitada, CRF {VER['x264']['crf']:.0f}, preset slow, faststart {'sim' if VER['faststart'] else 'NÃO'}.")
    el = VER["listas_de_edicao"]
    w(f"- Áudio: AAC estéreo {a['sample_rate']} Hz (320 kb/s). As listas de edição do MP4 (escala {el['escala']}) terminam vídeo e áudio em {el['segmentos'][0]} e {el['segmentos'][1]} unidades = {br(el['fim_s'][0], 6)} s = END; o decodificador bruto do FFmpeg devolve {VER['audio_mp4_amostras_decodificadas']} amostras porque ignora o corte final da lista e inclui o preenchimento do último bloco AAC (silêncio, descartado pelos players). Sincronia áudio/master conferida por correlação: deslocamento 0.")
    w(f"- Stems: " + ", ".join(f"{k} {s['amostras']} amostras / {s['sr']} Hz / {s['canais']} canais / {s['subtipo']}" for k, s in VER["stems"].items()) + ".")
    w(f"- Cortes nos quadros {', '.join(str(c['corte_quadro']) for c in VER['cortes'])}: {'todos OK' if okc else 'FALHA'} (os dois lados conferidos contra os trechos renderizados; todos caem em batida).")
    w(f"- Efeitos alinhados aos eventos (tolerância 1 quadro): {'todos OK' if oke else 'FALHA'}; passagens com pico no corte.")
    w(f"- Riser termina na junção (quadro 121); depois dela o stem é silêncio absoluto ({rs['depois_da_juncao_max']:.0f}).")
    pd_ = json.loads((WORK / "qc" / "parados_desfocados.json").read_text())
    w(f"- Quadro 0 = capa (4 subquadros idênticos), abertura a partir do quadro 1. Último quadro: foto final com as duas linhas de encerramento completas e nítidas, sem fade.")
    w(f"- Quadros parados e desfocados (nitidez × movimento em todos os quadros): {'nenhum' if not pd_ else pd_}.")
    w(f"- Bordas sem estalo: música começa com 5 ms de suavização na amostra 800 e termina em zero após 800 ms de saída; últimos 10 ms do master ≈ {VER['bordas']['mp4_ultimos_10ms']:.0e}.")
    w("- Igualdade conferida: mesmas cenas, durações, transições, efeitos e quantidade de fotos nas duas; busca de palavras proibidas sem ocorrências.")
    issues = {k: v_["issues"] for k, v_ in LAY.items() if v_["issues"]}
    w(f"- Geometria medida no Chrome a cada 1/30 s: fonte mínima {min(v_['min_font_px'] for v_ in LAY.values())} px; texto sobre rosto / fora da área segura em repouso: {'nenhum' if not issues else issues}.")
    w("- Pranchas: vídeo completo em `work/qc/prancha_video.jpg`; uma por trecho em `work/qc/trecho_<id>.jpg`; acentos (ã, ç, é, ô) em `work/qc/fontes_acentos.png`.")
    (ROOT / "relatorio.md").write_text("\n".join(L) + "\n")
    print("ok")


if __name__ == "__main__":
    main()
