/* Motor determinístico das composições (HyperFrames).
 * Cada quadro é função pura do tempo t (s): o relógio é uma tween GSAP numa propriedade
 * com setter, registrada em window.__timelines — o HyperFrames busca (seek) o tempo e o
 * setter redesenha a cena inteira.
 *
 * - câmera virtual (cx, cy, s): mundo -> tela
 * - desfoque de movimento por velocidade na tela: sigma = 0,29 x v x 0,75 / 60 (máx. 40 px),
 *   direcional (feGaussianBlur anisotrópico), só durante o movimento
 * - profundidade de campo (dof, px) nunca aplicada a texto
 * - sombra de 3 camadas mantida em pixels de tela durante zooms
 */
(function () {
  "use strict";
  const W = 1080, H = 1920, DT = 1 / 240;
  const KB = (0.29 * 0.75) / 60;
  const SIG_MAX = 40;
  const SVGNS = "http://www.w3.org/2000/svg";
  const SHADOW = [[60, 120, 0.16], [24, 48, 0.1], [4, 10, 0.06]];
  const cache = {};
  const ez = (n) => cache[n] || (cache[n] = gsap.parseEase(n));
  const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
  const lerp = (a, b, u) => a + (b - a) * u;
  function tw(t, t0, d, a, b, e) {
    if (t <= t0) return a;
    if (t >= t0 + d) return b;
    return a + (b - a) * ez(e || "none")((t - t0) / d);
  }
  function prog(t, t0, d, e) {
    return tw(t, t0, d, 0, 1, e);
  }
  function shadowCSS(k) {
    return SHADOW.map(([dy, bl, a]) => `0 ${(dy * k).toFixed(2)}px ${(bl * k).toFixed(2)}px rgba(24,24,32,${a})`).join(", ");
  }
  function sigmaOf(v) {
    return Math.min(SIG_MAX, KB * v);
  }
  function rng(seed) {
    let s = seed >>> 0;
    return () => {
      s = (s + 0x6d2b79f5) >>> 0;
      let r = Math.imul(s ^ (s >>> 15), 1 | s);
      r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
  }

  class Engine {
    constructor(root, duration) {
      this.root = root;
      this.D = duration;
      this.stage = root.querySelector(".stage");
      this.defs = root.querySelector("svg.defs defs");
      this.nodes = [];
      this.spans = [];
      this.hooks = [];
      this.events = [];
      this.camFn = () => ({ cx: W / 2, cy: H / 2, s: 1 });
      this.fid = 0;
      this.debug = [];
    }
    camera(fn) {
      this.camFn = fn;
    }
    event(t, type, label) {
      this.events.push({ t: Math.round(t * 1e6) / 1e6, type, label: label || "" });
    }
    hook(fn) {
      this.hooks.push(fn);
    }
    makeFilter() {
      const id = `${this.root.dataset.compositionId}-mb${this.fid++}`;
      const f = document.createElementNS(SVGNS, "filter");
      f.setAttribute("id", id);
      f.setAttribute("x", "-60%");
      f.setAttribute("y", "-60%");
      f.setAttribute("width", "220%");
      f.setAttribute("height", "220%");
      f.setAttribute("color-interpolation-filters", "sRGB");
      const g = document.createElementNS(SVGNS, "feGaussianBlur");
      g.setAttribute("stdDeviation", "0 0");
      f.appendChild(g);
      this.defs.appendChild(f);
      return { id, g };
    }
    /* nó posicionado: el com largura/altura fixas; state(t) -> {x,y,r,s,o,dof} (centro) */
    node(el, opt) {
      const n = Object.assign({ el, world: true, w: el.offsetWidth, h: el.offsetHeight, mb: true, shadow: false, state: () => ({}) }, opt);
      el.style.position = "absolute";
      el.style.left = "0px";
      el.style.top = "0px";
      el.style.width = n.w + "px";
      el.style.height = n.h + "px";
      el.style.transformOrigin = "50% 50%";
      if (n.mb || n.dofable) Object.assign(n, { f: this.makeFilter() });
      n.lastFilter = "";
      n.lastShadow = -1;
      this.nodes.push(n);
      return n;
    }
    /* trecho de texto animado em coordenadas locais (palavra/letra/linha) */
    span(el, fn, parent) {
      const s = { el, fn, parent: parent || null, f: this.makeFilter(), lastFilter: "" };
      el.style.display = el.style.display || "inline-block";
      this.spans.push(s);
      return s;
    }
    cam(t) {
      return Object.assign({ cx: W / 2, cy: H / 2, s: 1 }, this.camFn(t));
    }
    screen(n, t) {
      const st = Object.assign({ x: W / 2, y: H / 2, r: 0, s: 1, o: 1, dof: 0 }, n.state(t));
      if (n.world) {
        const c = this.cam(t);
        st.x = (st.x - c.cx) * c.s + W / 2;
        st.y = (st.y - c.cy) * c.s + H / 2;
        st.s = st.s * c.s;
      }
      return st;
    }
    velocity(fnAt, t) {
      // diferença para trás (obturador "traseiro"); no início do trecho, para frente
      const a = fnAt(t);
      const b = t >= DT ? fnAt(t - DT) : fnAt(t + DT);
      const k = t >= DT ? 1 : -1;
      return { a, vx: (k * (a.x - b.x)) / DT, vy: (k * (a.y - b.y)) / DT };
    }
    applyFilter(obj, sx, sy) {
      if (!isFinite(sx) || !isFinite(sy)) sx = sy = 0;
      const on = sx > 0.2 || sy > 0.2;
      const css = on ? `url(#${obj.f.id})` : "none";
      if (on) obj.f.g.setAttribute("stdDeviation", `${sx.toFixed(3)} ${sy.toFixed(3)}`);
      if (css !== obj.lastFilter) {
        obj.el.style.filter = css;
        obj.lastFilter = css;
      }
    }
    render(t) {
      for (const n of this.nodes) {
        const { a, vx, vy } = this.velocity((tt) => this.screen(n, tt), t);
        n.cur = a;
        n.vel = [vx, vy];
        const el = n.el;
        el.style.transform = `translate(${(a.x - n.w / 2).toFixed(3)}px, ${(a.y - n.h / 2).toFixed(3)}px) rotate(${a.r.toFixed(4)}deg) scale(${a.s.toFixed(5)})`;
        el.style.opacity = clamp(a.o, 0, 1).toFixed(4);
        el.style.visibility = a.o <= 0.001 ? "hidden" : "visible";
        if (n.shadow) {
          const k = Math.round((1 / a.s) * 1000) / 1000;
          if (k !== n.lastShadow) {
            el.style.boxShadow = shadowCSS(k);
            n.lastShadow = k;
          }
        }
        if (n.f) {
          const v = Math.hypot(vx, vy);
          const sig = n.mb ? sigmaOf(v) : 0;
          const rad = (-a.r * Math.PI) / 180;
          const lx = v > 0 ? Math.abs(vx * Math.cos(rad) - vy * Math.sin(rad)) / v : 0;
          const ly = v > 0 ? Math.abs(vx * Math.sin(rad) + vy * Math.cos(rad)) / v : 0;
          const d = n.text ? 0 : a.dof || 0; // nunca desfocar texto por profundidade
          if (a.s < 0.02 || a.o <= 0.001) this.applyFilter(n, 0, 0);
          else this.applyFilter(n, Math.hypot(sig * lx, d) / a.s, Math.hypot(sig * ly, d) / a.s);
        }
        if (n.update) n.update(t, a);
      }
      for (const s of this.spans) {
        const at = (tt) => Object.assign({ x: 0, y: 0, r: 0, s: 1, o: 1 }, s.fn(tt));
        const { a, vx, vy } = this.velocity(at, t);
        let pvx = 0, pvy = 0, ps = 1;
        if (s.parent && s.parent.vel) {
          [pvx, pvy] = s.parent.vel;
          ps = s.parent.cur ? s.parent.cur.s : 1;
        }
        const svx = vx * ps + pvx, svy = vy * ps + pvy;
        const el = s.el;
        el.style.transform = `translate(${a.x.toFixed(3)}px, ${a.y.toFixed(3)}px) rotate(${a.r.toFixed(4)}deg) scale(${a.s.toFixed(5)})`;
        el.style.opacity = clamp(a.o, 0, 1).toFixed(4);
        if (a.ls !== undefined) el.style.letterSpacing = `${a.ls.toFixed(4)}em`;
        // velocidade local (+ do pai) -> desfoque nos eixos locais
        const v = Math.hypot(vx * ps, vy * ps);
        const sig = sigmaOf(v);
        const k = ps * a.s;
        if (k < 0.02 || a.o <= 0.001) this.applyFilter(s, 0, 0);
        else this.applyFilter(s, (sig * (v > 0 ? Math.abs(vx * ps) / v : 0)) / k, (sig * (v > 0 ? Math.abs(vy * ps) / v : 0)) / k);
        s.svel = [svx, svy];
      }
      for (const h of this.hooks) h(t);
    }
    /* relógio GSAP: o HyperFrames busca o tempo; o setter redesenha.
       A composição registra o retorno em window.__timelines[id]. */
    timeline() {
      const clock = {};
      let cur = -1;
      const self = this;
      Object.defineProperty(clock, "t", {
        get() {
          return cur;
        },
        set(v) {
          cur = v;
          self.render(Math.max(0, Math.min(self.D, v)));
        },
      });
      const tl = gsap.timeline({ paused: true });
      tl.fromTo(clock, { t: 0 }, { t: this.D, duration: this.D, ease: "none", immediateRender: true }, 0);
      window.__events = this.events;
      window.__engine = this;
      this.render(0);
      return tl;
    }
  }

  window.HF = { Engine, tw, prog, clamp, lerp, ez, shadowCSS, sigmaOf, rng, W, H, DT, SVGNS };
})();
