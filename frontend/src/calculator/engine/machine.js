// The whole calculator: the current mode, one calculation per mode, settings,
// history and memory. Every action goes through reduce(); the UI only renders.
//
// Standard and Scientific share their history and memory (decimal numbers), as in
// Windows; Programmer keeps its own (whole numbers).
import * as core from "./core.js";
import { decimalFromText, fin } from "./decimal.js";
import { formatDecimal, formatEntry, formatProg, groupProgDigits, parseDecimalText } from "./format.js";
import { BASES, WORDS, fromBase, programmerDomain, toBase, wrap } from "./programmer.js";
import { ANGLES, CONSTANTS, scientificDomain } from "./scientific.js";
import { standardDomain } from "./standard.js";

export const MODES = ["standard", "scientific", "programmer"];
export const MEMORY_KEYS = ["mc", "mr", "mplus", "mminus", "ms"];
const MAX_HISTORY = 50;
const MAX_MEMORY = 50;
const MAX_TYPED_DIGITS = 16;

const programmerDomains = new Map();

export function domainFor(state, mode = state.mode) {
  if (mode === "standard") return standardDomain;
  if (mode === "scientific") return scientificDomain;
  const key = `${state.base}:${state.bits}`;
  if (!programmerDomains.has(key)) programmerDomains.set(key, programmerDomain(state.base, state.bits));
  return programmerDomains.get(key);
}

/** "decimal" for Standard and Scientific, "programmer" for Programmer. */
export function kindOf(mode) {
  return mode === "programmer" ? "programmer" : "decimal";
}

export function initMachine(saved = {}) {
  const settings = saved.settings || {};
  const state = {
    mode: MODES.includes(settings.mode) ? settings.mode : "standard",
    angle: ANGLES.includes(settings.angle) ? settings.angle : "deg",
    base: BASES.includes(settings.base) ? settings.base : 10,
    bits: WORDS.includes(settings.bits) ? settings.bits : 64,
    fe: false,
    second: false,
    hyp: false,
    history: { decimal: saved.history?.decimal || [], programmer: saved.history?.programmer || [] },
    memory: { decimal: saved.memory?.decimal || [], programmer: saved.memory?.programmer || [] },
  };
  state.calcs = {
    standard: core.initState(standardDomain),
    scientific: core.initState(scientificDomain),
    programmer: core.initState(domainFor(state, "programmer")),
  };
  return state;
}

const calcOf = (state) => state.calcs[state.mode];

function withCalc(state, calc) {
  return calc === calcOf(state) ? state : { ...state, calcs: { ...state.calcs, [state.mode]: calc } };
}

function setList(state, field, list) {
  const kind = kindOf(state.mode);
  return { ...state, [field]: { ...state[field], [kind]: list } };
}

// ---- Keys ------------------------------------------------------------------

/** Keys that still work while an error is shown: they start again (as in Windows). */
const ERROR_KEYS = new Set(["c", "ce", "back", "second", "hyp", "angle", "fe"]);

/** Is a key usable right now? (Disabled keys are greyed out, as in Windows.) */
export function isEnabled(state, key) {
  const calc = calcOf(state);
  const domain = domainFor(state);
  const isDigit = /^[0-9A-F]$/.test(key);
  if (state.mode === "programmer" && isDigit) return domain.appendDigit("0", key) !== null;
  if (calc.error) return isDigit || ERROR_KEYS.has(key);
  if (key === "point") return Boolean(domain.appendPoint);
  if (key === "mc" || key === "mr") return state.memory[kindOf(state.mode)].length > 0;
  return true;
}

function pressMemory(state, key) {
  const calc = calcOf(state);
  const domain = domainFor(state);
  const list = state.memory[kindOf(state.mode)];
  if (key === "mc") return setList(state, "memory", []);
  if (key === "mr") return list.length ? withCalc(state, core.setValue(calc, list[0], domain)) : state;
  const v = core.currentValue(calc, domain);
  if (v === null) return state;
  const frozen = withCalc(state, core.freeze(calc, domain));
  if (key === "ms") return setList(frozen, "memory", [v, ...list].slice(0, MAX_MEMORY));
  if (!list.length) return setList(frozen, "memory", [key === "mplus" ? v : negateValue(state, v)]);
  return memoryItem(frozen, key === "mplus" ? "add" : "sub", 0, v);
}

function negateValue(state, v) {
  return kindOf(state.mode) === "programmer" ? wrap(-v, state.bits) : fin(v.neg());
}

function combine(state, a, b, op) {
  if (kindOf(state.mode) === "programmer") return wrap(op === "add" ? a + b : a - b, state.bits);
  try {
    return fin(op === "add" ? a.plus(b) : a.minus(b));
  } catch {
    return null; // overflow: leave the memory as it was
  }
}

/** One memory item: "recall", "clear", "add" or "sub" (the display value, or `value`). */
export function memoryItem(state, op, index, value) {
  const calc = calcOf(state);
  const domain = domainFor(state);
  const list = state.memory[kindOf(state.mode)];
  if (index < 0 || index >= list.length) return state;
  if (op === "recall") return withCalc(state, core.setValue(calc, list[index], domain));
  if (op === "clear") return setList(state, "memory", list.filter((_, i) => i !== index));
  const v = value ?? core.currentValue(calc, domain);
  if (v === null) return state;
  const next = combine(state, list[index], v, op);
  if (next === null) return state;
  const s = withCalc(state, core.freeze(calc, domain));
  return setList(s, "memory", list.map((item, i) => (i === index ? next : item)));
}

function addHistory(state, record) {
  const list = state.history[kindOf(state.mode)];
  return setList(state, "history", [{ parts: record.parts, value: record.value }, ...list].slice(0, MAX_HISTORY));
}

export function press(state, key) {
  const calc = calcOf(state);
  const domain = domainFor(state);
  const ctx = { angle: state.angle };
  if (!isEnabled(state, key)) return state;
  if (MEMORY_KEYS.includes(key)) return pressMemory(state, key);
  let next = calc;
  if (/^[0-9A-F]$/.test(key)) next = core.digit(calc, key, domain);
  else {
    switch (key) {
      case "point":
        next = core.point(calc, domain);
        break;
      case "neg":
        next = core.negate(calc, domain, ctx);
        break;
      case "equals":
        next = core.equals(calc, domain);
        break;
      case "percent":
        next = core.percent(calc, domain);
        break;
      case "ce":
        next = core.clearEntry(calc, domain);
        break;
      case "c":
        next = core.clear(calc, domain);
        break;
      case "back":
        next = core.backspace(calc, domain);
        break;
      case "open":
        if (!domain.immediate) next = core.openParen(calc, domain);
        break;
      case "close":
        if (!domain.immediate) next = core.closeParen(calc, domain);
        break;
      case "exp":
        next = core.expEntry(calc, domain);
        break;
      case "pi":
      case "e":
        if (state.mode === "scientific") next = core.setValue(calc, CONSTANTS[key], domain);
        break;
      case "fe":
        return { ...state, fe: !state.fe };
      case "second":
        return { ...state, second: !state.second };
      case "hyp":
        return { ...state, hyp: !state.hyp };
      case "angle":
        return { ...state, angle: ANGLES[(ANGLES.indexOf(state.angle) + 1) % ANGLES.length] };
      default:
        if (domain.binary[key]) next = core.binary(calc, key, domain);
        else if (domain.unary[key]) next = core.unary(calc, key, domain, ctx);
    }
  }
  let s = withCalc(state, next);
  if (next.record && next.record !== calc.record) s = addHistory(s, next.record);
  return s;
}

// ---- Settings ----------------------------------------------------------------

export function setMode(state, mode) {
  return MODES.includes(mode) ? { ...state, mode } : state;
}

/** Programmer: choose the input base. A number being typed is converted and can be continued. */
export function setBase(state, base) {
  if (!BASES.includes(base) || base === state.base) return state;
  const calc = state.calcs.programmer;
  const next = { ...state, base };
  if (calc.entry === null || calc.error) return next;
  const v = domainFor(state, "programmer").parse(calc.entry);
  return { ...next, calcs: { ...state.calcs, programmer: { ...calc, entry: toBase(v, base, state.bits) } } };
}

/** Programmer: change the word size. Values are cut to the new size (two's complement). */
export function setBits(state, bits) {
  if (!WORDS.includes(bits) || bits === state.bits) return state;
  const cut = (v) => wrap(v, bits);
  let calc = state.calcs.programmer;
  if (calc.entry !== null && !calc.error) {
    const v = cut(domainFor(state, "programmer").parse(calc.entry));
    calc = { ...calc, entry: toBase(v, state.base, bits) };
  }
  calc = core.mapValues(calc, cut);
  return {
    ...state,
    bits,
    calcs: { ...state.calcs, programmer: calc },
    memory: { ...state.memory, programmer: state.memory.programmer.map(cut) },
  };
}

/** The next word size, for the QWORD/DWORD/WORD/BYTE button. */
export function nextBits(bits) {
  return WORDS[(WORDS.indexOf(bits) + 1) % WORDS.length];
}

// ---- History -----------------------------------------------------------------

export function recallHistory(state, index) {
  const item = state.history[kindOf(state.mode)][index];
  if (!item) return state;
  const calc = calcOf(state);
  let value = item.value;
  if (state.mode === "programmer") value = wrap(value, state.bits);
  return withCalc(state, core.restore(calc, value, item.parts, domainFor(state)));
}

export function clearHistory(state) {
  return setList(state, "history", []);
}

// ---- Paste -------------------------------------------------------------------

function significantDigits(entry) {
  return entry
    .split("e")[0]
    .replace(/[-.]/g, "")
    .replace(/^0+/, "").length;
}

/** Ctrl+V: a pasted number becomes the number being typed. Anything else is ignored. */
export function paste(state, text, lang = "en") {
  const calc = calcOf(state);
  const domain = domainFor(state);
  if (state.mode === "programmer") {
    let raw = String(text).trim().replace(/[\s_]/g, "").replace(/^−/, "-");
    let base = state.base;
    const prefix = /^0([xob])/i.exec(raw);
    if (prefix) {
      base = { x: 16, o: 8, b: 2 }[prefix[1].toLowerCase()];
      raw = raw.slice(2);
    } else {
      // Grouping commas in decimal numbers (spaces were removed above).
      raw = raw.replace(/,/g, "");
    }
    const v = fromBase(raw, base, state.bits);
    if (v === null) return state;
    // Shown in the current base (the bit pattern, cut to the word size), ready to edit.
    return withCalc(state, core.setEntry(calc, toBase(wrap(v, state.bits), state.base, state.bits), domain));
  }
  const entry = parseDecimalText(text, lang);
  if (entry === null) return state;
  let v;
  try {
    v = domain.parse(entry);
  } catch {
    return state;
  }
  const typeable = significantDigits(entry) <= MAX_TYPED_DIGITS && (!entry.includes("e") || domain.appendExp);
  return withCalc(state, typeable ? core.setEntry(calc, entry, domain) : core.setValue(calc, v, domain));
}

// ---- What the UI shows -------------------------------------------------------

/** Format a value of the current mode (results, history, memory). */
export function formatValue(state, v, lang = "en") {
  if (state.mode === "programmer") return formatProg(v, state.base, state.bits, { lang });
  return formatDecimal(v, { lang, fe: state.fe });
}

export function expressionText(state, lang = "en", parts = null) {
  const calc = calcOf(state);
  return core.renderParts(parts ?? core.exprParts(calc, domainFor(state)), (v) => formatValue(state, v, lang));
}

/** The big number (or null while an error is shown: see errorOf). */
export function displayText(state, lang = "en") {
  const calc = calcOf(state);
  if (calc.error) return null;
  if (calc.entry !== null) {
    if (state.mode === "programmer") return groupProgDigits(calc.entry, state.base, lang);
    return formatEntry(calc.entry, lang);
  }
  return formatValue(state, calc.value, lang);
}

export function errorOf(state) {
  return calcOf(state).error;
}

/** Programmer: the current value in every base, for the HEX/DEC/OCT/BIN list. */
export function baseValues(state, lang = "en") {
  const v = core.currentValue(state.calcs.programmer, domainFor(state, "programmer")) ?? 0n;
  return BASES.map((base) => ({ base, text: formatProg(v, base, state.bits, { lang }) }));
}

/** Ctrl+C: the number on the display without digit grouping. */
export function copyText(state, lang = "en") {
  const calc = calcOf(state);
  const v = core.currentValue(calc, domainFor(state));
  if (v === null) return "";
  if (state.mode === "programmer") return toBase(v, state.base, state.bits);
  if (calc.entry !== null) return formatEntry(calc.entry, lang, false);
  return formatDecimal(v, { lang, fe: state.fe, grouping: false });
}

export function openParens(state) {
  return core.openParens(calcOf(state));
}

// ---- Saving --------------------------------------------------------------------

const valueToText = (v) => v.toString();

function valueFromText(text, kind) {
  if (typeof text !== "string") return null;
  if (kind === "programmer") {
    if (!/^-?\d{1,20}$/.test(text)) return null;
    return wrap(BigInt(text), 64);
  }
  return decimalFromText(text);
}

function partsToJSON(parts) {
  return parts.map((p) => (typeof p === "string" ? p : { v: valueToText(p.v) }));
}

function partsFromJSON(parts, kind) {
  if (!Array.isArray(parts)) return null;
  const out = [];
  for (const p of parts) {
    if (typeof p === "string") out.push(p);
    else {
      const v = valueFromText(p?.v, kind);
      if (v === null) return null;
      out.push({ v });
    }
  }
  return out;
}

export function savedSettings(state) {
  return { mode: state.mode, angle: state.angle, base: state.base, bits: state.bits };
}

const savedLists = (lists, map) => ({ decimal: lists.decimal.map(map), programmer: lists.programmer.map(map) });

export function savedHistory(state) {
  return savedLists(state.history, (h) => ({ parts: partsToJSON(h.parts), value: valueToText(h.value) }));
}

export function savedMemory(state) {
  return savedLists(state.memory, valueToText);
}

/** Plain JSON for localStorage. */
export function toSaved(state) {
  return { settings: savedSettings(state), history: savedHistory(state), memory: savedMemory(state) };
}

/** Read what toSaved() wrote, dropping anything that does not look right. */
export function fromSaved(data) {
  const out = { settings: {}, history: {}, memory: {} };
  if (!data || typeof data !== "object") return out;
  if (data.settings && typeof data.settings === "object") out.settings = data.settings;
  for (const kind of ["decimal", "programmer"]) {
    const history = Array.isArray(data.history?.[kind]) ? data.history[kind] : [];
    out.history[kind] = history
      .map((h) => ({ parts: partsFromJSON(h?.parts, kind), value: valueFromText(h?.value, kind) }))
      .filter((h) => h.parts && h.value !== null)
      .slice(0, MAX_HISTORY);
    const memory = Array.isArray(data.memory?.[kind]) ? data.memory[kind] : [];
    out.memory[kind] = memory
      .map((m) => valueFromText(m, kind))
      .filter((m) => m !== null)
      .slice(0, MAX_MEMORY);
  }
  return out;
}
