// Graphing mode, like Windows 11: functions y = f(x), each in its own colour, plotted on a
// canvas with a grid, axes and labels. Drag to pan; zoom with the buttons, the mouse wheel
// or two fingers; hover or tap a curve to see a point. The maths (parsing, sampling,
// the view) is in engine/expression.js and engine/plot.js.
import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";

import { Icon } from "../components/Icon";
import { compile, parseFunction } from "./engine/expression.js";
import * as P from "./engine/plot.js";
import "./graphing.css";
import { load, store } from "./storage.js";

const MAX_FUNCTIONS = 6;
const COLOURS = 6;
const MAX_LENGTH = 200;
const ZOOM_STEP = 1.5;
const PAN_STEP = 40; // pixels moved by an arrow key
const TAP_SLOP = 5; // pixels a finger may move and still count as a tap
const PICK = { mouse: 24, touch: 40 }; // how close to a curve a pointer must be to trace it
const ERROR_DELAY = 900; // ms of no typing before the box being typed in shows its error

// Keys that type into the function box, like the keypad of Windows Graphing mode.
const INSERTS = [
  { id: "x", text: "x", label: "x" },
  {
    id: "sqr",
    text: "^2",
    label: (
      <>
        x<sup>2</sup>
      </>
    ),
  },
  {
    id: "pow",
    text: "^",
    label: (
      <>
        x<sup>y</sup>
      </>
    ),
  },
  { id: "sqrt", text: "√(", label: "√" },
  { id: "pi", text: "π", label: "π" },
  { id: "e", text: "e", label: "e" },
  { id: "open", text: "(", label: "(" },
  { id: "sin", text: "sin(", label: "sin" },
  { id: "cos", text: "cos(", label: "cos" },
  { id: "tan", text: "tan(", label: "tan" },
  { id: "ln", text: "ln(", label: "ln" },
  { id: "log", text: "log(", label: "log" },
  { id: "abs", text: "abs(", label: "|x|" },
  { id: "close", text: ")", label: ")" },
];

function fill(text, vars) {
  return text.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
}

function initialGraph() {
  const saved = load("graph");
  const list = Array.isArray(saved?.functions) ? saved.functions : [];
  const fns = list
    .filter((fn) => typeof fn?.text === "string")
    .slice(0, MAX_FUNCTIONS)
    .map((fn, i) => ({
      key: i + 1,
      text: fn.text.slice(0, MAX_LENGTH),
      colour: Number.isInteger(fn.colour) && fn.colour >= 0 && fn.colour < COLOURS ? fn.colour : i % COLOURS,
      hidden: fn.hidden === true,
    }));
  return {
    fns: fns.length ? fns : [{ key: 1, text: "", colour: 0, hidden: false }],
    angle: saved?.angle === "deg" ? "deg" : "rad",
  };
}

const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);

/** Draw the grid, axes, labels, curves and the traced point. Colours come from graphing.css. */
function drawGraph(canvas, { w, h, view, plots, point, lang }) {
  const dpr = window.devicePixelRatio || 1;
  const pw = Math.round(w * dpr);
  const ph = Math.round(h * dpr);
  if (canvas.width !== pw) canvas.width = pw;
  if (canvas.height !== ph) canvas.height = ph;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  const css = getComputedStyle(canvas);
  const colour = (name) => css.getPropertyValue(name).trim();
  const b = P.bounds(view, w, h);
  const X = (x) => P.toPx(view, w, x);
  const Y = (y) => P.toPy(view, h, y);
  // About one grid line every 64 pixels; minor lines split each step in 4 (steps of 2) or 5.
  const stepX = P.niceStep(b.xmax - b.xmin, w / 64);
  const stepY = P.niceStep(b.ymax - b.ymin, h / 64);
  const minor = (step) => step / (Math.round(step / 10 ** Math.floor(Math.log10(step))) === 2 ? 4 : 5);

  function grid(sx, sy, stroke) {
    ctx.beginPath();
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1;
    for (const x of P.ticks(b.xmin, b.xmax, sx)) {
      const px = Math.round(X(x)) + 0.5;
      ctx.moveTo(px, 0);
      ctx.lineTo(px, h);
    }
    for (const y of P.ticks(b.ymin, b.ymax, sy)) {
      const py = Math.round(Y(y)) + 0.5;
      ctx.moveTo(0, py);
      ctx.lineTo(w, py);
    }
    ctx.stroke();
  }
  grid(minor(stepX), minor(stepY), colour("--calc-graph-minor"));
  grid(stepX, stepY, colour("--calc-graph-grid"));

  const ax = Math.round(X(0)) + 0.5;
  const ay = Math.round(Y(0)) + 0.5;
  ctx.beginPath();
  ctx.strokeStyle = colour("--calc-graph-axis");
  ctx.lineWidth = 1.5;
  if (ay >= 0 && ay <= h) {
    ctx.moveTo(0, ay);
    ctx.lineTo(w, ay);
  }
  if (ax >= 0 && ax <= w) {
    ctx.moveTo(ax, 0);
    ctx.lineTo(ax, h);
  }
  ctx.stroke();

  // The curves, one path per function. Points far off the canvas are pulled in so
  // the line still runs off the edge in the right direction.
  ctx.lineWidth = 2.5;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  for (const plot of plots) {
    const stroke = colour(`--calc-graph-${plot.colour + 1}`);
    ctx.strokeStyle = stroke;
    ctx.fillStyle = stroke;
    ctx.beginPath();
    for (const segment of plot.segments) {
      segment.forEach(([x, y], i) => {
        const px = X(x);
        const py = clamp(Y(y), -1e4, h + 1e4);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
    }
    ctx.stroke();
    for (const segment of plot.segments) {
      if (segment.length !== 1) continue;
      ctx.beginPath();
      ctx.arc(X(segment[0][0]), Y(segment[0][1]), 1.5, 0, 2 * Math.PI);
      ctx.fill();
    }
  }

  // Numbers along the axes, over the curves with a rim of background so they stay readable.
  // They stay at the edge when an axis is off the canvas.
  ctx.font = `12px ${css.fontFamily}`;
  ctx.fillStyle = colour("--calc-graph-label");
  ctx.strokeStyle = colour("--calc-graph-bg");
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  const text = (label, x, y) => {
    ctx.strokeText(label, x, y);
    ctx.fillText(label, x, y);
  };
  ctx.textBaseline = "top";
  ctx.textAlign = "center";
  let labelY = ay + 4;
  if (labelY > h - 18) labelY = Math.min(ay, h) - 18;
  labelY = clamp(labelY, 2, h - 16);
  for (const x of P.ticks(b.xmin, b.xmax, stepX)) {
    const px = X(x);
    if (x === 0 || px < 14 || px > w - 14) continue;
    text(P.tickLabel(x, stepX, lang), px, labelY);
  }
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  const yLabel = (label, py) => {
    const tw = ctx.measureText(label).width;
    let tx = ax - 6 - tw;
    if (tx < 4) tx = Math.max(4, ax + 6);
    if (tx + tw > w - 4) tx = w - 4 - tw;
    text(label, tx, py);
  };
  for (const y of P.ticks(b.ymin, b.ymax, stepY)) {
    const py = Y(y);
    if (y === 0 || py < 10 || py > h - 10) continue;
    yLabel(P.tickLabel(y, stepY, lang), py);
  }
  if (ax > 0 && ax < w && ay > 0 && ay < h - 16) {
    ctx.textBaseline = "top";
    yLabel("0", ay + 4);
  }

  if (point) {
    ctx.beginPath();
    ctx.arc(X(point.x), Y(point.y), 5.5, 0, 2 * Math.PI);
    ctx.fillStyle = colour(`--calc-graph-${point.colour + 1}`);
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = colour("--calc-graph-bg");
    ctx.stroke();
  }
}

const centroid = (points) => {
  const list = [...points.values()];
  return { x: list.reduce((s, p) => s + p.x, 0) / list.length, y: list.reduce((s, p) => s + p.y, 0) / list.length };
};

const spread = (points) => {
  const [a, b] = [...points.values()];
  return b ? Math.hypot(a.x - b.x, a.y - b.y) : 0;
};

export default function GraphingMode({ t, lang }) {
  const T = t.graph;
  const uid = useId();
  const [initial] = useState(initialGraph);
  const [fns, setFns] = useState(initial.fns);
  const [angle, setAngle] = useState(initial.angle);
  const [userView, setUserView] = useState(null); // null: the default window for the canvas size
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [trace, setTrace] = useState(null); // {key, x}: the traced point stays on its curve
  const [focused, setFocused] = useState(null);
  const [typing, setTyping] = useState(false);
  const [themeTick, setThemeTick] = useState(0);
  const nextKey = useRef(Math.max(...initial.fns.map((fn) => fn.key)) + 1);
  const activeKey = useRef(initial.fns[0].key); // the box the maths keys type into
  const caret = useRef(null); // {key, start, end} in that box
  const inputs = useRef(new Map());
  const focusKey = useRef(null);
  const typingTimer = useRef(null);
  const plotRef = useRef(null);
  const canvasRef = useRef(null);
  const gesture = useRef(null);

  useEffect(() => {
    store("graph", { functions: fns.map(({ text, colour, hidden }) => ({ text, colour, hidden })), angle });
  }, [fns, angle]);

  const parsed = useMemo(
    () =>
      fns.map((fn) => {
        const { tree, error } = parseFunction(fn.text);
        return { ...fn, error, f: tree ? compile(tree, angle) : null };
      }),
    [fns, angle],
  );
  const curves = useMemo(
    () => parsed.filter((fn) => fn.f && !fn.hidden).map((fn) => ({ id: fn.key, f: fn.f, colour: fn.colour })),
    [parsed],
  );
  const view = useMemo(() => userView ?? P.defaultView(size.w, size.h, angle), [userView, size.w, size.h, angle]);
  const plots = useMemo(
    () => (size.w && size.h ? curves.map((c) => ({ ...c, segments: P.sampleFunction(c.f, view, size.w, size.h) })) : []),
    [curves, view, size.w, size.h],
  );

  // The traced point, recomputed when its function changes.
  const point = useMemo(() => {
    const curve = trace && curves.find((c) => c.id === trace.key);
    const y = curve?.f(trace.x);
    return curve && Number.isFinite(y) ? { key: curve.id, colour: curve.colour, x: trace.x, y } : null;
  }, [trace, curves]);

  const live = useRef({ view, size });
  useLayoutEffect(() => {
    live.current = { view, size };
  });

  // Follow the size of the plot area.
  useLayoutEffect(() => {
    const el = plotRef.current;
    const measure = () => {
      const w = Math.round(el.clientWidth);
      const h = Math.round(el.clientHeight);
      setSize((s) => (s.w === w && s.h === h ? s : { w, h }));
    };
    measure();
    if (typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Redraw when the light or dark theme changes (the colours come from CSS).
  useEffect(() => {
    const bump = () => setThemeTick((n) => n + 1);
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    media?.addEventListener?.("change", bump);
    const observer = new MutationObserver(bump);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      media?.removeEventListener?.("change", bump);
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    if (canvasRef.current && size.w && size.h) drawGraph(canvasRef.current, { w: size.w, h: size.h, view, plots, point, lang });
  }, [size, view, plots, point, lang, themeTick]);

  // Wheel zoom needs a listener that may cancel scrolling the page.
  useEffect(() => {
    const canvas = canvasRef.current;
    function onWheel(event) {
      event.preventDefault();
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 400 : 1;
      const factor = Math.exp(clamp(event.deltaY * unit * 0.002, -0.7, 0.7));
      const rect = canvas.getBoundingClientRect();
      const { view: v, size: s } = live.current;
      setUserView(P.zoomView(v, factor, event.clientX - rect.left, event.clientY - rect.top, s.w, s.h));
    }
    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", onWheel);
  }, []);

  useEffect(() => () => clearTimeout(typingTimer.current), []);

  // Focus a box that was just added.
  useEffect(() => {
    if (focusKey.current === null) return;
    inputs.current.get(focusKey.current)?.focus();
    focusKey.current = null;
  }, [fns]);

  // ---- Functions -------------------------------------------------------------------

  function update(key, text) {
    setFns((list) => list.map((fn) => (fn.key === key ? { ...fn, text: text.slice(0, MAX_LENGTH) } : fn)));
    setTyping(true);
    clearTimeout(typingTimer.current);
    typingTimer.current = setTimeout(() => setTyping(false), ERROR_DELAY);
  }

  function add() {
    if (fns.length >= MAX_FUNCTIONS) return;
    const used = new Set(fns.map((fn) => fn.colour));
    const colour = [...Array(COLOURS).keys()].find((c) => !used.has(c)) ?? fns.length % COLOURS;
    const key = nextKey.current++;
    focusKey.current = key;
    activeKey.current = key;
    setFns([...fns, { key, text: "", colour, hidden: false }]);
  }

  function remove(key) {
    const rest = fns.filter((fn) => fn.key !== key);
    if (!rest.length) {
      // There is always one box to type in.
      update(key, "");
      inputs.current.get(key)?.focus();
      return;
    }
    if (activeKey.current === key) activeKey.current = rest[0].key;
    if (trace?.key === key) setTrace(null);
    setFns(rest);
  }

  function toggle(key) {
    setFns((list) => list.map((fn) => (fn.key === key ? { ...fn, hidden: !fn.hidden } : fn)));
  }

  function rememberCaret(key, event) {
    activeKey.current = key;
    caret.current = { key, start: event.target.selectionStart, end: event.target.selectionEnd };
  }

  /** A maths key: type its text at the caret of the box last used. */
  function insert(text) {
    const fn = fns.find((f) => f.key === activeKey.current) ?? fns[0];
    const at = caret.current?.key === fn.key ? caret.current : { start: fn.text.length, end: fn.text.length };
    const start = Math.min(at.start ?? fn.text.length, fn.text.length);
    const end = Math.min(at.end ?? start, fn.text.length);
    update(fn.key, fn.text.slice(0, start) + text + fn.text.slice(end));
    const pos = start + text.length;
    caret.current = { key: fn.key, start: pos, end: pos };
    const input = inputs.current.get(fn.key);
    if (input && document.activeElement === input) requestAnimationFrame(() => input.setSelectionRange(pos, pos));
  }

  // ---- The view --------------------------------------------------------------------

  function zoom(factor) {
    setUserView(P.zoomView(view, factor, size.w / 2, size.h / 2, size.w, size.h));
  }

  function pick(p, pointerType) {
    const hit = P.nearestPoint(curves, view, size.w, size.h, p.x, p.y, PICK[pointerType] ?? PICK.touch);
    return hit ? { key: hit.id, x: hit.x } : null;
  }

  function local(event) {
    const rect = canvasRef.current.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  /** Start (or restart, when a finger is added or lifted) a drag or pinch from the current view. */
  function restart(g) {
    g.startView = live.current.view;
    g.start = centroid(g.pointers);
    g.startSpread = spread(g.pointers);
  }

  function onPointerDown(event) {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    const g = gesture.current ?? { pointers: new Map(), moved: false };
    g.pointers.set(event.pointerId, local(event));
    if (g.pointers.size > 1) g.moved = true; // a pinch is never a tap
    restart(g);
    gesture.current = g;
  }

  function onPointerMove(event) {
    const g = gesture.current;
    if (!g || !g.pointers.has(event.pointerId)) {
      if (event.pointerType === "mouse") setTrace(pick(local(event), "mouse"));
      return;
    }
    g.pointers.set(event.pointerId, local(event));
    const c = centroid(g.pointers);
    if (!g.moved && Math.hypot(c.x - g.start.x, c.y - g.start.y) < TAP_SLOP) return;
    g.moved = true;
    let next = P.panView(g.startView, c.x - g.start.x, c.y - g.start.y);
    const now = spread(g.pointers);
    if (g.pointers.size > 1 && g.startSpread > 0 && now > 0) next = P.zoomView(next, g.startSpread / now, c.x, c.y, size.w, size.h);
    setUserView(next);
  }

  function onPointerEnd(event) {
    const g = gesture.current;
    if (!g || !g.pointers.has(event.pointerId)) return;
    g.pointers.delete(event.pointerId);
    if (event.type === "pointerup" && !g.moved) setTrace(pick(local(event), event.pointerType));
    if (g.pointers.size === 0) gesture.current = null;
    else restart(g);
  }

  function onKeyDown(event) {
    const moves = { ArrowLeft: [PAN_STEP, 0], ArrowRight: [-PAN_STEP, 0], ArrowUp: [0, PAN_STEP], ArrowDown: [0, -PAN_STEP] };
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (moves[event.key]) setUserView(P.panView(view, ...moves[event.key]));
    else if (event.key === "+" || event.key === "=") zoom(1 / ZOOM_STEP);
    else if (event.key === "-") zoom(ZOOM_STEP);
    else if (event.key === "0" || event.key === "Home") setUserView(null);
    else return;
    event.preventDefault();
  }

  // ---- Render ----------------------------------------------------------------------

  const described = parsed.filter((fn) => fn.f && !fn.hidden).map((fn) => `y = ${fn.text.replace(/^\s*(y|f\s*\(\s*x\s*\))\s*=\s*/i, "")}`);
  const graphLabel = described.length ? fill(T.graphOf, { list: described.join("; ") }) : T.empty;
  const places = P.traceDecimals(view);
  const pointName = point ? `f${parsed.findIndex((fn) => fn.key === point.key) + 1}` : "";
  const pointText = point ? P.formatPoint(point.x, point.y, places, lang) : "";
  const tip = point && { x: P.toPx(view, size.w, point.x), y: P.toPy(view, size.h, point.y) };

  return (
    <div className="calc-graph">
      <div className="calc-graph-side">
        <div className="calc-graph-head">
          <h3>{T.functions}</h3>
          <button
            type="button"
            className="calc-flat"
            aria-label={fill(t.angleKey, { unit: t.angles[angle] })}
            onClick={() => setAngle(angle === "rad" ? "deg" : "rad")}
          >
            {angle.toUpperCase()}
          </button>
        </div>

        <ul className="calc-fns">
          {parsed.map((fn, i) => {
            const n = i + 1;
            const errorId = `${uid}-error-${fn.key}`;
            const showError = fn.error && !(focused === fn.key && typing);
            return (
              <li
                key={fn.key}
                className={`calc-fn ${fn.hidden ? "is-hidden" : ""}`}
                style={{ "--calc-fn-colour": `var(--calc-graph-${fn.colour + 1})` }}
              >
                <button
                  type="button"
                  className="calc-fn-swatch"
                  aria-label={fill(T.show, { n })}
                  aria-pressed={!fn.hidden}
                  title={fill(fn.hidden ? T.show : T.hide, { n })}
                  onClick={() => toggle(fn.key)}
                >
                  f<sub>{n}</sub>
                </button>
                <span className="calc-fn-prefix" aria-hidden="true">
                  y =
                </span>
                <input
                  ref={(el) => {
                    if (el) inputs.current.set(fn.key, el);
                    else inputs.current.delete(fn.key);
                  }}
                  className="calc-fn-input"
                  type="text"
                  value={fn.text}
                  placeholder={T.placeholder}
                  aria-label={fill(T.fnInput, { n })}
                  aria-invalid={showError ? true : undefined}
                  aria-describedby={showError ? errorId : undefined}
                  autoComplete="off"
                  autoCapitalize="off"
                  autoCorrect="off"
                  spellCheck={false}
                  maxLength={MAX_LENGTH}
                  onChange={(event) => {
                    update(fn.key, event.target.value);
                    rememberCaret(fn.key, event);
                  }}
                  onFocus={() => {
                    setFocused(fn.key);
                    activeKey.current = fn.key;
                  }}
                  onBlur={() => setFocused(null)}
                  onSelect={(event) => rememberCaret(fn.key, event)}
                />
                <button
                  type="button"
                  className="calc-icon-btn calc-fn-remove"
                  aria-label={fill(T.remove, { n })}
                  onClick={() => remove(fn.key)}
                >
                  <Icon name="close" size={18} />
                </button>
                {showError && (
                  <p id={errorId} className="calc-fn-error">
                    {fill(T.errors[fn.error.code], { near: fn.error.near })}
                  </p>
                )}
              </li>
            );
          })}
        </ul>

        <button type="button" className="calc-flat calc-fn-add" disabled={fns.length >= MAX_FUNCTIONS} onClick={add}>
          <Icon name="plus" size={18} />
          {T.add}
        </button>

        <div className="calc-keys calc-graph-keys" role="group" aria-label={T.mathKeys}>
          {INSERTS.map((key) => (
            <button
              key={key.id}
              type="button"
              className="calc-key calc-key-fn"
              aria-label={fill(T.insert, { name: key.id === "x" ? "x" : t.keys[key.id] })}
              onClick={() => insert(key.text)}
            >
              {key.label}
            </button>
          ))}
        </div>
      </div>

      <div className="calc-graph-plot" ref={plotRef}>
        <canvas
          ref={canvasRef}
          className="calc-graph-canvas"
          role="img"
          tabIndex={0}
          aria-label={graphLabel}
          aria-describedby={`${uid}-keys`}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerEnd}
          onPointerCancel={onPointerEnd}
          onPointerLeave={(event) => {
            if (event.pointerType === "mouse" && !gesture.current) setTrace(null);
          }}
          onKeyDown={onKeyDown}
        />
        <span id={`${uid}-keys`} className="sr-only">
          {T.keyHelp}
        </span>
        {tip && tip.x >= 0 && tip.x <= size.w && tip.y >= 0 && tip.y <= size.h && (
          <div
            className={`calc-graph-tip ${tip.x > size.w - 150 ? "is-left" : ""} ${tip.y < 44 ? "is-below" : ""}`}
            style={{ left: tip.x, top: tip.y }}
            aria-hidden="true"
          >
            {pointText}
          </div>
        )}
        <div className="calc-graph-tools">
          <button type="button" className="calc-icon-btn" aria-label={T.zoomIn} title={T.zoomIn} onClick={() => zoom(1 / ZOOM_STEP)}>
            <Icon name="zoomIn" size={18} />
          </button>
          <button type="button" className="calc-icon-btn" aria-label={T.zoomOut} title={T.zoomOut} onClick={() => zoom(ZOOM_STEP)}>
            <Icon name="zoomOut" size={18} />
          </button>
          <button type="button" className="calc-icon-btn" aria-label={T.reset} title={T.reset} onClick={() => setUserView(null)}>
            <Icon name="home" size={18} />
          </button>
        </div>
      </div>

      <p className="calc-graph-readout" aria-live="polite">
        {point ? (
          <>
            <span className="calc-fn-dot" style={{ "--calc-fn-colour": `var(--calc-graph-${point.colour + 1})` }} aria-hidden="true" />
            {fill(T.point, { name: pointName, point: pointText })}
          </>
        ) : (
          T.hint
        )}
      </p>
    </div>
  );
}
