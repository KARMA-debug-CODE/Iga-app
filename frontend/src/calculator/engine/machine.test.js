import { describe, expect, it } from "vitest";

import { keyFor } from "./keyboard.js";
import {
  clearHistory,
  copyText,
  expressionText,
  formatValue,
  fromSaved,
  initMachine,
  isEnabled,
  memoryItem,
  paste,
  press,
  recallHistory,
  setBits,
  setMode,
  toSaved,
} from "./machine.js";
import { inMode, keys, shows } from "./testkit.js";

const memory = (s, lang = "en") => s.memory[s.mode === "programmer" ? "programmer" : "decimal"].map((v) => formatValue(s, v, lang));

describe("Memory", () => {
  it("stores, adds, subtracts, recalls and clears like Windows", () => {
    let s = keys("5 ms");
    expect(memory(s)).toEqual(["5"]);
    s = keys("3 mplus", s);
    expect(memory(s)).toEqual(["8"]);
    s = keys("10 mminus", s);
    expect(memory(s)).toEqual(["-2"]);
    s = keys("7 ms", s);
    expect(memory(s)).toEqual(["7", "-2"]);
    s = keys("c mr", s);
    expect(shows(s)).toBe("7");
    s = keys("mc", s);
    expect(memory(s)).toEqual([]);
    expect(isEnabled(s, "mr")).toBe(false);
    expect(isEnabled(s, "mc")).toBe(false);
  });

  it("M+ and M− with an empty memory start a new item", () => {
    expect(memory(keys("4 mplus"))).toEqual(["4"]);
    expect(memory(keys("4 mminus"))).toEqual(["-4"]);
  });

  it("starts a new number after MS, so typing does not add digits", () => {
    const s = keys("12 ms 3");
    expect(shows(s)).toBe("3");
  });

  it("uses a recalled value in a calculation", () => {
    const s = keys("0.1 ms c 0.2 add mr equals");
    expect(shows(s)).toBe("0.3");
  });

  it("works on one item: recall, clear, add and subtract", () => {
    let s = keys("1 ms 2 ms 3 ms"); // [3, 2, 1]
    s = keys("10", s);
    s = memoryItem(s, "add", 1);
    expect(memory(s)).toEqual(["3", "12", "1"]);
    s = memoryItem(s, "sub", 2);
    expect(memory(s)).toEqual(["3", "12", "-9"]);
    s = memoryItem(s, "clear", 0);
    expect(memory(s)).toEqual(["12", "-9"]);
    s = memoryItem(s, "recall", 1);
    expect(shows(s)).toBe("-9");
  });

  it("is shared by Standard and Scientific, and separate in Programmer", () => {
    let s = keys("5 ms");
    s = setMode(s, "scientific");
    expect(memory(s)).toEqual(["5"]);
    s = setMode(s, "programmer");
    expect(memory(s)).toEqual([]);
    s = keys("9 ms", s);
    expect(memory(s)).toEqual(["9"]);
    s = setMode(s, "standard");
    expect(memory(s)).toEqual(["5"]);
  });

  it("cuts programmer memory to the word size", () => {
    let s = keys("300 ms", inMode("programmer"));
    s = setBits(s, 8);
    expect(memory(s)).toEqual(["44"]);
    s = keys("100 mplus 100 mplus", s);
    expect(memory(s)).toEqual(["-12"]);
  });

  it("is off while an error is shown", () => {
    const s = keys("5 ms 1 div 0 equals");
    expect(isEnabled(s, "mr")).toBe(false);
    expect(memory(keys("ms", s))).toEqual(["5"]);
  });
});

describe("History", () => {
  it('records "expression =" and the result each time = finishes a calculation', () => {
    let s = keys("2 add 3 equals");
    expect(s.history.decimal).toHaveLength(1);
    expect(expressionText(s, "en", s.history.decimal[0].parts)).toBe("2 + 3 =");
    expect(formatValue(s, s.history.decimal[0].value)).toBe("5");
    s = keys("equals", s);
    expect(s.history.decimal).toHaveLength(2);
    expect(expressionText(s, "en", s.history.decimal[0].parts)).toBe("5 + 3 =");
    // A number alone is not a calculation.
    expect(keys("7 equals").history.decimal).toHaveLength(0);
  });

  it("reuses an entry: its expression and result come back to the display", () => {
    let s = keys("12 mul 2 equals c 1 add 1 equals");
    s = recallHistory(s, 1);
    expect(shows(s)).toBe("24");
    expect(expressionText(s)).toBe("12 × 2 =");
    s = keys("add 1 equals", s);
    expect(shows(s)).toBe("25");
  });

  it("formats entries in the reader's language", () => {
    const s = keys("1234.5 add 1 equals");
    expect(expressionText(s, "fr", s.history.decimal[0].parts)).toBe("1 234,5 + 1 =");
  });

  it("can be cleared", () => {
    const s = clearHistory(keys("2 add 3 equals"));
    expect(s.history.decimal).toEqual([]);
  });

  it("keeps a separate history in Programmer mode", () => {
    let s = keys("2 add 3 equals");
    s = keys("4 mul 4 equals", setMode(s, "programmer"));
    expect(s.history.decimal).toHaveLength(1);
    expect(s.history.programmer).toHaveLength(1);
  });
});

describe("Saving", () => {
  it("round-trips settings, history and memory through JSON", () => {
    let s = keys("0.1 add 0.2 equals ms");
    s = setMode(s, "scientific");
    s = keys("angle", s);
    s = keys("255 neg ms 1 add 1 equals", setMode(s, "programmer"));
    const saved = JSON.parse(JSON.stringify(toSaved(s)));
    const back = initMachine(fromSaved(saved));
    expect(back.mode).toBe("programmer");
    expect(back.angle).toBe("rad");
    expect(back.memory.programmer).toEqual([-255n]);
    expect(back.memory.decimal.map(String)).toEqual(["0.3"]);
    expect(expressionText(setMode(back, "standard"), "en", back.history.decimal[0].parts)).toBe("0.1 + 0.2 =");
    expect(back.history.programmer[0].value).toBe(2n);
  });

  it("ignores saved data that does not look right", () => {
    const back = fromSaved({ settings: { mode: "graphing" }, history: { decimal: [{ parts: [{ v: "x" }], value: "1" }, 5] }, memory: { decimal: ["1e5", "abc", null] } });
    const s = initMachine(back);
    expect(s.mode).toBe("standard");
    expect(s.history.decimal).toEqual([]);
    expect(s.memory.decimal.map(String)).toEqual(["100000"]);
    expect(initMachine(fromSaved("nonsense")).history.decimal).toEqual([]);
  });
});

describe("Paste and copy", () => {
  it("pastes numbers written in English or French", () => {
    expect(shows(paste(initMachine(), "1,234.5"))).toBe("1,234.5");
    expect(shows(paste(initMachine(), "1 234,5", "fr"), "fr")).toBe("1 234,5");
    expect(shows(paste(initMachine(), "3,5", "en"))).toBe("3.5");
    expect(shows(paste(initMachine(), "1,234", "fr"), "fr")).toBe("1,234");
    expect(shows(paste(initMachine(), "−12"))).toBe("-12");
  });

  it("ignores text that is not a number", () => {
    const s = keys("7");
    expect(paste(s, "hello")).toBe(s);
    expect(paste(s, "2+3")).toBe(s);
    expect(paste(s, "")).toBe(s);
  });

  it("pastes long numbers as a value", () => {
    expect(shows(paste(initMachine(), "3.14159265358979323846"))).toBe("3.141592653589793");
    expect(shows(paste(initMachine(), "2e5"))).toBe("200,000");
    expect(shows(paste(inMode("scientific"), "2e5"))).toBe("2.e+5");
  });

  it("pastes in the programmer base, or with a 0x / 0b prefix", () => {
    const dec = inMode("programmer");
    expect(shows(paste(dec, "0xFF"))).toBe("255");
    expect(shows(paste(dec, "0b1010"))).toBe("10");
    expect(shows(paste(dec, "1,000"))).toBe("1,000");
    expect(paste(dec, "FF")).toBe(dec);
  });

  it("copies the display without grouping", () => {
    expect(copyText(keys("1234567 add 0.5 equals"))).toBe("1234567.5");
    expect(copyText(keys("1234.5"), "fr")).toBe("1234,5");
    expect(copyText(keys("1 div 0 equals"))).toBe("");
  });
});

describe("Modes", () => {
  it("keeps each mode's calculation when switching", () => {
    let s = keys("2 add 3");
    s = keys("9 sqrt", setMode(s, "scientific"));
    expect(shows(s)).toBe("3");
    s = setMode(s, "standard");
    expect(shows(s)).toBe("3");
    expect(expressionText(s)).toBe("2 +");
    expect(shows(keys("equals", s))).toBe("5");
    expect(setMode(s, "graphing")).toBe(s);
  });

  it("ignores keys of other modes", () => {
    const s = keys("5");
    expect(press(s, "sin")).toBe(s);
    expect(press(s, "open")).toBe(s);
    expect(press(s, "pi")).toBe(s);
    expect(shows(press(inMode("scientific"), "percent"))).toBe("0");
  });
});

describe("Keyboard", () => {
  const k = (key, mode = "standard", extra = {}, base = 10) => keyFor({ key, ...extra }, mode, base);

  it("maps the Windows shortcuts", () => {
    expect(k("7")).toBe("7");
    expect(k("+")).toBe("add");
    expect(k("-")).toBe("sub");
    expect(k("*")).toBe("mul");
    expect(k("/")).toBe("div");
    expect(k("Enter")).toBe("equals");
    expect(k("=")).toBe("equals");
    expect(k("Backspace")).toBe("back");
    expect(k("Escape")).toBe("c");
    expect(k("Delete")).toBe("ce");
    expect(k("F9")).toBe("neg");
    expect(k("r")).toBe("inv");
    expect(k("@")).toBe("sqrt");
    expect(k("%")).toBe("percent");
    expect(k(".")).toBe("point");
    expect(k(",")).toBe("point");
  });

  it("maps Ctrl + M, R, P, Q, L to memory", () => {
    expect(k("m", "standard", { ctrlKey: true })).toBe("ms");
    expect(k("r", "standard", { ctrlKey: true })).toBe("mr");
    expect(k("p", "standard", { ctrlKey: true })).toBe("mplus");
    expect(k("q", "standard", { ctrlKey: true })).toBe("mminus");
    expect(k("L", "standard", { ctrlKey: true })).toBe("mc");
    expect(k("c", "standard", { ctrlKey: true })).toBeNull();
    expect(k("a", "standard", { altKey: true })).toBeNull();
  });

  it("has scientific and programmer keys", () => {
    expect(k("^", "scientific")).toBe("pow");
    expect(k("(", "scientific")).toBe("open");
    expect(k("%", "scientific")).toBe("mod");
    expect(k("!", "scientific")).toBe("fact");
    expect(k("s", "scientific")).toBe("sin");
    expect(k("(", "standard")).toBeNull();
    expect(k("^", "programmer")).toBe("xor");
    expect(k("&", "programmer")).toBe("and");
    expect(k("<", "programmer")).toBe("lsh");
    expect(k("a", "programmer", {}, 16)).toBe("A");
    expect(k("c", "programmer", {}, 16)).toBe("C");
    expect(k("a", "programmer", {}, 10)).toBeNull();
    expect(k(".", "programmer")).toBeNull();
  });
});
