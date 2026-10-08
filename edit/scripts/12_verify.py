"""Verificação final de edit/final.mp4 e dos stems. Saída: edit/work/verificacao.json + pranchas em edit/work/qc/."""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
QC = WORK / "qc"
QC.mkdir(exist_ok=True)
TL = json.loads((WORK / "trechos.json").read_text())
FINAL = ROOT / "final.mp4"
SR, SPF, END = 48000, 800, TL["END_quadro"]
R = {}


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def probe():
    j = json.loads(sh(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-count_frames", "-of", "json", str(FINAL)]).stdout)
    v = [s for s in j["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in j["streams"] if s["codec_type"] == "audio"][0]
    R["video"] = {k: v.get(k) for k in ("codec_name", "profile", "width", "height", "pix_fmt", "r_frame_rate", "avg_frame_rate", "nb_read_frames", "color_space", "color_transfer", "color_primaries", "color_range", "duration")}
    R["audio"] = {k: a.get(k) for k in ("codec_name", "sample_rate", "channels", "channel_layout", "duration", "bit_rate")}
    R["formato"] = {k: j["format"].get(k) for k in ("duration", "size", "bit_rate")}
    # faststart: átomo moov antes de mdat
    head = FINAL.read_bytes()[:200000]
    R["faststart"] = head.find(b"moov") != -1 and (head.find(b"mdat") == -1 or head.find(b"moov") < head.find(b"mdat"))
    sei = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_tag_string", "-of", "csv=p=0", str(FINAL)]).stdout
    enc = subprocess.run(["sh", "-c", f"strings -n 8 '{FINAL}' | grep -m1 'crf='"], capture_output=True, text=True).stdout
    m = re.search(r"crf=([\d.]+)", enc)
    R["x264"] = {"crf": float(m.group(1)) if m else None, "preset_slow": "subme=8" in enc or "me=umh" in enc, "trecho": enc[:180]}


def frame_rgb(path, n, scale=None):
    vf = f"select=eq(n\\,{n})" + (f",scale={scale}" if scale else "")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", vf, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    w, h = (1080, 1920) if not scale else map(int, scale.split(":"))
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float64)


def psnr(a, b):
    mse = ((a - b) ** 2).mean()
    return 99.0 if mse == 0 else 10 * np.log10(255**2 / mse)


def cuts():
    """os dois lados de cada corte: quadro C-1 = último do trecho anterior; quadro C = primeiro do novo."""
    out = []
    segs = TL["trechos"]
    for a, b in zip(segs, segs[1:]):
        C = b["quadro_inicio"]
        fa = frame_rgb(FINAL, C - 1)
        fb = frame_rgb(FINAL, C)
        la = frame_rgb(WORK / "seg" / f"{a['id']}.mkv", a["quadros"] - 1)
        fb0 = frame_rgb(WORK / "seg" / f"{b['id']}.mkv", 0)
        out.append({
            "corte_quadro": C, "ms": round(C * 1000 / 60, 3), "batida": (C - 1) % 30 == 0, "de": a["id"], "para": b["id"],
            "psnr_C-1_vs_ultimo_anterior": round(psnr(fa, la), 2), "psnr_C-1_vs_primeiro_novo": round(psnr(fa, fb0), 2),
            "psnr_C_vs_primeiro_novo": round(psnr(fb, fb0), 2), "psnr_C_vs_ultimo_anterior": round(psnr(fb, la), 2),
        })
    for c in out:
        c["ok"] = c["psnr_C-1_vs_ultimo_anterior"] > c["psnr_C-1_vs_primeiro_novo"] and c["psnr_C_vs_primeiro_novo"] > c["psnr_C_vs_ultimo_anterior"] and c["batida"]
    R["cortes"] = out


def contact_sheet():
    """prancha do vídeo completo: 1 quadro a cada 12 (0,2 s)"""
    idx = list(range(0, END, 12)) + [END - 1]
    tw, th = 135, 240
    cols = 16
    rows = (len(idx) + cols - 1) // cols
    S = Image.new("RGB", (cols * (tw + 4) + 4, rows * (th + 18) + 4), (30, 30, 30))
    d = ImageDraw.Draw(S)
    f = ImageFont.load_default(size=12)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(FINAL), "-vf", f"select='not(mod(n\\,12))+eq(n\\,{END - 1})',scale={tw}:{th}", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, th, tw, 3)
    for i, n in enumerate(idx[: len(arr)]):
        x, y = 4 + (i % cols) * (tw + 4), 4 + (i // cols) * (th + 18)
        S.paste(Image.fromarray(arr[i]), (x, y + 16))
        d.text((x, y + 1), f"{n} ({n / 60:.2f}s)", fill=(220, 220, 220), font=f)
    S.save(QC / "prancha_video.jpg", quality=85)
    R["prancha"] = str((QC / "prancha_video.jpg").relative_to(ROOT))


def ebur(path, stream_sel=None):
    cmd = ["ffmpeg", "-nostats", "-i", str(path)]
    cmd += ["-filter_complex", "ebur128=peak=true", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    summ = err[err.rfind("Summary:"):]
    I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1))
    tp = re.search(r"Peak:\s+(-?[\d.inf]+) dBFS", summ)
    return {"lufs_integrado": I, "true_peak_dbtp": float(tp.group(1)) if tp else None}


def audio():
    R["loudness"] = {
        "music.wav": ebur(ROOT / "stems" / "music.wav"),
        "sfx.wav": ebur(ROOT / "stems" / "sfx.wav"),
        "riser.wav": ebur(ROOT / "stems" / "riser.wav"),
        "master (final.mp4)": ebur(FINAL),
    }
    st = {}
    for name in ("music", "sfx", "riser"):
        x, sr = sf.read(ROOT / "stems" / f"{name}.wav")
        info = sf.info(str(ROOT / "stems" / f"{name}.wav"))
        st[name] = {"amostras": len(x), "sr": sr, "canais": x.shape[1], "subtipo": info.subtype, "duracao_s": len(x) / sr,
                    "inicio_abs_max": float(np.abs(x[:8]).max()), "fim_abs_max": float(np.abs(x[-8:]).max())}
    R["stems"] = st
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", str(FINAL), "-map", "0:a:0", "-f", "f32le", "-ac", "2", "-ar", "48000", "-"], capture_output=True).stdout
    a = np.frombuffer(dec, np.float32).reshape(-1, 2)
    R["audio_mp4_amostras_decodificadas"] = len(a)
    music, _ = sf.read(ROOT / "stems" / "music.wav")
    sfx, _ = sf.read(ROOT / "stems" / "sfx.wav")
    riser, _ = sf.read(ROOT / "stems" / "riser.wav")
    # efeitos: início detectado (envelope) vs. quadro do evento
    info = json.loads((WORK / "audio_mix_info.json").read_text())
    env = np.abs(sfx).max(axis=1)
    checks = []
    for e in info["efeitos"]:
        s0 = e["amostra"]
        if e["tipo"] == "passagem":
            w = 240  # janela de 5 ms
            seg = sfx[s0 - 24000 : s0 + 24000]
            rms = np.sqrt(np.convolve((seg**2).mean(axis=1), np.ones(w) / w, mode="same"))
            pk = int(np.argmax(rms)) - 24000
            checks.append({**e, "pico_rel_amostras": pk, "pico_rel_quadros": round(pk / SPF, 3), "ok": abs(pk) <= SPF})
        else:
            win = env[s0 - 4000 : s0 + 4000]
            thr = 0.05 * win.max()
            on = int(np.argmax(win > thr)) - 4000
            checks.append({**e, "inicio_rel_amostras": on, "inicio_rel_quadros": round(on / SPF, 3), "ok": abs(on) <= SPF})
    R["efeitos"] = checks
    # riser termina na junção (quadro 121)
    nz = np.flatnonzero(np.abs(riser).max(axis=1) > 1e-6)
    j = 121 * SPF
    R["riser"] = {"primeira_amostra": int(nz[0]), "ultima_amostra": int(nz[-1]), "juncao_amostra": j,
                  "duracao_s": round((nz[-1] + 1 - nz[0]) / SR, 4), "energia_ultimos_20ms_db": round(20 * np.log10(np.sqrt((riser[j - 960 : j] ** 2).mean()) + 1e-12), 1),
                  "depois_da_juncao_max": float(np.abs(riser[j:]).max())}
    # batidas da música coincidem com os cortes (onsets do bumbo / ataques nos tempos)
    low = np.abs(music).max(axis=1)
    beats = []
    for c in TL["cortes"][:-1]:
        s = c * SPF
        pre = np.sqrt((music[s - 2400 : s - 240] ** 2).mean())
        post = np.sqrt((music[s : s + 2160] ** 2).mean())
        beats.append({"corte": c, "ataque_db": round(20 * np.log10((post + 1e-12) / (pre + 1e-12)), 2)})
    R["musica_nos_cortes"] = beats
    # nada soando depois de END / estalos nas bordas
    R["bordas"] = {"music_ultimas_amostras": float(np.abs(music[-480:]).max()), "music_primeiras_800": float(np.abs(music[:800]).max()),
                   "mp4_ultimos_10ms": float(np.abs(a[-480:]).max()) if len(a) else None}


def words():
    txt = ""
    for f in sorted((WORK / "hf").rglob("*.js")) + sorted((WORK / "hf" / "compositions").glob("*.html")) + [ROOT / "scripts" / "06_build_comps.mjs"]:
        if f.name in ("gsap.min.js", "data.js"):
            continue
        txt += f.read_text()
    vis = re.findall(r'\{ t: "([^"]+)"', txt) + re.findall(r'\["([^"]+)", [GE]\.text\]', txt)
    bad = [w for w in vis if re.search(r"\b(nova|antiga|velha|substituta|melhor|pior)\b", w, re.I)]
    R["palavras_proibidas"] = {"textos_verificados": sorted(set(vis)), "ocorrencias": bad}


def main():
    probe()
    cuts()
    contact_sheet()
    audio()
    words()
    (WORK / "verificacao.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps({k: R[k] for k in ("video", "audio", "faststart", "x264", "loudness", "audio_mp4_amostras_decodificadas", "riser", "bordas", "palavras_proibidas")}, indent=1, ensure_ascii=False))
    for c in R["cortes"]:
        print("corte", c["corte_quadro"], c["de"], "->", c["para"], "ok" if c["ok"] else "FALHA", c["psnr_C-1_vs_ultimo_anterior"], c["psnr_C_vs_primeiro_novo"])
    for e in R["efeitos"]:
        print("efeito", e["tipo"], e["quadro"], "ok" if e["ok"] else "FALHA", e.get("inicio_rel_quadros", e.get("pico_rel_quadros")))
    for b in R["musica_nos_cortes"]:
        print("música no corte", b)


if __name__ == "__main__":
    main()
