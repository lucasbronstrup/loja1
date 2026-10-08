// Prévia rápida: serve edit/work/hf, carrega uma composição, busca tempos e salva PNGs.
// Também exporta eventos (window.__events) e geometria de rostos/textos (verificação).
// uso: node snap.mjs <id> <t1,t2,...> <outDir> [--events] [--debug t1,t2,...]
import http from "node:http";
import { readFileSync, existsSync, mkdirSync, writeFileSync, statSync } from "node:fs";
import { join, extname, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const HF = join(ROOT, "work", "hf");
const CHROME = process.env.CHROME || "/root/.cache/puppeteer/chrome-headless-shell/linux-152.0.7977.42/chrome-headless-shell-linux64/chrome-headless-shell";
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".png": "image/png", ".jpg": "image/jpeg", ".woff2": "font/woff2", ".json": "application/json" };

export async function withPage(fn) {
  const server = http.createServer((req, res) => {
    const p = join(HF, decodeURIComponent(req.url.split("?")[0]));
    if (!p.startsWith(HF) || !existsSync(p) || statSync(p).isDirectory()) {
      res.writeHead(404);
      return res.end();
    }
    res.writeHead(200, { "Content-Type": MIME[extname(p)] || "application/octet-stream" });
    res.end(readFileSync(p));
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ["--no-sandbox", "--force-color-profile=srgb", "--font-render-hinting=none", "--hide-scrollbars"] });
  try {
    return await fn(browser, port);
  } finally {
    await browser.close();
    server.close();
  }
}

export async function openComp(browser, port, id) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", (e) => { errors.push(String(e)); console.error("PAGEERROR", String(e)); });
  page.on("console", (m) => {
    if (m.type() === "error") { errors.push(m.text()); console.error("CONSOLE", m.text()); }
  });
  await page.evaluateOnNewDocument(() => {
    window.__timelines = {};
  });
  await page.goto(`http://127.0.0.1:${port}/compositions/${id}.html`, { waitUntil: "load" });
  await page.waitForFunction((id) => !!(window.__timelines && window.__timelines[id] && window.__engine), { timeout: 30000, polling: 100 }, id);
  return { page, errors };
}

async function main() {
  const [id, times, out, ...rest] = process.argv.slice(2);
  const wantEvents = rest.includes("--events");
  const di = rest.indexOf("--debug");
  const debugTimes = di >= 0 ? rest[di + 1].split(",").map(Number) : [];
  mkdirSync(out, { recursive: true });
  await withPage(async (browser, port) => {
    const { page, errors } = await openComp(browser, port, id);
    for (const t of times ? times.split(",").filter(Boolean).map(Number) : []) {
      await page.evaluate((id, t) => { window.__timelines[id].totalTime(t, true); }, id, t);
      await page.screenshot({ path: join(out, `${id}_${t.toFixed(4)}.png`) });
    }
    if (wantEvents) {
      const ev = await page.evaluate(() => window.__events);
      writeFileSync(join(out, `${id}.events.json`), JSON.stringify(ev, null, 1));
    }
    if (debugTimes.length) {
      const dbg = await page.evaluate((ts) => ts.map((t) => window.SCENES.debugAt(window.__engine, t)), debugTimes);
      writeFileSync(join(out, `${id}.debug.json`), JSON.stringify(dbg));
    }
    if (errors.length) console.error("ERROS", id, errors);
  });
}

if (process.argv[1] && process.argv[1].endsWith("snap.mjs")) main();
