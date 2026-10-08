"""Utilitários de áudio: grade de batidas, síntese, reverb, loudness (BS.1770) e WAV 24 bits."""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
SR = 48000
TL = json.loads((WORK / "trechos.json").read_text())
FPS = TL["fps"]
SPF = SR // FPS                                   # 800 amostras por quadro
END_SAMPLES = TL["END_quadro"] * SPF              # 1 728 800
BEAT = SR * 60 // TL["bpm"]                       # 24 000 amostras por batida
FIRST = TL["quadro_primeira_batida"] * SPF        # 800


def beat_sample(bar, beat=1.0):
    """amostra do tempo `beat` (1-based, fracionário) do compasso `bar` (1-based)"""
    return FIRST + int(round(((bar - 1) * 4 + (beat - 1)) * BEAT))


def frame_sample(frame):
    return int(frame) * SPF


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def envelope(n, attack, decay_tau, sustain, release, note_len):
    """envelope (amostras): ataque linear, decaimento exponencial até `sustain`,
    release suave (quadrática) a partir de `note_len`."""
    t = np.arange(n, dtype=np.float64)
    att = np.clip(t / max(attack, 1), 0, 1)
    dec = sustain + (1 - sustain) * np.exp(-np.maximum(t - attack, 0) / max(decay_tau, 1))
    e = att * dec
    if note_len < n:
        lvl = e[note_len]
        rt = t[note_len:] - note_len
        e[note_len:] = lvl * np.clip(1 - rt / max(release, 1), 0, 1) ** 2
    return e


def polyblep_saw(freq, n, phase0=0.0):
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    dt = f / SR
    ph = (phase0 + np.cumsum(dt)) % 1.0
    out = 2 * ph - 1
    m1 = ph < dt
    x = ph[m1] / dt[m1]
    out[m1] -= x + x - x * x - 1
    m2 = ph > 1 - dt
    x = (ph[m2] - 1) / dt[m2]
    out[m2] -= x * x + x + x + 1
    return out


def lowpass(x, fc, order=2):
    sos = signal.butter(order, fc, "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def highpass(x, fc, order=2):
    sos = signal.butter(order, fc, "high", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def bandpass(x, f1, f2, order=2):
    sos = signal.butter(order, [f1, f2], "band", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def pan(mono, p):
    """p em [-1, 1]; lei de potência constante"""
    th = (p + 1) * np.pi / 4
    return np.stack([mono * np.cos(th), mono * np.sin(th)], axis=1)


def add(buf, x, at):
    """soma x (n,2) ou (n,) em buf a partir da amostra `at`, cortando nas bordas"""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    if at < 0:
        x = x[-at:]
        at = 0
    n = min(len(x), len(buf) - at)
    if n > 0:
        buf[at : at + n] += x[:n]


def reverb_ir(seconds=2.4, rt60=1.7, seed=7, lp=6500, hp=180, predelay=0.018):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    decay = np.exp(-6.91 * t / rt60)
    ir = rng.standard_normal((n, 2)) * decay[:, None]
    ir = lowpass(highpass(ir, hp), lp)
    pre = int(predelay * SR)
    ir = np.concatenate([np.zeros((pre, 2)), ir])
    ir /= np.sqrt((ir**2).sum(axis=0, keepdims=True))
    return ir


def convolve_stereo(x, ir):
    out = np.zeros((len(x) + len(ir) - 1, 2))
    for c in range(2):
        out[:, c] = signal.fftconvolve(x[:, c], ir[:, c])
    return out[: len(x)]


# ---------- loudness ITU-R BS.1770-4 ----------
def _kweight(x):
    # coeficientes para 48 kHz (BS.1770)
    b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a1 = [1.0, -1.69065929318241, 0.73248077421585]
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, -1.99004745483398, 0.99007225036621]
    y = signal.lfilter(b1, a1, x, axis=0)
    return signal.lfilter(b2, a2, y, axis=0)


def lufs(x):
    y = _kweight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    pw = []
    for s in range(0, len(y) - blk + 1, hop):
        seg = y[s : s + blk]
        pw.append((seg**2).mean(axis=0).sum())
    pw = np.array(pw)
    lk = -0.691 + 10 * np.log10(pw + 1e-20)
    g = pw[lk > -70]
    if not len(g):
        return -np.inf
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g2 = pw[(lk > -70) & (lk > rel)]
    return -0.691 + 10 * np.log10(g2.mean())


def short_term(x, start, end):
    return lufs(x[start:end]) if end - start > int(0.4 * SR) else -np.inf


def true_peak_db(x, os=4):
    up = signal.resample_poly(x, os, 1, axis=0)
    return 20 * np.log10(np.abs(up).max() + 1e-20)


def peak_db(x):
    return 20 * np.log10(np.abs(x).max() + 1e-20)


def write_wav(path, x):
    assert x.shape == (END_SAMPLES, 2), x.shape
    sf.write(str(path), x.astype(np.float64), SR, subtype="PCM_24")
