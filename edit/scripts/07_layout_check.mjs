// Geometria real (Chrome) de rostos e textos em cada composição, a cada 1/30 s,
// e exportação dos eventos de cada composição (edit/work/events/<id>.json).
import { withPage, openComp } from "./snap.mjs";
import { mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const WORK = join(ROOT, "work");
const tl = JSON.parse(readFileSync(join(WORK, "trechos.json"), "utf8"));
mkdirSync(join(WORK, "events"), { recursive: true });
mkdirSync(join(WORK, "layout"), { recursive: true });
const only = process.argv.slice(2);

await withPage(async (browser, port) => {
  for (const seg of tl.trechos) {
    if (only.length && !only.includes(seg.id)) continue;
    const { page, errors } = await openComp(browser, port, seg.id);
    const D = seg.id === "capa" ? 0 : seg.quadros / tl.fps;
    const times = [];
    for (let f = 0; f <= Math.round(D * 60); f += 2) times.push(Math.min(f / 60, D - 1 / 240));
    if (seg.id === "capa") times.splice(0, times.length, 0);
    const dbg = await page.evaluate((ts) => ts.map((t) => window.SCENES.debugAt(window.__engine, t)), times);
    writeFileSync(join(WORK, "layout", `${seg.id}.json`), JSON.stringify(dbg));
    const ev = await page.evaluate(() => window.__events);
    const glob = ev.map((e) => ({
      ...e,
      local_s: e.t,
      quadro: seg.quadro_inicio + e.t * tl.fps,
      ms: ((seg.quadro_inicio + e.t * tl.fps) * 1000) / tl.fps,
      trecho: seg.id,
    }));
    writeFileSync(join(WORK, "events", `${seg.id}.json`), JSON.stringify(glob, null, 1));
    if (errors.length) console.error("ERROS", seg.id, errors.slice(0, 3));
    console.log(seg.id, "amostras", times.length, "eventos", ev.length);
    await page.close();
  }
});
