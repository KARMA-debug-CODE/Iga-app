// The maths behind the graph: the visible window, zoom and pan, grid steps and labels,
// sampling a function into line segments, and the point shown when tracing.
//
// A view is {cx, cy, sx, sy}: the centre of the canvas in graph units and the units per
// CSS pixel across (sx) and up (sy). Screen y grows downwards, graph y grows upwards.
//
// Sampling breaks the curve where it has no value (sqrt of a negative, ln of 0) and at
// jumps such as the asymptotes of tan x and 1/x, so they are never joined by a line.

/** Default window: x from −10 to 10 with equal units, or −400° to 400° in degrees. */
export function defaultView(width, height, angle = "rad") {
  const w = Math.max(width, 1);
  const h = Math.max(height, 1);
  if (angle === "deg") return { cx: 0, cy: 0, sx: 800 / w, sy: 5 / h };
  const s = Math.max(20 / w, 12 / h);
  return { cx: 0, cy: 0, sx: s, sy: s };
}

export function bounds(view, w, h) {
  return {
    xmin: view.cx - (view.sx * w) / 2,
    xmax: view.cx + (view.sx * w) / 2,
    ymin: view.cy - (view.sy * h) / 2,
    ymax: view.cy + (view.sy * h) / 2,
  };
}

export const toPx = (view, w, x) => (x - view.cx) / view.sx + w / 2;
export const toPy = (view, h, y) => h / 2 - (y - view.cy) / view.sy;
export const fromPx = (view, w, px) => view.cx + (px - w / 2) * view.sx;
export const fromPy = (view, h, py) => view.cy - (py - h / 2) * view.sy;

// Beyond these scales the numbers lose their precision (or the grid has nothing to show).
const MIN_SCALE = 1e-12;
const MAX_SCALE = 1e12;

/** Zoom by `factor` (below 1 zooms in) keeping the point under pixel (px, py) still. */
export function zoomView(view, factor, px, py, w, h) {
  const sx = view.sx * factor;
  const sy = view.sy * factor;
  if (Math.min(sx, sy) < MIN_SCALE || Math.max(sx, sy) > MAX_SCALE) return view;
  const x = fromPx(view, w, px);
  const y = fromPy(view, h, py);
  return { cx: x - (px - w / 2) * sx, cy: y + (py - h / 2) * sy, sx, sy };
}

/** Move the graph with the pointer: dragging right shows what is on the left. */
export function panView(view, dx, dy) {
  return { ...view, cx: view.cx - dx * view.sx, cy: view.cy + dy * view.sy };
}

// ---- Grid ------------------------------------------------------------------------

/** A round step (1, 2 or 5 times a power of ten) giving about `count` lines across `span`. */
export function niceStep(span, count) {
  const raw = span / Math.max(count, 1);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const nice = norm < 1.5 ? 1 : norm < 3.5 ? 2 : norm < 7.5 ? 5 : 10;
  return nice * mag;
}

/** Multiples of step between min and max (at most 500). */
export function ticks(min, max, step) {
  const out = [];
  const first = Math.ceil(min / step);
  const last = Math.floor(max / step);
  if (last - first > 500) return out;
  for (let k = first; k <= last; k += 1) out.push(Number((k * step).toPrecision(12)));
  return out;
}

const DECIMAL = { en: ".", fr: "," };

/** "−" (the minus sign) and the reader's decimal separator. */
function localise(text, lang) {
  return text.replace("-", "−").replace(".", DECIMAL[lang] || ".");
}

/** Places after the decimal point needed to tell apart multiples of step. */
function placesFor(step) {
  return Math.max(0, -Math.floor(Math.log10(step) + 1e-9));
}

/** Label for a grid line: "2", "0.5", "−1.5", "2e+6"; French "0,5". */
export function tickLabel(v, step, lang = "en") {
  if (v === 0) return "0";
  const abs = Math.abs(v);
  if (abs >= 1e6 || step < 1e-4) return localise(Number(v.toPrecision(6)).toExponential(), lang);
  return localise(v.toFixed(placesFor(step)), lang);
}

// ---- Sampling ----------------------------------------------------------------------

const MAX_DEPTH = 5; // up to 32 extra points across one pixel where the curve is steep
const STEEP_PX = 2;

/**
 * Sample f across the view into segments of [x, y] points (graph units). One point per
 * pixel, more where the curve is steep. A new segment starts after a gap where f has no
 * value, and after a jump (a pole such as x = 0 for 1/x, or 90° for tan x).
 */
export function sampleFunction(f, view, w, h) {
  const { xmin, xmax } = bounds(view, w, h);
  const n = Math.max(2, Math.ceil(w));
  const dx = (xmax - xmin) / n;
  const pxPerUnit = 1 / view.sy;
  const at = (x) => {
    const y = f(x);
    return Number.isFinite(y) ? y : NaN;
  };
  const segments = [];
  let current = null;
  const push = (x, y) => {
    if (!current) {
      current = [];
      segments.push(current);
    }
    current.push([x, y]);
  };
  const end = () => {
    current = null;
  };

  /** The point with a value closest to the edge of a gap (between x `inside` and x `outside`). */
  function edge(inside, outside) {
    let a = inside;
    let b = outside;
    for (let i = 0; i < 48; i += 1) {
      const m = (a + b) / 2;
      if (m === a || m === b) break;
      if (Number.isNaN(at(m))) b = m;
      else a = m;
    }
    return [a, at(a)];
  }

  /** A big change across a tiny step: a jump (break the line) or just a steep curve? */
  function jump(x0, y0, x1, y1) {
    let a = x0;
    let ya = y0;
    let b = x1;
    let yb = y1;
    for (let i = 0; i < 60; i += 1) {
      const m = (a + b) / 2;
      if (m === a || m === b) break;
      const ym = at(m);
      if (Number.isNaN(ym)) return { left: edge(a, m), right: edge(b, m) };
      // Follow the half where the change is bigger; a continuous curve shrinks it below a pixel.
      if (Math.abs(ym - ya) >= Math.abs(yb - ym)) {
        b = m;
        yb = ym;
      } else {
        a = m;
        ya = ym;
      }
      if (Math.abs(yb - ya) * pxPerUnit < 1) return null;
    }
    return { left: [a, ya], right: [b, yb] };
  }

  function connect(x0, y0, x1, y1, depth) {
    const ok0 = !Number.isNaN(y0);
    const ok1 = !Number.isNaN(y1);
    if (!ok0 && !ok1) {
      end();
      return;
    }
    if (ok0 && !ok1) {
      push(...edge(x0, x1));
      end();
      return;
    }
    if (!ok0) {
      push(...edge(x1, x0));
      push(x1, y1);
      return;
    }
    if (Math.abs(y1 - y0) * pxPerUnit <= STEEP_PX) {
      push(x1, y1);
      return;
    }
    if (depth < MAX_DEPTH) {
      const m = (x0 + x1) / 2;
      const ym = at(m);
      connect(x0, y0, m, ym, depth + 1);
      connect(m, ym, x1, y1, depth + 1);
      return;
    }
    const gap = jump(x0, y0, x1, y1);
    if (gap) {
      push(...gap.left);
      end();
      push(...gap.right);
    }
    push(x1, y1);
  }

  let x0 = xmin;
  let y0 = at(x0);
  if (!Number.isNaN(y0)) push(x0, y0);
  for (let i = 1; i <= n; i += 1) {
    const x1 = xmin + i * dx;
    const y1 = at(x1);
    connect(x0, y0, x1, y1, 0);
    x0 = x1;
    y0 = y1;
  }
  return segments;
}

// ---- Tracing ------------------------------------------------------------------------

/**
 * The curve nearest to pixel (px, py), if one passes within maxDist pixels.
 * curves: [{id, f}]. Returns {id, x, y} or null.
 */
export function nearestPoint(curves, view, w, h, px, py, maxDist = Infinity) {
  const x = fromPx(view, w, px);
  let best = null;
  for (const curve of curves) {
    const y = curve.f(x);
    if (!Number.isFinite(y)) continue;
    const dist = Math.abs(toPy(view, h, y) - py);
    if (dist <= maxDist && (!best || dist < best.dist)) best = { id: curve.id, x, y, dist };
  }
  return best && { id: best.id, x: best.x, y: best.y };
}

/** Decimal places that show a point to about a tenth of a pixel. */
export function traceDecimals(view) {
  const scale = Math.min(view.sx, view.sy);
  return Math.min(12, Math.max(0, Math.ceil(-Math.log10(scale)) + 1));
}

/** One coordinate, rounded and trimmed: "1.5", "−0.25", "3"; very large or small in exponent form. */
export function formatCoord(v, places, lang = "en") {
  const abs = Math.abs(v);
  if (abs >= 1e9 || (abs !== 0 && abs < 1e-9)) return localise(Number(v.toPrecision(5)).toExponential(), lang);
  let text = v.toFixed(places);
  if (text.includes(".")) text = text.replace(/0+$/, "").replace(/\.$/, "");
  return localise(text === "-0" ? "0" : text, lang);
}

/** "(1.5, 2.25)"; in French the decimal comma needs a semicolon: "(1,5 ; 2,25)". */
export function formatPoint(x, y, places, lang = "en") {
  const sep = lang === "fr" ? " ; " : ", ";
  return `(${formatCoord(x, places, lang)}${sep}${formatCoord(y, places, lang)})`;
}
