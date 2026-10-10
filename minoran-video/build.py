#!/usr/bin/env python3
"""Orquestrador do vídeo institucional Minoran (42 s · 1080p60).

    python build.py assets   # vendor, capture, fotos, recortes, enquadramento, texturas, paleta, timeline.js
    python build.py audio    # trilha + SFX sintetizados (NumPy/SciPy) -> audio/master.wav
    python build.py check    # hyperframes lint/check em cada cena isolada + index
    python build.py draft    # render rápido (30 qps) de todas as cenas + áudio -> out/draft.mp4
    python build.py render   # cada cena isolada a 240 qps -> renders/240/<cena>.mp4
    python build.py master   # concat + blend 240->60 (4 subquadros) + pós + H.264/AAC -> out/…mp4
    python build.py qa       # verificação técnica do master + folha de contato
    python build.py all      # tudo, em ordem

Multiplataforma: Python da .venv quando existir; FFmpeg e npx sempre via subprocess
com lista de argumentos (sem shell).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TL_PATH = ROOT / "timeline.json"
RENDERS = ROOT / "renders"
OUT = ROOT / "out"
FINAL = OUT / "minoran-institucional-1080p60.mp4"
AUDIO = ROOT / "audio" / "master.wav"
HF_VERSION = "0.8.143"

# ---------------------------------------------------------------- utilidades


def venv_python() -> str:
    for p in (ROOT / ".venv" / "bin" / "python", ROOT / ".venv" / "Scripts" / "python.exe"):
        if p.exists():
            return str(p)
    return sys.executable


def npx() -> str:
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx"


def node() -> str:
    return shutil.which("node") or "node"


def ffmpeg() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def ffprobe() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def run(args: list[str], cwd: Path = ROOT, check: bool = True, quiet: bool = False, env: dict | None = None) -> subprocess.CompletedProcess:
    t0 = time.time()
    print(f"$ {' '.join(str(a) for a in args)}", flush=True)
    kw = {}
    if quiet:
        kw = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True}
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run([str(a) for a in args], cwd=cwd, check=False, env=e, **kw)
    if check and r.returncode != 0:
        if quiet and r.stdout:
            print(r.stdout[-6000:])
        raise SystemExit(f"falhou ({r.returncode}): {args[0]} … [{time.time() - t0:.1f}s]")
    return r


def py(script: str, *args: str) -> None:
    run([venv_python(), "-I", str(ROOT / "scripts" / script), *args])


def hf(*args: str, quiet: bool = False, check: bool = True, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    local = ROOT / "node_modules" / ".bin" / ("hyperframes.cmd" if os.name == "nt" else "hyperframes")
    cmd = [str(local)] if local.exists() else [npx(), "--yes", f"hyperframes@{HF_VERSION}"]
    return run([*cmd, *args], quiet=quiet, check=check, cwd=cwd, env={"HYPERFRAMES_SKIP_SKILLS": "1"})


def load_tl() -> dict:
    return json.loads(TL_PATH.read_text(encoding="utf-8"))


def expand(v):
    """{"from","to","every"} -> lista de tempos."""
    if isinstance(v, dict) and "every" in v:
        n = int(round((v["to"] - v["from"]) / v["every"])) + 1
        return [round(v["from"] + i * v["every"], 6) for i in range(n)]
    return v


# ---------------------------------------------------------------- timeline.js


def write_timeline_js() -> None:
    tl = load_tl()
    scenes = {}
    for s in tl["scenes"]:
        sid, st, en = s["id"], s["start"], s["end"]
        audio = {k: expand(v) for k, v in tl["audio"].get(sid, {}).items()}
        local_audio = {}
        for k, v in audio.items():
            if isinstance(v, list):
                local_audio[k] = [round(x - st, 6) for x in v]
            else:
                local_audio[k] = round(v - st, 6)
        visual = {k: expand(v) for k, v in tl["visual"].get(sid, {}).items()}
        scenes[sid] = {
            "id": sid,
            "start": st,
            "end": en,
            "dur": round(en - st, 6),
            "audio": audio,
            "cue": {**local_audio, **visual},
        }
    out = {
        "bpm": tl["bpm"],
        "bar": tl["bar"],
        "beat": tl["beat"],
        "grid": tl["grid"],
        "duration": tl["duration"],
        "order": [s["id"] for s in tl["scenes"]],
        "scenes": scenes,
        "transitions": tl["transitions"],
    }
    # validação: todo cue cai na grade de 0.25 s (exceto as cabeças de whoosh/riser,
    # que terminam na grade: o fim de cada intervalo é o que importa para o corte)
    bad = []
    for sid, sc in scenes.items():
        for k, v in sc["audio"].items():
            vals = v if isinstance(v, list) else [v]
            if k.startswith("whoosh") and not isinstance(v, list):
                continue  # whoosh avulso acompanha um gesto, não é corte
            ends = [vals[-1]] if k.startswith(("whoosh", "riser", "reverse", "iris", "tick_roll", "gap", "slide", "lpf")) else vals
            for x in ends:
                if abs(x / tl["grid"] - round(x / tl["grid"])) > 1e-6 and not k.startswith("riser"):
                    bad.append(f"{sid}.{k}={x}")
    if bad:
        print("  aviso: cues fora da grade:", bad)
    shared = ROOT / "shared"
    shared.mkdir(exist_ok=True)
    js = (
        "/* gerado por build.py a partir de timeline.json — não editar */\n"
        "window.MINORAN_TL = " + json.dumps(out, separators=(",", ":")) + ";\n"
        "window.MINORAN_TL.scene = function (id) { return window.MINORAN_TL.scenes[id]; };\n"
        "window.MINORAN_TL.cue = function (id, name) { var c = window.MINORAN_TL.scenes[id].cue[name];"
        " if (c === undefined) throw new Error('cue ausente: ' + id + '.' + name); return c; };\n"
    )
    (shared / "timeline.js").write_text(js, encoding="utf-8")
    print(f"  shared/timeline.js: {len(scenes)} cenas")


# ---------------------------------------------------------------- assets


def cmd_assets() -> None:
    run([node(), str(ROOT / "scripts" / "vendor.mjs")])
    if not (ROOT / "capture" / "AGENTS.md").exists():
        hf("capture", "https://minoran.com", "-o", "capture", "--skip-vision")
    py("fetch_images.py")
    py("prep_images.py")
    py("cutouts.py")
    py("framing.py")
    py("align.py")
    py("paths.py")
    py("textures.py")
    py("palette.py")
    py("plates.py")
    write_timeline_js()


# ---------------------------------------------------------------- audio


def cmd_audio() -> None:
    write_timeline_js()
    py("audio.py")


# ---------------------------------------------------------------- check


def scene_project(scene_file: str) -> Path:
    """Projeto temporário com a cena como index.html (check/snapshot rodam sobre index.html)."""
    d = ROOT / ".hf" / "scene" / Path(scene_file).stem
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for name in ("assets", "vendor", "shared", "audio"):
        src = ROOT / name
        if not src.exists():
            continue
        try:
            os.symlink(src, d / name, target_is_directory=True)
        except OSError:
            shutil.copytree(src, d / name)
    shutil.copy2(ROOT / scene_file, d / "index.html")
    motion = ROOT / (Path(scene_file).stem + ".motion.json")
    if motion.exists():
        shutil.copy2(motion, d / "index.motion.json")
    return d


def cmd_check(only: list[str] | None = None) -> None:
    write_timeline_js()
    tl = load_tl()
    failures = []
    for s in tl["scenes"]:
        if only and s["id"] not in only:
            continue
        d = scene_project(s["file"])
        r = hf("check", str(d), "--json", "--samples", "13", quiet=True, check=False)
        try:
            data = json.loads(r.stdout[r.stdout.index("{") :])
        except Exception:  # noqa: BLE001
            print(r.stdout[-4000:])
            failures.append(s["id"])
            continue
        (ROOT / ".hf" / f"check-{s['id']}.json").write_text(json.dumps(data, indent=2))
        ok = data.get("ok", False)
        nerr = sum(1 for sec in ("lint", "runtime", "layout", "motion", "contrast") for f in (data.get(sec, {}) or {}).get("findings", []) if f.get("severity") == "error") if isinstance(data, dict) else -1
        print(f"  {s['id']:16s} ok={ok} errors={nerr}")
        if not ok:
            failures.append(s["id"])
    if not only:
        # index.html montado: as cenas ficam na raiz (contrato do projeto), o que faz o lint do
        # projeto acusar multiple_root_compositions; para o gate, monta-se uma cópia com as cenas
        # em compositions/ (mesmo HTML, mesmos assets) e roda-se o check completo + motion.json.
        d = ROOT / ".hf" / "index"
        if d.exists():
            shutil.rmtree(d)
        (d / "compositions").mkdir(parents=True)
        for name in ("assets", "vendor", "shared", "audio"):
            try:
                os.symlink(ROOT / name, d / name, target_is_directory=True)
            except OSError:
                shutil.copytree(ROOT / name, d / name)
        idx = (ROOT / "index.html").read_text(encoding="utf-8")
        for s in tl["scenes"]:
            shutil.copy2(ROOT / s["file"], d / "compositions" / s["file"])
            idx = idx.replace(f'data-composition-src="{s["file"]}"', f'data-composition-src="compositions/{s["file"]}"')
        (d / "index.html").write_text(idx, encoding="utf-8")
        shutil.copy2(ROOT / "index.motion.json", d / "index.motion.json")
        r = hf("check", str(d), "--json", "--samples", "43", "--timeout", "60000", quiet=True, check=False)
        try:
            data = json.loads(r.stdout[r.stdout.index("{") :])
            (ROOT / ".hf" / "check-index.json").write_text(json.dumps(data, indent=2))
            errs = [(sec, f.get("code"), f.get("selector")) for sec in ("lint", "runtime", "layout", "motion", "contrast") for f in (data.get(sec, {}) or {}).get("findings", []) if f.get("severity") == "error"]
            print(f"  index            ok={data.get('ok')} errors={len(errs)}")
            for e in errs[:20]:
                print("    ", e)
            if not data.get("ok"):
                failures.append("index")
        except Exception:  # noqa: BLE001
            print(r.stdout[-4000:])
            failures.append("index")
    if failures:
        raise SystemExit(f"check falhou: {failures}")


def cmd_snap(scene_id: str, times: str, out: str | None = None) -> None:
    """Snapshots de uma cena isolada: python build.py snap s01-tic 0.5,1.2[,…] [dir]"""
    write_timeline_js()
    tl = load_tl()
    s = next(x for x in tl["scenes"] if x["id"] == scene_id)
    d = scene_project(s["file"])
    dest = Path(out) if out else ROOT / ".hf" / "snap" / scene_id
    if dest.exists():
        shutil.rmtree(dest)
    hf("snapshot", str(d), "--at", times, "--no-end", "-o", str(dest), quiet=True)
    print(f"  {dest}")


# ---------------------------------------------------------------- render


def render_scene(scene_file: str, out: Path, fps: int, quality: str, crf: int | None = None, workers: str | None = None) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    args = ["render", str(ROOT), "-c", scene_file, "--fps", str(fps), "-o", str(out), "--quality", quality, "--quiet"]
    if crf is not None:
        args += ["--crf", str(crf)]
    if workers:
        args += ["--workers", workers]
    hf(*args)


def probe_frames(p: Path) -> int:
    r = run([ffprobe(), "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(p)], quiet=True)
    return int(r.stdout.strip().splitlines()[-1])


def cmd_draft(only: list[str] | None = None) -> None:
    write_timeline_js()
    tl = load_tl()
    parts = []
    for s in tl["scenes"]:
        p = RENDERS / "draft" / f"{s['id']}.mp4"
        if not only or s["id"] in only:
            render_scene(s["file"], p, 30, "draft")
        parts.append(p)
    if only:
        return
    concat_and_mux(parts, OUT / "draft.mp4", fps=30, blend=1, post=False)


def cmd_render(only: list[str] | None = None) -> None:
    write_timeline_js()
    tl = load_tl()
    workers = os.environ.get("MN_WORKERS")
    for s in tl["scenes"]:
        if only and s["id"] not in only:
            continue
        p = RENDERS / "240" / f"{s['id']}.mp4"
        dur = s["end"] - s["start"]
        expect = int(round(dur * 240))
        if p.exists() and probe_frames(p) == expect and os.environ.get("MN_FORCE") != "1" and p.stat().st_mtime > max((ROOT / s["file"]).stat().st_mtime, (ROOT / "shared" / "fx.js").stat().st_mtime):
            print(f"  {s['id']}: já renderizada ({expect} quadros)")
            continue
        t0 = time.time()
        render_scene(s["file"], p, 240, "delivery", crf=8, workers=workers)
        n = probe_frames(p)
        if n != expect:
            raise SystemExit(f"{s['id']}: {n} quadros, esperado {expect}")
        print(f"  {s['id']}: {n} quadros a 240 qps em {time.time() - t0:.0f}s")


# ---------------------------------------------------------------- master


VIGNETTE = ROOT / "assets" / "tex" / "vignette.png"
IN_709 = "matrixin=709:transferin=709:primariesin=709:rangein=limited"
RGB_FULL = "matrix=709:transfer=709:primaries=709:range=full"


def video_graph(fps: int, blend: int, post: bool) -> str:
    """240 -> 60 por média de subquadros e pós-produção, tudo em RGB 16 bits.

    tmix=frames=4 entrega no quadro n a média de n-3..n; select pega n = 4k+3, ou seja,
    a média exata dos subquadros 4k..4k+3 (obturador de 360°), 10080 -> 2520 quadros.
    Pós (depois do blend, para o grão não ser apagado): bloom aditivo das altas luzes,
    vinheta por máscara multiplicada, grão monocromático temporal; volta a BT.709 limitado.
    """
    g = f"[0:v]zscale={IN_709}:{RGB_FULL},format=gbrp16le"
    if blend > 1:
        w = " ".join(["1"] * blend)
        g += f",tmix=frames={blend}:weights='{w}',select='eq(mod(n\\,{blend})\\,{blend - 1})',setpts=N/({fps}*TB)"
    if post:
        g += (
            ",split=2[pb][ph];"
            "[ph]colorlevels=rimin=0.62:gimin=0.62:bimin=0.62,gblur=sigma=26:steps=3[bl];"
            "[pb][bl]blend=all_mode=addition:all_opacity=0.16[bb];"
            "[1:v]format=gbrp16le[vg];"
            "[bb][vg]blend=all_mode=multiply:shortest=1,"
            "noise=alls=5:allf=t+u:all_seed=20260214"
        )
    g += ",zscale=matrixin=gbr:transferin=709:primariesin=709:rangein=full:matrix=709:transfer=709:primaries=709:range=limited:dither=error_diffusion,format=yuv420p[v]"
    return g


def concat_and_mux(parts: list[Path], out: Path, fps: int, blend: int, post: bool) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lst = RENDERS / f"concat-{fps}.txt"
    lst.parent.mkdir(parents=True, exist_ok=True)
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    tl = load_tl()
    dur = tl["duration"]
    args = [ffmpeg(), "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", str(lst)]
    if post:
        if not VIGNETTE.exists():
            py("textures.py", "--vignette-only")
        args += ["-loop", "1", "-framerate", str(fps), "-i", str(VIGNETTE)]
    a_idx = 2 if post else 1
    has_audio = AUDIO.exists()
    if has_audio:
        args += ["-i", str(AUDIO)]
    args += ["-filter_complex", video_graph(fps, blend, post), "-map", "[v]"]
    if has_audio:
        args += ["-map", f"{a_idx}:a", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2"]
    args += [
        "-r", str(fps),
        "-c:v", "libx264", "-profile:v", "high", "-preset", "slow" if post else "veryfast",
        "-crf", "14" if post else "23", "-tune", "film",
        "-x264-params", f"keyint={fps * 2}:min-keyint={fps}:bframes=3",
        "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
        "-t", f"{dur:.3f}", "-movflags", "+faststart", str(out),
    ]
    run(args)


def cmd_master() -> None:
    tl = load_tl()
    parts = [RENDERS / "240" / f"{s['id']}.mp4" for s in tl["scenes"]]
    missing = [p for p in parts if not p.exists()]
    if missing:
        raise SystemExit(f"faltam renders: {missing}")
    for s, p in zip(tl["scenes"], parts):
        n = probe_frames(p)
        expect = int(round((s["end"] - s["start"]) * 240))
        if n != expect:
            raise SystemExit(f"{p.name}: {n} quadros (esperado {expect})")
    if not AUDIO.exists():
        cmd_audio()
    concat_and_mux(parts, FINAL, fps=60, blend=4, post=True)
    print(f"  master: {FINAL}")


# ---------------------------------------------------------------- qa


def cmd_qa() -> None:
    py("qa.py", str(FINAL))


# ---------------------------------------------------------------- main


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]
    if cmd == "timeline":
        write_timeline_js()
    elif cmd == "assets":
        cmd_assets()
    elif cmd == "audio":
        cmd_audio()
    elif cmd == "snap":
        cmd_snap(rest[0], rest[1], rest[2] if len(rest) > 2 else None)
    elif cmd == "check":
        cmd_check(rest or None)
    elif cmd == "draft":
        cmd_draft(rest or None)
    elif cmd == "render":
        cmd_render(rest or None)
    elif cmd == "master":
        cmd_master()
    elif cmd == "qa":
        cmd_qa()
    elif cmd == "all":
        cmd_assets()
        cmd_audio()
        cmd_check()
        cmd_render()
        cmd_master()
        cmd_qa()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
