# Minoran — vídeo institucional (42 s · 1920×1080 · 60 qps)

Entrega: `out/minoran-institucional-1080p60.mp4` (H.264 High, AAC 48 kHz estéreo).

```bash
npm i                                   # gsap + fontes (local, sem CDN) + hyperframes 0.8.143
python -m venv .venv && .venv/bin/python -m pip install numpy scipy "opencv-python==4.14.0.94" pillow
npx hyperframes browser ensure          # Chrome headless do render
.venv/bin/python build.py all           # assets → audio → check → render (240 qps) → master → qa
```

Subcomandos de `build.py`: `assets`, `audio`, `check`, `draft`, `render`, `master`, `qa`, `all`
(e `snap <cena> <t1,t2,…>` para snapshots de uma cena).

- `timeline.json` é a fonte única de tempos (cenas, cues de áudio, cues visuais, transições);
  `build.py` gera `shared/timeline.js` e `scripts/audio.py` sintetiza trilha e SFX a partir dele.
- Cada cena (`sNN-*.html`, na raiz) é renderizada isolada a 240 qps; o master concatena,
  faz a média de 4 subquadros (motion blur real) → 60 qps e aplica bloom, vinheta e grão no FFmpeg.
- `index.html` só serve para revisão (monta as 8 cenas + `audio/master.wav`).
- OpenCV 4.14 é fixado: o pacote 5.x removeu `CascadeClassifier` (Haar) do build principal.
