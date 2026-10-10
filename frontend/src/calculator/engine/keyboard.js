// Keyboard shortcuts, following the Windows calculator. Returns the key id that the
// on-screen key of the same name uses (see machine.press), or null.

const COMMON = {
  "+": "add",
  "-": "sub",
  "*": "mul",
  "/": "div",
  "=": "equals",
  Enter: "equals",
  Backspace: "back",
  Escape: "c",
  Delete: "ce",
  F9: "neg",
};

const DECIMAL = { ".": "point", ",": "point", r: "inv", R: "inv", "@": "sqrt", q: "sqr", Q: "sqr" };

const BY_MODE = {
  standard: { ...DECIMAL, "%": "percent" },
  scientific: {
    ...DECIMAL,
    "%": "mod",
    "^": "pow",
    "(": "open",
    ")": "close",
    "#": "cube",
    "!": "fact",
    "|": "abs",
    p: "pi",
    P: "pi",
    e: "e",
    x: "exp",
    X: "exp",
    l: "log",
    L: "log",
    n: "ln",
    N: "ln",
    y: "pow",
    Y: "pow",
    v: "fe",
    V: "fe",
    s: "sin",
    S: "asin",
    o: "cos",
    O: "acos",
    t: "tan",
    T: "atan",
  },
  programmer: {
    "%": "mod",
    "^": "xor",
    "&": "and",
    "|": "or",
    "~": "not",
    "<": "lsh",
    ">": "rsh",
    "(": "open",
    ")": "close",
  },
};

// Ctrl + letter: memory, as in Windows.
const WITH_CTRL = { m: "ms", r: "mr", p: "mplus", q: "mminus", l: "mc" };

/**
 * @param {{key: string, ctrlKey?: boolean, metaKey?: boolean, altKey?: boolean}} event
 * @param {string} mode "standard" | "scientific" | "programmer"
 * @param {number} base programmer input base (letters A-F are digits in HEX)
 */
export function keyFor(event, mode, base = 10) {
  const { key } = event;
  if (event.altKey) return null;
  if (event.ctrlKey || event.metaKey) return WITH_CTRL[key.toLowerCase()] ?? null;
  if (/^[0-9]$/.test(key)) return key;
  if (mode === "programmer" && /^[a-f]$/i.test(key)) return base === 16 ? key.toUpperCase() : null;
  return BY_MODE[mode]?.[key] ?? COMMON[key] ?? null;
}
