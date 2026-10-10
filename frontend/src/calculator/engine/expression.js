// The parser for Graphing mode. It reads a function typed by a student ("2x^2 - 3x + 1",
// "sin x", "sqrt(x)", "1/x") into a small tree, then turns the tree into a plain function
// of x for plotting. It never uses eval or Function: only the names and operators below
// are understood, so nothing typed here can run as code.
//
// Grammar (implicit multiplication binds like ×, so 2x^2 is 2·x², 1/2x is (1/2)·x):
//   expr    := term (("+" | "-") term)*
//   term    := unary (("*" | "/") unary | power)*      a power right after a term multiplies it
//   unary   := ("-" | "+") unary | power
//   power   := postfix ("^" unary)?                    right to left: 2^3^2 = 2^9
//   postfix := primary ("²" | "³")*
//   primary := number | x | pi | e | "(" expr ")" | "|" expr "|" | function argument
// A function takes a bracket, or else the factors that follow it up to the next function:
// sin 2x = sin(2x), sin x cos x = sin(x)·cos(x), sin x^2 = sin(x²), sin²x = (sin x)².

const FUNCTIONS = {
  sin: "sin",
  cos: "cos",
  tan: "tan",
  asin: "asin",
  acos: "acos",
  atan: "atan",
  arcsin: "asin",
  arccos: "acos",
  arctan: "atan",
  sinh: "sinh",
  cosh: "cosh",
  tanh: "tanh",
  sqrt: "sqrt",
  cbrt: "cbrt",
  abs: "abs",
  ln: "ln",
  log: "log",
  exp: "exp",
};
const CONSTANTS = { pi: Math.PI, e: Math.E };
// Longest names first, so "sinh" is not read as "sin" then "h", and "exp" not as e·x·p.
const NAMES = [...Object.keys(FUNCTIONS), ...Object.keys(CONSTANTS), "x"].sort((a, b) => b.length - a.length);
const SUPERSCRIPTS = "⁰¹²³⁴⁵⁶⁷⁸⁹";

class ParseError extends Error {
  constructor(code, near = "") {
    super(code);
    this.code = code; // "unexpected" | "unknown" | "unclosed" | "end"
    this.near = near;
  }
}

/** Split a run of letters into known names ("xsinx" -> x, sin, x), or throw for an unknown name. */
function splitNames(run) {
  const out = [];
  let i = 0;
  while (i < run.length) {
    const name = NAMES.find((n) => run.startsWith(n, i));
    if (!name) throw new ParseError("unknown", run);
    out.push(name);
    i += name.length;
  }
  return out;
}

export function tokenize(text) {
  const tokens = [];
  const s = text.toLowerCase();
  let i = 0;
  while (i < s.length) {
    const ch = s[i];
    if (/\s/.test(ch)) {
      i += 1;
      continue;
    }
    // A comma is a decimal separator too (French), since no function takes two arguments.
    const number = /^(\d+([.,]\d*)?|[.,]\d+)/.exec(s.slice(i));
    if (number) {
      tokens.push({ type: "num", value: Number(number[0].replace(",", ".")), text: number[0] });
      i += number[0].length;
      continue;
    }
    if (/[a-z]/.test(ch)) {
      const run = /^[a-z]+/.exec(s.slice(i))[0];
      for (const name of splitNames(run)) {
        if (FUNCTIONS[name]) tokens.push({ type: "fn", value: FUNCTIONS[name], text: name });
        else tokens.push({ type: "name", value: name, text: name });
      }
      i += run.length;
      continue;
    }
    if (SUPERSCRIPTS.includes(ch)) {
      let digits = "";
      while (i < s.length && SUPERSCRIPTS.includes(s[i])) {
        digits += SUPERSCRIPTS.indexOf(s[i]);
        i += 1;
      }
      tokens.push({ type: "sup", value: Number(digits), text: digits });
      continue;
    }
    i += 1;
    if ("+-*/^()|".includes(ch)) tokens.push({ type: ch, text: ch });
    else if ("−–".includes(ch)) tokens.push({ type: "-", text: ch });
    else if ("×·∙".includes(ch)) tokens.push({ type: "*", text: ch });
    else if (ch === "÷") tokens.push({ type: "/", text: ch });
    else if (ch === "π") tokens.push({ type: "name", value: "pi", text: ch });
    else if (ch === "√") tokens.push({ type: "fn", value: "sqrt", text: ch });
    else if (ch === "∛") tokens.push({ type: "fn", value: "cbrt", text: ch });
    else throw new ParseError("unexpected", ch);
  }
  return tokens;
}

const num = (value) => ({ t: "num", value });
const bin = (op, a, b) => ({ t: "bin", op, a, b });

function parseTokens(tokens) {
  let i = 0;
  let bars = 0; // how many |...| are open: a "|" then closes one instead of opening one
  const peek = () => tokens[i];
  const next = () => tokens[i++];
  const fail = () => {
    const tok = peek();
    throw tok ? new ParseError("unexpected", tok.text) : new ParseError("end");
  };
  const startsFactor = (tok) => Boolean(tok) && (["num", "name", "fn", "("].includes(tok.type) || (tok.type === "|" && bars === 0));
  // Two numbers side by side ("2 3", "2.3.4", "x²3") are a typing mistake, not a product.
  const multiplies = (tok) => startsFactor(tok) && !(tok.type === "num" && ["num", "sup"].includes(tokens[i - 1]?.type));

  function expr() {
    let node = term();
    while (peek()?.type === "+" || peek()?.type === "-") {
      const op = next().type;
      node = bin(op, node, term());
    }
    return node;
  }

  function term() {
    let node = unary();
    for (;;) {
      const tok = peek();
      if (tok?.type === "*" || tok?.type === "/") {
        next();
        node = bin(tok.type, node, unary());
      } else if (multiplies(tok)) node = bin("*", node, power());
      else return node;
    }
  }

  function unary() {
    if (peek()?.type === "-") {
      next();
      return { t: "neg", a: unary() };
    }
    if (peek()?.type === "+") {
      next();
      return unary();
    }
    return power();
  }

  function power() {
    const base = postfix();
    if (peek()?.type !== "^") return base;
    next();
    return { t: "pow", a: base, b: unary() };
  }

  function postfix() {
    let node = primary();
    while (peek()?.type === "sup") node = { t: "pow", a: node, b: num(next().value) };
    return node;
  }

  function closing(type) {
    if (peek()?.type === type) {
      next();
      return;
    }
    if (!peek()) throw new ParseError("unclosed");
    fail();
  }

  function fnArgument() {
    if (peek()?.type === "(") {
      next();
      const inner = expr();
      closing(")");
      return inner;
    }
    if (!peek()) fail();
    let node = unary();
    while (multiplies(peek()) && peek().type !== "fn") node = bin("*", node, power());
    return node;
  }

  function primary() {
    const tok = peek();
    if (!tok) fail();
    if (tok.type === "num") {
      next();
      return num(tok.value);
    }
    if (tok.type === "name") {
      next();
      return tok.value === "x" ? { t: "x" } : num(CONSTANTS[tok.value]);
    }
    if (tok.type === "(") {
      next();
      const inner = expr();
      closing(")");
      return inner;
    }
    if (tok.type === "|" && bars === 0) {
      next();
      bars += 1;
      const inner = expr();
      bars -= 1;
      closing("|");
      return { t: "fn", name: "abs", a: inner };
    }
    if (tok.type === "fn") {
      next();
      // sin²x and sin^2 x mean (sin x)².
      let exponent = null;
      if (peek()?.type === "sup") exponent = num(next().value);
      else if (peek()?.type === "^") {
        next();
        exponent = unary();
      }
      const node = { t: "fn", name: tok.value, a: fnArgument() };
      return exponent ? { t: "pow", a: node, b: exponent } : node;
    }
    return fail();
  }

  const tree = expr();
  if (i < tokens.length) fail();
  return tree;
}

/**
 * Read what a student typed. A leading "y =" or "f(x) =" is allowed.
 * Returns {tree} or {error: {code, near}}; an empty box gives {tree: null}.
 */
export function parseFunction(text) {
  const body = String(text ?? "").replace(/^\s*(?:y|f\s*\(\s*x\s*\))\s*=/i, "");
  if (!body.trim()) return { tree: null };
  try {
    return { tree: parseTokens(tokenize(body)) };
  } catch (e) {
    if (!(e instanceof ParseError)) throw e;
    return { error: { code: e.code, near: e.near } };
  }
}

// ---- Evaluation ----------------------------------------------------------------

const RAD_PER_DEG = Math.PI / 180;

/** Trigonometry in degrees, exact at quarter turns: sin 180° = 0, tan 90° has no value. */
function degreeTrig(name, deg) {
  const r = ((deg % 360) + 360) % 360;
  const quarter = r / 90;
  if (Number.isInteger(quarter)) {
    if (name === "sin") return [0, 1, 0, -1][quarter];
    if (name === "cos") return [1, 0, -1, 0][quarter];
    return quarter % 2 ? NaN : 0;
  }
  return Math[name](r * RAD_PER_DEG);
}

/**
 * x^y with real results where a student expects them: (−8)^(1/3) = −2, x^(2/3) for x < 0.
 * A negative base with an exponent p/q (q odd, up to 99) gives ±|x|^y; otherwise no value.
 */
export function realPow(x, y) {
  if (x >= 0 || Number.isInteger(y)) return x ** y;
  for (let q = 3; q < 100; q += 2) {
    const p = Math.round(y * q);
    if (Math.abs(y * q - p) < 1e-9) return (p % 2 ? -1 : 1) * (-x) ** y;
  }
  return NaN;
}

function functionFor(name, angle) {
  const deg = angle === "deg";
  const fromRad = deg ? (r) => r / RAD_PER_DEG : (r) => r;
  switch (name) {
    case "sin":
    case "cos":
    case "tan":
      return deg ? (v) => degreeTrig(name, v) : Math[name];
    case "asin":
    case "acos":
    case "atan":
      return (v) => fromRad(Math[name](v));
    case "sinh":
    case "cosh":
    case "tanh":
    case "sqrt":
    case "cbrt":
    case "abs":
    case "exp":
      return Math[name];
    case "ln":
      return Math.log;
    case "log":
      return Math.log10;
    default:
      throw new Error(`unknown function ${name}`);
  }
}

/** Turn a tree into a function of x. angle: "rad" or "deg" (for sin, cos, tan and their inverses). */
export function compile(tree, angle = "rad") {
  switch (tree.t) {
    case "num": {
      const v = tree.value;
      return () => v;
    }
    case "x":
      return (x) => x;
    case "neg": {
      const a = compile(tree.a, angle);
      return (x) => -a(x);
    }
    case "pow": {
      const a = compile(tree.a, angle);
      const b = compile(tree.b, angle);
      return (x) => realPow(a(x), b(x));
    }
    case "fn": {
      const a = compile(tree.a, angle);
      const fn = functionFor(tree.name, angle);
      return (x) => fn(a(x));
    }
    case "bin": {
      const a = compile(tree.a, angle);
      const b = compile(tree.b, angle);
      if (tree.op === "+") return (x) => a(x) + b(x);
      if (tree.op === "-") return (x) => a(x) - b(x);
      if (tree.op === "*") return (x) => a(x) * b(x);
      return (x) => a(x) / b(x);
    }
    default:
      throw new Error(`unknown node ${tree.t}`);
  }
}

/** Does the function use sin, cos, tan or their inverses? (Only they depend on DEG or RAD.) */
export function usesTrig(tree) {
  if (!tree) return false;
  if (tree.t === "fn" && /^a?(sin|cos|tan)$/.test(tree.name)) return true;
  return [tree.a, tree.b].some((child) => child && usesTrig(child));
}
