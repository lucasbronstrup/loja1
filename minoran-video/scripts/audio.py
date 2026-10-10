"""Trilha + SFX da Minoran, sintetizados do zero (NumPy/SciPy). Nada baixado.

Fonte única: timeline.json (120 BPM, compasso 2.0 s, cues globais).
Conceito: a trilha nasce dos tiques — o tique do relógio vira o hi-hat da música.
Saída: audio/master.wav (48 kHz, estéreo, 24 bits, 42.0 s), -14 LUFS integrado, pico real <= -1 dBTP
       audio/stems/{music,sfx}.wav, audio/report.json
"""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

ROOT = Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / "timeline.json").read_text(encoding="utf-8"))
SR = 48000
DUR = float(TL["duration"])
N = int(round(DUR * SR))
BPM = TL["bpm"]
BEAT = 60.0 / BPM  # 0.5 s
BAR = TL["bar"]  # 2.0 s
RNG = np.random.default_rng(20260214)


# ------------------------------------------------------------------ utilidades


def cues(scene: str, name: str):
    v = TL["audio"][scene][name]
    if isinstance(v, dict) and "every" in v:
        n = int(round((v["to"] - v["from"]) / v["every"])) + 1
        return [round(v["from"] + i * v["every"], 6) for i in range(n)]
    return v


def tt(n):
    return np.arange(n) / SR


def note(name: str) -> float:
    names = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    p, o = (name[:-1], int(name[-1]))
    midi = 12 * (o + 1) + names[p]
    return 440.0 * 2 ** ((midi - 69) / 12)


def noise(n):
    return RNG.standard_normal(n)


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="low", fs=SR, output="sos"), x)


def saw(f, n, harmonics_max=7000.0, phase=0.0):
    """Dente de serra limitado em banda (aditivo)."""
    t = tt(n)
    out = np.zeros(n)
    k = 1
    while k * f < harmonics_max and k < 60:
        out += ((-1) ** (k + 1)) * np.sin(2 * np.pi * k * f * t + k * phase) / k
        k += 1
    return out * (2 / np.pi)


def adsr(n, a, d, s, r, hold=None):
    """Envelope em segundos; hold = duração antes do release (padrão: até o fim - r)."""
    e = np.zeros(n)
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    H = int((hold if hold is not None else n / SR - r) * SR)
    H = max(H, A + D)
    i = 0
    if A > 0:
        e[:A] = np.linspace(0, 1, A, endpoint=False) ** 1.0
    if D > 0:
        e[A : A + D] = np.linspace(1, s, D, endpoint=False)
    e[A + D : H] = s
    if R > 0 and H < n:
        m = min(R, n - H)
        e[H : H + m] = s * np.linspace(1, 0, R, endpoint=False)[:m]
    return e


class Bus:
    def __init__(self):
        self.x = np.zeros((N, 2))

    def add(self, sig, t, gain=1.0, pan=0.0):
        """Mono ou estéreo em t (s); pan -1..1 constant-power (mono)."""
        i0 = int(round(t * SR))
        if i0 >= N:
            return
        if sig.ndim == 1:
            a = (pan + 1) * np.pi / 4
            st = np.stack([sig * np.cos(a), sig * np.sin(a)], axis=1) * np.sqrt(2)
        else:
            st = sig
        if i0 < 0:
            st = st[-i0:]
            i0 = 0
        m = min(len(st), N - i0)
        self.x[i0 : i0 + m] += st[:m] * gain


def panned(sig, pan_curve):
    a = (np.clip(pan_curve, -1, 1) + 1) * np.pi / 4
    return np.stack([sig * np.cos(a), sig * np.sin(a)], axis=1) * np.sqrt(2)


def reverb_ir(seconds, damp=0.6, seed=1, predelay=0.012):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = tt(n)
    decay = np.exp(-6.9 * t / seconds)
    ir = np.zeros((n + int(predelay * SR), 2))
    for c in range(2):
        nz = r.standard_normal(n) * decay
        # amortecimento de agudos crescente com o tempo (filtro em blocos)
        nz = lp(nz, 9000) * (1 - damp * t / seconds) + lp(nz, 2500) * (damp * t / seconds)
        ir[int(predelay * SR) :, c] = nz
    ir /= np.sqrt((ir**2).sum() / 2)
    return ir


def convolve_stereo(x, ir, wet=0.25):
    out = np.zeros_like(x)
    for c in range(2):
        out[:, c] = signal.fftconvolve(x[:, c], ir[:, c])[: len(x)]
    return x * (1 - wet) + out * wet


# ------------------------------------------------------------------ instrumentos


def tick(pitch=1.0, decay=1.0, tock=False):
    """Tique de quartzo: clique de ruído + ressonâncias metálicas curtas + corpo."""
    n = int(0.08 * SR * decay)
    t = tt(n)
    f = (2650 if tock else 3150) * pitch
    click = bp(noise(n), 2500, 9000) * np.exp(-t / 0.0011)
    r1 = np.sin(2 * np.pi * f * t) * np.exp(-t / (0.010 * decay))
    r2 = 0.45 * np.sin(2 * np.pi * f * 1.73 * t + 0.4) * np.exp(-t / (0.006 * decay))
    body = 0.32 * np.sin(2 * np.pi * (980 if tock else 1180) * pitch * t) * np.exp(-t / (0.018 * decay))
    x = 0.9 * click + 0.55 * r1 + 0.35 * r2 + body
    return x / np.max(np.abs(x))


def kick(level=1.0, tight=False, n_s=0.42):
    n = int(n_s * SR)
    t = tt(n)
    f = 44 + 96 * np.exp(-t / (0.035 if tight else 0.05))
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / (0.16 if tight else 0.28))
    click = hp(noise(n), 1500) * np.exp(-t / 0.0025) * 0.35
    x = np.tanh(1.6 * (body + click)) / np.tanh(1.6)
    return x * level


def clap():
    n = int(0.45 * SR)
    t = tt(n)
    env = np.zeros(n)
    for d in (0.0, 0.0085, 0.017, 0.026):
        i = int(d * SR)
        env[i:] += np.exp(-(t[: n - i]) / 0.006)
    env += 0.55 * np.exp(-t / 0.13) * (t > 0.026)
    x = bp(noise(n), 900, 4200) * env
    return x / np.max(np.abs(x))


def snare(tone=190.0):
    n = int(0.3 * SR)
    t = tt(n)
    x = bp(noise(n), 1500, 7000) * np.exp(-t / 0.06) + 0.6 * np.sin(2 * np.pi * tone * t) * np.exp(-t / 0.05)
    return x / np.max(np.abs(x))


def bass_note(f, dur, cutoff=520.0):
    n = int((dur + 0.05) * SR)
    s = saw(f, n, 2500) * 0.55 + np.sin(2 * np.pi * f * tt(n)) * 0.75
    # filtro com envelope: abre no ataque, fecha rápido (pluck de baixo)
    env_f = cutoff * (1 + 2.2 * np.exp(-tt(n) / 0.06))
    out = np.zeros(n)
    blk = 256
    zi = None
    for i in range(0, n, blk):
        sos = signal.butter(2, min(env_f[i], 8000), btype="low", fs=SR, output="sos")
        if zi is None:
            zi = signal.sosfilt_zi(sos) * 0
        out[i : i + blk], zi = signal.sosfilt(sos, s[i : i + blk], zi=zi)
    return out * adsr(n, 0.004, 0.12, 0.6, 0.06, hold=dur)


def pad_chord(freqs, dur, attack=0.35, release=0.7, cutoff=1900.0, detune=0.006):
    n = int((dur + release) * SR)
    x = np.zeros(n)
    for k, f in enumerate(freqs):
        for d in (-detune, 0.0, detune):
            x += saw(f * (1 + d), n, 6000, phase=0.7 * k + 13 * d)
    x = lp(x, cutoff, 2)
    x /= max(1e-9, np.max(np.abs(x)))
    e = adsr(n, attack, 0.3, 0.85, release, hold=dur)
    return x * e


def fm_bell(f, dur, ratio=3.5, index=4.0, decay=1.4, bright=1.0):
    n = int(dur * SR)
    t = tt(n)
    idx = index * np.exp(-t / (0.25 * decay)) * bright
    mod = np.sin(2 * np.pi * f * ratio * t)
    x = np.sin(2 * np.pi * f * t + idx * mod) * np.exp(-t / decay)
    att = np.minimum(1, t / 0.002)
    return x * att


def ep_pluck(f, dur=0.45):
    n = int(dur * SR)
    t = tt(n)
    idx = 2.2 * np.exp(-t / 0.08)
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 2 * t)) * np.exp(-t / 0.22)
    x += 0.25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.08)
    return x * np.minimum(1, t / 0.0015)


def sweep_noise(dur, f0, f1, q=1.2, shape="rise", seed_gain=1.0):
    """Ruído em banda com centro varrendo de f0 a f1 (exponencial)."""
    n = int(dur * SR)
    x = noise(n)
    fc = f0 * (f1 / f0) ** np.linspace(0, 1, n)
    out = np.zeros(n)
    blk = 256
    zi = None
    for i in range(0, n, blk):
        c = fc[i]
        lo, hi = max(30, c / (1 + 1 / q)), min(SR / 2 - 500, c * (1 + 1 / q))
        sos = signal.butter(2, [lo, hi], btype="band", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[i : i + blk], zi = signal.sosfilt(sos, x[i : i + blk], zi=zi)
    t = np.linspace(0, 1, n)
    if shape == "rise":
        env = t**2.2 * (1 - np.exp(-(1 - t) * 40))
    elif shape == "fall":
        env = (1 - t) ** 1.6 * (1 - np.exp(-t * 30))
    else:  # bell
        env = np.sin(np.pi * t) ** 1.5
    out = out / max(1e-9, np.max(np.abs(out))) * env
    return out


def whoosh(dur, f0, f1, pan0=0.0, pan1=0.0, shape="rise", tone=None):
    x = sweep_noise(dur, f0, f1, 1.4, shape)
    if tone is not None:
        n = len(x)
        fr = tone[0] * (tone[1] / tone[0]) ** np.linspace(0, 1, n)
        ph = 2 * np.pi * np.cumsum(fr) / SR
        x = x + 0.18 * np.sin(ph) * np.abs(x).max() * np.linspace(0, 1, n) ** 2
    return panned(x, np.linspace(pan0, pan1, len(x)))


def riser(dur, f0=110.0, f1=880.0):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    fr = f0 * (f1 / f0) ** (t**1.4)
    ph = 2 * np.pi * np.cumsum(fr) / SR
    tone = np.zeros(n)
    for k in range(1, 9):
        tone += np.sin(k * ph) / k
    tone = lp(tone, 4000)
    nz = sweep_noise(dur, 400, 9000, 1.0, "rise")
    x = 0.55 * tone / np.max(np.abs(tone)) * t**1.8 + 0.6 * nz
    # trêmulo acelerando
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * np.cumsum(4 + 22 * t**2) / SR)
    return x * trem


def cymbal(dur=2.2, bright=1.0):
    n = int(dur * SR)
    t = tt(n)
    x = hp(noise(n), 4500) * 0.8
    for f in (3920, 5170, 6830, 8210, 10340, 12500):
        x += 0.12 * np.sin(2 * np.pi * f * t + RNG.random() * 6) * bright
    return x * np.exp(-t / (dur / 4.5)) * np.minimum(1, t / 0.003)


def reverse_cymbal(dur):
    c = cymbal(dur + 0.4)[::-1][: int(dur * SR)]
    c = c[-int(dur * SR) :]
    t = np.linspace(0, 1, len(c))
    return c * t**1.2 * (1 - np.exp(-(1 - t) * 60))


def impact(big=False):
    dur = 3.2 if big else 2.2
    n = int(dur * SR)
    t = tt(n)
    f = 34 + (66 if big else 46) * np.exp(-t / 0.18)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.9 if big else 0.55))
    thump = lp(noise(n), 260) * np.exp(-t / 0.05) * 1.2
    x = np.tanh(1.8 * (sub + thump)) * 0.9
    if big:
        x += 0.32 * cymbal(dur, 1.0)
        x += 0.25 * bp(noise(n), 300, 2400) * np.exp(-t / 0.09)
    return x / np.max(np.abs(x))


def glass_swell(dur=2.4, f0=880.0):
    n = int(dur * SR)
    t = tt(n)
    x = np.zeros(n)
    for r, a in ((1.0, 1.0), (2.76, 0.45), (5.4, 0.25), (8.93, 0.12)):
        x += a * np.sin(2 * np.pi * f0 * r * t + 2 * np.sin(2 * np.pi * 0.7 * t))
    env = np.minimum(1, t / 0.55) ** 1.6 * np.exp(-np.maximum(0, t - 0.55) / 0.8)
    return x / np.max(np.abs(x)) * env


def shimmer():
    out = np.zeros(int(2.4 * SR))
    for k, nm in enumerate(("C7", "G6", "E7", "B6", "D7", "G7")):
        b = fm_bell(note(nm), 2.0, ratio=4.0, index=1.6, decay=0.7)
        i = int(k * 0.035 * SR)
        out[i : i + len(b)] += b * (0.9 - 0.08 * k)
    sp = hp(noise(len(out)), 7000) * np.exp(-tt(len(out)) / 0.35) * 0.25
    return (out + sp) / np.max(np.abs(out + sp))


def shutter():
    n = int(0.09 * SR)
    t = tt(n)
    x = np.zeros(n)
    for d, g, f in ((0.0, 1.0, 2400), (0.028, 0.75, 1900)):
        i = int(d * SR)
        m = n - i
        x[i:] += g * (bp(noise(m), 1200, 7000) * np.exp(-t[:m] / 0.0025) + 0.5 * np.sin(2 * np.pi * f * t[:m]) * np.exp(-t[:m] / 0.008))
    return x / np.max(np.abs(x))


def iris_sfx(dur=0.3):
    n = int(dur * SR)
    x = np.zeros(n)
    k = 0
    tpos = 0.0
    while tpos < dur - 0.01:
        c = tick(pitch=1.4 + 0.3 * (tpos / dur), decay=0.4) * (0.4 + 0.6 * tpos / dur)
        i = int(tpos * SR)
        m = min(len(c), n - i)
        x[i : i + m] += c[:m]
        tpos += 0.03 * (1 - 0.7 * tpos / dur)
        k += 1
    x += 0.5 * sweep_noise(dur, 600, 5000, 1.5, "rise")
    return x / np.max(np.abs(x))


def focus_sfx():
    n = int(0.5 * SR)
    t = tt(n)
    x = np.zeros(n)
    for d in (0.0, 0.045):
        c = tick(pitch=0.85, decay=0.5)
        i = int(d * SR)
        x[i : i + len(c)] += 0.6 * c[: n - i]
    f = 520 * (1.6 ** np.minimum(1, t / 0.25))
    x += 0.35 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.15) * np.minimum(1, t / 0.01)
    return x / np.max(np.abs(x))


# ------------------------------------------------------------------ música

# 4 compassos: Fmaj7 · Em7 · Dm9 · Cmaj7(9) — descendente, elegante
PROG = [
    ("F2", ["F3", "A3", "C4", "E4"], ["A4", "C5", "E5", "G5"]),
    ("E2", ["E3", "G3", "B3", "D4"], ["G4", "B4", "D5", "E5"]),
    ("D2", ["D3", "F3", "A3", "C4", "E4"], ["F4", "A4", "C5", "E5"]),
    ("C2", ["C3", "E3", "G3", "B3", "D4"], ["E4", "G4", "B4", "D5"]),
]


def chord_at(t):
    return PROG[int(t // BAR) % 4]


def build_music() -> tuple[np.ndarray, list]:
    drums = Bus()
    bass = Bus()
    pads = Bus()
    keys = Bus()
    log = []

    gap = cues("s04-nuances", "gap")  # [19.5, 20.0]
    riser2_end = cues("s07-rythme", "riser")[1]  # 35.875
    final_chord_t = cues("s08-signature", "final_chord")

    def muted(t):
        return gap[0] <= t < gap[1] or riser2_end <= t < 36.0 or t >= final_chord_t

    # ---- pad: 0–4 drone, depois acordes por compasso
    drone = pad_chord([note("C2"), note("G2"), note("C3")], 4.2, attack=1.6, release=0.6, cutoff=420)
    pads.add(drone, 0.0, 0.32)
    for b in range(2, 19):  # 4.0 .. 38.0
        t0 = b * BAR
        if t0 >= final_chord_t:
            break
        _, tones, _ = chord_at(t0)
        cut = 1500 if t0 < 20 else 2300
        if 32 <= t0 < 36:
            cut = 1200
        d = BAR
        if t0 + d > gap[0] and t0 < gap[1]:
            d = gap[0] - t0
        p = pad_chord([note(x) for x in tones], d, attack=0.25, release=0.45, cutoff=cut)
        pads.add(p, t0, 0.20 if t0 < 20 else 0.24)

    # ---- bateria
    for i in range(int(DUR / (BEAT / 2))):
        t = i * BEAT / 2  # colcheias
        if muted(t):
            continue
        beat_i = i // 2
        off = i % 2 == 1
        sect = "intro" if t < 4 else "verse" if t < 20 else "drop" if t < 32 else "break" if t < 36 else "end"
        if sect == "intro":
            continue
        # kick
        if not off and sect in ("verse", "drop", "end"):
            if sect == "end" and t >= 37.0:
                pass
            elif sect == "verse":
                if t >= 18.0 and t < 19.5:
                    drums.add(kick(0.9), t, 0.55)
                else:
                    drums.add(kick(0.8), t, 0.5)
            elif sect == "drop":
                drums.add(kick(1.0, tight=True), t, 0.78)
            elif sect == "end" and t < 37.0:
                drums.add(kick(1.0), t, 0.6)
        # clap nos tempos 2 e 4 (drop)
        if not off and sect == "drop" and beat_i % 2 == 1:
            drums.add(clap(), t, 0.28, pan=0.05)
        if not off and sect == "verse" and beat_i % 2 == 1 and t >= 10.0:
            drums.add(snare(), t, 0.10, pan=-0.05)
        # hi-hat = o tique do relógio
        if sect in ("verse", "drop"):
            vel = 0.20 if off else 0.10
            if sect == "drop":
                vel *= 1.35
            drums.add(tick(pitch=1.22, decay=0.6, tock=not off), t, vel, pan=0.22 if off else -0.12)
            if sect == "drop" or t >= 14.0:  # semicolcheias
                drums.add(tick(pitch=1.45, decay=0.35), t + BEAT / 4, vel * 0.45, pan=0.3)
        if sect == "break" and t < 34.0 and t >= 33.0:
            drums.add(tick(pitch=1.0, decay=0.6), t, 0.08)

    # ---- baixo
    pat_verse = [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0]  # semicolcheias por compasso (8 tempos? não: 16 x 0.125)
    pat_drop = [1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0]
    step = BAR / 16
    for b in range(2, 19):
        t0 = b * BAR
        root, _, _ = chord_at(t0)
        f = note(root)
        pat = pat_drop if 20 <= t0 < 32 else pat_verse
        for k, on in enumerate(pat):
            t = t0 + k * step
            if not on or muted(t) or t >= final_chord_t:
                continue
            fk = f * (2 if (k in (6, 14) and 20 <= t0 < 32) else 1)
            dur = step * (1.6 if 20 <= t0 < 32 else 1.8)
            cut = 480 if t0 < 20 else 700
            if 32 <= t0 < 36:
                cut = 380
            bass.add(bass_note(fk, dur, cut), t, 0.30 if t0 < 20 else 0.36)

    # ---- teclas: arpejo em semicolcheias (desde o shimmer do s02) + stabs no drop
    shimmer_t = cues("s02-elegance", "shimmer")
    for b in range(int(shimmer_t // BAR), 19):
        t0 = b * BAR
        _, _, arp = chord_at(t0)
        seq = [arp[0], arp[2], arp[1], arp[3], arp[2], arp[0], arp[3], arp[1]]
        for k in range(16):
            t = t0 + k * step
            if t < shimmer_t or muted(t) or t >= final_chord_t:
                continue
            if 32 <= t < 34 and k % 2 == 1:
                continue
            g = 0.10 if k % 4 == 0 else 0.065
            keys.add(ep_pluck(note(seq[k % 8]), 0.4), t, g, pan=0.35 * np.sin(k * 0.9))
        if 20 <= t0 < 32:
            _, tones, _ = chord_at(t0)
            for off in (0.25, 0.75, 1.25, 1.75):
                st = sum(ep_pluck(note(x) * 2, 0.3) for x in tones[:4])
                keys.add(st / 3, t0 + off, 0.11, pan=-0.15)

    # ---- acorde final (38.0) e notas longas
    fin = pad_chord([note(x) for x in ("C3", "G3", "B3", "D4", "E4", "G4")], DUR - final_chord_t - 0.6, attack=0.08, release=1.8, cutoff=2600)
    pads.add(fin, final_chord_t, 0.30)
    fb = np.zeros(int((DUR - final_chord_t) * SR))
    for k, nm in enumerate(("C5", "G5", "B5", "D6", "E6")):
        b = fm_bell(note(nm), DUR - final_chord_t - 0.05, ratio=3.0, index=1.2, decay=1.6)
        i = int(k * 0.06 * SR)
        fb[i : i + len(b)] += b[: len(fb) - i] * (0.6 - 0.07 * k)
    keys.add(fb, final_chord_t, 0.16)
    bass.add(bass_note(note("C2"), 3.0, 300) * np.linspace(1, 0.6, int(3.05 * SR)), final_chord_t, 0.32)
    log.append(("final_chord", final_chord_t))

    # ---- mix da música: sidechain do kick no pad, reverb, filtro (lpf_down) e gap
    mus = drums.x * 1.0 + bass.x * 1.0 + keys.x * 1.0
    # sidechain: envelope do kick reduz pads
    kenv = np.zeros(N)
    for i in range(int(DUR / BEAT)):
        t = i * BEAT
        if 4 <= t < 36.0 and not muted(t) and not (32 <= t < 34):
            i0 = int(t * SR)
            m = min(int(0.32 * SR), N - i0)
            kenv[i0 : i0 + m] = np.maximum(kenv[i0 : i0 + m], np.exp(-tt(m) / 0.12) * (0.55 if 20 <= t < 32 else 0.35))
    pads_sc = pads.x * (1 - kenv)[:, None]
    mus = mus + pads_sc
    mus = convolve_stereo(mus, reverb_ir(2.2, seed=3), wet=0.22)

    # lpf_down 32.0 -> 33.0 (fecha até ~380 Hz), segura, reabre 34.0 -> 35.875 com o riser
    lpf = cues("s07-rythme", "lpf_down")
    rz = cues("s07-rythme", "riser")
    fc = np.full(N, 18000.0)
    t = tt(N)
    a = (t >= lpf[0]) & (t < lpf[1])
    fc[a] = 18000 * (380 / 18000) ** ((t[a] - lpf[0]) / (lpf[1] - lpf[0]))
    b_ = (t >= lpf[1]) & (t < rz[0])
    fc[b_] = 380
    c_ = (t >= rz[0]) & (t < rz[1])
    fc[c_] = 380 * (16000 / 380) ** ((t[c_] - rz[0]) / (rz[1] - rz[0])) ** 2
    out = np.zeros_like(mus)
    blk = 256
    zi = np.zeros((1, 2, 2))
    for i in range(0, N, blk):
        f = min(fc[i], 20000)
        if f >= 17999:
            seg = mus[i : i + blk]
            # mantém o estado coerente quando o filtro está aberto
            sos = signal.butter(2, 19000, btype="low", fs=SR, output="sos")
            for ch in range(2):
                out[i : i + blk, ch], zi[:, ch, :] = signal.sosfilt(sos, seg[:, ch], zi=zi[:, ch, :])
            continue
        sos = signal.butter(2, f, btype="low", fs=SR, output="sos")
        for ch in range(2):
            out[i : i + blk, ch], zi[:, ch, :] = signal.sosfilt(sos, mus[i : i + blk, ch], zi=zi[:, ch, :])
    mus = out

    # gap: música muda (19.5 -> 20.0) e respiro antes do impacto final (35.875 -> 36.0)
    gain = np.ones(N)
    for g0, g1 in ((gap[0], gap[1]), (riser2_end, 36.0)):
        i0, i1 = int(g0 * SR), int(g1 * SR)
        ramp = int(0.012 * SR)
        gain[i0 : i0 + ramp] = np.minimum(gain[i0 : i0 + ramp], np.linspace(1, 0, ramp))
        gain[i0 + ramp : i1] = 0
        gain[i1 : i1 + int(0.004 * SR)] = np.linspace(0, 1, int(0.004 * SR))
    mus = mus * gain[:, None]
    # dinâmica por seção: o verso respira, o build cresce, o drop bate mais forte
    keys_t = [0.0, 4.0, 17.9, 19.5, 20.0, 26.0, 32.0, 36.0, DUR]
    keys_g = [1.0, 0.68, 0.70, 0.92, 1.0, 0.9, 0.85, 1.0, 1.0]
    sec = np.interp(tt(N), keys_t, keys_g)
    # degrau seco no drop (o ganho sobe exatamente no corte de 20.0)
    sec[int(20.0 * SR) :][: int(6.0 * SR)] = np.interp(tt(N)[int(20.0 * SR) :][: int(6.0 * SR)], [20.0, 26.0], [1.0, 0.95])
    mus = mus * sec[:, None]
    return mus, log


# ------------------------------------------------------------------ SFX


def build_sfx() -> tuple[np.ndarray, list]:
    sfx = Bus()
    wet = Bus()  # envio para reverb longo
    log = []

    def put(sig, t, g, pan=0.0, rev=0.0, name=""):
        sfx.add(sig, t, g, pan)
        if rev > 0:
            wet.add(sig, t, g * rev, pan)
        log.append((name, round(t, 4)))

    # s01
    for k, t in enumerate(cues("s01-tic", "tick")):
        put(tick(pitch=1.0, decay=1.2, tock=k % 2 == 1), t, 0.62, pan=0.25, rev=0.25, name="tick")
    put(whoosh(0.9, 900, 3200, -0.4, 0.3, "bell"), cues("s01-tic", "whoosh_soft"), 0.16, name="whoosh_soft")
    rc = cues("s01-tic", "reverse_cymbal")
    put(reverse_cymbal(rc[1] - rc[0]), rc[0], 0.20, rev=0.2, name="reverse_cymbal")
    put(glass_swell(2.0, note("E5")), cues("s01-tic", "glass_swell"), 0.20, pan=0.2, rev=0.6, name="glass_swell")
    wz = cues("s01-tic", "whoosh_zoom")
    put(whoosh(wz[1] - wz[0], 300, 7000, 0, 0, "rise", tone=(200, 1600)), wz[0], 0.42, name="whoosh_zoom")
    # s02
    put(impact(False), cues("s02-elegance", "impact_soft"), 0.62, rev=0.3, name="impact_soft")
    put(shimmer(), cues("s02-elegance", "shimmer"), 0.18, pan=0.3, rev=0.7, name="shimmer")
    wl = cues("s02-elegance", "whoosh_left")
    put(whoosh(wl[1] - wl[0], 600, 5000, 0.8, -0.9, "rise"), wl[0], 0.48, name="whoosh_left")
    # s03
    for k, t in enumerate(cues("s03-lignes", "punch")):
        p = kick(0.8, tight=True, n_s=0.3) * 0.8 + snare(220 + 20 * k) * 0.35
        put(p / np.max(np.abs(p)), t, 0.38, pan=(-0.15, 0.15, 0.0)[k], rev=0.12, name="punch")
    put(focus_sfx(), cues("s03-lignes", "focus"), 0.26, pan=0.3, rev=0.2, name="focus")
    ir_ = cues("s03-lignes", "iris")
    put(iris_sfx(ir_[1] - ir_[0]), ir_[0], 0.30, pan=0.1, name="iris")
    # s04
    for nm, t in zip(("B5", "C6", "D6"), cues("s04-nuances", "chime")):
        put(fm_bell(note(nm), 2.4, ratio=3.5, index=3.0, decay=1.1), t, 0.20, pan=0.25, rev=0.55, name="chime")
    tr = cues("s04-nuances", "tick_roll")
    tpos, k = tr[0], 0
    while tpos < tr[1] - 0.02:
        prog = (tpos - tr[0]) / (tr[1] - tr[0])
        if not (cues("s04-nuances", "gap")[0] <= tpos < cues("s04-nuances", "gap")[1]) or True:
            put(tick(pitch=1.1 + 0.4 * prog, decay=0.5), tpos, 0.18 + 0.25 * prog, pan=(-0.3 if k % 2 else 0.3), name="tick_roll")
        tpos += 0.25 * (1 - 0.85 * prog)
        k += 1
    rz = cues("s04-nuances", "riser")
    put(riser(rz[1] - rz[0]), rz[0], 0.26, rev=0.15, name="riser")
    wu = cues("s04-nuances", "whoosh_up")
    put(whoosh(wu[1] - wu[0], 500, 8000, 0, 0, "rise", tone=(300, 2400)), wu[0], 0.5, name="whoosh_up")
    # s05
    put(impact(True), cues("s05-styles", "impact_big"), 0.8, rev=0.35, name="impact_big")
    for k, t in enumerate(cues("s05-styles", "swish")):
        put(whoosh(0.42, 700, 3800, 0.7, -0.7, "bell"), t - 0.06, 0.34, name="swish")
    ws = cues("s05-styles", "whoosh_spin")
    w = whoosh(ws[1] - ws[0], 400, 6000, 0, 0, "rise")
    am = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(np.linspace(6, 26, len(w))) / SR)
    put(w * am[:, None], ws[0], 0.5, name="whoosh_spin")
    # s06
    sl = cues("s06-geste", "slide")
    sw = sweep_noise(sl[1] - sl[0], 700, 2600, 2.0, "bell")
    put(panned(sw, np.linspace(-0.85, 0.85, len(sw))), sl[0], 0.24, name="slide")
    put(shimmer(), cues("s06-geste", "shimmer"), 0.2, pan=0.25, rev=0.7, name="shimmer")
    wf = cues("s06-geste", "whoosh_flash")
    put(whoosh(wf[1] - wf[0], 1200, 12000, 0, 0, "rise"), wf[0], 0.5, name="whoosh_flash")
    # s07
    for k, t in enumerate(cues("s07-rythme", "shutter")):
        put(shutter(), t, 0.42, pan=(-0.35 if k % 2 else 0.35), rev=0.08, name="shutter")
    rc = cues("s07-rythme", "reverse_cymbal")
    put(reverse_cymbal(rc[1] - rc[0]), rc[0], 0.26, rev=0.25, name="reverse_cymbal")
    rz = cues("s07-rythme", "riser")
    put(riser(rz[1] - rz[0], 90, 1200), rz[0], 0.28, rev=0.15, name="riser")
    tr = cues("s07-rythme", "tick_roll")
    tpos, k = tr[0], 0
    while tpos < tr[1] - 0.02:
        prog = (tpos - tr[0]) / (tr[1] - tr[0])
        put(tick(pitch=1.0 + 0.5 * prog, decay=0.5), tpos, 0.2 + 0.3 * prog, pan=(-0.3 if k % 2 else 0.3), name="tick_roll")
        tpos += 0.2 * (1 - 0.88 * prog)
        k += 1
    wd = cues("s07-rythme", "whoosh_dark")
    put(whoosh(wd[1] - wd[0], 4000, 160, 0, 0, "rise", tone=(800, 60)), wd[0], 0.5, name="whoosh_dark")
    # s08
    put(impact(True), cues("s08-signature", "impact_big"), 0.85, rev=0.45, name="impact_big")
    put(shimmer(), cues("s08-signature", "shimmer"), 0.22, pan=0.2, rev=0.8, name="shimmer")
    put(tick(pitch=0.95, decay=2.2), cues("s08-signature", "final_tick"), 0.85, pan=-0.2, rev=0.6, name="final_tick")

    long_ir = reverb_ir(3.4, damp=0.5, seed=9, predelay=0.02)
    tail = np.zeros_like(wet.x)
    for c in range(2):
        tail[:, c] = signal.fftconvolve(wet.x[:, c], long_ir[:, c])[:N]
    short_ir = reverb_ir(0.9, damp=0.4, seed=5)
    room = np.zeros_like(sfx.x)
    for c in range(2):
        room[:, c] = signal.fftconvolve(sfx.x[:, c], short_ir[:, c])[:N]
    return sfx.x + 0.5 * tail + 0.08 * room, log


# ------------------------------------------------------------------ loudness / limiter


def k_weight(x):
    # ITU-R BS.1770-4, 48 kHz
    b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a1 = [1.0, -1.69065929318241, 0.73248077421585]
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, -1.99004745483398, 0.99007225036621]
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)


def lufs(x):
    y = k_weight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = []
    for i in range(0, len(y) - blk + 1, hop):
        ms.append(np.mean(y[i : i + blk] ** 2, axis=0).sum())
    ms = np.array(ms)
    L = -0.691 + 10 * np.log10(ms + 1e-12)
    g1 = ms[L > -70]
    if len(g1) == 0:
        return -99.0
    rel = -0.691 + 10 * np.log10(g1.mean()) - 10
    g2 = ms[(L > -70) & (L > rel)]
    return float(-0.691 + 10 * np.log10(g2.mean()))


def true_peak(x):
    up = signal.resample_poly(x, 4, 1, axis=0)
    return float(20 * np.log10(np.max(np.abs(up)) + 1e-12))


def limit(x, ceiling_db=-1.2, look_ms=3.0, release_ms=40.0):
    """Limitador de pico real (4x) com look-ahead: o ganho é sempre <= o requerido."""
    thr = 10 ** (ceiling_db / 20)
    up = np.abs(signal.resample_poly(x, 4, 1, axis=0)).max(axis=1)
    peak = up[: len(x) * 4].reshape(-1, 4).max(axis=1)
    peak = np.pad(peak, (0, max(0, len(x) - len(peak))), mode="edge")[: len(x)]
    g_req = np.minimum(1.0, thr / np.maximum(peak, 1e-9))
    # min (janela 2R) seguido de média (janela R): curva suave e nunca acima de g_req
    R = max(3, int(release_ms * SR / 1000))
    g = uniform_filter1d(minimum_filter1d(g_req, size=2 * R + 1, mode="nearest"), size=R, mode="nearest")
    L = max(3, int(look_ms * SR / 1000))
    g = np.minimum(g, uniform_filter1d(minimum_filter1d(g_req, size=2 * L + 1, mode="nearest"), size=L, mode="nearest"))
    return x * g[:, None]


def write_wav(path: Path, x: np.ndarray, bits=24):
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.clip(x, -1, 1)
    if bits == 24:
        q = (x * (2**23 - 1)).astype(np.int32)
        b = np.zeros((q.shape[0], q.shape[1], 3), np.uint8)
        b[..., 0] = q & 0xFF
        b[..., 1] = (q >> 8) & 0xFF
        b[..., 2] = (q >> 16) & 0xFF
        data = b.tobytes()
        sw = 3
    else:
        data = (x * 32767).astype("<i2").tobytes()
        sw = 2
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(sw)
        w.setframerate(SR)
        w.writeframes(data)


def main() -> int:
    mus, mlog = build_music()
    sfx, slog = build_sfx()
    # balanço: a música carrega, os SFX pontuam
    mix = 0.9 * mus + 1.0 * sfx
    # fade-out final suave (o acorde termina no fim do filme)
    fo = int(1.2 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    mix[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))[:, None]
    # loudness alvo (YouTube): -14 LUFS integrado, pico real <= -1 dBTP
    L0 = lufs(mix)
    mix *= 10 ** ((-14.0 - L0) / 20)
    for _ in range(4):
        mix = limit(mix, -1.3)
        L1 = lufs(mix)
        if abs(L1 + 14.0) < 0.25:
            break
        mix *= 10 ** ((-14.0 - L1) / 20)
    mix = limit(mix, -1.3)
    tp = true_peak(mix)
    L = lufs(mix)
    write_wav(ROOT / "audio" / "master.wav", mix)
    write_wav(ROOT / "audio" / "stems" / "music.wav", mus / max(1e-9, np.abs(mus).max()) * 0.8)
    write_wav(ROOT / "audio" / "stems" / "sfx.wav", sfx / max(1e-9, np.abs(sfx).max()) * 0.8)
    rep = {"sr": SR, "duration": len(mix) / SR, "lufs": round(L, 2), "truePeak_dBTP": round(tp, 2), "cues": slog + mlog}
    (ROOT / "audio" / "report.json").write_text(json.dumps(rep, indent=1))
    print(f"  audio/master.wav  {len(mix) / SR:.3f}s  {L:.2f} LUFS  TP {tp:.2f} dBTP  ({len(slog)} SFX)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
