# Relatório — homenagem a Graziela e Eduarda

## 1. Resumo

- END: quadro **2161** (exclusivo) = **36016,667 ms**
- Duração total: **2161 quadros a 60 qps = 36,017 s**
- Andamento: **120 BPM** (30 quadros por batida, 120 por compasso; 1ª batida no quadro 1)
- Tonalidade: **Ré maior** · **18 compassos**
- Entregas: `final.mp4`, `stems/music.wav`, `stems/sfx.wav`, `stems/riser.wav`, este relatório; intermediários em `work/`.

## 2. Tabela de trechos

| Quadros (início–fim excl.) | ms | Compassos | Bloco | Cena | Conteúdo | Saída |
|---|---|---|---|---|---|---|
| 0–1 | 0,000–16,667 | — | CAPA | CAPA | Título “Graziela / & Eduarda” em caixa branca; 6 cartões (3 + 3) abaixo de y = 620 | corte seco (quadro 1) |
| 1–121 | 16,667–2016,667 | 1 | ABERTURA | TIPOGRAFIA | “Duas coordenadoras” / “no coração.” + 6 cartões em parallax (3 da Graziela, 3 da Eduarda) | zoom-through com o riser |
| 121–241 | 2016,667–4016,667 | 2 | ATO 1 · Graziela | DESTAQUE | Cartão da Graziela + “Graziela,” / “bem-vinda!” | corte seco |
| 241–361 | 4016,667–6016,667 | 3 | ATO 1 · Graziela | PILHA | 3 cartões empilhados + carimbo “carinho” | corte seco |
| 361–601 | 6016,667–10016,667 | 4–5 | ATO 1 · Graziela | MOSAICO | Mosaico 2×2 + “Nossa história tá só começando.” + carimbo “gratidão” | zoom-through |
| 601–721 | 10016,667–12016,667 | 6 | ATO 1 · Graziela | NOME | GRAZIELA atrás do recorte + etiqueta “coordenadora” | whip |
| 721–1081 | 12016,667–18016,667 | 7–9 | PIVÔ | ESPELHO | Cartões espelhados + “Gostamos muito da Graziela” / “Nunca vamos esquecer a Eduarda.” / “Ninguém substitui ninguém.” + coração | corte seco |
| 1081–1201 | 18016,667–20016,667 | 10 | ATO 2 · Eduarda | DESTAQUE | Cartão da Eduarda + “Eduarda,” / “inesquecível!” | corte seco |
| 1201–1321 | 20016,667–22016,667 | 11 | ATO 2 · Eduarda | PILHA | 3 cartões empilhados + carimbo “carinho” | corte seco |
| 1321–1561 | 22016,667–26016,667 | 12–13 | ATO 2 · Eduarda | MOSAICO | Mosaico 2×2 + “Nossas memórias ficam pra sempre.” + carimbo “gratidão” | zoom-through |
| 1561–1681 | 26016,667–28016,667 | 14 | ATO 2 · Eduarda | NOME | EDUARDA atrás do recorte + etiqueta “coordenadora” | whip |
| 1681–1921 | 28016,667–32016,667 | 15–16 | FINAL | FINAL | Foto da turma 1 + “Eduarda,” / “esse momento fica com a gente.” | corte seco |
| 1921–2161 | 32016,667–36016,667 | 17–18 | FINAL | FINAL | Foto da turma 2 + confete + “Graziela, bem-vinda.” / “Eduarda, gratidão.” | fim (END) |

Fonte única: `work/trechos.json` (usada pelas composições, pela música e pelos efeitos).

## 3. Fotos

**Atribuição de quem é quem.** A pasta `drive-download-20261008T002502Z-1-001` chegou sem subpastas e com nomes do WhatsApp. A foto anexada no chat (indicada como Eduarda) é idêntica, pixel a pixel, ao arquivo `IMG-20261007-WA0086.jpg`. Pela numeração dos arquivos: o bloco contíguo `WA0086–WA0090` (mesmo envio) foi atribuído à **Eduarda**; as demais fotos individuais do mesmo dia (`WA0078`, `WA0092–WA0094`, `WA0097`) à **Graziela**; as duas fotos de grupo de outra data (`20260313`) são as fotos **finais** da turma com a Eduarda. Nenhum reconhecimento facial foi usado — a detecção de rostos (YuNet/OpenCV, local) serviu só para enquadrar. **Se a atribuição estiver trocada, basta inverter as listas em `work/selecao.json` e renderizar de novo.**

**Graziela** (4 fotos): `IMG-20261007-WA0078.jpg`, `IMG-20261007-WA0092.jpg`, `IMG-20261007-WA0094.jpg`, `IMG-20261007-WA0097.jpg`
- DESTAQUE: `IMG-20261007-WA0078.jpg` · PILHA (topo / segundo / terceiro): `IMG-20261007-WA0092.jpg` / `IMG-20261007-WA0097.jpg` / `IMG-20261007-WA0094.jpg`
- MOSAICO (TL, TR=NOME, BL, BR): `IMG-20261007-WA0078.jpg`, `IMG-20261007-WA0094.jpg`, `IMG-20261007-WA0092.jpg`, `IMG-20261007-WA0097.jpg` · NOME: `IMG-20261007-WA0094.jpg` · ESPELHO: `IMG-20261007-WA0094.jpg`
- ABERTURA/CAPA: `IMG-20261007-WA0078.jpg`, `IMG-20261007-WA0092.jpg`, `IMG-20261007-WA0097.jpg`

**Eduarda** (4 fotos): `IMG-20261007-WA0086.jpg`, `IMG-20261007-WA0087.jpg`, `IMG-20261007-WA0088.jpg`, `IMG-20261007-WA0089.jpg`
- DESTAQUE: `IMG-20261007-WA0089.jpg` · PILHA (topo / segundo / terceiro): `IMG-20261007-WA0087.jpg` / `IMG-20261007-WA0088.jpg` / `IMG-20261007-WA0086.jpg`
- MOSAICO (TL, TR=NOME, BL, BR): `IMG-20261007-WA0089.jpg`, `IMG-20261007-WA0086.jpg`, `IMG-20261007-WA0087.jpg`, `IMG-20261007-WA0088.jpg` · NOME: `IMG-20261007-WA0086.jpg` · ESPELHO: `IMG-20261007-WA0086.jpg`
- ABERTURA/CAPA: `IMG-20261007-WA0089.jpg`, `IMG-20261007-WA0087.jpg`, `IMG-20261007-WA0088.jpg`

**Fotos finais:** `IMG-20260313-WA0053.jpg` (22 rostos detectados) e `IMG-20260313-WA0054.jpg` (19 rostos detectados) — mostradas inteiras.

**Descartes:**

- `IMG-20261007-WA0078(1).jpg` — duplicata exata de IMG-20261007-WA0078.jpg (mesmo md5)
- `IMG-20261007-WA0093.jpg` — rosto desfocado/tremido (variância do Laplaciano no rosto 3,0 contra mediana 57,2 do conjunto)
- `IMG-20261007-WA0090.jpg` — excedente para igualar o número de fotos (4 por coordenadora); menor pontuação do conjunto (rosto de 56 px, nitidez do rosto 9,0)

**Igualdade:** 4 fotos para cada uma; mesma estrutura de cenas (DESTAQUE 1, PILHA 3, MOSAICO 4 com a foto do NOME, NOME), mesmas durações (5 compassos por ato), mesmas transições (corte seco, corte seco, zoom-through, whip), mesmos efeitos sonoros (impacto no pouso do DESTAQUE e na chegada do NOME, passagem no whip), mesmos tamanhos de cartão e de fonte; nome gigante no mesmo tamanho (181 px) para as duas. Com menos de 8 fotos, cada foto aparece em até duas cenas do ato, com enquadramentos diferentes (o mosaico usa recortes mais fechados); a foto do NOME é a miniatura ampliada pelo zoom-through (exceção prevista).

Pré-processamento: orientação EXIF aplicada, conversão ICC → sRGB, máximo de 2160 px (nenhuma ampliação). Recortes centrados nos rostos; nenhuma foto ampliada mais de 1,3× em repouso (NOME da Graziela: 1,18× com a aproximação de 1,06 → 1,26×).

## 4. Roteiro final dos textos

| Trecho | Texto na tela | Ajuste em relação à base |
|---|---|---|
| Capa (quadro 0) | Graziela / & Eduarda | título criado (110 px, caixa branca y 262–603) |
| Abertura | Duas / coordenadoras / no coração. | “Duas coordenadoras” não cabe em 960 px a ≥ 96 px: a 1ª linha da base foi quebrada em duas etiquetas (3 linhas no total); “coração.” em Instrument Serif itálico com as duas cores |
| Ato 1 · DESTAQUE | Graziela, / bem-vinda! | sem mudança (“bem-vinda!” em Instrument Serif itálico terracota, sublinhado à mão) |
| Ato 1 · PILHA | carinho (carimbo) | sem mudança |
| Ato 1 · MOSAICO | Nossa história / tá só começando. + carimbo “gratidão” | sem mudança (“história” em itálico) |
| Ato 1 · NOME | GRAZIELA + etiqueta “coordenadora” | sem mudança |
| Pivô · compasso 7 | Gostamos / muito / da Graziela | quebrado em 3 linhas para ocupar a mesma grade da frase seguinte (troca limpa, mesmo peso visual) |
| Pivô · compasso 8 | Nunca vamos / esquecer / a Eduarda. | sem mudança (3 linhas a 96 px) |
| Pivô · compasso 9 | Ninguém substitui / ninguém. + coração | marca-texto: “Ninguém” na faixa da Graziela, “ninguém.” na faixa da Eduarda |
| Ato 2 · DESTAQUE | Eduarda, / inesquecível! | sem mudança |
| Ato 2 · PILHA | carinho (carimbo) | sem mudança |
| Ato 2 · MOSAICO | Nossas memórias / ficam pra sempre. + carimbo “gratidão” | sem mudança (“memórias” em itálico) |
| Ato 2 · NOME | EDUARDA + etiqueta “coordenadora” | sem mudança |
| Final · foto 1 | Eduarda, / esse momento / fica com a gente. | sem mudança (3 linhas acima do cartão; “momento” em itálico, sublinhado) |
| Final · foto 2 (compasso 18) | Graziela, bem-vinda. / Eduarda, gratidão. | sem mudança (80 px, mesmo tamanho, terracota / azul-petróleo) |

Busca por palavras proibidas (nova, antiga, velha, substituta, melhor, pior) nos textos finais: **0 ocorrências**. Única exceção usada: “Ninguém substitui ninguém.”

## 5. Cenas

- **CAPA (quadro 0)** — fundo radial quase branco, caixa branca com o título e 6 cartões (3 + 3) estáticos e nítidos abaixo de y = 620.
- **TIPOGRAFIA (abertura)** — três etiquetas brancas com o texto entram no centro (máscara na batida 1, mola meia batida depois) sobre 6 cartões pequenos (3 de cada) em três camadas de parallax com 5–9 px de desfoque; nos últimos 1,2 s a câmera atravessa os cartões até o retrato da Graziela preencher a largura da tela (zoom-through com o riser).
- **DESTAQUE** — cartão flutuante de 812 px com pílula do nome; entra de 0,86 → 1 e −4° → 0° (back.out(1.4), 0,5 s) e pousa na batida 2; depois deriva. Frase acima do cartão: máscara + sublinhado desenhado.
- **PILHA** — três cartões empilhados (−4,5° a +6°); carimbo “carinho” na batida 2; na batida 3 o cartão do topo é arremessado para a direita com rotação e desfoque de movimento; o segundo cresce de 0,96 a 1.
- **MOSAICO** — 2×2 com 24 px de espaçamento; miniaturas entram em stagger de 1/4 de batida (back.out(1.6)); frase no topo; carimbo “gratidão” no centro na batida 3; nos últimos 1,5 s a câmera vai até a miniatura do NOME (power2.inOut), que termina exatamente no enquadramento do cartão do NOME.
- **NOME** — retrato em cartão grande (912 × 1140), nome gigante branco com contorno de 14 px na cor dela atrás da cabeça e o recorte da pessoa por cima; letras em stagger de 0,04 s, câmera 1 → 1,06, etiqueta “coordenadora” na batida 3 (carimbo); sai com whip vertical.
- **ESPELHO (pivô)** — cartões idênticos 720 × 440 (Graziela em cima, Eduarda embaixo) deslizando da esquerda e da direita (power3.out, 0,5 s), pílulas com as cores; três frases em sequência numa grade fixa de 3 linhas, nomes coloridos; marca-texto em “Ninguém substitui ninguém.”; coração de 134 px desenhado traço a traço na batida 3 do compasso 9 (metade terracota, metade azul-petróleo).
- **FINAL · foto 1** — foto da turma inteira num cartão largo (750 px) sobre cópia desfocada quase branca da própria foto; chega com o whip e para na batida 2; aproximação 1 → 1,08 (sine.inOut); frase acima (mola + sublinhado).
- **FINAL · foto 2** — corte seco; foto vertical inteira, recuo 1,08 → 1; confete retangular (36 peças nas duas cores, atrás do cartão) na batida 3; no compasso 18 as duas linhas de encerramento entram juntas (respiro) e ficam paradas e nítidas até END.

Transições: Abertura → Ato 1 zoom-through com riser; DESTAQUE → PILHA e PILHA → MOSAICO cortes secos; MOSAICO → NOME zoom-through; NOME → bloco seguinte whip vertical (saída 0,45 s power3.in, chegada 0,6 s power3.out, velocidade contínua de 3 500 px/s no corte); Pivô → Ato 2 e Final 1 → Final 2 cortes secos. Nenhum fade ou dissolve entre trechos.

## 6. Efeitos sonoros (stems/sfx.wav)

| Quadro | ms | Tipo | Evento (arquivo de eventos da composição) |
|---|---|---|---|
| 151 | 2516,667 | impacto | a1_destaque: cartão DESTAQUE (Graziela) |
| 601 | 10016,667 | impacto | a1_nome: nome gigante GRAZIELA |
| 721 | 12016,667 | passagem | a1_nome: whip de saída (pico no corte) |
| 751 | 12516,667 | impacto | pivo: dois cartões do ESPELHO |
| 961 | 16016,667 | sinal | pivo: Ninguém substitui ninguém. (sinal) |
| 1111 | 18516,667 | impacto | a2_destaque: cartão DESTAQUE (Eduarda) |
| 1561 | 26016,667 | impacto | a2_nome: nome gigante EDUARDA |
| 1681 | 28016,667 | passagem | a2_nome: whip de saída (pico no corte) |
| 1711 | 28516,667 | impacto | final1: foto final 1 |
| 1921 | 32016,667 | impacto | final2: foto final 2 (corte seco) |
| 1981 | 33016,667 | brilho | final2: confete retangular |
| 2041 | 34016,667 | sinal | final2: linhas de encerramento |

Picos relativos ao pico da música: impactos e sinais −9 dB, passagens −9 dB (pico no corte), brilho −12 dB; riser −10 dB. Nenhum efeito em cortes secos, derivas, aproximações, zoom-throughs ou entradas da pilha/mosaico; na junção abertura → Ato 1 soa só o riser.

## 7. Loudness (FFmpeg ebur128)

| Faixa | LUFS integrados | Pico verdadeiro (dBTP) |
|---|---|---|
| music.wav | −14,6 | −2,0 |
| sfx.wav | −22,2 | −11,0 |
| riser.wav | −25,0 | −11,9 |
| master (final.mp4) | −14,4 | −1,3 |

Ganho comum aplicado às três faixas: +0,40 dB. A soma passou do limite num único ponto (impacto da foto final 2 sobre o 1º tempo do compasso 17, pico verdadeiro da soma −0,3 dBTP); ali atuou um limitador transparente de pico verdadeiro (−1,3 dBTP, antecipação de 10 ms): 38 ms no total, redução máxima 0,96 dB em 32,035 s. Fora desse trecho o master é a soma exata dos três stems.

## 8. Música (stems/music.wav) e riser

Trilha original sintetizada com NumPy/SciPy: piano elétrico FM, pad de serras com passa-baixa, pluck aditivo, sinos FM discretos, baixo suave, bumbo macio, shaker, palmas leves e cordas macias; reverb por convolução sintética. 120 BPM, Ré maior, progressão I–V–vi–IV (um acorde por compasso), melodia simples no piano elétrico. Só entrada de 5 ms anti-estalo e saída gradual de 800 ms no fim; dinâmica pelo arranjo (sem automação de volume).

| Compasso | Acorde | Arranjo |
|---|---|---|
| 1 | Lá sus4 → Lá (V) | piano elétrico e pad esparsos + riser (stem separado) |
| 2 | Ré (I) | ritmo completo: bumbo, shaker, baixo, arpejo de pluck, piano elétrico, pad, melodia, sino discreto no 1º tempo |
| 3 | Lá (V) | ritmo completo: bumbo, shaker, baixo, arpejo de pluck, piano elétrico, pad, melodia, sino discreto no 1º tempo |
| 4 | Si menor (vi) | ritmo completo: bumbo, shaker, baixo, arpejo de pluck, piano elétrico, pad, melodia, sino discreto no 1º tempo |
| 5 | Sol (IV) | ritmo completo: bumbo, shaker, baixo, arpejo de pluck, piano elétrico, pad, melodia, sino discreto no 1º tempo |
| 6 | Ré (I) | ritmo completo: bumbo, shaker, baixo, arpejo de pluck, piano elétrico, pad, melodia, sino discreto no 1º tempo |
| 7 | Si menor (vi) | respiro: pad + piano (acordes e arpejo lento) + melodia suave |
| 8 | Sol (IV) | respiro: pad + piano + melodia suave |
| 9 | Lá sus4 → Lá (V) | respiro: pad + piano (Lá sus4 → Lá), sem ritmo |
| 10 | Ré (I) | ritmo volta igual ao Ato 1 (bumbo, shaker, baixo, piano, pad, melodia, sino) com cordas macias no lugar do pluck |
| 11 | Lá (V) | ritmo volta igual ao Ato 1 (bumbo, shaker, baixo, piano, pad, melodia, sino) com cordas macias no lugar do pluck |
| 12 | Si menor (vi) | ritmo volta igual ao Ato 1 (bumbo, shaker, baixo, piano, pad, melodia, sino) com cordas macias no lugar do pluck |
| 13 | Sol (IV) | ritmo volta igual ao Ato 1 (bumbo, shaker, baixo, piano, pad, melodia, sino) com cordas macias no lugar do pluck |
| 14 | Ré (I) | ritmo volta igual ao Ato 1 (bumbo, shaker, baixo, piano, pad, melodia, sino) com cordas macias no lugar do pluck |
| 15 | Si menor (vi) | arranjo completo e amplo: ritmo + palmas leves + pluck + cordas sustentadas + sinos dobrando a melodia |
| 16 | Sol (IV) | arranjo completo e amplo (idem) |
| 17 | Lá sus4 → Lá (V) | construção: bumbo nos 4 tempos, palmas, Lá sus4 → Lá (dominante) |
| 18 | Ré (I) | cadência resolvida no 1º tempo (Ré maior), acorde soando até a saída gradual de 800 ms |

Loudness por seção (antes do ganho comum): abertura −20,15 · Ato 1 −14,47 · pivô −18,33 · Ato 2 −14,45 · final −14,06 LUFS — os dois atos ficam iguais (diferença 0,02 LU; o ganho das cordas foi calibrado para isso).

Riser (stems/riser.wav): ruído filtrado com filtro abrindo + tom grave subindo (55 → 196 Hz), **2 s exatos**: começa na amostra 800 (quadro 1) e cresce até a junção com o Ato 1 (amostra 96 800 = quadro 121), com 4 ms anti-estalo nas pontas; última amostra audível 96798; nada depois do corte. Pico 10 dB abaixo do pico da música.

## 9. Decisões, alternativas e limitações

- Atribuição das fotos pela numeração dos arquivos + foto de referência do chat (ver seção 3); sem reconhecimento facial.
- 4 fotos por coordenadora (mínimo entre os conjuntos após descartes): `WA0093` descartada por desfoque, `WA0090` como excedente, `WA0078(1)` duplicata.
- Renderização: HyperFrames 0.8.140 (`render --fps 240 --format png-sequence`, uma composição por trecho, motor determinístico com relógio GSAP). Os 240 qps foram viáveis (~10 subquadros/s), sem precisar do modo 120 qps.
- Combinação dos 4 subquadros (FFmpeg tpad + tmix + select) com obturador “traseiro”: o quadro n é a média dos instantes n/60 − 3/240 … n/60. Assim o 1º quadro de cada trecho é o instante exato do corte (nítido) e a capa usa 4 subquadros idênticos.
- Desfoque de movimento: além da mistura de subquadros, cada elemento recebe desfoque gaussiano direcional (SVG) com sigma = 0,29 × v × 0,75 / 60 (máx. 40 px) pela velocidade de translação na tela; parado = sem desfoque. Profundidade de campo só em cartões (até 14 px), nunca em texto.
- Whips verticais (para cima) nos dois atos: os cartões do ESPELHO deslizam em sentidos opostos (esquerda/direita), então um whip horizontal favoreceria um deles; o vertical mantém a simetria.
- NOME: recorte pela remoção de fundo do HyperFrames (u2net_human_seg, local), refinado com filtro guiado, erosão de 1 px e suavização de ~2 px; o nome fica atrás da cabeça (cobertura de ~19% das letras). Na altura dos ombros a cobertura passava de 40% e o nome ficava ilegível, por isso os ombros não cobrem o nome.
- NOME em cartão grande (912 × 1140), e não em tela cheia: em tela cheia a foto passaria de 1,3× de ampliação. O nome mais largo ocupa 83% da largura no início e 88% no fim da aproximação, para não sair da área segura.
- Abertura: o texto vai em etiquetas brancas porque o zoom-through termina com a foto atrás do texto (regra de texto sobre foto); o rosto termina acima das etiquetas.
- Pivô: as frases 1 e 2 saem por fade de 0,2 s (com leve subida) junto com a entrada da seguinte, para não sobrepor letras; a 3ª sai por máscara (0,3 s).
- Loudness: os efeitos são esparsos e somam só ~0,2 LU à música; as metas −15 (música) e −14 (soma) não cabem juntas com um ganho único, então o ganho comum deixa as duas dentro de 0,5 LU (música −14,6, master −14,4).
- Fotos finais com tamanho limitado pela faixa y 260–1230 incluindo a aproximação de 8% (cartões de 750 px e 500 px de largura).
- A remoção de fundo do HyperFrames instalou o `onnxruntime-node` e baixou o modelo (168 MB) no cache do usuário (`~/.cache/hyperframes`); nenhuma foto saiu da máquina.

## 10. Verificação final

- Vídeo: H.264 High, 1080×1920, yuv420p, 60 qps, **2161 quadros (36,016667 s)**, BT.709 (primárias, transferência e matriz), faixa limitada, CRF 15, preset slow, faststart sim.
- Áudio: AAC estéreo 48000 Hz (320 kb/s). As listas de edição do MP4 (escala 48000) terminam vídeo e áudio em 1728800 e 1728800 unidades = 36,016667 s = END; o decodificador bruto do FFmpeg devolve 1729536 amostras porque ignora o corte final da lista e inclui o preenchimento do último bloco AAC (silêncio, descartado pelos players). Sincronia áudio/master conferida por correlação: deslocamento 0.
- Stems: music 1728800 amostras / 48000 Hz / 2 canais / PCM_24, sfx 1728800 amostras / 48000 Hz / 2 canais / PCM_24, riser 1728800 amostras / 48000 Hz / 2 canais / PCM_24.
- Cortes nos quadros 1, 121, 241, 361, 601, 721, 1081, 1201, 1321, 1561, 1681, 1921: todos OK (os dois lados conferidos contra os trechos renderizados; todos caem em batida).
- Efeitos alinhados aos eventos (tolerância 1 quadro): todos OK; passagens com pico no corte.
- Riser termina na junção (quadro 121); depois dela o stem é silêncio absoluto (0).
- Quadro 0 = capa (4 subquadros idênticos), abertura a partir do quadro 1. Último quadro: foto final com as duas linhas de encerramento completas e nítidas, sem fade.
- Quadros parados e desfocados (nitidez × movimento em todos os quadros): nenhum.
- Bordas sem estalo: música começa com 5 ms de suavização na amostra 800 e termina em zero após 800 ms de saída; últimos 10 ms do master ≈ 5e-07.
- Igualdade conferida: mesmas cenas, durações, transições, efeitos e quantidade de fotos nas duas; busca de palavras proibidas sem ocorrências.
- Geometria medida no Chrome a cada 1/30 s: fonte mínima 36 px; texto sobre rosto / fora da área segura em repouso: nenhum.
- Pranchas: vídeo completo em `work/qc/prancha_video.jpg`; uma por trecho em `work/qc/trecho_<id>.jpg`; acentos (ã, ç, é, ô) em `work/qc/fontes_acentos.png`.
