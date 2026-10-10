// Shared Decimal set-up for every decimal calculator mode.
//
// Like the Windows calculator, values are kept to 32 significant digits between
// operations (SIG) while each operation is worked out with a few guard digits
// (precision 40), so 0.1 + 0.2 is exactly 0.3 and sin 30 degrees is exactly 0.5.
import Decimal from "decimal.js";

export const D = Decimal.clone({
  precision: 40,
  rounding: Decimal.ROUND_HALF_UP,
  // "mod" takes the sign of the divisor (-7 mod 3 = 2), as in Python and Excel.
  modulo: Decimal.ROUND_FLOOR,
  toExpNeg: -7,
  toExpPos: 21,
});

export const SIG = 32;

const PI_TEXT = "3.14159265358979323846264338327950288419716939937510582097494459230781640628620899";

/** pi with all the digits above (the Decimal constructor does not round its input). */
export const PI = new D(PI_TEXT);
export const PI_TEXT_LONG = PI_TEXT;
/** Euler's number to 40 digits. */
export const E = D.exp(1);

const LIMIT = new D("1e10000");
const TINY = new D("1e-10000");

export class CalcError extends Error {
  constructor(code) {
    super(code);
    this.name = "CalcError";
    this.code = code; // "divzero" | "undefined" | "invalid" | "overflow"
  }
}

export function fail(code) {
  throw new CalcError(code);
}

/** Check a result and round it to the stored precision. */
export function fin(x) {
  if (x.isNaN()) fail("invalid");
  if (!x.isFinite()) fail("overflow");
  if (x.isZero()) return new D(0);
  const a = x.abs();
  if (a.gte(LIMIT)) fail("overflow");
  if (a.lt(TINY)) return new D(0);
  return x.toSignificantDigits(SIG);
}

/** Run a Decimal computation, turning decimal.js exceptions into "Invalid input". */
export function guarded(fn) {
  try {
    return fn();
  } catch (e) {
    if (e instanceof CalcError) throw e;
    throw new CalcError("invalid");
  }
}

export function isDecimal(v) {
  return D.isDecimal(v);
}

/** Plain text for storage: round-trips through new D(text). */
export function decimalToText(v) {
  return v.toString();
}

export function decimalFromText(text) {
  if (typeof text !== "string" || !/^-?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(text.trim())) return null;
  const v = new D(text.trim());
  return v.isFinite() ? v : null;
}
