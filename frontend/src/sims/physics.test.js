import { describe, expect, it } from "vitest";

import { marketAtPrice, marketEquilibrium, niceStep, ohmsLaw, positionAt, projectile, quadraticFeatures } from "./physics";

describe("projectile", () => {
  it("matches the worked example in the S4 lesson", () => {
    const p = projectile({ speed: 20, angleDeg: 30, g: 9.8 });
    expect(p.time).toBeCloseTo(2.04, 2);
    expect(p.maxHeight).toBeCloseTo(5.1, 1);
    expect(p.range).toBeCloseTo(35.3, 1);
  });

  it("gives the maximum range at 45° and equal ranges for complementary angles", () => {
    const r = (angleDeg) => projectile({ speed: 15, angleDeg }).range;
    expect(r(45)).toBeGreaterThan(r(40));
    expect(r(45)).toBeGreaterThan(r(50));
    expect(r(30)).toBeCloseTo(r(60), 8);
  });

  it("lands back at y = 0 after the time of flight", () => {
    const p = projectile({ speed: 12, angleDeg: 70 });
    expect(positionAt(p, p.time).y).toBeCloseTo(0, 8);
  });
});

describe("ohmsLaw", () => {
  it("computes current and power", () => {
    expect(ohmsLaw({ voltage: 12, resistance: 4 })).toEqual({ current: 3, power: 36 });
  });
  it("rejects zero resistance", () => {
    expect(() => ohmsLaw({ voltage: 1, resistance: 0 })).toThrow();
  });
});

describe("market", () => {
  const m = { a: 100, b: 2, c: 20, d: 2 };
  it("finds the equilibrium from the economics lesson", () => {
    expect(marketEquilibrium(m)).toEqual({ price: 20, quantity: 60 });
  });
  it("detects shortages and surpluses", () => {
    expect(marketAtPrice(m, 10).status).toBe("shortage");
    expect(marketAtPrice(m, 30).status).toBe("surplus");
    expect(marketAtPrice(m, 20).status).toBe("equilibrium");
  });
});

describe("quadraticFeatures", () => {
  it("finds vertex and roots", () => {
    const f = quadraticFeatures(1, -4, 3);
    expect(f.vertex).toEqual({ x: 2, y: -1 });
    expect(f.roots).toEqual([1, 3]);
  });
  it("handles no real roots and repeated roots", () => {
    expect(quadraticFeatures(1, 2, 5).roots).toEqual([]);
    expect(quadraticFeatures(1, 6, 9).roots).toEqual([-3]);
  });
});

describe("niceStep", () => {
  it("picks 1/2/5 steps", () => {
    expect(niceStep(20)).toBe(2);
    expect(niceStep(100)).toBe(10);
    expect(niceStep(7)).toBe(1);
  });
});
