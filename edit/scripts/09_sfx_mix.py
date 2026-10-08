"""Efeitos sonoros (a partir dos eventos exportados pelas composições) e mixagem.

Regras: impacto abafado (pousos de DESTAQUE, chegada do NOME, ESPELHO, finais), passagens só nos 2 whips
(pico no corte), sinal de duas notas 2x, brilho no confete. Picos relativos ao pico da música:
impactos/sinais -9 dB, passagens -9 dB, brilho -12 dB; riser -10 dB (já calibrado em 05_music.py).
Master = soma simples dos 3 stems; um único ganho comum leva a soma a ~-14 LUFS.
"""
import glob
import json
import subprocess

import numpy as np

from audiolib import (
    END_SAMPLES, ROOT, SR, SPF, WORK, bandpass, highpass, lowpass, lufs, peak_db, true_peak_db, write_wav,
)

N = END_SAMPLES
RNG = np.random.default_rng(777)
STEMS = ROOT / "stems"


def impact():
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = 46 + 58 * np.exp(-t / 0.05)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    thump = lowpass(RNG.standard_normal(n), 280) * np.exp(-t / 0.028) * 2.2
    x = (body + thump) * np.clip(t / 0.003, 0, 1)
    x = lowpass(x, 850, order=4)
    return np.stack([x, x], axis=1)


def whoosh(variant):
    """passagem de ruído filtrado: sobe até o corte (pico) e cai depois. Retorna (sinal, índice do pico)."""
    pre, post = 0.46, 0.34
    n_pre, n_post = int(pre * SR), int(post * SR)
    n = n_pre + n_post
    t = (np.arange(n) - n_pre) / SR  # 0 no corte
    noise = RNG.standard_normal((n, 2))
    lo, hi, end = (420, 2600, 650) if variant == 0 else (300, 1900, 480)
    # centro do filtro: sobe até o corte, desce depois (processado em blocos)
    from scipy import signal as sg

    out = np.zeros((n, 2))
    blk = 256
    zi = None
    for i in range(0, n, blk):
        tt = t[min(i + blk // 2, n - 1)]
        if tt < 0:
            fc = lo * (hi / lo) ** ((1 + tt / pre) ** 2.2)
        else:
            fc = hi * (end / hi) ** ((tt / post) ** 0.7)
        sos = sg.butter(2, [fc * 0.6, fc * 1.5], "band", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2, 2))
        seg, zi = sg.sosfilt(sos, noise[i : i + blk], axis=0, zi=zi)
        out[i : i + blk] = seg
    env = np.where(t < 0, (1 + t / pre) ** 3.2, np.exp(-t / (0.07 if variant == 0 else 0.09)))
    env *= np.clip((t + pre) / 0.01, 0, 1)
    # panorâmica em movimento (variação diferente em cada whip)
    p = np.clip(t / (pre + post) * 2.2, -1, 1) * (0.55 if variant == 0 else -0.45)
    th = (p + 1) * np.pi / 4
    out[:, 0] *= np.cos(th) * env * np.sqrt(2)
    out[:, 1] *= np.sin(th) * env * np.sqrt(2)
    return highpass(out, 150), n_pre


def chime():
    notes = [(81, 0.0), (86, 0.12)]  # Lá5 -> Ré6 (dentro do acorde nos dois pontos)
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for m, off in notes:
        f = 440 * 2 ** ((m - 69) / 12)
        tt = np.maximum(t - off, 0)
        on = (t >= off).astype(float)
        idx = 0.6 * np.exp(-tt / 0.25)
        tone = np.sin(2 * np.pi * f * tt + idx * np.sin(2 * np.pi * 2 * f * tt))
        tone += 0.18 * np.sin(2 * np.pi * 3 * f * tt) * np.exp(-tt / 0.2)
        x += tone * np.exp(-tt / 0.55) * np.clip(tt / 0.003, 0, 1) * on
    x = lowpass(x, 5000)
    return np.stack([x * 0.95, x], axis=1)


def sparkle():
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    x = np.zeros((n, 2))
    pitches = [2093, 2637, 3136, 2349, 2794, 3520, 2489]
    for i, f in enumerate(pitches):
        off = 0.018 * i + RNG.uniform(0, 0.01)
        tt = np.maximum(t - off, 0)
        ping = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.07) * (t >= off) * np.clip(tt / 0.002, 0, 1)
        pan = -0.6 + 1.2 * (i / (len(pitches) - 1))
        th = (pan + 1) * np.pi / 4
        x[:, 0] += ping * np.cos(th)
        x[:, 1] += ping * np.sin(th)
    air = bandpass(RNG.standard_normal((n, 2)), 3500, 7000) * (np.exp(-t / 0.12) * np.clip(t / 0.01, 0, 1))[:, None] * 0.35
    return lowpass(x + air, 7500)


def tp_limiter(x, thr_db=-1.3, win_ms=10):
    """Limitador de pico verdadeiro transparente, só onde a soma passa do limite:
    ganho requerido medido com sobreamostragem 4x, mínimo móvel (antecipação) e suavização Hann."""
    from scipy import signal as sg
    from scipy.ndimage import minimum_filter1d

    thr = 10 ** (thr_db / 20)
    up = sg.resample_poly(x, 4, 1, axis=0)
    env = np.abs(up).max(axis=1)
    env = env[: len(x) * 4].reshape(-1, 4).max(axis=1)
    req = np.minimum(1.0, thr / np.maximum(env, 1e-9))
    if req.min() >= 1.0:
        return x.copy(), {"ativado": False}
    W = int(win_ms * SR / 1000)
    gmin = minimum_filter1d(req, size=2 * W + 1, mode="nearest")
    win = np.hanning(2 * W + 1)
    win /= win.sum()
    gs = 1 - np.convolve(1 - gmin, win, mode="same")
    gs = np.minimum(gs, gmin + 0.0)  # nunca acima do mínimo exigido na janela
    y = x * gs[:, None]
    active = gs < 0.9999
    return y, {
        "ativado": True,
        "limiar_dbtp": thr_db,
        "reducao_max_db": round(float(-20 * np.log10(gs.min())), 2),
        "tempo_ativo_ms": round(float(active.sum() / SR * 1000), 1),
        "trechos_s": [round(float(i / SR), 3) for i in np.flatnonzero(np.diff(active.astype(int)) == 1)],
    }


def place(buf, x, at):
    a = max(0, at)
    xs = x[a - at :]
    m = min(len(xs), N - a)
    if m > 0:
        buf[a : a + m] += xs[:m]


def main():
    events = []
    for f in sorted(glob.glob(str(WORK / "events" / "*.json"))):
        events += json.loads(open(f).read())
    events.sort(key=lambda e: e["quadro"])
    music = np.load(WORK / "music_raw.npy").astype(np.float64)
    riser = np.load(WORK / "riser_raw.npy").astype(np.float64)
    pm = np.abs(music).max()
    ref = {"impacto": pm * 10 ** (-9 / 20), "passagem": pm * 10 ** (-9 / 20), "sinal": pm * 10 ** (-9 / 20), "brilho": pm * 10 ** (-12 / 20)}

    sfx = np.zeros((N, 2))
    placed = []
    whip_i = 0
    used_beats = set()
    for e in events:
        kind = None
        if e["type"] in ("pouso", "nome"):
            kind = "impacto"
        elif e["type"] == "whip":
            kind = "passagem"
        elif e["type"] == "frase-chave" and ("(sinal)" in e["label"] or "encerramento" in e["label"]):
            kind = "sinal"
        elif e["type"] == "confete":
            kind = "brilho"
        if not kind:
            continue
        s0 = int(round(e["quadro"] * SPF))
        beat = round((e["quadro"] - 1) / 30, 3)
        assert beat not in used_beats, f"dois efeitos na mesma batida: {e}"
        used_beats.add(beat)
        if kind == "impacto":
            x = impact()
            x *= ref[kind] / np.abs(x).max()
            place(sfx, x, s0)
        elif kind == "passagem":
            x, ipk = whoosh(whip_i)
            whip_i += 1
            x *= ref[kind] / np.abs(x).max()
            place(sfx, x, s0 - ipk)
        elif kind == "sinal":
            x = chime()
            x *= ref[kind] / np.abs(x).max()
            place(sfx, x, s0)
        else:
            x = sparkle()
            x *= ref[kind] / np.abs(x).max()
            place(sfx, x, s0)
        placed.append({"tipo": kind, "evento": e["type"], "rotulo": e["label"], "trecho": e["trecho"], "quadro": e["quadro"], "ms": round(e["ms"], 3), "amostra": s0})

    # Ganho comum único nas três faixas. Os efeitos são esparsos (somam só ~0,2 LU à música), então
    # -15 (música) e -14 (soma) não cabem juntos: escolhe-se o ganho que deixa as DUAS metas a <= 0,5 LU.
    Lm = lufs(music)
    Ls = lufs(music + sfx + riser)
    diff = Ls - Lm
    target_music = (-15.0 + (-14.0 - diff)) / 2
    g = 10 ** ((target_music - Lm) / 20)
    music, sfx, riser = music * g, sfx * g, riser * g
    summed = music + sfx + riser
    master, lim = tp_limiter(summed, -1.3)
    tp = true_peak_db(master)
    info = {
        "ganho_comum_db": round(20 * np.log10(g), 3),
        "lufs_musica_interno": round(lufs(music), 2),
        "lufs_master_interno": round(lufs(master), 2),
        "true_peak_soma_db": round(true_peak_db(summed), 2),
        "true_peak_master_interno_db": round(tp, 2),
        "limitador": lim,
        "efeitos": placed,
    }
    if tp > -1.0:
        raise SystemExit(f"pico verdadeiro acima de -1 dBTP ({tp:.2f}); revisar níveis")
    STEMS.mkdir(exist_ok=True)
    write_wav(STEMS / "music.wav", music)
    write_wav(STEMS / "sfx.wav", sfx)
    write_wav(STEMS / "riser.wav", riser)
    write_wav(WORK / "master.wav", master)
    (WORK / "audio_mix_info.json").write_text(json.dumps(info, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in info.items() if k != "efeitos"}, indent=1))
    for p in placed:
        print(f"  {p['tipo']:9s} quadro {p['quadro']:7.2f}  {p['ms']:10.3f} ms  ({p['trecho']}: {p['rotulo']})")


if __name__ == "__main__":
    main()
