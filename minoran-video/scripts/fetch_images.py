"""Baixa as fotos de minoran.com em alta resolução para assets/src/.

Base: https://minoran.com/cdn/shop/files/<nome>?width=3200
Cada entrada tem um nome curto (chave usada no resto do pipeline) e uma lista
de candidatos; o primeiro que responder 200 com imagem válida vence.
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "src"
FILES = "https://minoran.com/cdn/shop/files/"
ARTICLES = "https://minoran.com/cdn/shop/articles/"
W = "?width=3200"

IMAGES: dict[str, list[str]] = {
    "hero": [FILES + "minoran-studio-11-hero.webp"],
    "story_home": [FILES + "minoran-studio-11-story-home.webp"],
    "apres": [FILES + "minoran-studio-11-story-product.webp"],
    "avant": [FILES + "minoran-studio-20-before.webp"],
    "rect_argentee_34": [
        FILES + "montre-rectangulaire-femme-argentee-minoran-9093-trois-quarts_423a9189-2ec7-423f-95f6-9298a2f2591a.webp",
        FILES + "montre-rectangulaire-femme-argentee-minoran-9093-trois-quarts.webp",
    ],
    "sil_creme": [FILES + "montre-femme-creme-silicone-minoran-nf6111-face.webp"],
    "sil_rose": [FILES + "montre-femme-rose-silicone-minoran-nf6111-face.webp"],
    "sil_noir_or": [FILES + "montre-femme-noir-dore-silicone-minoran-nf6111-face.webp"],
    "sil_bleu_clair": [FILES + "montre-femme-minoran-nf6108-bleu-clair-argente-vue-principale.webp"],
    "sil_nude": [FILES + "montre-femme-minoran-nf6108-nude-dore-vue-principale.webp"],
    "sil_peche": [FILES + "montre-femme-minoran-nf6108-peche-argente-vue-principale.webp"],
    "nf5075_noir": [FILES + "montre-femme-minoran-nf5075-argentee-noir-vue-principale.webp"],
    "doree_noir_9093": [ARTICLES + "minoran-9093-doree-cadran-noir.webp"],
    # coleções (/collections/montres-femme-rectangulaires, -dorees, -vertes)
    "rect_argentee_bleu": [FILES + "montre-femme-argentee-cadran-bleu-minoran-9093-face.webp"],
    "doree_blanc": [
        FILES + "curren-9115-montre-femme-doree-cadran-blanc-vue-principale.webp",
    ],
    "doree_vert": [FILES + "montre-femme-9093-doree-vert-vue-principale.webp"],
}


def fetch(url: str) -> bytes:
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "minoran-video-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}
    failed = []
    for key, candidates in IMAGES.items():
        dst = OUT / f"{key}.webp"
        ok = False
        for base in candidates:
            url = base + W
            try:
                data = fetch(url)
                im = Image.open(io.BytesIO(data))
                im.load()
            except Exception as e:  # noqa: BLE001
                print(f"  ! {key}: {url} -> {e}")
                continue
            dst.write_bytes(data)
            manifest[key] = {"url": url, "file": dst.name, "size": list(im.size), "mode": im.mode}
            print(f"  ok {key:20s} {im.size[0]}x{im.size[1]}  {base.split('/')[-1]}")
            ok = True
            break
        if not ok:
            failed.append(key)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    if failed:
        print("FAILED:", failed)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
