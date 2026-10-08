"""Renderiza cada composição no HyperFrames a 240 qps (PNG) e combina grupos de 4 subquadros em 60 qps.

Combinação (mistura temporal no FFmpeg, obturador "traseiro"): o quadro n do trecho é a média dos
subquadros nos tempos n/60 - 3/240 ... n/60 (limitados ao início do trecho), ou seja,
tpad (3 clones do 1º subquadro) -> tmix=4 -> mantém 1 de cada 4. Assim o 1º quadro após cada junção
mostra exatamente o tempo 0 do trecho (nítido), e os 4 subquadros da capa são idênticos.
Saída: edit/work/seg/<id>.mkv (FFV1 RGB sem perdas, 60 qps, número exato de quadros).
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
HF = WORK / "hf"
FR = WORK / "frames"
SEG = WORK / "seg"
TL = json.loads((WORK / "trechos.json").read_text())
HFBIN = str(ROOT / "node_modules/.bin/hyperframes")


def run(cmd, **kw):
    print("$", " ".join(cmd)[:220], flush=True)
    return subprocess.run(cmd, check=True, **kw)


def count_frames(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return int(out)


def render(seg):
    sid = seg["id"]
    out = FR / sid
    if out.exists():
        shutil.rmtree(out)
    t0 = time.time()
    log = WORK / "logs" / f"render_{sid}.log"
    log.parent.mkdir(exist_ok=True)
    with open(log, "w") as fh:
        run([HFBIN, "render", "-c", f"compositions/{sid}.html", "--fps", "240", "--workers", "4", "--format", "png-sequence", "-o", str(out), "--quiet"],
            cwd=HF, stdout=fh, stderr=subprocess.STDOUT)
    pngs = sorted(out.glob("*.png"))
    print(f"  {sid}: {len(pngs)} subquadros em {time.time() - t0:.0f}s", flush=True)
    return out, pngs


def combine(seg, out, pngs):
    sid = seg["id"]
    SEG.mkdir(exist_ok=True)
    dst = SEG / f"{sid}.mkv"
    n_out = seg["quadros"]
    first = pngs[0].name
    pattern = str(out / first.replace(first.split("_")[-1].split(".")[0], "%06d"))
    start = int(first.split("_")[-1].split(".")[0])
    if sid == "capa":
        # quadro 0: os 4 subquadros são a capa idêntica (composição estática)
        vf = "tmix=frames=4:weights='1 1 1 1',select='eq(n\\,3)',setpts=N/(60*TB)"
        frames_in = ["-frames:v", "4"]
    else:
        vf = "tpad=start=3:start_mode=clone,tmix=frames=4:weights='1 1 1 1',select='eq(mod(n\\,4)\\,3)',setpts=N/(60*TB)"
        frames_in = []
    run(["ffmpeg", "-v", "error", "-y", "-framerate", "240", "-start_number", str(start), "-i", pattern, *frames_in,
         "-vf", vf, "-fps_mode", "cfr", "-r", "60", "-frames:v", str(n_out), "-c:v", "ffv1", "-level", "3", "-pix_fmt", "bgr0", str(dst)])
    n = count_frames(dst)
    assert n == n_out, f"{sid}: {n} quadros, esperado {n_out}"
    print(f"  {sid}: {n} quadros a 60 qps OK", flush=True)
    return dst


def main():
    only = sys.argv[1:]
    for seg in TL["trechos"]:
        if only and seg["id"] not in only:
            continue
        out, pngs = render(seg)
        expected = 12 if seg["id"] == "capa" else seg["quadros"] * 4
        assert len(pngs) == expected, f"{seg['id']}: {len(pngs)} subquadros, esperado {expected}"
        combine(seg, out, pngs)
        # guarda alguns subquadros para inspeção e apaga o resto (disco)
        keep = WORK / "subframes_sample" / seg["id"]
        keep.mkdir(parents=True, exist_ok=True)
        for p in pngs[:: max(1, len(pngs) // 8)]:
            shutil.copy(p, keep / p.name)
        shutil.rmtree(out)


if __name__ == "__main__":
    main()
