import { useEffect, useRef, useState } from "react";

/** Theme-aware colours read from CSS variables at draw time. */
export function palette() {
  const css = getComputedStyle(document.documentElement);
  const v = (name, fallback) => css.getPropertyValue(name).trim() || fallback;
  return {
    bg: v("--surface-2", "#eef3f8"),
    grid: v("--border", "#dbe3ea"),
    text: v("--text-soft", "#52606d"),
    strong: v("--text", "#13202b"),
    blue: "#00A1DE",
    yellow: "#FAD201",
    green: "#2E8B57",
    red: "#D64545",
    primary: v("--primary", "#0077a8"),
  };
}

/** Resize a canvas to its CSS width × `aspect`, accounting for high-DPI screens. */
export function useCanvas(aspect = 0.6, minHeight = 240) {
  const ref = useRef(null);
  const [size, setSize] = useState({ width: 600, height: 360 });

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return undefined;
    const resize = () => {
      const width = canvas.parentElement.clientWidth || 600;
      const height = Math.max(minHeight, Math.round(width * aspect));
      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.height = `${height}px`;
      canvas.getContext("2d").setTransform(dpr, 0, 0, dpr, 0, 0);
      setSize({ width, height });
    };
    resize();
    const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(resize) : null;
    observer?.observe(canvas.parentElement);
    return () => observer?.disconnect();
  }, [aspect, minHeight]);

  return [ref, size];
}

/** Map world coordinates to canvas pixels. */
export function makeView({ width, height, xMin, xMax, yMin, yMax, pad = { l: 40, r: 12, t: 12, b: 30 } }) {
  const sx = (width - pad.l - pad.r) / (xMax - xMin);
  const sy = (height - pad.t - pad.b) / (yMax - yMin);
  return {
    pad,
    x: (wx) => pad.l + (wx - xMin) * sx,
    y: (wy) => height - pad.b - (wy - yMin) * sy,
    xMin,
    xMax,
    yMin,
    yMax,
    width,
    height,
  };
}

export function drawAxes(ctx, view, { xStep, yStep, xLabel = "", yLabel = "", colors }) {
  const { x, y, xMin, xMax, yMin, yMax, width, height } = view;
  ctx.save();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = colors.bg;
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = colors.grid;
  ctx.fillStyle = colors.text;
  ctx.lineWidth = 1;
  ctx.font = "11px system-ui, sans-serif";

  const start = (min, step) => Math.ceil(min / step) * step;
  for (let gx = start(xMin, xStep); gx <= xMax + 1e-9; gx += xStep) {
    ctx.beginPath();
    ctx.moveTo(x(gx), y(yMin));
    ctx.lineTo(x(gx), y(yMax));
    ctx.stroke();
    ctx.textAlign = "center";
    ctx.fillText(+gx.toFixed(6), x(gx), height - view.pad.b + 14);
  }
  for (let gy = start(yMin, yStep); gy <= yMax + 1e-9; gy += yStep) {
    ctx.beginPath();
    ctx.moveTo(x(xMin), y(gy));
    ctx.lineTo(x(xMax), y(gy));
    ctx.stroke();
    ctx.textAlign = "right";
    ctx.fillText(+gy.toFixed(6), view.pad.l - 6, y(gy) + 4);
  }
  // Axes through zero when visible.
  ctx.strokeStyle = colors.strong;
  ctx.lineWidth = 1.5;
  if (yMin <= 0 && yMax >= 0) {
    ctx.beginPath();
    ctx.moveTo(x(xMin), y(0));
    ctx.lineTo(x(xMax), y(0));
    ctx.stroke();
  }
  if (xMin <= 0 && xMax >= 0) {
    ctx.beginPath();
    ctx.moveTo(x(0), y(yMin));
    ctx.lineTo(x(0), y(yMax));
    ctx.stroke();
  }
  ctx.fillStyle = colors.strong;
  ctx.font = "600 12px system-ui, sans-serif";
  ctx.textAlign = "right";
  if (xLabel) ctx.fillText(xLabel, width - view.pad.r, y(Math.max(yMin, 0)) - 6);
  ctx.textAlign = "left";
  if (yLabel) ctx.fillText(yLabel, x(Math.max(xMin, 0)) + 6, view.pad.t + 10);
  ctx.restore();
}

export function Slider({ label, value, min, max, step = 1, unit = "", onChange }) {
  return (
    <label>
      <span className="range-label">
        <span>{label}</span>
        <span>
          {value}
          {unit}
        </span>
      </span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}
