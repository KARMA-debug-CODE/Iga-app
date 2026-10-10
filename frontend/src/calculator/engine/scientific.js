// Scientific mode: operator precedence and brackets (2 + 3 x 4 = 14), angles in
// degrees, radians or gradians, the inverse (2nd) and hyperbolic functions,
// powers, roots, logarithms and n! (with the gamma function for non-integers).
import { around, call, postfix } from "./core.js";
import { D, E, PI, PI_TEXT_LONG, fail, fin, guarded } from "./decimal.js";
import { ARITHMETIC, BASIC_UNARY, decimalEntry } from "./standard.js";

export const ANGLES = ["deg", "rad", "grad"];
const HALF_TURN = { deg: new D(180), grad: new D(200) };
const MARK = { deg: "°", rad: "", grad: "ᵍ" };

const ONE = new D(1);
// Results this far below the angle are rounding noise (sin of a 32-digit pi is about 3e-33).
const NOISE = new D("1e-31");
// 10^x beyond this is an overflow (the display stops at 1e10000, like Windows).
const MAX_EXP10 = new D(10000);

function toRadians(x, angle) {
  return angle === "rad" ? x : x.times(PI).div(HALF_TURN[angle]);
}

function fromRadians(r, angle) {
  return angle === "rad" ? r : r.times(HALF_TURN[angle]).div(PI);
}

/** Exact values at quarter turns (sin 180° = 0, tan 90° = Invalid input), as on Windows. */
function quarterTurn(name, x, angle) {
  if (angle === "rad") return null;
  const quarter = HALF_TURN[angle].div(2);
  const turns = x.div(quarter);
  if (!turns.isInteger()) return null;
  const k = turns.mod(4).toNumber(); // 0, 1, 2 or 3 (mod rounds towards -Infinity)
  if (name === "sin") return new D([0, 1, 0, -1][k]);
  if (name === "cos") return new D([1, 0, -1, 0][k]);
  if (k % 2) fail("invalid");
  return new D(0);
}

function snap(r, x) {
  return r.abs().lt(x.abs().times(NOISE)) ? new D(0) : r;
}

function circular(name, x, angle) {
  return guarded(() => {
    const exact = quarterTurn(name, x, angle);
    if (exact) return exact;
    // Reduce whole turns exactly before converting, so sin(30 + 360k)° is still exactly 0.5.
    const reduced = angle === "rad" ? x : x.mod(HALF_TURN[angle].times(2));
    const r = toRadians(reduced, angle);
    const sin = () => snap(D.sin(r), r);
    const cos = () => snap(D.cos(r), r);
    if (name === "sin") return fin(sin());
    if (name === "cos") return fin(cos());
    const c = cos();
    if (c.isZero()) fail("invalid");
    return fin(sin().div(c));
  });
}

function inverseCircular(name, x, angle) {
  if ((name === "asin" || name === "acos") && x.abs().gt(ONE)) fail("invalid");
  return guarded(() => fin(fromRadians(D[name](x), angle)));
}

const COSH_LIMIT = new D(23100);

function hyperbolic(name, x) {
  if ((name === "sinh" || name === "cosh") && x.abs().gt(COSH_LIMIT)) fail("overflow");
  if (name === "acosh" && x.lt(ONE)) fail("invalid");
  if (name === "atanh" && x.abs().gte(ONE)) fail("invalid");
  return guarded(() => fin(D[name](x)));
}

/** True when y is 1/n for an odd integer n (within the stored precision): (−8)^(1/3) = −2. */
function isOddRoot(y) {
  if (y.isZero()) return false;
  const n = ONE.div(y);
  const r = n.round();
  return r.minus(n).abs().lt("1e-25") && r.mod(2).abs().eq(1);
}

/** Guard against results beyond 1e10000 before computing them. */
function checkSize(x, y) {
  if (x.isZero() || x.abs().eq(ONE)) return;
  const size = y.times(D.log10(x.abs()));
  if (size.gt(MAX_EXP10)) fail("overflow");
}

export function power(x, y) {
  return guarded(() => {
    if (x.isZero()) {
      if (y.isNeg()) fail("divzero");
      return new D(y.isZero() ? 1 : 0);
    }
    if (x.isNeg() && !y.isInteger()) {
      if (!isOddRoot(y)) fail("invalid");
      checkSize(x, y);
      return fin(x.neg().pow(y).neg());
    }
    checkSize(x, y);
    const size = y.times(D.log10(x.abs()));
    if (size.lt(MAX_EXP10.neg())) return new D(0);
    return fin(x.pow(y));
  });
}

/** x ʸ√ y: the y-th root of x. Odd roots of negative numbers are allowed (³√−8 = −2). */
export function root(x, y) {
  if (y.isZero()) fail("invalid");
  return guarded(() => {
    if (x.isNeg()) {
      if (!y.isInteger() || y.mod(2).isZero()) fail("invalid");
      return fin(power(x.neg(), ONE.div(y)).neg());
    }
    return power(x, ONE.div(y));
  });
}

/** x log base y. */
export function logBase(x, y) {
  if (!x.isPositive() || x.isZero() || !y.isPositive() || y.isZero() || y.eq(ONE)) fail("invalid");
  return guarded(() => fin(D.ln(x).div(D.ln(y))));
}

export function modulo(x, y) {
  if (y.isZero()) fail("divzero");
  // decimal.js is set to take the sign of the divisor: −7 mod 3 = 2.
  return guarded(() => fin(x.mod(y)));
}

// ---- n! and the gamma function ---------------------------------------------

// Working precision for the gamma function, above the 32 digits that are kept.
const G = D.clone({ precision: 50 });
const G_PI = new G(PI_TEXT_LONG);
const HALF_LN_2PI = G.ln(G_PI.times(2)).div(2);
// Bernoulli numbers B2, B4, ... B40 for Stirling's series.
const BERNOULLI = [
  [1, 6],
  [-1, 30],
  [1, 42],
  [-1, 30],
  [5, 66],
  [-691, 2730],
  [7, 6],
  [-3617, 510],
  [43867, 798],
  [-174611, 330],
  [854513, 138],
  ["-236364091", 2730],
  [8553103, 6],
  ["-23749461029", 870],
  ["8615841276005", 14322],
  ["-7709321041217", 510],
  ["2577687858367", 6],
  ["-26315271553053477373", 1919190],
  ["2929993913841559", 6],
  ["-261082718496449122051", 13530],
].map(([n, d]) => new G(n).div(d));
const SHIFT = 40;

/** ln Γ(z) for z >= 40 by Stirling's series (error far below 1e-40 there). */
function lnGammaLarge(z) {
  let sum = z.minus(0.5).times(G.ln(z)).minus(z).plus(HALF_LN_2PI);
  const z2 = z.times(z);
  let zp = z;
  BERNOULLI.forEach((b, i) => {
    const k = 2 * (i + 1);
    sum = sum.plus(b.div(zp.times(k * (k - 1))));
    zp = zp.times(z2);
  });
  return sum;
}

function gamma(z) {
  if (z.lt(0.5)) {
    // Reflection: Γ(z) Γ(1 − z) = π / sin(πz).
    const s = G.sin(G_PI.times(z));
    if (s.isZero()) fail("invalid");
    return G_PI.div(s.times(gamma(new G(1).minus(z))));
  }
  let w = z;
  let product = new G(1);
  while (w.lt(SHIFT)) {
    product = product.times(w);
    w = w.plus(1);
  }
  return G.exp(lnGammaLarge(w)).div(product);
}

const MAX_FACTORIAL = 3249; // 3249! is beyond 1e10000

export function factorial(x) {
  if (x.gt(MAX_FACTORIAL)) fail("overflow");
  if (x.isInteger()) {
    if (x.isNeg()) fail("invalid");
    let r = new D(1);
    for (let i = 2; x.gte(i); i += 1) r = r.times(i);
    return fin(r);
  }
  return guarded(() => fin(new D(gamma(new G(x).plus(1)))));
}

// ---- The scientific domain ---------------------------------------------------

const angled = (name) => (inner, _domain, ctx) => call(name, MARK[ctx.angle || "deg"])(inner);

const trig = {};
for (const name of ["sin", "cos", "tan"]) {
  trig[name] = { show: angled(name), fn: (x, ctx) => circular(name, x, ctx.angle || "deg") };
  trig[`a${name}`] = { show: call(`${name}⁻¹`), fn: (x, ctx) => inverseCircular(`a${name}`, x, ctx.angle || "deg") };
  trig[`${name}h`] = { show: call(`${name}h`), fn: (x) => hyperbolic(`${name}h`, x) };
  trig[`a${name}h`] = { show: call(`${name}h⁻¹`), fn: (x) => hyperbolic(`a${name}h`, x) };
}

export const SCIENTIFIC_UNARY = {
  ...BASIC_UNARY,
  ...trig,
  cube: { show: postfix("³"), fn: (x) => fin(x.times(x).times(x)) },
  cbrt: { show: around("∛(", ")"), fn: (x) => guarded(() => fin(D.cbrt(x))) },
  abs: { show: around("|", "|"), fn: (x) => x.abs() },
  fact: { show: postfix("!"), fn: factorial },
  tenx: { show: around("10^(", ")"), fn: (x) => power(new D(10), x) },
  twox: { show: around("2^(", ")"), fn: (x) => power(new D(2), x) },
  ex: { show: around("e^(", ")"), fn: (x) => power(E, x) },
  log: {
    show: call("log"),
    fn: (x) => {
      if (!x.isPositive() || x.isZero()) fail("invalid");
      return guarded(() => fin(D.log10(x)));
    },
  },
  ln: {
    show: call("ln"),
    fn: (x) => {
      if (!x.isPositive() || x.isZero()) fail("invalid");
      return guarded(() => fin(D.ln(x)));
    },
  },
};

export const scientificDomain = {
  kind: "decimal",
  zero: new D(0),
  immediate: false,
  ...decimalEntry(16),
  binary: {
    ...ARITHMETIC,
    mod: { sym: "mod", prec: 6, fn: modulo },
    // x^y^z is x^(y^z), as in mathematics.
    pow: { sym: "^", prec: 7, right: true, fn: power },
    yroot: { sym: "ʸ√", prec: 7, fn: root },
    logy: { sym: "log base", prec: 7, fn: logBase },
  },
  unary: SCIENTIFIC_UNARY,
  percent: null,
};

export const CONSTANTS = { pi: fin(PI), e: fin(E) };
