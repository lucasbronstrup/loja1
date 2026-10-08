"""Prancha de quadros: sheet.py out.jpg cols thumbW img1 [img2 ...] (rótulo = nome do arquivo)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    out, cols, tw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    files = sys.argv[4:]
    th = round(tw * 1920 / 1080)
    rows = (len(files) + cols - 1) // cols
    S = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 30) + 8), (40, 40, 40))
    d = ImageDraw.Draw(S)
    font = ImageFont.load_default(size=16)
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB").resize((tw, th), Image.LANCZOS)
        x = 8 + (i % cols) * (tw + 8)
        y = 8 + (i // cols) * (th + 30)
        S.paste(im, (x, y + 22))
        d.text((x, y + 2), Path(f).stem[-28:], fill=(255, 255, 255), font=font)
    S.save(out, quality=88)


if __name__ == "__main__":
    main()
