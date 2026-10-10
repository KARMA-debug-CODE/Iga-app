// Number formatting for the display, the expression line and the history.
// The rules follow the Windows calculator: up to 16 significant digits, trailing
// zeros trimmed, digit grouping, and exponent form ("1.e+16", "1.428571428571429e-4")
// when a number is too large or has too many leading zeros to show in full.
import { toBase } from "./programmer.js";

export const SEPARATORS = {
  en: { group: ",", decimal: "." },
  // French: a narrow no-break space between groups of digits and a decimal comma.
  fr: { group: " ", decimal: "," },
};

export const DISPLAY_DIGITS = 16;
const MAX_LEADING_ZEROS = 2;

export function separators(lang) {
  return SEPARATORS[lang] || SEPARATORS.en;
}

/** "1234567" -> "1,234,567" (groups counted from the right). */
export function groupDigits(digits, sep, size = 3) {
  let out = "";
  for (let end = digits.length; end > 0; end -= size) {
    const chunk = digits.slice(Math.max(0, end - size), end);
    out = out ? chunk + sep + out : chunk;
  }
  return out;
}

function split(x) {
  // x is a positive Decimal. Returns its significant digits and exponent (x = d.ddd * 10^e).
  const [mant, exp] = x.toExponential().split("e");
  return { ds: mant.replace(".", ""), e: Number(exp) };
}

/**
 * Format a Decimal for display.
 * @param {object} opts lang ("en" | "fr"), fe (force exponent form), grouping, digits
 */
export function formatDecimal(x, { lang = "en", fe = false, grouping = true, digits = DISPLAY_DIGITS } = {}) {
  const { group, decimal } = separators(lang);
  if (x.isZero()) return fe ? `0${decimal}e+0` : "0";
  const sign = x.isNeg() ? "-" : "";
  let r = x.abs().toSignificantDigits(digits);
  let { ds, e } = split(r);
  let ew = e + 1; // number of digits before the decimal point
  let sci = fe || ew > digits;
  if (!sci && ds.length - ew > digits) {
    if (ew >= -MAX_LEADING_ZEROS) {
      // Small number with a long fraction: keep `digits` places after the point.
      r = r.toSignificantDigits(digits + ew);
      ({ ds, e } = split(r));
      ew = e + 1;
    } else {
      sci = true;
    }
  }
  if (sci) {
    return `${sign}${ds[0]}${decimal}${ds.slice(1)}e${e < 0 ? "-" : "+"}${Math.abs(e)}`;
  }
  let int;
  let frac;
  if (ew <= 0) {
    int = "0";
    frac = "0".repeat(-ew) + ds;
  } else if (ds.length <= ew) {
    int = ds + "0".repeat(ew - ds.length);
    frac = "";
  } else {
    int = ds.slice(0, ew);
    frac = ds.slice(ew);
  }
  return sign + (grouping ? groupDigits(int, group) : int) + (frac ? decimal + frac : "");
}

/** Format a number while it is being typed ("1234.50" -> "1,234.50", "2e+" -> "2.e+0"). */
export function formatEntry(entry, lang = "en", grouping = true) {
  const { group, decimal } = separators(lang);
  let s = entry;
  let sign = "";
  if (s.startsWith("-")) {
    sign = "-";
    s = s.slice(1);
  }
  const [mant, exp] = s.split("e");
  const hasPoint = mant.includes(".");
  const [int, frac = ""] = mant.split(".");
  let out = (grouping ? groupDigits(int || "0", group) : int || "0") + (hasPoint ? decimal + frac : "");
  if (exp !== undefined) out += `${hasPoint ? "" : decimal}e${exp[0] || "+"}${exp.slice(1) || "0"}`;
  return sign + out;
}

/** Text for copying to the clipboard: no grouping, the reader's decimal separator. */
export function plainDecimal(x, lang = "en") {
  return formatDecimal(x, { lang, grouping: false });
}

/**
 * Read a pasted number ("1,234.5", "1 234,5", "-2.5e3") into the form used while typing
 * ("1234.5"). A comma is the decimal separator in French, a group separator in English
 * when it is followed by groups of three digits. Returns null for anything else.
 */
export function parseDecimalText(text, lang = "en") {
  let s = String(text)
    .trim()
    .replace(/[\s']/g, "") // \s includes the no-break spaces
    .replace(/[−–]/g, "-")
    .replace(/^\+/, "");
  if (!s) return null;
  const lastComma = s.lastIndexOf(",");
  const lastPoint = s.lastIndexOf(".");
  if (lastComma >= 0 && lastPoint >= 0) {
    // Both: the last one is the decimal separator.
    s = lastComma > lastPoint ? s.replace(/\./g, "").replace(",", ".") : s.replace(/,/g, "");
  } else if (lastComma >= 0) {
    const grouped = /^-?\d{1,3}(,\d{3})+$/.test(s);
    s = lang !== "fr" && grouped ? s.replace(/,/g, "") : s.replace(",", ".");
  }
  const m = /^(-?)(\d*)(?:\.(\d*))?(?:e([+-]?)(\d{1,4}))?$/i.exec(s);
  if (!m || (!m[2] && !m[3])) return null;
  const [, sign, intDigits, fracDigits, expSign, expDigits] = m;
  const int = intDigits.replace(/^0+(?=\d)/, "") || "0";
  let entry = sign + int + (fracDigits !== undefined ? `.${fracDigits}` : "");
  if (expDigits !== undefined) entry += `e${expSign || "+"}${expDigits.replace(/^0+(?=\d)/, "")}`;
  return entry;
}

// ---- Programmer mode -------------------------------------------------------

export function groupProgDigits(text, base, lang = "en") {
  let sign = "";
  let digits = text;
  if (digits.startsWith("-")) {
    sign = "-";
    digits = digits.slice(1);
  }
  if (base === 10) return sign + groupDigits(digits, separators(lang).group, 3);
  return sign + groupDigits(digits, " ", base === 8 ? 3 : 4);
}

export function formatProg(v, base, bits, { grouping = true, lang = "en" } = {}) {
  const digits = toBase(v, base, bits);
  return grouping ? groupProgDigits(digits, base, lang) : digits;
}
