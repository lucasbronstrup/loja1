/* Cenas da homenagem: CAPA, TIPOGRAFIA, DESTAQUE, PILHA, MOSAICO, NOME, ESPELHO, FINAL.
 * Todas constroem o DOM a partir de window.DATA e animam pelo motor (engine.js).
 * Tempos em segundos locais do trecho; batida = 0,5 s (120 BPM).
 */
(function () {
  "use strict";
  const { Engine, tw, prog, clamp, lerp, ez, shadowCSS, rng, W, H, SVGNS } = window.HF;
  const D = window.DATA;
  const BEAT = 0.5;
  const TEXT = "#111111";
  const BORDER = 0.02 / 0.96; // borda = 2% da largura externa
  const RADIUS = 0.03;        // raio = 3% da largura externa
  const FADE_IN = 0.06;

  // ---------------------------------------------------------------- utilidades DOM
  function el(tag, cls, parent, css) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (css) Object.assign(e.style, css);
    if (parent) parent.appendChild(e);
    return e;
  }
  function outerW(innerW) {
    return innerW + 2 * innerW * BORDER;
  }
  function co(key) {
    return D.co[key];
  }

  /* cartão de foto: largura interna fixa, altura pela proporção do recorte */
  function card(stage, pid, usage, innerW, opt = {}) {
    const crop = D.crops[pid][usage];
    const ph = D.photos[pid];
    const innerH = opt.innerH || (innerW * crop.h) / crop.w;
    const b = Math.round(innerW * BORDER * 1000) / 1000;
    const w = innerW + 2 * b, h = innerH + 2 * b;
    const R = RADIUS * w;
    const root = el("div", "card", stage, { width: w + "px", height: h + "px", borderRadius: R + "px", background: opt.cutout ? "transparent" : "#fff" });
    const box = el("div", "ph", root, {
      position: "absolute", left: b + "px", top: b + "px", width: innerW + "px", height: innerH + "px",
      borderRadius: Math.max(2, R - b) + "px", overflow: "hidden",
    });
    const k = innerW / crop.w;
    const img = el("img", "", box, {
      position: "absolute", left: -crop.x * k + "px", top: -crop.y * k + "px",
      width: ph.size[0] * k + "px", height: ph.size[1] * k + "px", maxWidth: "none",
    });
    img.src = opt.cutout ? ph.cut : ph.src;
    img.decoding = "sync";
    img.draggable = false;
    return { el: root, w, h, b, innerW, innerH, R, faces: crop.faces, pid, usage, img, scaleSrc: k };
  }

  /* pílula com ponto colorido (nome / "coordenadora") */
  function pill(stage, text, color, size = 36) {
    const p = el("div", "pill", stage, {
      display: "inline-flex", alignItems: "center", gap: Math.round(size * 0.36) + "px",
      padding: `${Math.round(size * 0.36)}px ${Math.round(size * 0.78)}px ${Math.round(size * 0.36)}px ${Math.round(size * 0.62)}px`,
      background: "#fff", borderRadius: "999px", font: `700 ${size}px Poppins`, color: TEXT, whiteSpace: "nowrap", lineHeight: "1.15",
    });
    el("span", "dot", p, { width: Math.round(size * 0.5) + "px", height: Math.round(size * 0.5) + "px", borderRadius: "50%", background: color, flex: "0 0 auto" });
    const t = el("span", "", p);
    t.textContent = text;
    return p;
  }

  /* carimbo: etiqueta branca arredondada com uma palavra */
  function stampEl(stage, text, color, size) {
    const s = el("div", "stamp", stage, {
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      padding: `${Math.round(size * 0.2)}px ${Math.round(size * 0.5)}px ${Math.round(size * 0.24)}px`,
      background: "#fff", borderRadius: "999px", font: `700 ${size}px Poppins`, color, whiteSpace: "nowrap", lineHeight: "1.12",
    });
    s.textContent = text;
    return s;
  }

  /* bloco de texto: linhas -> palavras (-> letras). spec.lines = [[{t, color, serif}]] */
  function textBlock(stage, spec) {
    const size = spec.size;
    const blk = el("div", "tb", stage, { textAlign: spec.align || "center", color: spec.color || TEXT, whiteSpace: "nowrap" });
    const out = { el: blk, lines: [], words: [], letters: [] };
    spec.lines.forEach((line, li) => {
      const ln = el("div", "ln", blk, {
        display: "block", font: `700 ${size}px Poppins`, lineHeight: (spec.lh || 1.04) * size + "px",
        overflow: spec.clip === false ? "visible" : "hidden",
        padding: "0.08em 0.12em 0.2em", margin: "-0.08em -0.12em -0.2em",
      });
      out.lines.push(ln);
      line.forEach((wd, wi) => {
        if (wi > 0) ln.appendChild(document.createTextNode(" "));
        const w = el("span", "w", ln, { display: "inline-block", position: "relative", zIndex: "0" });
        if (wd.color) w.style.color = wd.color;
        if (wd.serif) {
          w.style.font = `italic 400 ${Math.round(size * (spec.serifScale || 1.15))}px "Instrument Serif"`;
          w.style.lineHeight = "1";
        }
        if (wd.grad) {
          w.style.backgroundImage = wd.grad;
          w.style.webkitBackgroundClip = "text";
          w.style.backgroundClip = "text";
          w.style.color = "transparent";
        }
        const word = { el: w, li, wi, text: wd.t, spec: wd, letters: [] };
        if (spec.letters) {
          for (const ch of wd.t) {
            const c = el("span", "ch", w, { display: "inline-block" });
            if (wd.grad) {
              c.style.backgroundImage = wd.grad;
              c.style.webkitBackgroundClip = "text";
              c.style.backgroundClip = "text";
              c.style.color = "transparent";
            }
            c.textContent = ch;
            word.letters.push(c);
            out.letters.push({ el: c, word });
          }
        } else {
          w.textContent = wd.t;
        }
        out.words.push(word);
      });
    });
    return out;
  }

  // ---------------------------------------------------------------- animações de texto
  const anim = {
    /* 1. máscara: palavras sobem de 110% a 0 (power3.out 0,45 s, stagger 0,08) */
    maskIn(eng, words, t0, parent, opt = {}) {
      const st = opt.stagger ?? 0.08, d = opt.dur ?? 0.45;
      words.forEach((w, i) => {
        const lh = w.el.parentElement.getBoundingClientRect().height || 100;
        const s0 = t0 + i * st;
        const prev = w.fn;
        w.inAt = s0;
        w.inEnd = s0 + d;
        w.fn = (t) => {
          let y = tw(t, s0, d, 1.1 * lh, 0, "power3.out");
          let o = t < s0 ? 0 : 1;
          if (w.outAt !== undefined && t >= w.outAt) {
            if (w.outType === "fade") o = 1 - prog(t, w.outAt, 0.2);
            else if (w.outType === "fadeup") {
              // troca simultânea com a frase seguinte: fade de 0,2 s com leve subida na máscara
              o = 1 - prog(t, w.outAt, 0.2);
              y = tw(t, w.outAt, 0.2, 0, -0.35 * lh, "power3.in");
            } else y = tw(t, w.outAt, 0.3, 0, -1.1 * lh, "power3.in");
          }
          return { y, o };
        };
        if (!w.spanObj) w.spanObj = eng.span(w.el, (t) => w.fn(t), parent);
      });
    },
    /* saída por máscara (0,3 s power3.in) ou fade (0,2 s) */
    out(words, t, type = "mask") {
      words.forEach((w) => {
        w.outAt = t;
        w.outType = type;
      });
    },
    /* 2. mola: letras caem e quicam (back.out(1.7), stagger 0,03) */
    mola(eng, letters, t0, parent, opt = {}) {
      const st = opt.stagger ?? 0.03, d = opt.dur ?? 0.4, drop = opt.drop ?? 0.75;
      letters.forEach((L, i) => {
        const size = parseFloat(getComputedStyle(L.el).fontSize);
        const s0 = t0 + i * st;
        L.inAt = s0;
        L.inEnd = s0 + d;
        L.fn = (t) => {
          const y = tw(t, s0, d, -drop * size, 0, "back.out(1.7)");
          let o = clamp((t - s0) / (d * 0.3), 0, 1);
          if (L.outAt !== undefined && t >= L.outAt) o *= 1 - prog(t, L.outAt, 0.2);
          return { y, o };
        };
        eng.span(L.el, (t) => L.fn(t), parent);
      });
    },
    /* 6. respiro: espaçamento largo -> normal (0,8 s power2.out) */
    respiro(eng, lines, t0, parent, opt = {}) {
      const d = opt.dur ?? 0.8, from = opt.from ?? 0.05;
      lines.forEach((ln) => {
        ln.style.display = "block";
        eng.span(ln, (t) => ({ ls: tw(t, t0, d, from, 0, "power2.out"), o: clamp((t - t0) / (d * 0.45), 0, 1) }), parent);
      });
    },
    /* 3. marca-texto: faixa varre a palavra da esquerda para a direita (0,4 s power2.out) */
    marker(eng, word, color, t0) {
      const band = el("span", "band", word.el, {
        position: "absolute", left: "-0.12em", right: "-0.12em", top: "0.2em", bottom: "0.04em",
        background: color, borderRadius: "0.14em", zIndex: "-1", transformOrigin: "0% 50%", transform: "scaleX(0)",
      });
      eng.hook((t) => {
        const sx = prog(t, t0, 0.4, "power2.out");
        band.style.transform = `scaleX(${sx.toFixed(4)})`;
        band.style.opacity = t < t0 ? "0" : "1";
      });
      return band;
    },
    /* 4. sublinhado à mão: traço SVG desenhado em 0,5 s */
    underline(eng, word, color, t0, block) {
      const r = word.el.getBoundingClientRect();
      const br = block.getBoundingClientRect();
      const x0 = r.left - br.left + r.width * 0.02, x1 = r.right - br.left - r.width * 0.02;
      const y = r.bottom - br.top - r.height * 0.06;
      const svg = document.createElementNS(SVGNS, "svg");
      Object.assign(svg.style, { position: "absolute", left: "0px", top: "0px", overflow: "visible", pointerEvents: "none" });
      svg.setAttribute("width", Math.ceil(br.width));
      svg.setAttribute("height", Math.ceil(br.height));
      const p = document.createElementNS(SVGNS, "path");
      const wv = (x1 - x0);
      p.setAttribute("d", `M ${x0} ${y + 4} C ${x0 + wv * 0.3} ${y - 6}, ${x0 + wv * 0.62} ${y + 9}, ${x1} ${y - 3}`);
      p.setAttribute("fill", "none");
      p.setAttribute("stroke", color);
      p.setAttribute("stroke-width", "9");
      p.setAttribute("stroke-linecap", "round");
      svg.appendChild(p);
      block.style.position = "absolute";
      block.appendChild(svg);
      const len = p.getTotalLength();
      p.setAttribute("stroke-dasharray", `${len} ${len}`);
      eng.hook((t) => {
        const u = prog(t, t0, 0.5, "power2.out");
        p.setAttribute("stroke-dashoffset", (len * (1 - u)).toFixed(2));
        let o = t < t0 ? 0 : 1;
        if (word.outAt !== undefined && t >= word.outAt) o = 1 - prog(t, word.outAt, word.outType === "fade" ? 0.2 : 0.3);
        if (word.fadeAt !== undefined) o *= 1 - prog(t, word.fadeAt, 0.2);
        svg.style.opacity = o.toFixed(3);
      });
      return svg;
    },
  };

  /* carimbo animado (5): escala 1,3 -> 1, rotação r0 -> r1 (power4.out 0,3 s) */
  function stamp(eng, stage, text, color, size, x, y, t0, opt = {}) {
    const s = stampEl(stage, text, color, size);
    const w = s.offsetWidth, h = s.offsetHeight;
    const r1 = opt.r ?? -3, r0 = r1 + (opt.dr ?? 6);
    const n = eng.node(s, {
      w, h, world: !!opt.world, shadow: true,
      state: (t) => {
        let o = t < t0 ? 0 : clamp((t - t0) / 0.05, 0, 1);
        return { x, y: y + (opt.yfn ? opt.yfn(t) : 0), s: tw(t, t0, 0.3, 1.3, 1, "power4.out"), r: tw(t, t0, 0.3, r0, r1, "power4.out"), o };
      },
    });
    n.text = true;
    if (opt.maskOutAt !== undefined) {
      // saída por máscara: a etiqueta é recolhida de baixo para cima
      n.update = (t) => {
        const u = prog(t, opt.maskOutAt, 0.3, "power3.in");
        s.style.clipPath = u > 0 ? `inset(0 0 ${(u * 100).toFixed(2)}% 0 round 999px)` : "none";
      };
    }
    eng.event(t0, "carimbo", text);
    return n;
  }

  /* posição de um ponto preso a um nó (offset local girado/escalado) */
  function attach(eng, parent, lx, ly) {
    return (t) => {
      const p = Object.assign({ x: 540, y: 960, r: 0, s: 1, o: 1 }, parent.state(t));
      const a = (p.r * Math.PI) / 180;
      return { x: p.x + (lx * Math.cos(a) - ly * Math.sin(a)) * p.s, y: p.y + (lx * Math.sin(a) + ly * Math.cos(a)) * p.s, r: p.r, s: p.s, o: p.o };
    };
  }

  function pillOnCard(eng, stage, c, cn, key, label, corner = "bl", size = 36) {
    const color = co(key).fill;
    const p = pill(stage, label, color, size);
    const pw = p.offsetWidth, ph = p.offsetHeight;
    const m = Math.max(22, c.w * 0.045);
    const lx = corner.includes("l") ? -c.w / 2 + m + pw / 2 : c.w / 2 - m - pw / 2;
    const ly = corner.includes("b") ? c.h / 2 - m - ph / 2 : -c.h / 2 + m + ph / 2;
    const n = eng.node(p, { w: pw, h: ph, world: cn.world, shadow: true, state: attach(eng, cn, lx, ly) });
    n.text = true;
    return n;
  }

  /* registro de rostos e textos em coordenadas de tela (verificação) */
  function registerFaces(eng, c, n) {
    eng.faceSources = eng.faceSources || [];
    eng.faceSources.push({ c, n });
  }
  function debugAt(eng, t) {
    eng.render(t);
    const faces = [];
    for (const { c, n } of eng.faceSources || []) {
      const a = n.cur;
      if (!a || a.o < 0.5) continue;
      for (const f of c.faces) {
        const pts = [[f.x, f.y], [f.x + f.w, f.y], [f.x, f.y + f.h], [f.x + f.w, f.y + f.h]].map(([u, v]) => {
          const lx = -c.innerW / 2 + u * c.innerW, ly = -c.innerH / 2 + v * c.innerH;
          const r = (a.r * Math.PI) / 180;
          return [a.x + (lx * Math.cos(r) - ly * Math.sin(r)) * a.s, a.y + (lx * Math.sin(r) + ly * Math.cos(r)) * a.s];
        });
        const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
        // visível só se estiver dentro da área da foto (clip) — aproximação pelo centro
        faces.push({ pid: c.pid, usage: c.usage, x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys), o: a.o, cover: c.cover || false, z: [...eng.stage.children].indexOf(n.el) });
      }
    }
    const texts = [];
    eng.root.querySelectorAll(".tb .w, .stamp, .pill, .namechar, .closing .w").forEach((e) => {
      const r = e.getBoundingClientRect();
      const cs = getComputedStyle(e);
      let op = 1, p = e;
      while (p && p !== eng.root) {
        op *= parseFloat(getComputedStyle(p).opacity);
        if (getComputedStyle(p).visibility === "hidden") op = 0;
        p = p.parentElement;
      }
      // recorta pelo ancestral com overflow:hidden (máscara de linha)
      let x0 = r.left, y0 = r.top, x1 = r.right, y1 = r.bottom;
      for (let a = e.parentElement; a && a !== eng.root; a = a.parentElement) {
        if (getComputedStyle(a).overflow === "hidden") {
          const ar = a.getBoundingClientRect();
          x0 = Math.max(x0, ar.left); y0 = Math.max(y0, ar.top); x1 = Math.min(x1, ar.right); y1 = Math.min(y1, ar.bottom);
        }
      }
      if (x1 - x0 > 1 && y1 - y0 > 1 && op > 0.5) texts.push({ cls: e.className, text: e.textContent.trim().slice(0, 30), x0, y0, x1, y1, fs: parseFloat(cs.fontSize), op, z: [...eng.stage.children].indexOf(e.closest(".stage > *")) });
    });
    return { t, faces, texts };
  }

  // ---------------------------------------------------------------- fundo
  function bgRadial(root) {
    const b = el("div", "bg", null, { position: "absolute", inset: "0", background: "radial-gradient(farthest-corner at 50% 36%, #FFFFFF 0%, #F3F3F0 100%)" });
    root.insertBefore(b, root.querySelector(".stage"));
  }
  function bgPhoto(root, pid) {
    const ph = D.photos[pid];
    const wrap = el("div", "bgp", null, { position: "absolute", inset: "0", overflow: "hidden", background: "#F3F3F0" });
    root.insertBefore(wrap, root.querySelector(".stage"));
    const scale = Math.max(W / ph.size[0], H / ph.size[1]) * 1.18;
    const iw = ph.size[0] * scale, ih = ph.size[1] * scale;
    const img = el("img", "", wrap, {
      position: "absolute", left: (W - iw) / 2 + "px", top: (H - ih) / 2 + "px", width: iw + "px", height: ih + "px", maxWidth: "none",
      filter: "blur(40px) saturate(0.7) brightness(1.05)",
    });
    img.src = ph.src;
    el("div", "", wrap, { position: "absolute", inset: "0", background: "rgba(255,255,255,0.72)" });
  }

  // ---------------------------------------------------------------- whip (vertical, para cima)
  const WHIP_OUT = 525, WHIP_IN = 700; // velocidade contínua no corte: 3x525/0,45 = 3x700/0,6 = 3500 px/s
  function whipOutY(t, D) {
    return -WHIP_OUT * prog(t, D - 0.45, 0.45, "power3.in");
  }
  function whipInY(t) {
    return WHIP_IN * (1 - prog(t, 0, 0.6, "power3.out"));
  }

  // ================================================================ CENAS
  const S = {};

  /* ---------- CAPA (quadro 0) ---------- */
  S.capa = function (eng) {
    const st = eng.stage;
    const g = D.plan.graziela.abertura, e = D.plan.eduarda.abertura;
    const slots = [
      [200, 845, -4, "graziela", g[0]], [540, 830, 2, "eduarda", e[0]], [880, 845, 4, "graziela", g[1]],
      [200, 1290, 3, "eduarda", e[1]], [540, 1275, -2, "graziela", g[2]], [880, 1290, -4, "eduarda", e[2]],
    ];
    for (const [x, y, r, key, pid] of slots) {
      const c = card(st, pid, "abertura", 288);
      const n = eng.node(c.el, { w: c.w, h: c.h, world: false, shadow: true, mb: false, state: () => ({ x, y, r }) });
      registerFaces(eng, c, n);
    }
    // título
    const box = el("div", "titlebox", st, {
      position: "absolute", background: "#fff", padding: "0 50px", textAlign: "center",
      font: "700 110px Poppins", color: TEXT, lineHeight: "1.18", whiteSpace: "nowrap",
      display: "flex", flexDirection: "column", justifyContent: "center",
    });
    const l1 = el("div", "tb", box); l1.innerHTML = '<span class="w">Graziela</span>';
    const l2 = el("div", "tb", box); l2.innerHTML = '<span class="w">&amp; Eduarda</span>';
    const bw = box.offsetWidth, bh = 603 - 262;
    box.style.height = bh + "px";
    box.style.borderRadius = Math.round(0.028 * bw) + "px";
    const bn = eng.node(box, { w: bw, h: bh, world: false, shadow: true, mb: false, state: () => ({ x: 540, y: (262 + 603) / 2 }) });
    bn.text = true;
  };

  /* ---------- ABERTURA: TIPOGRAFIA ---------- */
  S.abertura = function (eng) {
    const st = eng.stage;
    const g = D.plan.graziela.abertura, e = D.plan.eduarda.abertura;
    const LAYER = { far: { s: 0.8, dof: 9, v: 18 }, mid: { s: 1.0, dof: 7, v: 30 }, near: { s: 1.2, dof: 5, v: 46 } };
    const slots = [
      { x: 540, y: 455, r: -3, layer: "far", key: "graziela", pid: g[0], target: true },
      { x: 205, y: 565, r: -6, layer: "mid", key: "eduarda", pid: e[0] },
      { x: 880, y: 560, r: 5, layer: "near", key: "eduarda", pid: e[1] },
      { x: 205, y: 1430, r: 6, layer: "near", key: "graziela", pid: g[1] },
      { x: 540, y: 1545, r: 3, layer: "far", key: "eduarda", pid: e[2] },
      { x: 880, y: 1410, r: -5, layer: "mid", key: "graziela", pid: g[2] },
    ];
    const Z0 = 0.8, ZD = 1.2; // aproximação final (1,2 s) com o riser
    const zu = (t) => prog(t, Z0, ZD, "power2.inOut");
    const drift = (sl, t) => {
      const L = LAYER[sl.layer];
      return { x: sl.x + 7 * Math.sin(1.7 * t + sl.x * 0.01), y: sl.y - L.v * t };
    };
    // câmera: deriva suave e aproximação ao cartão-alvo (Graziela, mesmo retrato do DESTAQUE)
    const tgt = slots[0];
    const sEnd = 1080 / (outerW(346) * LAYER.far.s); // alvo termina com a largura da tela
    const camDrift = (t) => ({ cx: 540 + 6 * Math.sin(0.9 * t), cy: 960 - 10 * t, s: 1 + 0.01 * t });
    let P0 = null;
    eng.camera((t) => {
      const c0 = camDrift(Math.min(t, Z0));
      const u = zu(t);
      if (u <= 0) return camDrift(t);
      const tp = drift(tgt, t);
      if (!P0) {
        const p = drift(tgt, Z0);
        P0 = { x: (p.x - c0.cx) * c0.s + 540, y: (p.y - c0.cy) * c0.s + 960 };
      }
      const s = c0.s * Math.pow(sEnd / c0.s, u);
      const P = { x: lerp(P0.x, 540, u), y: lerp(P0.y, 960, u) };
      return { cx: tp.x - (P.x - 540) / s, cy: tp.y - (P.y - 960) / s, s };
    });
    const order = [0, 1, 2, 3, 4, 5];
    slots.forEach((sl, i) => {
      const c = card(st, sl.pid, "abertura", 346);
      const L = LAYER[sl.layer];
      const t0 = -0.06 + order.indexOf(i) * (BEAT / 4);
      const n = eng.node(c.el, {
        w: c.w, h: c.h, world: true, shadow: true,
        state: (t) => {
          const p = drift(sl, t);
          const ue = prog(t, t0, 0.55, "power3.out");
          const u = zu(t);
          let r = sl.r, dof = L.dof, o = clamp((t - t0) / 0.22, 0, 1);
          if (sl.target) {
            r = lerp(sl.r, -4, u);
            dof = L.dof * (1 - u);
          } else {
            dof = u < 0.7 ? lerp(L.dof, 14, u / 0.7) : lerp(14, 9, (u - 0.7) / 0.3);
            o *= u < 0.7 ? lerp(1, 0.7, u / 0.7) : lerp(0.7, 0.4, (u - 0.7) / 0.3);
          }
          return { x: p.x, y: p.y + 70 * (1 - ue), s: L.s * lerp(0.6, 1, ue), r, o, dof };
        },
      });
      registerFaces(eng, c, n);
      if (sl.target) eng.targetNode = n;
    });
    // camada de texto (HUD), sempre por cima
    const rowsSpec = [
      { lines: [[{ t: "Duas" }]], size: 104 },
      { lines: [[{ t: "coordenadoras" }]], size: 104 },
      { lines: [[{ t: "no" }, { t: "coração.", serif: true, grad: "linear-gradient(90deg, #B25730 0%, #B25730 30%, #1F6F7D 70%, #1F6F7D 100%)" }]], size: 104, letters: true, clip: false, serifScale: 1.25 },
    ];
    const rowY = [792, 960, 1128];
    const tilt = [-1.5, 1, -1];
    rowsSpec.forEach((spec, i) => {
      const p = el("div", "pillrow", st, { background: "#fff", borderRadius: "999px", padding: "10px 44px 14px", display: "inline-block", overflow: "hidden" });
      const tb = textBlock(p, spec);
      tb.el.style.position = "relative";
      const pw = p.offsetWidth, ph = p.offsetHeight;
      const t0 = i < 2 ? 0 : BEAT / 2;
      const n = eng.node(p, {
        w: pw, h: ph, world: false, shadow: true,
        state: (t) => ({ x: 540, y: rowY[i], r: tilt[i], s: tw(t, t0, 0.45, 0.55, 1, "back.out(1.6)"), o: t < t0 ? 0 : 1 }),
      });
      n.text = true;
      if (i < 2) anim.maskIn(eng, tb.words, i * 0.08, n, { stagger: 0.08 });
      else {
        p.style.overflow = "visible";
        anim.mola(eng, tb.letters, t0 + 0.06, n, { stagger: 0.03, dur: 0.4, drop: 0.7 });
      }
    });
    eng.event(0, "frase-chave", "Duas coordenadoras");
    eng.event(BEAT / 2, "frase-chave", "no coração.");
    eng.event(Z0, "zoom-through", "aproximação com o riser");
  };

  /* ---------- DESTAQUE ---------- */
  S.destaque = function (eng, key, opts) {
    const st = eng.stage;
    const pid = D.plan[key].destaque;
    const C = co(key);
    const c = card(st, pid, "destaque", 780);
    const cx = 540, cy = 1052;
    const cn = eng.node(c.el, {
      w: c.w, h: c.h, world: true, shadow: true,
      state: (t) => {
        const u = prog(t, 0.5, 1.5, "sine.inOut");
        return {
          x: cx + 4 * u, y: cy - 12 * u,
          s: tw(t, 0, 0.5, 0.86, 1, "back.out(1.4)") * (1 + 0.012 * u),
          r: tw(t, 0, 0.5, -4, 0, "back.out(1.4)") + 0.7 * u,
        };
      },
    });
    registerFaces(eng, c, cn);
    pillOnCard(eng, st, c, cn, key, C.name, "bl");
    const tb = textBlock(st, {
      size: 104, lh: 1.08, serifScale: 1.23,
      lines: [[{ t: C.name + "," }], [{ t: opts.word, serif: true, color: C.text }]],
    });
    const tw_ = tb.el.offsetWidth, th = tb.el.offsetHeight;
    const tn = eng.node(tb.el, { w: tw_, h: th, world: false, mb: false, state: () => ({ x: 540, y: 252 + th / 2 }) });
    tn.text = true;
    anim.maskIn(eng, tb.words, 0, tn, { stagger: 0.08 });
    anim.underline(eng, tb.words[1], C.fill, 0.55, tb.el);
    eng.event(0.5, "pouso", `cartão DESTAQUE (${C.name})`);
    eng.event(0, "frase-chave", `${C.name}, ${opts.word}`);
  };

  /* ---------- PILHA ---------- */
  S.pilha = function (eng, key) {
    const st = eng.stage;
    const C = co(key);
    const [p1, p2, p3] = D.plan[key].pilha;
    const sway = (t) => 5 * Math.sin((2 * Math.PI * t) / 2.0);
    const c3 = card(st, p3, "pilha_terceiro", 690);
    const n3 = eng.node(c3.el, { w: c3.w, h: c3.h, world: true, shadow: true, state: (t) => ({ x: 584, y: 1086 + sway(t) * 0.6, r: 6 }) });
    const c2 = card(st, p2, "pilha_segundo", 720);
    const n2 = eng.node(c2.el, {
      w: c2.w, h: c2.h, world: true, shadow: true,
      state: (t) => ({ x: 514, y: 1058 + sway(t) * 0.8, r: -4.5, s: tw(t, 2 * BEAT, 0.5, 0.96, 1, "power2.out") }),
    });
    const c1 = card(st, p1, "pilha_topo", 740);
    const T = 2 * BEAT; // batida 3: arremesso
    const n1 = eng.node(c1.el, {
      w: c1.w, h: c1.h, world: true, shadow: true,
      state: (t) => ({
        x: 540 + 1500 * prog(t, T, 0.42, "power2.in"),
        y: 1028 + sway(t) - 90 * prog(t, T, 0.42, "power1.out"),
        r: 2 + 30 * prog(t, T, 0.42, "power2.in"),
        o: t > T + 0.42 ? 0 : 1,
      }),
    });
    for (const [c, n] of [[c3, n3], [c2, n2], [c1, n1]]) registerFaces(eng, c, n);
    stamp(eng, st, "carinho", C.text, 96, 540, 392, BEAT, { r: -3, dr: 7 });
    eng.event(T, "arremesso", "cartão do topo");
  };

  /* ---------- MOSAICO ---------- */
  S.mosaico = function (eng, key, opts) {
    const st = eng.stage;
    const C = co(key);
    const plan = D.plan[key];
    const pids = plan.mosaico; // TL, TR(zoom, foto do NOME), BL, BR
    const pos = [[328, 778], [752, 778], [328, 1298], [752, 1298]];
    const ZT = 2.5, ZD = 1.5;
    const zu = (t) => prog(t, ZT, ZD, "power2.inOut");
    const NOME_W = D.nome.card_outer_w; // largura externa do cartão do NOME
    const thumbs = [];
    const camDrift = (t) => ({ cx: 540 + 4 * Math.sin(1.3 * t), cy: 960, s: 1 + 0.02 * prog(t, 0.6, ZT - 0.6, "sine.inOut") });
    const tgtWorld = { x: pos[1][0], y: pos[1][1] };
    const cam0 = camDrift(ZT);
    const P0 = { x: (tgtWorld.x - cam0.cx) * cam0.s + 540, y: (tgtWorld.y - cam0.cy) * cam0.s + 960 };
    const sEnd = NOME_W / outerW(384);
    eng.camera((t) => {
      const u = zu(t);
      if (u <= 0) return camDrift(t);
      const s = cam0.s * Math.pow(sEnd / cam0.s, u);
      const P = { x: lerp(P0.x, 540, u), y: lerp(P0.y, 960, u) };
      return { cx: tgtWorld.x - (P.x - 540) / s, cy: tgtWorld.y - (P.y - 960) / s, s };
    });
    pids.forEach((pid, i) => {
      const isN = pid === plan.nome;
      const c = card(st, pid, isN ? "nome" : "mosaico", 384, { innerH: 480 });
      const t0 = -0.05 + i * (BEAT / 4);
      const n = eng.node(c.el, {
        w: c.w, h: c.h, world: true, shadow: true,
        state: (t) => {
          const u = zu(t);
          return {
            x: pos[i][0], y: pos[i][1],
            s: tw(t, t0, 0.5, 0, 1, "back.out(1.6)"),
            o: t < t0 ? 0 : isN ? 1 : u < 0.7 ? lerp(1, 0.7, u / 0.7) : lerp(0.7, 0.4, (u - 0.7) / 0.3),
            dof: isN ? 0 : u < 0.7 ? 14 * (u / 0.7) : lerp(14, 9, (u - 0.7) / 0.3),
          };
        },
      });
      registerFaces(eng, c, n);
      thumbs.push(n);
      if (isN) eng.targetNode = n;
    });
    const tb = textBlock(st, { size: 96, lh: 1.06, lines: opts.lines, serifScale: 1.18 });
    const th = tb.el.offsetHeight;
    const tn = eng.node(tb.el, { w: tb.el.offsetWidth, h: th, world: false, mb: false, state: () => ({ x: 540, y: 252 + th / 2 }) });
    tn.text = true;
    anim.maskIn(eng, tb.words, 0, tn, { stagger: 0.08 });
    anim.out(tb.words, ZT, "mask");
    stamp(eng, st, "gratidão", C.text, 52, 540, 1038, 2 * BEAT, { r: -3, dr: 7, maskOutAt: ZT });
    eng.event(0, "frase-chave", opts.lines.flat().map((w) => w.t).join(" "));
    eng.event(ZT, "zoom-through", "aproximação à miniatura do NOME");
  };

  /* ---------- NOME ---------- */
  S.nome = function (eng, key) {
    const st = eng.stage;
    const C = co(key);
    const pid = D.plan[key].nome;
    const L = D.nome.names[key];
    const DUR = eng.D;
    eng.camera((t) => {
      const s = 1 + 0.06 * prog(t, 0, DUR, "power1.inOut");
      const wy = whipOutY(t, DUR);
      return { cx: 540, cy: 960 - wy / s, s };
    });
    const IW = D.nome.inner_w, IH = D.nome.inner_h;
    const c = card(st, pid, "nome", IW, { innerH: IH });
    const cn = eng.node(c.el, { w: c.w, h: c.h, world: true, shadow: true, state: () => ({ x: 540, y: 960 }) });
    registerFaces(eng, c, cn);
    // nome gigante: letras com contorno (camada de traço + camada branca)
    const fs = D.nome.font_size, sw = D.nome.stroke;
    const nameBox = el("div", "namebox", st, { position: "absolute" });
    const total = L.width;
    const boxW = total + 2 * sw + 8, boxH = fs * 1.4;
    nameBox.style.width = boxW + "px";
    nameBox.style.height = boxH + "px";
    const base = fs * 1.05; // linha de base dentro da caixa
    let x = sw + 4;
    const letters = [];
    [...L.text].forEach((ch, i) => {
      const wrap = el("div", "namechar", nameBox, { position: "absolute", left: x + "px", top: "0px", width: L.letter_advances[i] + "px", height: boxH + "px", font: `700 ${fs}px Poppins`, lineHeight: base * 2 + "px" });
      const sEl = el("span", "", wrap, { position: "absolute", left: "0", top: "0", height: base * 2 + "px", lineHeight: "normal", color: C.fill, webkitTextStroke: `${2 * sw}px ${C.fill}`, paintOrder: "stroke fill" });
      const fEl = el("span", "", wrap, { position: "absolute", left: "0", top: "0", color: "#fff", lineHeight: "normal" });
      sEl.textContent = ch;
      fEl.textContent = ch;
      letters.push({ wrap, sEl, fEl, x });
      x += L.letter_advances[i];
    });
    // linha de base medida: sonda inline-block alinhada pela base
    const probeWrap = el("div", "", st, { position: "absolute", left: "0", top: "0", font: `700 ${fs}px Poppins`, lineHeight: "normal", whiteSpace: "nowrap" });
    probeWrap.textContent = "E";
    const probe = el("span", "", probeWrap, { display: "inline-block", width: "1px", height: "0px", verticalAlign: "baseline" });
    const baseInSpan = probe.getBoundingClientRect().top - probeWrap.getBoundingClientRect().top;
    probeWrap.remove();
    const ny = L.baseline_y - baseInSpan + boxH / 2; // centro da caixa em y de tela (quadro 0, câmera 1)
    const nn = eng.node(nameBox, { w: boxW, h: boxH, world: true, mb: true, state: () => ({ x: 540, y: ny }) });
    nn.text = true;
    letters.forEach((Lt, i) => {
      const t0 = i * 0.04;
      eng.span(Lt.wrap, (t) => ({ y: tw(t, t0, 0.45, 80, 0, "back.out(1.6)"), s: tw(t, t0, 0.45, 0.82, 1, "back.out(1.6)"), o: clamp((t - t0) / 0.12, 0, 1) }), nn);
    });
    // recorte por cima (mesma geometria da foto: alinhado ao pixel)
    const cut = card(st, pid, "nome", IW, { innerH: IH, cutout: true });
    cut.el.style.background = "transparent";
    const cutn = eng.node(cut.el, { w: cut.w, h: cut.h, world: true, shadow: false, state: () => ({ x: 540, y: 960 }) });
    // etiqueta "coordenadora" (carimbo na batida 3)
    const p = pill(st, "coordenadora", C.fill, 36);
    const pw = p.offsetWidth, ph = p.offsetHeight;
    const T3 = 2 * BEAT;
    const pn = eng.node(p, {
      w: pw, h: ph, world: true, shadow: true,
      state: (t) => ({ x: 540, y: 960 + IH / 2 - 44 - ph / 2, s: tw(t, T3, 0.3, 1.3, 1, "power4.out"), r: tw(t, T3, 0.3, 4, -1.5, "power4.out"), o: t < T3 ? 0 : clamp((t - T3) / 0.05, 0, 1) }),
    });
    pn.text = true;
    eng.nameDebug = { nameBox, ny, baseline: L.baseline_y };
    eng.event(0, "nome", `nome gigante ${L.text}`);
    eng.event(T3, "carimbo", "coordenadora");
    eng.event(DUR, "whip", "whip de saída (pico no corte)");
  };

  /* ---------- ESPELHO (pivô) ---------- */
  S.espelho = function (eng, opts) {
    const st = eng.stage;
    eng.camera((t) => ({ cx: 540, cy: 960 - whipInY(t), s: 1 }));
    const mk = (key, y, dir) => {
      const pid = D.plan[key].espelho;
      const c = card(st, pid, "espelho", 691.2);
      const n = eng.node(c.el, {
        w: c.w, h: c.h, world: true, shadow: true,
        state: (t) => ({ x: 540 + dir * 560 * (1 - prog(t, 0, 0.5, "power3.out")), y: y + 5 * Math.sin((2 * Math.PI * Math.max(0, t - 0.5)) / 3) }),
      });
      registerFaces(eng, c, n);
      pillOnCard(eng, st, c, n, key, co(key).name, "bl");
      return n;
    };
    mk("graziela", 470, -1);
    mk("eduarda", 1330, +1);
    const G = co("graziela"), E = co("eduarda");
    // grade fixa de 3 linhas (centros 796 / 900 / 1004): a frase que sai e a que entra usam as mesmas
    // máscaras de linha, então a troca simultânea é limpa
    const LH = 104, FIRST_LINE = 796;
    const phrases = [
      { lines: [[{ t: "Gostamos" }], [{ t: "muito" }], [{ t: "da" }, { t: "Graziela", color: G.text }]], at: 0.25, out: 2.0 },
      { lines: [[{ t: "Nunca" }, { t: "vamos" }], [{ t: "esquecer" }], [{ t: "a" }, { t: "Eduarda.", color: E.text }]], at: 2.0, out: 4.0 },
      { lines: [[{ t: "Ninguém" }, { t: "substitui" }], [{ t: "ninguém." }]], at: 4.0, out: 5.7 },
    ];
    phrases.forEach((ph, i) => {
      const tb = textBlock(st, { size: 96, lh: LH / 96, lines: ph.lines });
      const w = tb.el.offsetWidth, h = ph.lines.length * LH;
      const tn = eng.node(tb.el, { w, h, world: true, mb: true, state: () => ({ x: 540, y: FIRST_LINE - LH / 2 + h / 2 }) });
      tn.text = true;
      anim.maskIn(eng, tb.words, ph.at, tn, { stagger: 0.08 });
      anim.out(tb.words, ph.out, i < 2 ? "fadeup" : "mask");
      if (i === 2) {
        anim.marker(eng, tb.words[0], G.band, 4.32);
        anim.marker(eng, tb.words[2], E.band, 4.4);
      }
      eng.event(ph.at, "frase-chave", ph.lines.flat().map((w) => w.t).join(" "));
    });
    // coração desenhado traço a traço (metade terracota, metade azul-petróleo)
    const svg = document.createElementNS(SVGNS, "svg");
    svg.setAttribute("width", "180");
    svg.setAttribute("height", "160");
    svg.setAttribute("viewBox", "-90 -78 180 160");
    svg.style.overflow = "visible";
    st.appendChild(svg);
    const halves = [
      ["M 0 -36 C -12 -62 -74 -64 -74 -14 C -74 22 -32 46 0 74", G.fill],
      ["M 0 -36 C 12 -62 74 -64 74 -14 C 74 22 32 46 0 74", E.fill],
    ].map(([d, col]) => {
      const p = document.createElementNS(SVGNS, "path");
      p.setAttribute("d", d);
      p.setAttribute("fill", "none");
      p.setAttribute("stroke", col);
      p.setAttribute("stroke-width", "10");
      p.setAttribute("stroke-linecap", "round");
      p.setAttribute("stroke-linejoin", "round");
      svg.appendChild(p);
      const len = p.getTotalLength();
      p.setAttribute("stroke-dasharray", `${len} ${len}`);
      return { p, len };
    });
    const HT = 4.0 + 2 * BEAT; // compasso 3, batida 3
    const hn = eng.node(svg, { w: 180, h: 160, world: true, mb: false, state: (t) => ({ x: 540, y: 1020, o: t < HT ? 0 : 1 }) });
    eng.hook((t) => {
      const u = prog(t, HT, 0.7, "power1.inOut");
      halves.forEach(({ p, len }) => p.setAttribute("stroke-dashoffset", (len * (1 - u)).toFixed(2)));
    });
    eng.event(0.5, "pouso", "dois cartões do ESPELHO");
    eng.event(4.0, "frase-chave", "Ninguém substitui ninguém. (sinal)");
    eng.event(HT, "coracao", "coração desenhado");
  };

  /* ---------- FINAL ---------- */
  S.final1 = function (eng) {
    const st = eng.stage;
    const pid = D.finais[0];
    const E = co("eduarda");
    eng.camera((t) => ({ cx: 540, cy: 960 - whipInY(t), s: 1 }));
    const c = card(st, pid, "final", 720);
    const cy = 915;
    const cn = eng.node(c.el, {
      w: c.w, h: c.h, world: false, shadow: true,
      state: (t) => ({ x: 540, y: cy + WHIP_IN * (1 - prog(t, 0, 0.5, "power3.out")), s: 1 + 0.08 * prog(t, 0.5, 3.5, "sine.inOut") }),
    });
    c.cover = true;
    registerFaces(eng, c, cn);
    const tb = textBlock(st, {
      size: 96, lh: 1.02, letters: true, clip: false, serifScale: 1.2,
      lines: [[{ t: "Eduarda,", color: E.text }], [{ t: "esse" }, { t: "momento", serif: true, color: E.text }], [{ t: "fica" }, { t: "com" }, { t: "a" }, { t: "gente." }]],
    });
    const w = tb.el.offsetWidth, h = tb.el.offsetHeight;
    const tn = eng.node(tb.el, { w, h, world: true, mb: true, state: () => ({ x: 540, y: 262 + h / 2 }) });
    tn.text = true;
    let li = 0;
    tb.lines.forEach((ln, i) => {
      const ls = tb.letters.filter((L) => L.word.li === i);
      anim.mola(eng, ls, 0.25 + 0.1 * i, tn, { stagger: 0.03, dur: 0.4, drop: 0.7 });
      ls.forEach((L) => (L.outAt = 3.8));
    });
    const mw = tb.words.find((w) => w.text === "momento");
    mw.fadeAt = 3.8;
    anim.underline(eng, mw, E.fill, 1.35, tb.el);
    eng.event(0.5, "pouso", "foto final 1");
    eng.event(0.25, "frase-chave", "Eduarda, esse momento fica com a gente.");
  };

  S.final2 = function (eng) {
    const st = eng.stage;
    const pid = D.finais[1];
    const G = co("graziela"), E = co("eduarda");
    // confete retangular (atrás do cartão e do texto)
    const conf = el("div", "confetti", st, { position: "absolute", inset: "0" });
    const R = rng(1708);
    const cols = [G.fill, E.fill, G.text, E.text];
    const T3 = 2 * BEAT;
    for (let i = 0; i < 36; i++) {
      const left = i % 2 === 0;
      const x0 = left ? 150 : 930, y0 = 880 + R() * 60;
      const ang = ((left ? -62 : -118) + (R() - 0.5) * 50) * (Math.PI / 180);
      const sp = 950 + R() * 650;
      const vx = Math.cos(ang) * sp, vy = Math.sin(ang) * sp;
      const rot0 = R() * 360, wr = (R() - 0.5) * 900, flip = 6 + R() * 8;
      const piece = el("div", "cf", conf, { background: cols[i % 4], borderRadius: "2px" });
      const pw = 13 + R() * 6, ph = 22 + R() * 8;
      eng.node(piece, {
        w: pw, h: ph, world: false, mb: true,
        state: (t) => {
          const tt = Math.max(0, t - T3);
          const drag = (1 - Math.exp(-2.2 * tt)) / 2.2;
          const x = x0 + vx * drag + 40 * Math.sin(3 * tt + i);
          const y = y0 + vy * drag + 0.5 * 1500 * tt * tt * 0.55;
          return { x, y, r: rot0 + wr * tt, s: 1, o: t < T3 ? 0 : 1, sy: Math.cos(flip * tt) };
        },
        update: (t, a) => {
          piece.style.transform += ` scaleY(${Math.cos((6 + (i % 7)) * Math.max(0, t - T3)).toFixed(3)})`;
        },
      });
    }
    const c = card(st, pid, "final", 480);
    const cy = 745;
    const cn = eng.node(c.el, { w: c.w, h: c.h, world: false, shadow: true, state: (t) => ({ x: 540, y: cy, s: 1.08 - 0.08 * prog(t, 0, 4, "sine.inOut") }) });
    c.cover = true;
    registerFaces(eng, c, cn);
    // encerramento: duas linhas, 80 px, mesmo tamanho, entram juntas no compasso 18
    const T18 = 2.0;
    const box = el("div", "closing", st, { textAlign: "center" });
    const lines = [["Graziela, bem-vinda.", G.text], ["Eduarda, gratidão.", E.text]];
    const lineEls = lines.map(([txt, col]) => {
      const d = el("div", "ln", box, { font: "700 80px Poppins", lineHeight: "104px", color: col, whiteSpace: "nowrap" });
      const w = el("span", "w", d);
      w.textContent = txt;
      return d;
    });
    const bw = Math.max(...lineEls.map((d) => d.offsetWidth)) + 40, bh = box.offsetHeight;
    box.style.width = bw + "px";
    const bn = eng.node(box, { w: bw, h: bh, world: false, mb: false, state: () => ({ x: 540, y: 1396 }) });
    bn.text = true;
    anim.respiro(eng, lineEls, T18, bn, { from: 0.05, dur: 0.8 });
    eng.event(0, "pouso", "foto final 2 (corte seco)");
    eng.event(T3, "confete", "confete retangular");
    eng.event(T18, "frase-chave", "linhas de encerramento");
  };

  window.SCENES = { S, debugAt, anim, card, bgRadial, bgPhoto, outerW };
})();
