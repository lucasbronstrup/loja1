// Gera edit/work/hf/assets/data.js e uma composição HyperFrames por trecho (compositions/<id>.html).
import { readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const WORK = join(ROOT, "work");
const HF = join(WORK, "hf");
const sel = JSON.parse(readFileSync(join(WORK, "selecao.json"), "utf8"));
const nome = JSON.parse(readFileSync(join(WORK, "nome_layout.json"), "utf8"));
const tl = JSON.parse(readFileSync(join(WORK, "trechos.json"), "utf8"));

const photos = {};
for (const [pid, p] of Object.entries(sel.photos)) {
  photos[pid] = { src: `../assets/photos/${pid}.jpg`, size: p.size, file: p.file };
  if (existsSync(join(HF, "assets/photos", `${pid}_cut.png`))) photos[pid].cut = `../assets/photos/${pid}_cut.png`;
}
const co = {};
const plan = {};
for (const [k, v] of Object.entries(sel.coordenadoras)) {
  co[k] = { name: v.name, fill: v.fill, text: v.text, band: v.band };
  plan[k] = v.plano;
}
const IW = 912, IH = 1140;
const data = {
  photos,
  crops: sel.crops,
  co,
  plan,
  finais: sel.finais.map((f) => f.id),
  nome: { ...nome, inner_w: IW, inner_h: IH, card_outer_w: IW + (2 * IW * 0.02) / 0.96 },
  timeline: tl,
};
writeFileSync(join(HF, "assets/data.js"), `window.DATA = ${JSON.stringify(data)};\n`);

const G = co.graziela, E = co.eduarda;
const CALLS = {
  capa: "S.capa(eng)",
  abertura: "S.abertura(eng)",
  a1_destaque: `S.destaque(eng, "graziela", { word: "bem-vinda!" })`,
  a1_pilha: `S.pilha(eng, "graziela")`,
  a1_mosaico: `S.mosaico(eng, "graziela", { lines: [[{ t: "Nossa" }, { t: "história", serif: true, color: "${G.text}" }], [{ t: "tá" }, { t: "só" }, { t: "começando." }]] })`,
  a1_nome: `S.nome(eng, "graziela")`,
  pivo: "S.espelho(eng)",
  a2_destaque: `S.destaque(eng, "eduarda", { word: "inesquecível!" })`,
  a2_pilha: `S.pilha(eng, "eduarda")`,
  a2_mosaico: `S.mosaico(eng, "eduarda", { lines: [[{ t: "Nossas" }, { t: "memórias", serif: true, color: "${E.text}" }], [{ t: "ficam" }, { t: "pra" }, { t: "sempre." }]] })`,
  a2_nome: `S.nome(eng, "eduarda")`,
  final1: "S.final1(eng)",
  final2: "S.final2(eng)",
};
const BG = { final1: `SCENES.bgPhoto(root, DATA.finais[0])`, final2: `SCENES.bgPhoto(root, DATA.finais[1])` };

mkdirSync(join(HF, "compositions"), { recursive: true });
for (const seg of tl.trechos) {
  const id = seg.id;
  // capa: composição estática (4 subquadros idênticos usados no quadro 0)
  const dur = id === "capa" ? 0.05 : seg.quadros / tl.fps;
  const html = `<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>${id} · ${seg.cena}</title>
    <style>
      @font-face { font-family: "Poppins"; font-style: normal; font-weight: 700; font-display: block; src: url("../assets/fonts/poppins-latin-700-normal.woff2") format("woff2"); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; }
      @font-face { font-family: "Poppins"; font-style: normal; font-weight: 700; font-display: block; src: url("../assets/fonts/poppins-latin-ext-700-normal.woff2") format("woff2"); unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF; }
      @font-face { font-family: "Instrument Serif"; font-style: italic; font-weight: 400; font-display: block; src: url("../assets/fonts/instrument-serif-latin-400-italic.woff2") format("woff2"); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; }
      @font-face { font-family: "Instrument Serif"; font-style: italic; font-weight: 400; font-display: block; src: url("../assets/fonts/instrument-serif-latin-ext-400-italic.woff2") format("woff2"); unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF; }
      * { box-sizing: border-box; margin: 0; padding: 0; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: #f3f3f0; }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; font-family: "Poppins", sans-serif; -webkit-font-smoothing: antialiased; text-rendering: geometricPrecision; }
      .stage { position: absolute; inset: 0; }
      svg.defs { position: absolute; width: 0; height: 0; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="${id}" data-start="0" data-width="1080" data-height="1920" data-duration="${dur}">
      <svg class="defs" aria-hidden="true"><defs></defs></svg>
      <div class="stage"></div>
    </div>
    <script src="../assets/gsap.min.js"></script>
    <script src="../assets/data.js"></script>
    <script src="../assets/engine.js"></script>
    <script src="../assets/scenes.js"></script>
    <script>
      (async () => {
        const root = document.getElementById("root");
        await Promise.all([
          document.fonts.load('700 96px "Poppins"', "ãçéôÁÉ"),
          document.fonts.load('italic 400 96px "Instrument Serif"', "ãçéô"),
        ]);
        await document.fonts.ready;
        ${BG[id] || "SCENES.bgRadial(root)"};
        const eng = new HF.Engine(root, ${dur});
        const S = SCENES.S;
        ${CALLS[id]};
        await Promise.all([...root.querySelectorAll("img")].map((i) => (i.decode ? i.decode().catch(() => {}) : null)));
        window.__timelines["${id}"] = eng.timeline();
      })();
    </script>
  </body>
</html>
`;
  writeFileSync(join(HF, "compositions", `${id}.html`), html);
}
console.log("ok", tl.trechos.map((s) => s.id).join(", "));
