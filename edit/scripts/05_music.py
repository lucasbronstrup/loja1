"""Trilha original (stems/music.wav) e riser da abertura (stems/riser.wav), sintetizados com NumPy/SciPy.

120 BPM, Ré maior, um acorde por compasso, primeira batida no quadro 1 (amostra 800).
Dinâmica pelo arranjo; nível único; saída gradual de 800 ms no fim; entrada só com 5 ms anti-estalo.
"""
import json

import numpy as np

from audiolib import (
    BEAT, END_SAMPLES, FIRST, SR, ROOT, WORK, add, bandpass, beat_sample, convolve_stereo, envelope,
    highpass, lowpass, lufs, mtof, pan, peak_db, polyblep_saw, reverb_ir, short_term, true_peak_db, write_wav,
)

N = END_SAMPLES
RNG = np.random.default_rng(20261008)
STEMS = ROOT / "stems"

# ---------------- harmonia ----------------
CHORD_OF_BAR = {1: "Vsus", 2: "I", 3: "V", 4: "vi", 5: "IV", 6: "I", 7: "vi", 8: "IV", 9: "Vsus",
                10: "I", 11: "V", 12: "vi", 13: "IV", 14: "I", 15: "vi", 16: "IV", 17: "Vsus", 18: "I"}
ROOT_BASS = {"I": 38, "V": 33, "vi": 35, "IV": 31, "Vsus": 33}
COMP = {"I": [54, 57, 62, 64], "V": [52, 57, 61, 64], "vi": [54, 59, 62, 66], "IV": [55, 59, 62, 66], "Vsus": [52, 57, 62, 64]}
PAD = {"I": [50, 57, 62, 66], "V": [45, 52, 57, 61], "vi": [47, 54, 59, 62], "IV": [43, 50, 55, 59], "Vsus": [45, 52, 57, 62]}
ARP = {"I": [62, 66, 69, 74, 69, 66, 62, 66], "V": [57, 61, 64, 69, 64, 61, 57, 61],
       "vi": [59, 62, 66, 71, 66, 62, 59, 62], "IV": [55, 59, 62, 67, 62, 59, 55, 59],
       "Vsus": [57, 62, 64, 69, 64, 61, 57, 61]}
# melodia (tempo 1-based, duração em batidas, nota MIDI)
MEL = {
    "I": [(1, 1.5, 78), (2.5, 0.5, 76), (3, 1, 74), (4, 1, 69)],
    "V": [(1, 1.5, 73), (2.5, 0.5, 74), (3, 1.5, 76), (4.5, 0.5, 69)],
    "vi": [(1, 1.5, 74), (2.5, 0.5, 78), (3, 1, 76), (4, 1, 74)],
    "IV": [(1, 2, 71), (3, 1, 74), (4, 1, 76)],
    "I_end": [(1, 2, 78), (3, 2, 74)],
    "Vsus_final": [(1, 2, 74), (3, 1.5, 73), (4.5, 0.5, 76)],
    "I_final": [(1, 4.5, 78)],
}
SECTION = {1: "intro", **{b: "act1" for b in range(2, 7)}, **{b: "pivot" for b in range(7, 10)},
           **{b: "act2" for b in range(10, 15)}, **{b: "final" for b in range(15, 19)}}


# ---------------- instrumentos ----------------
STRUM = [0, 0.006, 0.011, 0.017]


def ep_chord(bus, notes, dur, vel, at):
    for i, m in enumerate(notes):
        add(bus, epiano(m, dur, vel), at + int(STRUM[i % 4] * SR))


def epiano(m, dur_beats, vel):
    f = mtof(m)
    note = int(dur_beats * BEAT)
    n = note + int(0.45 * SR)
    t = np.arange(n) / SR
    idx = (1.4 * vel) * np.exp(-t / 0.32) + 0.22
    ph = RNG.uniform(0, 2 * np.pi, 3)
    mod = np.sin(2 * np.pi * f * t + ph[0])
    car = np.sin(2 * np.pi * f * t + ph[1] + idx * mod)
    body = 0.22 * np.sin(2 * np.pi * 2 * f * t + ph[2] + 0.5 * idx * mod) * np.exp(-t / 0.5)
    tine = 0.035 * vel * np.sin(2 * np.pi * min(f * 7.0, 5200) * t) * np.exp(-t / 0.025)
    env = envelope(n, int(0.002 * SR), int(1.7 * SR), 0.0, int(0.28 * SR), note)
    x = (car + body + tine) * env * vel
    x = lowpass(x, 5200)
    trem = 0.18 * np.sin(2 * np.pi * 2.6 * t + RNG.uniform(0, 6.28))
    return np.stack([x * (1 - trem) * 0.75, x * (1 + trem) * 0.75], axis=1)


def pluck(m, vel, length=0.95):
    f = mtof(m)
    n = int(length * SR)
    t = np.arange(n) / SR
    K = int(min(28, 9000 / f))
    x = np.zeros(n)
    for k in range(1, K + 1):
        x += (1 / k**1.15) * np.sin(2 * np.pi * k * f * t + RNG.uniform(0, 6.28)) * np.exp(-t * (2.6 + 2.4 * k))
    att = np.clip(t / 0.0015, 0, 1)
    return lowpass(x * att * vel, 6000)


def strings_note(m, dur_beats, vel, attack=0.055, release=0.22):
    f0 = mtof(m)
    note = int(dur_beats * BEAT)
    n = note + int(release * SR) + 200
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    vib = 1 + 0.0016 * np.sin(2 * np.pi * 5.1 * t + RNG.uniform(0, 6.28)) * np.clip(t / 0.25, 0, 1)
    for i, cents in enumerate([-11, -5, 0, 5, 11]):
        f = f0 * 2 ** (cents / 1200) * vib
        v = polyblep_saw(f, n, RNG.uniform(0, 1))
        out += pan(v, -0.6 + 0.3 * i)
    out = highpass(lowpass(out, 2300), 140)
    env = envelope(n, int(attack * SR), int(2.0 * SR), 0.85, int(release * SR), note)
    return out * env[:, None] * vel / 5


def pad_note(m, dur_beats, vel):
    f0 = mtof(m)
    note = int(dur_beats * BEAT)
    n = note + int(0.9 * SR)
    out = np.zeros((n, 2))
    for i, cents in enumerate([-8, 0, 8]):
        v = polyblep_saw(f0 * 2 ** (cents / 1200), n, RNG.uniform(0, 1))
        out += pan(v, [-0.7, 0.0, 0.7][i])
    out = lowpass(out, 1100, order=2)
    env = envelope(n, int(0.32 * SR), int(3 * SR), 0.9, int(0.85 * SR), note)
    return out * env[:, None] * vel / 3


def bass_note(m, dur_beats, vel):
    f = mtof(m)
    note = int(dur_beats * BEAT)
    n = note + int(0.08 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.32 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    x = np.tanh(1.4 * x) / np.tanh(1.4)
    env = envelope(n, int(0.006 * SR), int(0.9 * SR), 0.55, int(0.07 * SR), note)
    return lowpass(x * env * vel, 900)


def kick(vel):
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 46 + 64 * np.exp(-t / 0.032)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / 0.15) * np.clip(t / 0.0015, 0, 1)
    return lowpass(x * vel, 2500)


def shaker(vel):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    x = RNG.standard_normal(n)
    x = bandpass(x, 3200, 7600)
    env = np.clip(t / 0.007, 0, 1) * np.exp(-t / 0.024)
    return x * env * vel


def clap(vel):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    x = RNG.standard_normal(n)
    env = np.zeros(n)
    for off in (0.0, 0.009, 0.018):
        env += np.clip((t - off) / 0.001, 0, 1) * np.exp(-np.maximum(t - off, 0) / 0.006) * (t >= off)
    env += 0.5 * np.clip((t - 0.02) / 0.002, 0, 1) * np.exp(-np.maximum(t - 0.02, 0) / 0.09) * (t >= 0.02)
    return bandpass(x * env, 900, 3000) * vel


def bell(m, vel):
    f = mtof(m)
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    idx = 1.1 * np.exp(-t / 0.6)
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * 2.0 * f * t))
    x += 0.25 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.35)
    env = np.clip(t / 0.002, 0, 1) * np.exp(-t / 0.9)
    return lowpass(x * env * vel, 4500)


# ---------------- arranjo ----------------
def build_music():
    bus = {k: np.zeros((N, 2)) for k in ("pad", "ep", "mel", "pluck", "strings", "bass", "kick", "shaker", "clap", "bell")}
    for bar in range(1, 19):
        ch = CHORD_OF_BAR[bar]
        sec = SECTION[bar]
        b0 = beat_sample(bar, 1)
        # PAD: sempre (Vsus resolve para V no tempo 3)
        if ch == "Vsus":
            for m in PAD["Vsus"]:
                add(bus["pad"], pad_note(m, 2.0, 0.55), b0)
            for m in PAD["V"]:
                add(bus["pad"], pad_note(m, 2.0 if bar < 18 else 4, 0.55), beat_sample(bar, 3))
        else:
            for m in PAD[ch]:
                add(bus["pad"], pad_note(m, 4.0 if bar < 18 else 4.4, 0.55), b0)

        # PIANO ELÉTRICO
        if sec == "intro":
            ep_chord(bus["ep"], COMP["Vsus"], 1.9, 0.55, b0)
            ep_chord(bus["ep"], COMP["V"], 1.9, 0.5, beat_sample(bar, 3))
        elif sec in ("act1", "act2", "final"):
            voic = COMP["V"] if ch == "Vsus" else COMP[ch]
            hits = [(1, 1.4, 0.62), (2.5, 0.4, 0.42), (3, 1.0, 0.56), (4.5, 0.4, 0.38)]
            if bar == 18:
                hits = [(1, 4.4, 0.7)]
            for beat, dur, vel in hits:
                vv = COMP["Vsus"] if (ch == "Vsus" and beat < 3) else voic
                ep_chord(bus["ep"], vv, dur, vel, beat_sample(bar, beat))
        elif sec == "pivot":
            voic = COMP[ch] if ch != "Vsus" else COMP["Vsus"]
            for beat, dur, vel in [(1, 1.9, 0.5), (3, 1.9, 0.45)]:
                vv = COMP["V"] if (ch == "Vsus" and beat >= 3) else voic
                ep_chord(bus["ep"], vv, dur, vel, beat_sample(bar, beat))
            # arpejo lento em semínimas (respiro)
            arp = (ARP["V"] if ch == "Vsus" else ARP[ch])[::2]
            for i, m in enumerate(arp):
                add(bus["ep"], epiano(m + 12, 0.9, 0.3), beat_sample(bar, 1 + i))

        # MELODIA (piano elétrico, voz superior) — atos iguais; pivô e final também
        mel = None
        if sec in ("act1", "act2"):
            first = 2 if sec == "act1" else 10
            mel = MEL["I_end"] if bar == first + 4 else MEL[ch]
        elif sec == "pivot" and bar in (7, 8):
            mel = MEL[ch]
        elif sec == "final":
            mel = {15: MEL["vi"], 16: MEL["IV"], 17: MEL["Vsus_final"], 18: MEL["I_final"]}[bar]
        if mel:
            for beat, dur, m in mel:
                add(bus["mel"], epiano(m, dur, 0.78 if sec != "pivot" else 0.62), beat_sample(bar, beat))
                if sec == "final":
                    add(bus["bell"], pan(bell(m, 0.32), 0.3), beat_sample(bar, beat))

        # SINOS discretos nos atos: um toque no 1º tempo (igual nos dois atos)
        if sec in ("act1", "act2"):
            top = {"I": 74, "V": 69, "vi": 71, "IV": 74, "Vsus": 69}[ch]
            add(bus["bell"], pan(bell(top + 12, 0.22), 0.35), b0)

        # RITMO: atos e final
        if sec in ("act1", "act2", "final"):
            if bar < 18:
                kb = [1, 3] if bar != 17 else [1, 2, 3, 4]
                if sec == "final" and bar != 17:
                    kb = [1, 3, 4.5]
                for k in kb:
                    add(bus["kick"], kick(0.95 if k in (1, 3) else 0.6), beat_sample(bar, k))
                for i in range(16):
                    v = [0.55, 0.28, 0.85, 0.3][i % 4]
                    add(bus["shaker"], pan(shaker(v), -0.35), beat_sample(bar, 1 + i * 0.25))
                # baixo
                r = ROOT_BASS[ch]
                for beat, dur, m in [(1, 1.45, r), (2.5, 0.45, r), (3, 1.45, r), (4.5, 0.45, r + 7)]:
                    add(bus["bass"], bass_note(m, dur, 0.9), beat_sample(bar, beat))
                if sec == "final":
                    for c in (2, 4):
                        add(bus["clap"], clap(0.9), beat_sample(bar, c))
                    if bar == 17:
                        for c in (4.5, 4.75):
                            add(bus["clap"], clap(0.5), beat_sample(bar, c))
            else:
                add(bus["kick"], kick(1.0), b0)
                add(bus["bass"], bass_note(38, 4.4, 0.95), b0)

            # cor do arranjo: pluck (ato 1) | cordas (ato 2) | ambos (final)
            arp = ARP[ch]
            if sec in ("act1", "final") and bar < 18:
                for i, m in enumerate(arp):
                    add(bus["pluck"], pluck(m, 0.85 if i % 2 == 0 else 0.62), beat_sample(bar, 1 + i * 0.5))
            if sec == "act2":
                for i, m in enumerate(arp):
                    add(bus["strings"], strings_note(m, 0.46, 0.85 if i % 2 == 0 else 0.62), beat_sample(bar, 1 + i * 0.5))
            if sec == "final":
                chord = PAD["V"] if ch == "Vsus" else PAD[ch]
                for m in chord:
                    add(bus["strings"], strings_note(m + 12, 4.0 if bar < 18 else 4.4, 0.55, attack=0.25, release=0.8), b0)
    return bus


def mix(bus, strings_gain):
    g = {"pad": 0.55, "ep": 0.42, "mel": 0.55, "pluck": 0.30, "strings": strings_gain, "bass": 0.48,
         "kick": 0.62, "shaker": 0.06, "clap": 0.11, "bell": 0.16}
    send = {"pad": 0.25, "ep": 0.22, "mel": 0.28, "pluck": 0.3, "strings": 0.32, "bell": 0.5, "clap": 0.25, "shaker": 0.08}
    dry = np.zeros((N, 2))
    rev = np.zeros((N, 2))
    for k, x in bus.items():
        if x.ndim == 1:
            x = np.stack([x, x], axis=1)
        if k == "pluck":
            # pluck com leve abertura estéreo e eco pontuado (3/4 de batida)
            x = np.stack([x[:, 0] * 0.8, x[:, 1] * 1.0], axis=1)
            d = int(0.75 * BEAT)
            echo = np.zeros_like(x)
            echo[d:, 1] += x[:-d, 0] * 0.28
            echo[2 * d :, 0] += x[: -2 * d, 1] * 0.14
            x = x + lowpass(echo, 3500)
        dry += x * g[k]
        rev += x * g[k] * send.get(k, 0)
    wet = convolve_stereo(rev, reverb_ir())
    return highpass(dry + wet * 0.55, 30)


def fades(x):
    y = x.copy()
    y[:FIRST] = 0
    n5 = int(0.005 * SR)
    y[FIRST : FIRST + n5] *= np.linspace(0, 1, n5)[:, None]
    nf = int(0.8 * SR)
    w = 0.5 * (1 + np.cos(np.linspace(0, np.pi, nf)))
    y[N - nf :] *= w[:, None]
    return y


def build_riser():
    """2 s exatos: amostra 800 (quadro 1) até 96 800 (quadro 121); termina no corte."""
    s0, s1 = beat_sample(1, 1), beat_sample(2, 1)
    n = s1 - s0
    t = np.arange(n) / n
    # tom grave subindo (55 -> 196 Hz) com filtro abrindo
    f = 55 * (196 / 55) ** (t**1.6)
    tone = polyblep_saw(f, n) * 0.6 + np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.8
    noise = RNG.standard_normal((n, 2))
    out = np.zeros((n, 2))
    blk = 480
    from scipy import signal as sg

    zi_t = None
    zi_n = None
    for i in range(0, n, blk):
        u = (i + blk / 2) / n
        fc_t = 140 * (2400 / 140) ** (u**1.4)
        fc_n = 260 * (5200 / 260) ** (u**1.5)
        sos_t = sg.butter(2, fc_t, "low", fs=SR, output="sos")
        sos_n = sg.butter(2, [fc_n * 0.55, fc_n], "band", fs=SR, output="sos")
        if zi_t is None:
            zi_t = np.zeros((sos_t.shape[0], 2))
            zi_n = np.zeros((sos_n.shape[0], 2, 2))
        seg_t, zi_t = sg.sosfilt(sos_t, tone[i : i + blk], zi=zi_t)
        seg_n, zi_n = sg.sosfilt(sos_n, noise[i : i + blk], axis=0, zi=zi_n)
        out[i : i + blk] += seg_t[:, None] * 0.9 + seg_n * 1.6
    amp = (0.04 + 0.96 * t**2.4)
    out *= amp[:, None]
    # anti-estalo: 4 ms no fim, terminando exatamente na junção (quadro 121)
    k = int(0.004 * SR)
    out[-k:] *= np.linspace(1, 0, k)[:, None] ** 2
    out[:k] *= np.linspace(0, 1, k)[:, None]
    full = np.zeros((N, 2))
    full[s0:s1] = out
    return full


def main():
    STEMS.mkdir(exist_ok=True)
    bus = build_music()
    act1 = (beat_sample(2), beat_sample(7))
    act2 = (beat_sample(10), beat_sample(15))
    # cordas do ato 2 calibradas para a mesma energia do pluck do ato 1
    best = None
    for sg_ in np.linspace(0.3, 1.6, 27):
        x = mix(bus, sg_)
        d = abs(short_term(x, *act1) - short_term(x, *act2))
        if best is None or d < best[0]:
            best = (d, sg_)
    music = fades(mix(bus, best[1]))
    L = lufs(music)
    music *= 10 ** ((-15.0 - L) / 20)
    riser = build_riser()
    music_peak = np.abs(music).max()
    riser *= (music_peak * 10 ** (-10 / 20)) / np.abs(riser).max()
    info = {
        "strings_gain": round(float(best[1]), 3),
        "act1_lufs": round(short_term(music, *act1), 2),
        "act2_lufs": round(short_term(music, *act2), 2),
        "music_lufs": round(lufs(music), 2),
        "music_peak_db": round(peak_db(music), 2),
        "music_tp_db": round(true_peak_db(music), 2),
        "riser_peak_db": round(peak_db(riser), 2),
        "riser_start_sample": beat_sample(1),
        "riser_end_sample": beat_sample(2),
        "secoes_lufs": {
            name: round(short_term(music, beat_sample(a), beat_sample(b)), 2)
            for name, (a, b) in {"abertura": (1, 2), "ato1": (2, 7), "pivo": (7, 10), "ato2": (10, 15), "final": (15, 19)}.items()
        },
    }
    np.save(WORK / "music_raw.npy", music.astype(np.float32))
    np.save(WORK / "riser_raw.npy", riser.astype(np.float32))
    (WORK / "audio_music_info.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
