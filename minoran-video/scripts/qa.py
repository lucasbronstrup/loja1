"""QA técnico do master: especificação, loudness, emendas, congelamentos, folha de contato.

Uso: python scripts/qa.py out/minoran-institucional-1080p60.mp4
Saída: out/qa/report.json, out/qa/contact.jpg, out/qa/seams.jpg (sai com código 1 se algo reprovar)
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / "timeline.json").read_text(encoding="utf-8"))
QA = ROOT / "out" / "qa"
FF = shutil.which("ffmpeg") or "ffmpeg"
FP = shutil.which("ffprobe") or "ffprobe"


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in args], capture_output=True, text=True)


def probe(path: Path) -> dict:
    r = run([FP, "-v", "error", "-show_format", "-show_streams", "-count_frames", "-of", "json", str(path)])
    return json.loads(r.stdout)


def frame_at(path: Path, t: float, out: Path) -> Path:
    run([FF, "-v", "error", "-y", "-ss", f"{t:.4f}", "-i", str(path), "-frames:v", "1", str(out)])
    return out


def sheet(images: list[tuple[str, Path]], out: Path, cols: int = 4, w: int = 480) -> None:
    h = int(w * 9 / 16)
    rows = (len(images) + cols - 1) // cols
    s = Image.new("RGB", (cols * w, rows * (h + 22)), (20, 20, 20))
    d = ImageDraw.Draw(s)
    for i, (label, p) in enumerate(images):
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB").resize((w, h))
        x, y = (i % cols) * w, (i // cols) * (h + 22)
        s.paste(im, (x, y))
        d.text((x + 6, y + h + 4), label, fill=(230, 230, 230))
    s.save(out, quality=88)


def main(argv: list[str]) -> int:
    path = Path(argv[0]) if argv else ROOT / "out" / "minoran-institucional-1080p60.mp4"
    QA.mkdir(parents=True, exist_ok=True)
    info = probe(path)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    checks = {
        "video_codec_h264": v["codec_name"] == "h264",
        "video_profile_high": v.get("profile") == "High",
        "size_1920x1080": (v["width"], v["height"]) == (1920, 1080),
        "fps_60": v["r_frame_rate"] == "60/1",
        "frames_2520": int(v.get("nb_read_frames", 0)) == int(round(TL["duration"] * 60)),
        "pix_fmt_yuv420p": v["pix_fmt"] == "yuv420p",
        "bt709": v.get("color_primaries") == "bt709" and v.get("color_transfer") == "bt709",
        "duration_42": abs(dur - TL["duration"]) <= 1 / 60 + 1e-3,
        "audio_aac": bool(a) and a["codec_name"] == "aac",
        "audio_48k_stereo": bool(a) and a["sample_rate"] == "48000" and int(a["channels"]) == 2,
        "audio_duration": bool(a) and abs(float(a.get("duration", 0)) - TL["duration"]) <= 0.05,
    }
    # loudness (EBU R128) do master
    r = run([FF, "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"])
    m_i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    m_tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    loud = {"integrated_LUFS": float(m_i[-1]) if m_i else None, "true_peak_dBFS": float(m_tp[-1]) if m_tp else None}
    checks["loudness_youtube"] = loud["integrated_LUFS"] is not None and -16.0 <= loud["integrated_LUFS"] <= -12.0
    checks["true_peak_le_-1"] = loud["true_peak_dBFS"] is not None and loud["true_peak_dBFS"] <= -0.9
    # congelamentos (nada parado > 1.5 s): só relatório, o fim de cena pode segurar a marca
    r = run([FF, "-hide_banner", "-nostats", "-i", str(path), "-vf", "freezedetect=n=0.0008:d=1.5", "-map", "0:v", "-f", "null", "-"])
    freezes = re.findall(r"freeze_start: ([\d.]+).*?freeze_duration: ([\d.]+)", r.stderr, re.S)
    # quadros nas emendas (último antes / primeiro depois) e nos cues principais
    seams = []
    for s in TL["scenes"][1:]:
        t = s["start"]
        seams.append((f"{t - 1 / 60:.3f} fim {s['id'][:3]}-1", frame_at(path, t - 1 / 60 + 1e-4, QA / f"seam_{t:05.2f}_a.png")))
        seams.append((f"{t:.3f} início {s['id']}", frame_at(path, t + 1e-4, QA / f"seam_{t:05.2f}_b.png")))
    sheet(seams, QA / "seams.jpg", cols=4)
    mids = []
    for s in TL["scenes"]:
        for k in (0.2, 0.5, 0.85):
            t = s["start"] + k * (s["end"] - s["start"])
            mids.append((f"{t:.2f}s {s['id']}", frame_at(path, t, QA / f"f_{t:05.2f}.png")))
    sheet(mids, QA / "contact.jpg", cols=6, w=320)
    rep = {"file": str(path.relative_to(ROOT)), "size_MB": round(path.stat().st_size / 1e6, 2), "duration": dur, "video": {k: v.get(k) for k in ("codec_name", "profile", "width", "height", "r_frame_rate", "nb_read_frames", "pix_fmt", "color_primaries", "bit_rate")}, "audio": {k: a.get(k) for k in ("codec_name", "sample_rate", "channels", "duration", "bit_rate")} if a else None, "loudness": loud, "freezes": [{"start": float(x), "dur": float(y)} for x, y in freezes], "checks": checks, "ok": all(checks.values())}
    (QA / "report.json").write_text(json.dumps(rep, indent=2))
    for k, ok in checks.items():
        print(f"  {'OK ' if ok else 'FALHA'} {k}")
    print(f"  loudness {loud}  freezes>1.5s: {rep['freezes']}")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
