// Standard mode: immediate execution like Windows Standard (2 + 3 x 4 = 20),
// with %, 1/x, x squared and square root. Also the decimal number entry rules
// and the four operations shared with Scientific mode.
import { around, postfix } from "./core.js";
import { D, fail, fin, guarded } from "./decimal.js";

/** Digits typed so far, not counting the leading "0." of numbers below 1. */
function countDigits(entry) {
  const mant = entry.split("e")[0].replace("-", "");
  const digits = mant.replace(".", "");
  return /^0(\.|$)/.test(mant) ? digits.length - 1 : digits.length;
}

/** How numbers are typed in the decimal modes (at most maxDigits digits). */
export function decimalEntry(maxDigits) {
  return {
    appendDigit(entry, d) {
      if (!/^[0-9]$/.test(d)) return null;
      const e = entry.indexOf("e");
      if (e >= 0) {
        const exp = entry.slice(e + 2);
        if (exp.length >= 4) return null;
        return entry.slice(0, e + 2) + (exp === "0" ? d : exp + d);
      }
      if (countDigits(entry) >= maxDigits) return null;
      if (entry === "0") return d;
      if (entry === "-0") return `-${d}`;
      return entry + d;
    },
    appendPoint(entry) {
      if (entry.includes(".") || entry.includes("e")) return null;
      return `${entry}.`;
    },
    appendExp(entry) {
      if (entry.includes("e")) return null;
      return `${entry}e+`;
    },
    negateEntry(entry) {
      // While typing an exponent, +/- changes the exponent's sign (2e+3 -> 2e-3).
      const e = entry.indexOf("e");
      if (e >= 0) return entry.slice(0, e + 1) + (entry[e + 1] === "-" ? "+" : "-") + entry.slice(e + 2);
      if (entry.startsWith("-")) return entry.slice(1);
      return entry === "0" ? entry : `-${entry}`;
    },
    backspace(entry) {
      if (/e[+-]$/.test(entry)) return entry.slice(0, -2);
      const next = entry.slice(0, -1);
      return next === "" || next === "-" ? "0" : next;
    },
    parse(entry) {
      let s = entry;
      if (/e[+-]$/.test(s)) s += "0";
      s = s.replace(".e", "e");
      if (s.endsWith(".")) s = s.slice(0, -1);
      if (s === "" || s === "-") s = "0";
      return guarded(() => fin(new D(s)));
    },
    isNeg: (v) => v.isNeg() && !v.isZero(),
  };
}

export function divide(a, b) {
  if (b.isZero()) fail(a.isZero() ? "undefined" : "divzero");
  return fin(a.div(b));
}

export const ARITHMETIC = {
  add: { sym: "+", prec: 5, fn: (a, b) => fin(a.plus(b)) },
  sub: { sym: "−", prec: 5, fn: (a, b) => fin(a.minus(b)) },
  mul: { sym: "×", prec: 6, fn: (a, b) => fin(a.times(b)) },
  div: { sym: "÷", prec: 6, fn: divide },
};

export const BASIC_UNARY = {
  negate: { show: around("−(", ")"), fn: (x) => fin(x.neg()) },
  sqr: { show: postfix("²"), fn: (x) => fin(x.times(x)) },
  sqrt: {
    show: around("√(", ")"),
    fn: (x) => {
      if (x.isNeg()) fail("invalid");
      return fin(D.sqrt(x));
    },
  },
  inv: {
    show: around("1/(", ")"),
    fn: (x) => {
      if (x.isZero()) fail("divzero");
      return fin(new D(1).div(x));
    },
  },
};

export const standardDomain = {
  kind: "decimal",
  zero: new D(0),
  immediate: true,
  ...decimalEntry(16),
  appendExp: null,
  binary: ARITHMETIC,
  unary: BASIC_UNARY,
  percent(acc, cur, op) {
    if (op === "add" || op === "sub") return fin(acc.times(cur).div(100));
    return fin(cur.div(100));
  },
};
