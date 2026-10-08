"""Une os trechos (cortes secos nos quadros exatos) e exporta edit/final.mp4.

Vídeo: H.264 High, yuv420p, BT.709, CRF 15, preset slow, 1080x1920, 60 qps, faststart.
Áudio: master (soma dos 3 stems) em AAC estéreo 48 kHz.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
TL = json.loads((WORK / "trechos.json").read_text())


def run(cmd):
    print("$", " ".join(cmd)[:240], flush=True)
    subprocess.run(cmd, check=True)


def frames(path):
    return int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout.strip())


def main():
    lst = WORK / "concat.txt"
    lines = []
    total = 0
    for seg in TL["trechos"]:
        p = WORK / "seg" / f"{seg['id']}.mkv"
        n = frames(p)
        assert n == seg["quadros"], (seg["id"], n)
        total += n
        lines.append(f"file '{p}'")
    lst.write_text("\n".join(lines) + "\n")
    assert total == TL["END_quadro"] == 2161
    joined = WORK / "video_60.mkv"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
    assert frames(joined) == 2161
    out = ROOT / "final.mp4"
    run([
        "ffmpeg", "-v", "error", "-y", "-i", str(joined), "-i", str(WORK / "master.wav"),
        "-map", "0:v:0", "-map", "1:a:0",
        "-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=lanczos+accurate_rnd+full_chroma_int,format=yuv420p",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p",
        "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709:range=tv",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
        "-r", "60", "-fps_mode", "cfr", "-frames:v", "2161",
        "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2",
        # escala de tempo 48 000: as listas de edição de vídeo e áudio terminam exatamente em END (1 728 800 amostras)
        "-movie_timescale", "48000", "-movflags", "+faststart", str(out),
    ])
    print("ok", out)


if __name__ == "__main__":
    main()
