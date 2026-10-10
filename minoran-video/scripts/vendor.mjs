// Copia GSAP + plugins e as fontes locais para vendor/ e gera vendor/fonts/fonts.css.
// Nenhum CDN: tudo o que as cenas carregam sai daqui.
import { copyFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const nm = join(root, "node_modules");
const vendor = join(root, "vendor");
const fontsDir = join(vendor, "fonts");
mkdirSync(fontsDir, { recursive: true });

const gsapFiles = [
  "gsap.min.js",
  "SplitText.min.js",
  "CustomEase.min.js",
  "DrawSVGPlugin.min.js",
  "MorphSVGPlugin.min.js",
];
for (const f of gsapFiles) {
  const src = join(nm, "gsap", "dist", f);
  if (!existsSync(src)) throw new Error(`missing ${src}`);
  copyFileSync(src, join(vendor, f));
}

// unicode-range oficiais do Fontsource para latin e latin-ext
const RANGES = {
  latin:
    "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD",
  "latin-ext":
    "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF",
};

const faces = [];
const add = (pkg, family, slug, weight, style) => {
  for (const subset of ["latin-ext", "latin"]) {
    const file = `${slug}-${subset}-${weight}-${style}.woff2`;
    const src = join(nm, "@fontsource", pkg, "files", file);
    if (!existsSync(src)) throw new Error(`missing ${src}`);
    copyFileSync(src, join(fontsDir, file));
    faces.push(
      `@font-face {\n  font-family: "${family}";\n  font-style: ${style};\n  font-weight: ${weight};\n  font-display: block;\n  src: url("./${file}") format("woff2");\n  unicode-range: ${RANGES[subset]};\n}`,
    );
  }
};
for (const w of [300, 400, 500, 600]) add("poppins", "Poppins", "poppins", w, "normal");
add("instrument-serif", "Instrument Serif", "instrument-serif", 400, "normal");
add("instrument-serif", "Instrument Serif", "instrument-serif", 400, "italic");

writeFileSync(join(fontsDir, "fonts.css"), faces.join("\n\n") + "\n");
console.log(`vendor: ${gsapFiles.length} scripts, ${faces.length} @font-face`);
