import { describe, expect, it } from "vitest";

import { compile, parseFunction } from "./expression.js";
import {
  bounds,
  defaultView,
  formatCoord,
  formatPoint,
  fromPx,
  nearestPoint,
  niceStep,
  panView,
  sampleFunction,
  tickLabel,
  ticks,
  toPx,
  toPy,
  traceDecimals,
  zoomView,
} from "./plot.js";

const W = 400;
const H = 300;
const f = (text, angle) => compile(parseFunction(text).tree, angle);
const view = defaultView(W, H);
const sample = (text, v = view, angle = "rad") => sampleFunction(f(text, angle), v, W, H);

/** Is any segment's line crossing x (between two of its points)? */
const joinedAcross = (segments, x) => segments.some((seg) => seg[0][0] < x && seg[seg.length - 1][0] > x);

describe("Graph window", () => {
  it("starts with x from −10 to 10 and equal units", () => {
    const b = bounds(view, W, H);
    expect(b.xmin).toBeCloseTo(-10, 12);
    expect(b.xmax).toBeCloseTo(10, 12);
    expect(b.ymax).toBeCloseTo(7.5, 12);
    expect(view.sx).toBe(view.sy);
    // A tall phone canvas still shows y from −6 to 6 at least.
    expect(bounds(defaultView(300, 600), 300, 600).ymax).toBeGreaterThanOrEqual(6);
    // Degrees: −400° to 400° across, so sin x shows its waves.
    const deg = bounds(defaultView(W, H, "deg"), W, H);
    expect(deg.xmax).toBeCloseTo(400, 9);
    expect(deg.ymax).toBeCloseTo(2.5, 9);
  });

  it("converts between pixels and graph units", () => {
    expect(toPx(view, W, 0)).toBe(200);
    expect(toPy(view, H, 0)).toBe(150);
    expect(toPy(view, H, 7.5)).toBeCloseTo(0, 9);
    expect(fromPx(view, W, 400)).toBeCloseTo(10, 12);
  });

  it("zooms around the pointer and pans with a drag", () => {
    const zoomed = zoomView(view, 0.5, 300, 150, W, H);
    expect(zoomed.sx).toBeCloseTo(view.sx / 2, 15);
    expect(fromPx(zoomed, W, 300)).toBeCloseTo(fromPx(view, W, 300), 12); // the point under the pointer stays
    expect(bounds(zoomed, W, H).xmax).toBeCloseTo(7.5, 9);
    const moved = panView(view, 20, 10); // drag right and down
    expect(moved.cx).toBeCloseTo(-1, 12);
    expect(moved.cy).toBeCloseTo(0.5, 12);
    // Zooming stops before the numbers lose their precision.
    expect(zoomView({ ...view, sx: 1e-12, sy: 1e-12 }, 0.5, 0, 0, W, H).sx).toBe(1e-12);
  });

  it("picks round grid steps and labels", () => {
    expect(niceStep(20, 10)).toBe(2);
    expect(niceStep(1, 10)).toBe(0.1);
    expect(niceStep(700, 10)).toBe(50);
    expect(niceStep(0.03, 5)).toBeCloseTo(0.005, 15);
    expect(ticks(-1, 1, 0.5)).toEqual([-1, -0.5, 0, 0.5, 1]);
    expect(ticks(0.05, 0.35, 0.1)).toEqual([0.1, 0.2, 0.3]); // not 0.30000000000000004
    expect(tickLabel(-1.5, 0.5)).toBe("−1.5");
    expect(tickLabel(0.5, 0.5, "fr")).toBe("0,5");
    expect(tickLabel(4, 2)).toBe("4");
    expect(tickLabel(2000000, 1000000)).toBe("2e+6");
    expect(tickLabel(0, 1)).toBe("0");
  });
});

describe("Sampling", () => {
  it("draws a continuous curve as one line", () => {
    const segments = sample("x^2");
    expect(segments).toHaveLength(1);
    const [first] = segments[0];
    expect(first[0]).toBeCloseTo(-10, 9);
    expect(first[1]).toBeCloseTo(100, 6);
  });

  it("joins steep but continuous curves", () => {
    expect(sample("x^9")).toHaveLength(1);
    expect(sample("50x")).toHaveLength(1);
  });

  it("does not join across the asymptote of 1/x", () => {
    const segments = sample("1/x");
    expect(segments).toHaveLength(2);
    expect(joinedAcross(segments, 0)).toBe(false);
    // Each side runs off the canvas towards the asymptote.
    expect(Math.abs(segments[0].at(-1)[1])).toBeGreaterThan(1000);
    expect(Math.abs(segments[1][0][1])).toBeGreaterThan(1000);
  });

  it("does not join across x = 0 even when 0 falls between two samples", () => {
    const shifted = { ...view, cx: 0.0123 };
    const segments = sample("1/x", shifted);
    expect(segments).toHaveLength(2);
    expect(joinedAcross(segments, 0)).toBe(false);
  });

  it("breaks tan x at each asymptote, in radians and degrees", () => {
    const segments = sample("tan x");
    // −10..10 contains the asymptotes ±π/2, ±3π/2, ±5π/2: 6 of them, so 7 pieces.
    expect(segments).toHaveLength(7);
    for (const k of [-5, -3, -1, 1, 3, 5]) expect(joinedAcross(segments, (k * Math.PI) / 2)).toBe(false);
    const degView = defaultView(W, H, "deg");
    const deg = sample("tan x", degView, "deg");
    // −400°..400°: asymptotes at ±90° and ±270°.
    expect(deg).toHaveLength(5);
    for (const a of [-270, -90, 90, 270]) expect(joinedAcross(deg, a)).toBe(false);
  });

  it("leaves gaps where the function has no value, and finds where they end", () => {
    const sqrt = sample("sqrt(x)");
    expect(sqrt).toHaveLength(1);
    expect(sqrt[0][0][0]).toBeCloseTo(0, 6); // starts at the origin
    expect(sqrt[0][0][1]).toBeLessThan(0.01);
    const circle = sample("sqrt(9 - x^2)");
    expect(circle).toHaveLength(1);
    expect(circle[0][0][0]).toBeCloseTo(-3, 6);
    expect(circle[0].at(-1)[0]).toBeCloseTo(3, 6);
    const ln = sample("ln x");
    expect(ln).toHaveLength(1);
    expect(ln[0][0][1]).toBeLessThan(-20); // drops off the bottom near x = 0
    expect(sample("sqrt(-1 - x^2)")).toHaveLength(0);
  });

  it("breaks a jump that is not a pole", () => {
    const segments = sample("abs(x)/x");
    expect(segments).toHaveLength(2);
    expect(joinedAcross(segments, 0)).toBe(false);
  });
});

describe("Tracing", () => {
  const curves = [
    { id: "a", f: f("x") },
    { id: "b", f: f("x^2") },
  ];

  it("finds the curve nearest to the pointer", () => {
    // x = 2 at pixel 240; y = 2 at pixel 110 and y = 4 at pixel 70.
    expect(nearestPoint(curves, view, W, H, 240, 112)).toEqual({ id: "a", x: 2, y: 2 });
    expect(nearestPoint(curves, view, W, H, 240, 72)).toEqual({ id: "b", x: 2, y: 4 });
    expect(nearestPoint(curves, view, W, H, 240, 300, 20)).toBeNull();
    expect(nearestPoint([{ id: "c", f: f("sqrt(x)") }], view, W, H, 100, 150)).toBeNull();
  });

  it("rounds the point to what the pixels can show", () => {
    expect(traceDecimals(view)).toBe(3); // 0.05 units per pixel
    expect(formatCoord(1.23456, 3)).toBe("1.235");
    expect(formatCoord(2.0000001, 3)).toBe("2");
    expect(formatCoord(-0.0001, 3)).toBe("0");
    expect(formatCoord(-1.5, 3)).toBe("−1.5");
    expect(formatCoord(1.5e12, 3)).toBe("1.5e+12");
    expect(formatPoint(1.5, -2.25, 3)).toBe("(1.5, −2.25)");
    expect(formatPoint(1.5, -2.25, 3, "fr")).toBe("(1,5 ; −2,25)");
  });
});
