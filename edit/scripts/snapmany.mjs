// prévias em lote: node snapmany.mjs <outDir> id=t1,t2 id2=t1,t2 ...
import { withPage, openComp } from "./snap.mjs";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
const [out, ...specs] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
await withPage(async (browser, port) => {
  for (const spec of specs) {
    const [id, ts] = spec.split("=");
    const { page, errors } = await openComp(browser, port, id);
    for (const t of ts.split(",").map(Number)) {
      await page.evaluate((id, t) => { window.__timelines[id].totalTime(t, true); }, id, t);
      await page.screenshot({ path: join(out, `${id}_${t.toFixed(4)}.png`) });
    }
    const ev = await page.evaluate(() => window.__events);
    writeFileSync(join(out, `${id}.events.json`), JSON.stringify(ev, null, 1));
    if (errors.length) console.error("ERROS", id, errors);
    await page.close();
  }
});
