// Pure maths behind the built-in labs. Kept separate so it can be unit tested.

export const GRAVITY = { earth: 9.8, moon: 1.6, mars: 3.7 };

export function projectile({ speed, angleDeg, g = GRAVITY.earth }) {
  const angle = (angleDeg * Math.PI) / 180;
  const ux = speed * Math.cos(angle);
  const uy = speed * Math.sin(angle);
  const time = (2 * uy) / g;
  return {
    ux,
    uy,
    time,
    maxHeight: (uy * uy) / (2 * g),
    range: ux * time,
  };
}

export function positionAt({ ux, uy }, t, g = GRAVITY.earth) {
  return { x: ux * t, y: uy * t - 0.5 * g * t * t };
}

export function ohmsLaw({ voltage, resistance }) {
  if (resistance <= 0) throw new Error("Resistance must be positive");
  const current = voltage / resistance;
  return { current, power: voltage * current };
}

/** Qd = a − b·P and Qs = c + d·P */
export function marketEquilibrium({ a, b, c, d }) {
  const price = (a - c) / (b + d);
  return { price, quantity: a - b * price };
}

export function marketAtPrice({ a, b, c, d }, price) {
  const demanded = Math.max(0, a - b * price);
  const supplied = Math.max(0, c + d * price);
  const gap = demanded - supplied;
  return {
    demanded,
    supplied,
    status: Math.abs(gap) < 0.5 ? "equilibrium" : gap > 0 ? "shortage" : "surplus",
    gap: Math.abs(gap),
  };
}

export function quadraticFeatures(a, b, c) {
  if (a === 0) return null;
  const vx = -b / (2 * a);
  const vy = a * vx * vx + b * vx + c;
  const disc = b * b - 4 * a * c;
  let roots = [];
  if (disc > 1e-12) {
    const s = Math.sqrt(disc);
    roots = [(-b - s) / (2 * a), (-b + s) / (2 * a)].sort((p, q) => p - q);
  } else if (Math.abs(disc) <= 1e-12) {
    roots = [vx];
  }
  return { vertex: { x: vx, y: vy }, discriminant: disc, roots, opensUp: a > 0 };
}

/** A "nice" grid spacing (1, 2 or 5 × 10ⁿ) giving roughly `target` divisions. */
export function niceStep(span, target = 8) {
  const raw = span / target;
  const power = 10 ** Math.floor(Math.log10(raw));
  const unit = raw / power;
  const nice = unit < 1.5 ? 1 : unit < 3.5 ? 2 : unit < 7.5 ? 5 : 10;
  return nice * power;
}

export function round(value, digits = 2) {
  if (!Number.isFinite(value)) return "—";
  const f = 10 ** digits;
  return String(Math.round(value * f) / f);
}
