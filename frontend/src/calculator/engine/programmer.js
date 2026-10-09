// Programmer mode: whole numbers stored in two's complement in a word of 64, 32,
// 16 or 8 bits (QWORD, DWORD, WORD, BYTE), typed in HEX, DEC, OCT or BIN, with
// the bitwise operators and shifts. Values are BigInt, kept signed (−1, not 255).
import { around, call } from "./core.js";
import { fail } from "./decimal.js";

export const BASES = [16, 10, 8, 2];
export const BASE_NAMES = { 16: "HEX", 10: "DEC", 8: "OCT", 2: "BIN" };
export const WORDS = [64, 32, 16, 8];
export const WORD_NAMES = { 64: "QWORD", 32: "DWORD", 16: "WORD", 8: "BYTE" };

const PREFIX = { 16: "0x", 8: "0o", 2: "0b" };
const DIGITS = "0123456789ABCDEF";

export const wrap = (v, bits) => BigInt.asIntN(bits, v);

/** Digits of a value in a base: DEC is signed, the other bases show the bit pattern. */
export function toBase(v, base, bits) {
  if (base === 10) return wrap(v, bits).toString();
  return BigInt.asUintN(bits, v).toString(base).toUpperCase();
}

/** Parse digits typed in a base ("FF", "-12", "1010"); null if they are not valid. */
export function fromBase(text, base, bits) {
  const digits = text.trim().toUpperCase();
  if (base === 10) {
    if (!/^-?\d+$/.test(digits)) return null;
    return BigInt(digits);
  }
  const allowed = DIGITS.slice(0, base);
  if (!digits || [...digits].some((d) => !allowed.includes(d))) return null;
  return wrap(BigInt(PREFIX[base] + digits), bits);
}

/** Does the typed text fit in the word? HEX/OCT/BIN up to all bits set; DEC in the signed range. */
function fits(text, base, bits) {
  const max = 1n << BigInt(bits);
  if (base !== 10) return BigInt(PREFIX[base] + text) < max;
  const v = BigInt(text);
  const half = max >> 1n;
  return v >= -half && v < half;
}

export function digitAllowed(d, base) {
  const i = DIGITS.indexOf(d);
  return i >= 0 && i < base;
}

function shiftAmount(b, bits) {
  if (b < 0n) fail("invalid");
  return b >= BigInt(bits) ? null : b;
}

/** The programmer domain for a base and a word size (see core.js). */
export function programmerDomain(base, bits) {
  const w = (v) => wrap(v, bits);
  return {
    kind: "programmer",
    base,
    bits,
    zero: 0n,
    immediate: false,
    appendDigit(entry, d) {
      if (!digitAllowed(d, base)) return null;
      let next;
      if (entry === "0") next = d;
      else if (entry === "-0") next = `-${d}`;
      else next = entry + d;
      return fits(next, base, bits) ? next : null;
    },
    appendPoint: null,
    appendExp: null,
    // In DEC +/- changes the sign of the number being typed; elsewhere it negates the value.
    negateEntry:
      base === 10
        ? (entry) => {
            if (entry === "0") return entry;
            const next = entry.startsWith("-") ? entry.slice(1) : `-${entry}`;
            return fits(next, base, bits) ? next : null;
          }
        : null,
    backspace(entry) {
      const next = entry.slice(0, -1);
      return next === "" || next === "-" ? "0" : next;
    },
    parse(entry) {
      const v = fromBase(entry, base, bits);
      if (v === null) fail("invalid");
      return w(v);
    },
    isNeg: (v) => v < 0n,
    // Precedence as in the Windows calculator: OR XOR < AND NAND NOR < + − < × ÷ mod shifts.
    binary: {
      or: { sym: "OR", prec: 1, fn: (a, b) => w(a | b) },
      xor: { sym: "XOR", prec: 1, fn: (a, b) => w(a ^ b) },
      and: { sym: "AND", prec: 2, fn: (a, b) => w(a & b) },
      nand: { sym: "NAND", prec: 2, fn: (a, b) => w(~(a & b)) },
      nor: { sym: "NOR", prec: 2, fn: (a, b) => w(~(a | b)) },
      add: { sym: "+", prec: 3, fn: (a, b) => w(a + b) },
      sub: { sym: "−", prec: 3, fn: (a, b) => w(a - b) },
      mul: { sym: "×", prec: 4, fn: (a, b) => w(a * b) },
      div: {
        sym: "÷",
        prec: 4,
        fn: (a, b) => {
          if (b === 0n) fail(a === 0n ? "undefined" : "divzero");
          return w(a / b); // rounds towards zero, like C and Java
        },
      },
      mod: {
        sym: "mod",
        prec: 4,
        fn: (a, b) => {
          if (b === 0n) fail("divzero");
          return w(a % b); // the sign of the first number: −7 mod 3 = −1
        },
      },
      lsh: {
        sym: "Lsh",
        prec: 4,
        fn: (a, b) => {
          const n = shiftAmount(b, bits);
          return n === null ? 0n : w(a << n);
        },
      },
      rsh: {
        sym: "Rsh",
        prec: 4,
        fn: (a, b) => {
          // Arithmetic shift: the sign bit is copied (−8 Rsh 1 = −4).
          const n = shiftAmount(b, bits);
          if (n === null) return a < 0n ? -1n : 0n;
          return w(a >> n);
        },
      },
    },
    unary: {
      negate: { show: around("−(", ")"), fn: (x) => w(-x) },
      not: { show: call("NOT"), fn: (x) => w(~x) },
    },
    percent: null,
  };
}
