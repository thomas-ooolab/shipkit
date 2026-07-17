// shipkit · recon-extract — deterministic DOM → design-token extractor.
//
// Runs INSIDE the page via Playwright MCP `browser_evaluate`. It reads *computed*
// styles (the ground truth a mockup actually renders — not the authored CSS you'd
// get by reading HTML) and returns a COMPACT JSON token list. The heavy DOM stays
// in the browser; only the snapped tokens cross into the model's context, so recon
// is cheaper than reading markup, not just more accurate.
//
// Usage (from the skill):
//   1. browser_evaluate: set options —
//        () => { window.__SHIPKIT_OPTS = { rootSelector: "...", colors: {...}, maxNodes: 120 }; }
//      `colors` is the project's Tailwind theme palette ({ "blue-600": "#2563eb", ... }),
//      resolved by `recon.sh tailwind-config`. Omit to fall back to the built-in default palette.
//   2. browser_evaluate: paste THIS file's contents as the `function` argument. It reads
//      window.__SHIPKIT_OPTS, walks the DOM, and returns the token JSON.
//
// Every numeric style is snapped to the nearest Tailwind utility class so the
// implementer assembles known classes instead of interpreting raw px/hex. Each
// snap carries `exact:false` when it had to round, so /design-verify never asserts
// false precision on an approximate value.
//
// This file is data + pure functions only — no network, no writes, no page mutation
// (it never changes styles; it only reads getComputedStyle + getBoundingClientRect).

() => {
  const o = (typeof window !== "undefined" && window.__SHIPKIT_OPTS) || {};
  const ROOT = o.rootSelector || "body";
  const MAX_NODES = o.maxNodes || 140;
  const MIN_AREA = o.minArea || 24; // px² — skip slivers/hairlines

  // ---- Tailwind snap tables (default scale; overridable via opts) --------------
  // spacing: px -> class suffix (gap-N, p-N, m-N …). Default Tailwind rem*16 scale.
  const SPACING = [
    [0, "0"], [1, "px"], [2, "0.5"], [4, "1"], [6, "1.5"], [8, "2"], [10, "2.5"],
    [12, "3"], [14, "3.5"], [16, "4"], [20, "5"], [24, "6"], [28, "7"], [32, "8"],
    [36, "9"], [40, "10"], [44, "11"], [48, "12"], [56, "14"], [64, "16"], [80, "20"],
    [96, "24"], [112, "28"], [128, "32"], [144, "36"], [160, "40"], [176, "44"],
    [192, "48"], [208, "52"], [224, "56"], [240, "60"], [256, "64"], [288, "72"],
    [320, "80"], [384, "96"],
  ];
  const FONT_SIZE = [
    [12, "text-xs"], [14, "text-sm"], [16, "text-base"], [18, "text-lg"], [20, "text-xl"],
    [24, "text-2xl"], [30, "text-3xl"], [36, "text-4xl"], [48, "text-5xl"], [60, "text-6xl"],
    [72, "text-7xl"], [96, "text-8xl"], [128, "text-9xl"],
  ];
  const FONT_WEIGHT = [
    [100, "font-thin"], [200, "font-extralight"], [300, "font-light"], [400, "font-normal"],
    [500, "font-medium"], [600, "font-semibold"], [700, "font-bold"], [800, "font-extrabold"],
    [900, "font-black"],
  ];
  const RADIUS = [
    [0, "rounded-none"], [2, "rounded-sm"], [4, "rounded"], [6, "rounded-md"], [8, "rounded-lg"],
    [12, "rounded-xl"], [16, "rounded-2xl"], [24, "rounded-3xl"], [9999, "rounded-full"],
  ];
  // Built-in fallback palette — a compact slice of the Tailwind default palette.
  // Overridden/extended by opts.colors (the project's real theme) when provided.
  const DEFAULT_COLORS = {
    "white": "#ffffff", "black": "#000000",
    "slate-50": "#f8fafc", "slate-100": "#f1f5f9", "slate-200": "#e2e8f0",
    "slate-300": "#cbd5e1", "slate-400": "#94a3b8", "slate-500": "#64748b",
    "slate-600": "#475569", "slate-700": "#334155", "slate-800": "#1e293b", "slate-900": "#0f172a",
    "gray-100": "#f3f4f6", "gray-200": "#e5e7eb", "gray-300": "#d1d5db", "gray-400": "#9ca3af",
    "gray-500": "#6b7280", "gray-600": "#4b5563", "gray-700": "#374151", "gray-900": "#111827",
    "red-500": "#ef4444", "red-600": "#dc2626",
    "amber-400": "#fbbf24", "amber-500": "#f59e0b",
    "green-500": "#22c55e", "green-600": "#16a34a",
    "blue-500": "#3b82f6", "blue-600": "#2563eb", "blue-700": "#1d4ed8",
    "indigo-500": "#6366f1", "indigo-600": "#4f46e5",
    "violet-600": "#7c3aed", "purple-600": "#9333ea",
  };
  const COLORS = Object.assign({}, DEFAULT_COLORS, o.colors || {});

  // ---- snap helpers -----------------------------------------------------------
  const num = (v) => parseFloat(v) || 0;

  function snapScale(px, prefix, table) {
    if (px == null) return null;
    let best = table[0], bestD = Infinity;
    for (const [v, cls] of table) {
      const d = Math.abs(v - px);
      if (d < bestD) { bestD = d; best = [v, cls]; }
    }
    return { px: Math.round(px * 100) / 100, class: prefix ? prefix + "-" + best[1] : best[1], exact: bestD < 0.5 };
  }
  function snapNamed(px, table) {
    if (px == null) return null;
    let best = table[0], bestD = Infinity;
    for (const [v, cls] of table) {
      const d = Math.abs(v - px);
      if (d < bestD) { bestD = d; best = [v, cls]; }
    }
    return { px: Math.round(px * 100) / 100, class: best[1], exact: bestD < 0.5 };
  }
  function rgbToArr(s) {
    if (!s) return null;
    const m = s.match(/rgba?\(([^)]+)\)/i);
    if (!m) return null;
    const p = m[1].split(",").map((x) => parseFloat(x));
    if (p.length < 3) return null;
    const a = p.length >= 4 ? p[3] : 1;
    return { r: p[0], g: p[1], b: p[2], a };
  }
  function hexOf(c) {
    const h = (n) => ("0" + Math.round(n).toString(16)).slice(-2);
    return "#" + h(c.r) + h(c.g) + h(c.b);
  }
  function snapColor(cssColor) {
    const c = rgbToArr(cssColor);
    if (!c || c.a === 0) return null; // fully transparent → no color token
    const hex = hexOf(c);
    let best = null, bestD = Infinity;
    for (const name in COLORS) {
      const t = rgbToArr(hexToRgb(COLORS[name]));
      if (!t) continue;
      const d = (c.r - t.r) ** 2 + (c.g - t.g) ** 2 + (c.b - t.b) ** 2;
      if (d < bestD) { bestD = d; best = name; }
    }
    const exact = bestD <= 12; // ~ within rounding of the same swatch
    const token = best + (c.a < 1 ? "/" + Math.round(c.a * 100) : "");
    return { hex, class: token, exact };
  }
  function hexToRgb(hex) {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
    if (!m) return "rgb(0,0,0)";
    const n = parseInt(m[1], 16);
    return "rgb(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + ")";
  }

  // ---- DOM walk ---------------------------------------------------------------
  const rootEl = document.querySelector(ROOT) || document.body;
  const nodes = [];
  const seen = new Set();

  function shortSel(el) {
    if (el.id) return "#" + el.id;
    const parts = [];
    let cur = el, depth = 0;
    while (cur && cur.nodeType === 1 && depth < 4 && cur !== document.body) {
      let s = cur.tagName.toLowerCase();
      const cls = (cur.getAttribute && cur.getAttribute("class") || "").trim().split(/\s+/).filter(Boolean).slice(0, 2);
      if (cls.length) s += "." + cls.join(".");
      parts.unshift(s);
      cur = cur.parentElement; depth++;
    }
    return parts.join(" > ");
  }

  function significant(el, cs, rect) {
    if (cs.display === "none" || cs.visibility === "hidden" || num(cs.opacity) === 0) return false;
    if (rect.width * rect.height < MIN_AREA) return false;
    // Keep elements that carry visual identity: text, background, border, flex/grid container.
    const hasText = el.childNodes && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    const hasBg = cs.backgroundColor && rgbToArr(cs.backgroundColor) && rgbToArr(cs.backgroundColor).a > 0;
    const hasBorder = num(cs.borderTopWidth) + num(cs.borderBottomWidth) + num(cs.borderLeftWidth) + num(cs.borderRightWidth) > 0;
    const isLayout = cs.display === "flex" || cs.display === "grid" || cs.display === "inline-flex";
    const isControl = /^(button|a|input|select|textarea|img|svg)$/i.test(el.tagName);
    return hasText || hasBg || hasBorder || isLayout || isControl;
  }

  function tokensFor(el, cs, rect) {
    const t = { sel: shortSel(el), tag: el.tagName.toLowerCase() };
    const role = el.getAttribute && (el.getAttribute("role") || null);
    if (role) t.role = role;
    // DIRECT text only — a container must not absorb its descendants' text, or its
    // typography/color would be read from the wrong element (and the region mislabeled).
    const txt = [...el.childNodes]
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent)
      .join(" ").trim().replace(/\s+/g, " ");
    if (txt) t.text = txt.length > 48 ? txt.slice(0, 48) + "…" : txt;
    t.box = { w: Math.round(rect.width), h: Math.round(rect.height) };

    // layout
    if (/flex|grid/.test(cs.display)) {
      t.layout = { display: cs.display };
      if (cs.display.includes("flex")) t.layout.dir = cs.flexDirection;
      const gap = num(cs.rowGap || cs.gap);
      if (gap) t.layout.gap = snapScale(gap, "gap", SPACING);
      if (cs.justifyContent && cs.justifyContent !== "normal") t.layout.justify = cs.justifyContent;
      if (cs.alignItems && cs.alignItems !== "normal") t.layout.items = cs.alignItems;
    }
    // spacing (only sides that are non-zero, snapped)
    const pad = ["Top", "Right", "Bottom", "Left"].map((s) => num(cs["padding" + s]));
    if (pad.some((v) => v > 0)) t.padding = pad.map((v) => snapScale(v, "p", SPACING).class);
    const mar = ["Top", "Right", "Bottom", "Left"].map((s) => num(cs["margin" + s]));
    if (mar.some((v) => Math.abs(v) > 0)) t.margin = mar.map((v) => snapScale(v, "m", SPACING).class);

    // typography (only when the node holds direct text)
    if (t.text) {
      t.type = {
        size: snapNamed(num(cs.fontSize), FONT_SIZE),
        weight: snapNamed(num(cs.fontWeight), FONT_WEIGHT),
        family: (cs.fontFamily || "").split(",")[0].replace(/["']/g, "").trim(),
        color: snapColor(cs.color),
      };
      const lh = num(cs.lineHeight);
      if (lh) t.type.leading = Math.round((lh / (num(cs.fontSize) || 16)) * 100) / 100;
      const ls = num(cs.letterSpacing);
      if (ls) t.type.tracking = Math.round(ls * 100) / 100;
    }
    // surface
    const bg = snapColor(cs.backgroundColor);
    if (bg) t.bg = bg;
    const br = num(cs.borderTopWidth);
    if (br > 0) { t.border = { width: br, color: snapColor(cs.borderTopColor) }; }
    const rad = num(cs.borderTopLeftRadius);
    if (rad > 0) t.radius = snapNamed(rad, RADIUS);
    if (cs.boxShadow && cs.boxShadow !== "none") t.shadow = cs.boxShadow; // raw — hard to snap reliably
    return t;
  }

  const stack = [rootEl];
  while (stack.length && nodes.length < MAX_NODES) {
    const el = stack.shift();
    if (!el || el.nodeType !== 1 || seen.has(el)) continue;
    seen.add(el);
    let cs, rect;
    try { cs = getComputedStyle(el); rect = el.getBoundingClientRect(); } catch (e) { continue; }
    if (significant(el, cs, rect)) nodes.push(tokensFor(el, cs, rect));
    for (const c of el.children) stack.push(c);
  }

  return {
    meta: {
      url: location.href,
      viewport: { w: window.innerWidth, h: window.innerHeight },
      root: ROOT,
      nodeCount: nodes.length,
      truncated: nodes.length >= MAX_NODES,
      palette: o.colors ? "project" : "default",
    },
    nodes,
  };
}
