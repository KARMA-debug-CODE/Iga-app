import { useEffect, useState } from "react";

import { drawAxes, makeView, palette, Slider, useCanvas } from "./canvas";
import { quadraticFeatures, round } from "./physics";

const MODES = {
  linear: { label: "Linear", params: { m: 1, c: 0 } },
  quadratic: { label: "Quadratic", params: { a: 1, b: 0, c: -4 } },
  sine: { label: "Sine", params: { A: 2, B: 1, D: 0 } },
};

function fn(mode, p) {
  if (mode === "linear") return (x) => p.m * x + p.c;
  if (mode === "quadratic") return (x) => p.a * x * x + p.b * x + p.c;
  return (x) => p.A * Math.sin(p.B * x) + p.D;
}

const sign = (n) => (n < 0 ? `− ${Math.abs(n)}` : `+ ${n}`);

function equation(mode, p) {
  if (mode === "linear") return `y = ${p.m}x ${sign(p.c)}`;
  if (mode === "quadratic") return `y = ${p.a}x² ${sign(p.b)}x ${sign(p.c)}`;
  return `y = ${p.A} sin(${p.B}x) ${sign(p.D)}`;
}

export default function Grapher() {
  const [mode, setMode] = useState("linear");
  const [params, setParams] = useState(MODES.linear.params);
  const [canvasRef, size] = useCanvas(0.75, 260);
  const set = (key) => (value) => setParams((p) => ({ ...p, [key]: value }));

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const colors = palette();
    const view = makeView({ width: size.width, height: size.height, xMin: -10, xMax: 10, yMin: -10, yMax: 10, pad: { l: 28, r: 10, t: 10, b: 22 } });
    drawAxes(ctx, view, { xStep: 2, yStep: 2, xLabel: "x", yLabel: "y", colors });

    const f = fn(mode, params);
    ctx.save();
    ctx.beginPath();
    ctx.rect(view.pad.l, view.pad.t, size.width - view.pad.l - view.pad.r, size.height - view.pad.t - view.pad.b);
    ctx.clip();
    ctx.strokeStyle = colors.blue;
    ctx.lineWidth = 3;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i <= 400; i++) {
      const x = -10 + (20 * i) / 400;
      const y = f(x);
      if (!Number.isFinite(y) || Math.abs(y) > 1e4) {
        started = false;
        continue;
      }
      if (!started) ctx.moveTo(view.x(x), view.y(y));
      else ctx.lineTo(view.x(x), view.y(y));
      started = true;
    }
    ctx.stroke();

    const dot = (x, y, colour) => {
      ctx.fillStyle = colour;
      ctx.beginPath();
      ctx.arc(view.x(x), view.y(y), 6, 0, Math.PI * 2);
      ctx.fill();
    };
    dot(0, f(0), colors.green);
    if (mode === "quadratic") {
      const q = quadraticFeatures(params.a, params.b, params.c);
      if (q) {
        dot(q.vertex.x, q.vertex.y, colors.red);
        q.roots.forEach((r) => dot(r, 0, colors.yellow));
      }
    }
    if (mode === "linear" && params.m !== 0) dot(-params.c / params.m, 0, colors.yellow);
    ctx.restore();
  }, [canvasRef, size, mode, params]);

  const q = mode === "quadratic" ? quadraticFeatures(params.a, params.b, params.c) : null;

  return (
    <div className="lab">
      <div className="chips" role="group" aria-label="Function type">
        {Object.entries(MODES).map(([key, m]) => (
          <button
            key={key}
            className={`chip ${mode === key ? "active" : ""}`}
            aria-pressed={mode === key}
            onClick={() => {
              setMode(key);
              setParams(m.params);
            }}
          >
            {m.label}
          </button>
        ))}
      </div>
      <div style={{ fontFamily: "var(--mono)", fontSize: "1.2rem", fontWeight: 700 }} aria-live="polite">
        {equation(mode, params)}
      </div>
      <canvas ref={canvasRef} aria-label={`Graph of ${equation(mode, params)}`} />
      <div className="lab-controls">
        {mode === "linear" && (
          <>
            <Slider label="Gradient m" value={params.m} min={-5} max={5} step={0.5} onChange={set("m")} />
            <Slider label="Intercept c" value={params.c} min={-8} max={8} step={0.5} onChange={set("c")} />
          </>
        )}
        {mode === "quadratic" && (
          <>
            <Slider label="a" value={params.a} min={-3} max={3} step={0.25} onChange={(v) => set("a")(v === 0 ? 0.25 : v)} />
            <Slider label="b" value={params.b} min={-8} max={8} step={0.5} onChange={set("b")} />
            <Slider label="c" value={params.c} min={-8} max={8} step={0.5} onChange={set("c")} />
          </>
        )}
        {mode === "sine" && (
          <>
            <Slider label="Amplitude A" value={params.A} min={0} max={8} step={0.5} onChange={set("A")} />
            <Slider label="Frequency B" value={params.B} min={0.25} max={4} step={0.25} onChange={set("B")} />
            <Slider label="Vertical shift D" value={params.D} min={-5} max={5} step={0.5} onChange={set("D")} />
          </>
        )}
      </div>
      <div className="lab-readout">
        <div>
          <span style={{ color: "#2E8B57" }}>●</span> y-intercept <strong>(0, {round(fn(mode, params)(0))})</strong>
        </div>
        {mode === "linear" && (
          <div>
            <span style={{ color: "#FAD201" }}>●</span> x-intercept{" "}
            <strong>{params.m === 0 ? "none" : `(${round(-params.c / params.m)}, 0)`}</strong>
          </div>
        )}
        {q && (
          <>
            <div>
              <span style={{ color: "#D64545" }}>●</span> vertex <strong>({round(q.vertex.x)}, {round(q.vertex.y)})</strong>
              <span className="small muted">{q.opensUp ? "minimum" : "maximum"}</span>
            </div>
            <div>
              Discriminant <strong>{round(q.discriminant)}</strong>
              <span className="small muted">
                {q.roots.length === 0 ? "no real roots" : `roots: ${q.roots.map((r) => round(r)).join(", ")}`}
              </span>
            </div>
          </>
        )}
        {mode === "sine" && (
          <div>
            Period <strong>{round((2 * Math.PI) / params.B)}</strong>
            <span className="small muted">2π / B</span>
          </div>
        )}
      </div>
    </div>
  );
}
