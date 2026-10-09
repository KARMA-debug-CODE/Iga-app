// The calculator state machine shared by Standard, Scientific and Programmer modes.
//
// A "domain" describes the numbers of a mode (Decimal or BigInt), how numbers are
// typed, and the operators and functions. Standard mode sets `immediate: true`,
// so every operator has the same precedence and is worked out as soon as the next
// one is pressed (2 + 3 x 4 = 20, as in Windows Standard). The other modes use
// operator precedence and parentheses (2 + 3 x 4 = 14).
//
// State (never mutated; every action returns a new object):
//   items      committed tokens: {k:"num", v, parts}, {k:"op", op}, {k:"("}, {k:")"}
//   entry      the number being typed (string) or null
//   value      the value shown when nothing is being typed (partial result, result, recall)
//   error      null or an error code ("divzero", "undefined", "invalid", "overflow")
//   last       {op, operand} of the last calculation, used when "=" is pressed again
//   done       true right after "="; doneParts is the expression shown above the result
//   record     {parts, value} set only by the "=" that produced a new history entry
//
// Expression "parts" are strings and {v} values; the UI formats the values, so the
// expression follows the language, the number base and the F-E setting.
import { CalcError } from "./decimal.js";

export function initState(domain) {
  return { items: [], entry: null, value: domain.zero, error: null, last: null, done: false, doneParts: null, record: null };
}

const num = (v, parts) => ({ k: "num", v, parts: parts ?? [{ v }] });
const lastOf = (list) => list[list.length - 1];
const isOperand = (it) => Boolean(it) && (it.k === "num" || it.k === ")");

/** Expression of a function: "sin(30)". */
export const call = (name, after = "") => (inner) => [`${name}(`, ...inner, `${after})`];

/** Expression of a postfix operator: "5²", "(−3)²", "(2 + 3)!". */
export const postfix = (sym) => (inner, domain) => {
  const plain = inner.length === 1 && typeof inner[0] === "object" && !domain.isNeg(inner[0].v);
  return plain ? [...inner, sym] : ["(", ...inner, `)${sym}`];
};

/** Expression of an operator written around its operand: "|−3|". */
export const around = (open, close) => (inner) => [open, ...inner, close];

function openCount(items) {
  let n = 0;
  for (const it of items) {
    if (it.k === "(") n += 1;
    else if (it.k === ")") n -= 1;
  }
  return n;
}

/** Index where the trailing operand starts (a number, or the "(" matching a trailing ")"). */
function operandStart(items) {
  const last = lastOf(items);
  if (!last) return -1;
  if (last.k === "num") return items.length - 1;
  if (last.k !== ")") return -1;
  let depth = 0;
  for (let i = items.length - 1; i >= 0; i -= 1) {
    if (items[i].k === ")") depth += 1;
    else if (items[i].k === "(") {
      depth -= 1;
      if (depth === 0) return i;
    }
  }
  return -1;
}

function dropOperand(items) {
  const i = operandStart(items);
  return i >= 0 ? items.slice(0, i) : items;
}

/** Operator tokens outside any parentheses. */
function topLevelOps(items) {
  let depth = 0;
  const found = [];
  items.forEach((it, i) => {
    if (it.k === "(") depth += 1;
    else if (it.k === ")") depth -= 1;
    else if (it.k === "op" && depth === 0) found.push(i);
  });
  return found;
}

/** Evaluate tokens. With final=false, stop before the last pending operators (partial result). */
export function evaluate(items, domain, final = true) {
  const vals = [];
  const ops = [];
  const prec = (op) => (domain.immediate ? 1 : domain.binary[op].prec);
  const apply = () => {
    const op = ops.pop();
    const b = vals.pop();
    const a = vals.pop();
    vals.push(domain.binary[op].fn(a, b));
  };
  for (const it of items) {
    if (it.k === "num") vals.push(it.v);
    else if (it.k === "(") ops.push("(");
    else if (it.k === ")") {
      while (ops.length && lastOf(ops) !== "(") apply();
      ops.pop();
    } else {
      const p = prec(it.op);
      const right = !domain.immediate && domain.binary[it.op].right;
      while (ops.length && lastOf(ops) !== "(" && (prec(lastOf(ops)) > p || (prec(lastOf(ops)) === p && !right))) apply();
      ops.push(it.op);
    }
  }
  if (final) {
    while (ops.length) {
      if (lastOf(ops) === "(") ops.pop();
      else apply();
    }
  }
  return vals.length ? lastOf(vals) : domain.zero;
}

/** Expression text pieces: strings, and {v} values that the UI formats. */
export function partsOf(items, domain) {
  const out = [];
  for (const it of items) {
    if (it.k === "num") out.push(...it.parts);
    else if (it.k === "op") out.push(` ${domain.binary[it.op].sym} `);
    else out.push(it.k);
  }
  return out;
}

/** The expression line: what has been typed so far, or the finished calculation after "=". */
export function exprParts(state, domain) {
  return state.done ? state.doneParts || [] : partsOf(state.items, domain);
}

export function renderParts(parts, fmt) {
  return parts
    .map((p) => (typeof p === "string" ? p : fmt(p.v)))
    .join("")
    .trim();
}

function failWith(state, e) {
  if (!(e instanceof CalcError)) throw e;
  return { ...state, error: e.code, entry: null, record: null };
}

function begin(state) {
  return state.record ? { ...state, record: null } : state;
}

function freshAfterDone(s) {
  return s.done ? { ...s, items: [], done: false, doneParts: null } : s;
}

function partial(s, domain) {
  try {
    return { ...s, value: evaluate(s.items, domain, false) };
  } catch (e) {
    return failWith(s, e);
  }
}

/** Value currently on the display (null while an error is shown). */
export function currentValue(state, domain) {
  if (state.error) return null;
  try {
    return state.entry !== null ? domain.parse(state.entry) : state.value;
  } catch {
    return null;
  }
}

/** Commit the number being typed, so the next digit starts a new number (after MS, M+...). */
export function freeze(state, domain) {
  if (state.entry === null || state.error) return state;
  try {
    return { ...state, entry: null, value: domain.parse(state.entry) };
  } catch (e) {
    return failWith(state, e);
  }
}

function startEntry(state, domain, make) {
  let s = begin(state);
  if (s.error) s = initState(domain);
  s = freshAfterDone(s);
  if (s.entry === null) {
    const entry = make("0");
    if (entry === null) return s;
    return { ...s, items: dropOperand(s.items), entry };
  }
  const entry = make(s.entry);
  return entry === null ? s : { ...s, entry };
}

/** Digits start a new number, even after an error (as in Windows). */
export function digit(state, d, domain) {
  return startEntry(state, domain, (entry) => domain.appendDigit(entry, d));
}

export function point(state, domain) {
  if (!domain.appendPoint || state.error) return state;
  return startEntry(state, domain, (entry) => domain.appendPoint(entry));
}

/** "exp": start typing the exponent of a number in scientific notation (2 exp 3 = 2000). */
export function expEntry(state, domain) {
  if (!domain.appendExp || state.error) return state;
  return startEntry(state, domain, (entry) => domain.appendExp(entry));
}

/** Replace the number being typed (paste). */
export function setEntry(state, entry, domain) {
  try {
    domain.parse(entry);
  } catch {
    return state;
  }
  return startEntry(state, domain, () => entry);
}

/**
 * Standard mode works out each operator at once, so 2 + 3 x 4 is (2 + 3) x 4.
 * Like Windows, the expression line then shows the brackets: "(2 + 3) x".
 */
function bracketInversion(items, op, domain) {
  const p = domain.binary[op].prec;
  const ops = topLevelOps(items);
  if (!ops.some((i) => domain.binary[items[i].op].prec < p)) return items;
  return [num(evaluate(items, domain, true), ["(", ...partsOf(items, domain), ")"])];
}

export function binary(state, op, domain) {
  let s = begin(state);
  if (s.error || !domain.binary[op]) return s;
  if (s.done) s = { ...s, items: [num(s.value)], done: false, doneParts: null };
  let items = s.items;
  try {
    if (s.entry !== null) items = [...items, num(domain.parse(s.entry))];
    else if (lastOf(items)?.k === "op") items = items.slice(0, -1); // change the operator
    else if (!isOperand(lastOf(items))) items = [...items, num(s.value)];
    if (domain.immediate) items = bracketInversion(items, op, domain);
  } catch (e) {
    return failWith({ ...s, items }, e);
  }
  return partial({ ...s, items: [...items, { k: "op", op }], entry: null }, domain);
}

/** A function of the number on the display: square root, sin, n!, ... */
export function unary(state, name, domain, ctx = {}) {
  let s = begin(state);
  if (s.error) return s;
  const def = domain.unary[name];
  if (!def) return s;
  let items = s.done ? [num(s.value)] : s.items;
  s = { ...s, done: false, doneParts: null };
  let shown = null;
  try {
    if (s.entry !== null) items = [...items, num(domain.parse(s.entry))];
    else if (!isOperand(lastOf(items))) items = [...items, num(s.value)];
    else if (lastOf(items).k === ")") {
      const i = operandStart(items);
      const group = items.slice(i + 1, -1);
      const v = evaluate(group, domain, true);
      items = [...items.slice(0, i), { k: "num", v, parts: ["(", ...partsOf(group, domain), ")"], group: true }];
    }
    const target = lastOf(items);
    const inner = target.group ? target.parts.slice(1, -1) : target.parts;
    shown = (def.show || call(def.label))(inner, domain, ctx);
    const v = def.fn(target.v, ctx);
    items = [...items.slice(0, -1), { k: "num", v, parts: shown }];
    return { ...s, items, entry: null, value: v };
  } catch (e) {
    // Show what failed ("√(−4)") next to the message.
    if (shown) items = [...items.slice(0, -1), { k: "num", v: lastOf(items).v, parts: shown }];
    return failWith({ ...s, items, entry: null }, e);
  }
}

/** The +/- key: changes the sign of the number being typed, otherwise applies −(x). */
export function negate(state, domain, ctx) {
  if (state.error) return state;
  if (state.entry !== null && domain.negateEntry) {
    const entry = domain.negateEntry(state.entry);
    if (entry !== null) return { ...begin(state), entry };
  }
  return unary(state, "negate", domain, ctx);
}

/** Show a value (memory recall, pi, e) as the current operand. */
export function setValue(state, v, domain) {
  let s = begin(state);
  if (s.error) s = initState(domain);
  s = freshAfterDone(s);
  const items = isOperand(lastOf(s.items)) ? dropOperand(s.items) : s.items;
  return { ...s, items, entry: null, value: v };
}

/** Restore a history entry: its expression above, its result on the display. */
export function restore(state, v, parts, domain) {
  return { ...initState(domain), value: v, done: true, doneParts: parts, last: state.error ? null : state.last };
}

export function openParen(state, domain) {
  let s = begin(state);
  if (s.error) return s;
  s = freshAfterDone(s);
  let items = s.items;
  try {
    // 2( means 2 x (
    if (s.entry !== null && s.entry !== "0") items = [...items, num(domain.parse(s.entry)), { k: "op", op: "mul" }];
    else if (isOperand(lastOf(items))) items = [...items, { k: "op", op: "mul" }];
  } catch (e) {
    return failWith(s, e);
  }
  return { ...s, items: [...items, { k: "(" }], entry: null, value: domain.zero };
}

export function closeParen(state, domain) {
  const s = begin(state);
  if (s.error || s.done || openCount(s.items) <= 0) return s;
  let items = s.items;
  try {
    if (s.entry !== null) items = [...items, num(domain.parse(s.entry))];
    else if (!isOperand(lastOf(items))) items = [...items, num(s.value)];
  } catch (e) {
    return failWith(s, e);
  }
  items = [...items, { k: ")" }];
  try {
    // The display shows the value of the bracket that was just closed.
    const i = operandStart(items);
    return { ...s, items, entry: null, value: evaluate(items.slice(i + 1, -1), domain, true) };
  } catch (e) {
    return failWith({ ...s, items }, e);
  }
}

/** How many brackets are still open (shown next to the "(" key). */
export function openParens(state) {
  return state.done ? 0 : openCount(state.items);
}

export function equals(state, domain) {
  const s = begin(state);
  if (s.error) return s;
  let items = s.done ? [] : s.items;
  try {
    if (s.entry !== null) items = [...items, num(domain.parse(s.entry))];
    else if (!isOperand(lastOf(items))) items = [...items, num(s.value)];
  } catch (e) {
    return failWith(s, e);
  }
  for (let n = openCount(items); n > 0; n -= 1) items = [...items, { k: ")" }];
  let hasOp = items.some((it) => it.k === "op");
  // "=" again (or a new number then "="): repeat the last operation, as Windows does.
  if (!hasOp && s.last) {
    items = [...items, { k: "op", op: s.last.op }, num(s.last.operand)];
    hasOp = true;
  }
  const parts = [...partsOf(items, domain), " ="];
  try {
    let last = s.last;
    const ops = topLevelOps(items);
    if (ops.length) {
      const top = lastOf(ops);
      last = { op: items[top].op, operand: evaluate(items.slice(top + 1), domain, true) };
    }
    const v = evaluate(items, domain, true);
    return {
      ...s,
      items: [],
      entry: null,
      value: v,
      done: true,
      doneParts: parts,
      last,
      record: hasOp ? { parts, value: v } : null,
    };
  } catch (e) {
    return failWith({ ...s, items: [], done: true, doneParts: parts }, e);
  }
}

export function backspace(state, domain) {
  const s = begin(state);
  if (s.error) return initState(domain);
  if (s.done) return { ...s, doneParts: null }; // clears the expression line, keeps the result
  if (s.entry === null) return s;
  return { ...s, entry: domain.backspace(s.entry) };
}

export function clearEntry(state, domain) {
  const s = begin(state);
  if (s.error || s.done) return initState(domain);
  const items = isOperand(lastOf(s.items)) ? dropOperand(s.items) : s.items;
  return { ...s, items, entry: "0" };
}

export function clear(_state, domain) {
  return initState(domain);
}

/**
 * Windows Standard percent: with + or − it is a percentage of the first number
 * (200 + 10 % -> 200 + 20); with x or ÷ it is the number divided by 100; alone it gives 0.
 */
export function percent(state, domain) {
  let s = begin(state);
  if (s.error || !domain.percent) return s;
  let items = s.done ? [] : s.items;
  s = { ...s, done: false, doneParts: null };
  try {
    let cur;
    if (s.entry !== null) cur = domain.parse(s.entry);
    else if (isOperand(lastOf(items))) {
      cur = lastOf(items).v;
      items = dropOperand(items);
    } else cur = s.value;
    const last = lastOf(items);
    let v;
    if (last?.k === "op") v = domain.percent(evaluate(items.slice(0, -1), domain, true), cur, last.op);
    else {
      v = domain.zero;
      items = [];
    }
    return { ...s, items: [...items, num(v)], entry: null, value: v };
  } catch (e) {
    return failWith({ ...s, items }, e);
  }
}

/** Apply fn to every stored value (used when the programmer word size changes). */
export function mapValues(state, fn) {
  const mapParts = (parts) => parts?.map((p) => (typeof p === "string" ? p : { v: fn(p.v) }));
  return {
    ...state,
    value: fn(state.value),
    items: state.items.map((it) => (it.k === "num" ? { ...it, v: fn(it.v), parts: mapParts(it.parts) } : it)),
    doneParts: mapParts(state.doneParts) ?? null,
    last: state.last ? { ...state.last, operand: fn(state.last.operand) } : null,
  };
}
