/* Minoran — efeitos compartilhados (GSAP). Tudo é adicionado a uma timeline pausada,
   em posições explícitas, para ser seek-safe. Sem Math.random, Date, rAF ou timers. */
(function () {
  if (window.MN && window.MN.__v === 3) return;
  var MN = { __v: 3 };

  /* ---------- registro de plugins e eases ---------- */
  MN.init = function () {
    gsap.registerPlugin(CustomEase, SplitText, DrawSVGPlugin, MorphSVGPlugin);
    if (!CustomEase.get("mn.out")) {
      // expo.out suave
      CustomEase.create("mn.out", "M0,0 C0.16,0.84 0.3,1 1,1");
      // curva 0.7,0 -> 0.3,1
      CustomEase.create("mn.inOut", "M0,0 C0.7,0 0.3,1 1,1");
      // salto de ponteiro de quartzo: sobe em ~25 % do tempo, overshoot de ~8 %, assenta
      CustomEase.create("mn.tick", "M0,0 C0.05,0 0.09,1.08 0.24,1.08 C0.36,1.08 0.46,0.985 0.62,0.995 C0.76,1.003 0.88,1 1,1");
    }
  };
  // duração do tique: assenta em 80 ms depois do pico (pico em ~0.24 * 0.11 s)
  MN.TICK_DUR = 0.11;

  /* ---------- aleatório semeado ---------- */
  MN.rng = function (seed) {
    var a = seed >>> 0;
    return function () {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };
  MN.range = function (r, lo, hi) {
    return lo + (hi - lo) * r();
  };

  /* ---------- cena ---------- */
  MN.scene = function (id) {
    var root = document.querySelector('[data-composition-id="' + id + '"]');
    var tlData = window.MINORAN_TL.scene(id);
    return {
      id: id,
      root: root,
      dur: tlData.dur,
      data: tlData,
      q: function (sel) {
        return root.querySelector(sel);
      },
      qa: function (sel) {
        return Array.prototype.slice.call(root.querySelectorAll(sel));
      },
      cue: function (name) {
        return window.MINORAN_TL.cue(id, name);
      },
    };
  };

  MN.fonts = function (specs) {
    return Promise.all(
      specs.map(function (s) {
        return document.fonts.load(s, "L’élégance À é 0123456789");
      }),
    ).then(function () {
      return document.fonts.ready;
    });
  };

  /* ---------- SVG: filtros de motion blur direcional ---------- */
  MN.defs = function (root, id) {
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "mn-svgdefs");
    svg.setAttribute("aria-hidden", "true");
    svg.id = id + "-defs";
    var defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    svg.appendChild(defs);
    root.appendChild(svg);
    return defs;
  };
  // axis: "x" | "y" | "xy"
  MN.blurFilter = function (defs, id, axis) {
    var NS = "http://www.w3.org/2000/svg";
    var f = document.createElementNS(NS, "filter");
    f.id = id;
    f.setAttribute("color-interpolation-filters", "sRGB");
    if (axis === "x") {
      f.setAttribute("x", "-20%");
      f.setAttribute("width", "140%");
      f.setAttribute("y", "0%");
      f.setAttribute("height", "100%");
    } else if (axis === "y") {
      f.setAttribute("x", "0%");
      f.setAttribute("width", "100%");
      f.setAttribute("y", "-20%");
      f.setAttribute("height", "140%");
    } else {
      f.setAttribute("x", "-20%");
      f.setAttribute("width", "140%");
      f.setAttribute("y", "-20%");
      f.setAttribute("height", "140%");
    }
    var g = document.createElementNS(NS, "feGaussianBlur");
    g.setAttribute("stdDeviation", "0 0");
    g.setAttribute("edgeMode", "duplicate");
    f.appendChild(g);
    defs.appendChild(f);
    return g;
  };
  // blur proporcional à velocidade: a curva do blur acompanha a derivada da curva de movimento
  MN.blurPulse = function (tl, el, node, o) {
    var axis = o.axis || "x";
    var fmt = function (v) {
      return axis === "x" ? v + " 0" : axis === "y" ? "0 " + v : v + " " + v;
    };
    tl.set(el, { filter: "url(#" + node.parentNode.id + ")" }, o.at);
    tl.fromTo(node, { attr: { stdDeviation: fmt(o.from || 0) } }, { attr: { stdDeviation: fmt(o.to) }, duration: o.dur, ease: o.ease || "none", immediateRender: false }, o.at);
    if (o.clearAt !== undefined) tl.set(el, { filter: "none" }, o.clearAt);
  };

  /* ---------- texto ---------- */
  MN.split = function (el, mask) {
    return new SplitText(el, { type: "words,chars", mask: mask || "words", wordsClass: "mn-w", charsClass: "mn-c" });
  };
  // revelação por máscara: palavras ou caracteres sobem de dentro da máscara
  MN.splitReveal = function (tl, targets, o) {
    tl.fromTo(
      targets,
      Object.assign({ yPercent: 112, opacity: 0 }, o.from || {}),
      Object.assign({ yPercent: 0, opacity: 1, duration: o.dur || 0.7, ease: o.ease || "mn.out", stagger: o.stagger === undefined ? 0.03 : o.stagger, immediateRender: true }, o.to || {}),
      o.at,
    );
  };
  // saída padrão de texto: blur 0->12, y -20, opacity 0
  MN.textOut = function (tl, targets, o) {
    tl.to(targets, { filter: "blur(12px)", y: -20, opacity: 0, duration: o.dur || 0.38, ease: o.ease || "power2.in", stagger: o.stagger === undefined ? 0.012 : o.stagger }, o.at);
  };
  // gradiente ouro contínuo por palavra quando os caracteres são caixas separadas
  MN.goldChars = function (wordEl) {
    var chars = wordEl.querySelectorAll(".mn-c");
    var w = wordEl.getBoundingClientRect().width;
    var x0 = wordEl.getBoundingClientRect().left;
    Array.prototype.forEach.call(chars, function (c) {
      var r = c.getBoundingClientRect();
      c.classList.add("mn-gold-text");
      c.style.backgroundSize = w + "px 100%";
      c.style.backgroundPosition = -(r.left - x0) + "px 0";
    });
  };

  // ouro + glint por caractere: --g (px) no elemento pai move a faixa clara sobre a palavra
  MN.goldGlintChars = function (wordEl) {
    var chars = wordEl.querySelectorAll(".mn-c");
    var box = wordEl.getBoundingClientRect();
    var w = box.width;
    Array.prototype.forEach.call(chars, function (c) {
      var x = c.getBoundingClientRect().left - box.left;
      c.style.backgroundImage =
        "linear-gradient(100deg, rgba(255,252,240,0) 0%, rgba(255,252,240,0) 30%, rgba(255,252,240,0.95) 50%, rgba(255,252,240,0) 70%, rgba(255,252,240,0) 100%)," +
        "linear-gradient(100deg, #8C6A2E 0%, #D9B76A 34%, #F6E7B8 52%, #D9B76A 66%, #B8893B 100%)";
      c.style.backgroundSize = 0.6 * w + "px 100%, " + w + "px 100%";
      c.style.backgroundRepeat = "no-repeat";
      c.style.backgroundPosition = "calc(var(--g, -9999px) - " + x + "px) 0, " + -x + "px 0";
      c.style.webkitBackgroundClip = "text";
      c.style.backgroundClip = "text";
      c.style.color = "transparent";
      c.style.webkitTextFillColor = "transparent";
      // caixas de glifo itálico se sobrepõem: a sobreposição entre caracteres é intencional
      c.setAttribute("data-layout-allow-occlusion", "");
    });
    return w;
  };

  // tracking animado só com transform: cada caractere fica numa máscara própria e a máscara
  // desliza o equivalente ao espaçamento extra (sem animar letter-spacing)
  MN.trackingIn = function (tl, el, o) {
    var sp = new SplitText(el, { type: "words,chars", mask: "chars", charsClass: o.cls || "mn-tc" });
    var fs = parseFloat(getComputedStyle(el).fontSize);
    var extra = (o.from - o.to) * fs;
    var k = 0;
    var masks = sp.masks;
    sp.words.forEach(function (w, wi) {
      w.querySelectorAll("." + (o.cls || "mn-tc")).forEach(function () {
        var m = masks[k];
        var off = (k + wi) * extra;
        if (o.center) off = (k + wi - (o.center - 1) / 2) * extra;
        tl.fromTo(m, { x: off, opacity: 0 }, { x: 0, opacity: 1, duration: o.dur || 0.9, ease: o.ease || "mn.out", immediateRender: true }, o.at + (o.stagger || 0) * k);
        k++;
      });
    });
    return sp;
  };

  /* ---------- glint (faixa especular em screen) ---------- */
  // band: elemento com gradiente; anda de -60% a +160% da largura do container
  MN.glint = function (tl, band, o) {
    tl.fromTo(band, { xPercent: o.fromX === undefined ? -120 : o.fromX, opacity: 0 }, { xPercent: o.toX === undefined ? 220 : o.toX, duration: o.dur || 0.9, ease: o.ease || "power2.inOut", immediateRender: true }, o.at);
    tl.to(band, { opacity: o.peak || 1, duration: (o.dur || 0.9) * 0.3, ease: "sine.out" }, o.at);
    tl.to(band, { opacity: 0, duration: (o.dur || 0.9) * 0.35, ease: "sine.in" }, o.at + (o.dur || 0.9) * 0.65);
  };

  /* ---------- câmera ---------- */
  MN.drift = function (tl, el, from, to, at, dur, ease) {
    tl.fromTo(el, from, Object.assign({}, to, { duration: dur, ease: ease || "none", immediateRender: true }), at);
  };

  /* ---------- transições ---------- */
  MN.whipOut = function (tl, el, o) {
    var v = {};
    v[o.axis || "x"] = o.dist;
    var f = {};
    f[o.axis || "x"] = 0;
    tl.fromTo(el, f, Object.assign(v, { duration: o.dur, ease: "power4.in", immediateRender: false }), o.at);
    if (o.blur) MN.blurPulse(tl, el, o.blur, { at: o.at, dur: o.dur, to: o.maxBlur || 60, axis: o.axis || "x", ease: "power3.in" });
  };
  MN.whipIn = function (tl, el, o) {
    var f = {};
    f[o.axis || "x"] = o.dist;
    var v = {};
    v[o.axis || "x"] = 0;
    tl.fromTo(el, f, Object.assign(v, { duration: o.dur, ease: "power4.out", immediateRender: true }), o.at);
    if (o.blur) MN.blurPulse(tl, el, o.blur, { at: o.at, dur: o.dur, from: o.maxBlur || 60, to: 0, axis: o.axis || "x", ease: "power3.out", clearAt: o.at + o.dur });
  };
  MN.flash = function (tl, el, o) {
    tl.fromTo(el, { opacity: o.from === undefined ? 0 : o.from }, { opacity: o.to === undefined ? 1 : o.to, duration: o.dur, ease: o.ease || "none", immediateRender: o.immediate !== false }, o.at);
  };
  MN.iris = function (tl, el, o) {
    var c = " at " + o.cx + "px " + o.cy + "px)";
    tl.fromTo(el, { clipPath: "circle(" + o.r0 + "px" + c }, { clipPath: "circle(" + o.r1 + "px" + c, duration: o.dur, ease: o.ease || "mn.inOut", immediateRender: o.immediate !== false }, o.at);
  };

  /* ---------- shake semeado, decaindo ---------- */
  MN.shake = function (tl, el, o) {
    var r = MN.rng(o.seed || 7);
    var steps = Math.max(4, Math.round(o.dur * (o.hz || 30)));
    var dt = o.dur / steps;
    for (var i = 0; i < steps; i++) {
      var k = Math.pow(1 - i / steps, 2);
      tl.to(el, { x: (r() * 2 - 1) * o.px * k, y: (r() * 2 - 1) * o.px * k, rotation: (r() * 2 - 1) * o.deg * k, duration: dt, ease: "sine.inOut" }, o.at + i * dt);
    }
    tl.to(el, { x: 0, y: 0, rotation: 0, duration: dt, ease: "sine.out" }, o.at + o.dur);
  };

  /* ---------- campo de bokeh semeado ---------- */
  MN.bokehField = function (tl, container, o) {
    var r = MN.rng(o.seed || 11);
    var out = [];
    for (var i = 0; i < o.count; i++) {
      var img = document.createElement("img");
      img.src = "assets/tex/bokeh_" + (i % 4) + ".png";
      img.className = "mn-img mn-bokeh";
      var size = MN.range(r, o.size[0], o.size[1]);
      var x = MN.range(r, -0.05, 1.05) * o.w;
      var y = MN.range(r, -0.05, 1.05) * o.h;
      img.style.width = size + "px";
      img.style.height = size + "px";
      img.style.left = x - size / 2 + "px";
      img.style.top = y - size / 2 + "px";
      container.appendChild(img);
      var op = MN.range(r, o.opacity[0], o.opacity[1]);
      var dx = MN.range(r, -1, 1) * o.drift[0];
      var dy = MN.range(r, -1, 1) * o.drift[1] - (o.rise || 0);
      var ph = r();
      tl.fromTo(img, { x: 0, y: 0, opacity: 0, scale: 0.9 }, { x: dx, y: dy, scale: 1.08, duration: o.dur, ease: "none", immediateRender: true }, o.at || 0);
      // cintilar: sobe, respira, some — cada partícula com sua fase
      var t0 = (o.at || 0) + ph * Math.min(0.8, o.dur * 0.2);
      tl.to(img, { opacity: op, duration: 0.6, ease: "sine.out" }, t0);
      tl.to(img, { opacity: op * 0.45, duration: o.dur * 0.35, ease: "sine.inOut", yoyo: true, repeat: 1 }, t0 + 0.6);
      out.push(img);
    }
    return out;
  };

  /* ---------- odômetro (contador que rola) ---------- */
  MN.odometer = function (el, digits, h) {
    el.innerHTML = "";
    var cols = [];
    for (var d = 0; d < digits; d++) {
      var win = document.createElement("span");
      win.className = "mn-odo-win";
      win.style.display = "inline-block";
      win.style.height = h + "px";
      win.style.overflow = "hidden";
      win.style.verticalAlign = "top";
      var col = document.createElement("span");
      col.className = "mn-odo-col";
      col.style.display = "block";
      for (var n = 0; n <= 9; n++) {
        var s = document.createElement("span");
        s.textContent = String(n);
        s.style.display = "block";
        s.style.height = h + "px";
        s.style.lineHeight = h + "px";
        col.appendChild(s);
      }
      win.appendChild(col);
      el.appendChild(win);
      cols.push(col);
    }
    return { cols: cols, h: h };
  };
  MN.odoSet = function (tl, odo, value, at, dur, ease) {
    var str = String(value).padStart(odo.cols.length, "0");
    odo.cols.forEach(function (col, i) {
      var n = parseInt(str[i], 10);
      tl.to(col, { y: -n * odo.h, duration: dur || 0.45, ease: ease || "back.out(1.4)" }, at);
    });
  };
  MN.odoInit = function (odo, value) {
    var str = String(value).padStart(odo.cols.length, "0");
    odo.cols.forEach(function (col, i) {
      gsap.set(col, { y: -parseInt(str[i], 10) * odo.h });
    });
  };

  /* ---------- geometria ---------- */
  // ponto de um retângulo de cantos arredondados na direção do ângulo (graus, 0 = 12h, horário)
  MN.rectRadius = function (deg, hw, hh) {
    var a = (deg * Math.PI) / 180;
    var sx = Math.abs(Math.sin(a)),
      cy = Math.abs(Math.cos(a));
    var t = Math.min(sx > 1e-6 ? hw / sx : 1e9, cy > 1e-6 ? hh / cy : 1e9);
    return t;
  };
  // path de círculo (4 cúbicas, começa às 12h, horário)
  MN.circlePath = function (cx, cy, r) {
    var k = 0.5522847498 * r;
    return (
      "M" + cx + "," + (cy - r) +
      " C" + (cx + k) + "," + (cy - r) + " " + (cx + r) + "," + (cy - k) + " " + (cx + r) + "," + cy +
      " C" + (cx + r) + "," + (cy + k) + " " + (cx + k) + "," + (cy + r) + " " + cx + "," + (cy + r) +
      " C" + (cx - k) + "," + (cy + r) + " " + (cx - r) + "," + (cy + k) + " " + (cx - r) + "," + cy +
      " C" + (cx - r) + "," + (cy - k) + " " + (cx - k) + "," + (cy - r) + " " + cx + "," + (cy - r) + "Z"
    );
  };
  // retângulo de cantos arredondados (começa às 12h, horário)
  MN.roundRectPath = function (cx, cy, w, h, rad) {
    var x0 = cx - w / 2,
      x1 = cx + w / 2,
      y0 = cy - h / 2,
      y1 = cy + h / 2,
      k = 0.5522847498 * rad;
    return (
      "M" + cx + "," + y0 +
      " L" + (x1 - rad) + "," + y0 +
      " C" + (x1 - rad + k) + "," + y0 + " " + x1 + "," + (y0 + rad - k) + " " + x1 + "," + (y0 + rad) +
      " L" + x1 + "," + (y1 - rad) +
      " C" + x1 + "," + (y1 - rad + k) + " " + (x1 - rad + k) + "," + y1 + " " + (x1 - rad) + "," + y1 +
      " L" + (x0 + rad) + "," + y1 +
      " C" + (x0 + rad - k) + "," + y1 + " " + x0 + "," + (y1 - rad + k) + " " + x0 + "," + (y1 - rad) +
      " L" + x0 + "," + (y0 + rad) +
      " C" + x0 + "," + (y0 + rad - k) + " " + (x0 + rad - k) + "," + y0 + " " + (x0 + rad) + "," + y0 +
      " L" + cx + "," + y0 + "Z"
    );
  };

  // blob "líquido": 2n pontos com raio modulado (fase semeada), Catmull-Rom -> cúbicas.
  // Mesmo seed + mesmo n = mesma estrutura: o MorphSVG interpola ponto a ponto.
  MN.blobPath = function (cx, cy, r, o) {
    o = o || {};
    var n = o.n || 14,
      amp = o.amp === undefined ? 0.06 : o.amp,
      rot = o.rot || 0;
    var rr = MN.rng(o.seed || 5);
    var ph = [],
      k;
    for (k = 0; k < 3; k++) ph.push(rr() * Math.PI * 2);
    var pts = [];
    for (var i = 0; i < n; i++) {
      var a = (i / n) * Math.PI * 2 + rot;
      var m = 1 + amp * (0.55 * Math.sin(3 * a + ph[0]) + 0.3 * Math.sin(5 * a + ph[1]) + 0.15 * Math.sin(7 * a + ph[2]));
      pts.push([cx + Math.cos(a) * r * m, cy + Math.sin(a) * r * m]);
    }
    var d = "M" + pts[0][0].toFixed(2) + "," + pts[0][1].toFixed(2);
    for (i = 0; i < n; i++) {
      var p0 = pts[(i - 1 + n) % n],
        p1 = pts[i],
        p2 = pts[(i + 1) % n],
        p3 = pts[(i + 2) % n];
      var c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      var c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += " C" + c1[0].toFixed(2) + "," + c1[1].toFixed(2) + " " + c2[0].toFixed(2) + "," + c2[1].toFixed(2) + " " + p2[0].toFixed(2) + "," + p2[1].toFixed(2);
    }
    return d + "Z";
  };

  /* ---------- imagens: zoom máximo seguro ---------- */
  // escala de exibição (px de tela por px do arquivo) respeitando o teto do framing.json
  MN.safeScale = function (key, wanted, peak) {
    var f = window.MINORAN_FRAMING[key];
    var cap = (f && f.maxScale) || 1;
    var s = Math.min(wanted, cap / (peak || 1));
    return s;
  };

  window.MN = MN;
})();
