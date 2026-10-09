import { describe, expect, it } from "vitest";

import { compile, parseFunction, realPow, usesTrig } from "./expression.js";

/** f(x) for a typed function. */
function fn(text, angle = "rad") {
  const { tree, error } = parseFunction(text);
  if (error) throw new Error(`${text}: ${error.code} ${error.near}`);
  return compile(tree, angle);
}
const at = (text, x, angle) => fn(text, angle)(x);
const errorOf = (text) => parseFunction(text).error;

describe("Graphing parser", () => {
  it("follows the order of operations", () => {
    expect(at("2 + 3 * x", 4)).toBe(14);
    expect(at("(2 + 3) * x", 4)).toBe(20);
    expect(at("x - 2 - 3", 10)).toBe(5);
    expect(at("x / 2 / 5", 20)).toBe(2);
    expect(at("2 ^ 3 ^ 2", 0)).toBe(512);
    expect(at("-x^2", 3)).toBe(-9);
    expect(at("2^-x", 1)).toBe(0.5);
    expect(at("--x", 2)).toBe(2);
  });

  it("multiplies without a sign: 2x, 3(x + 1), (x + 1)(x - 1), 2pi", () => {
    expect(at("2x", 5)).toBe(10);
    expect(at("2x^2", 3)).toBe(18);
    expect(at("3(x + 1)", 1)).toBe(6);
    expect(at("(x + 1)(x - 1)", 3)).toBe(8);
    expect(at("x(x + 1)", 2)).toBe(6);
    expect(at("2pi", 0)).toBeCloseTo(2 * Math.PI, 12);
    expect(at("1/2x", 4)).toBe(2); // (1/2)·x, read from left to right
    expect(at("2 sin(x)", Math.PI / 2)).toBeCloseTo(2, 12);
  });

  it("knows the functions and constants", () => {
    expect(at("sqrt(x)", 9)).toBe(3);
    expect(at("√x", 16)).toBe(4);
    expect(at("abs(x)", -3)).toBe(3);
    expect(at("|x - 5|", 2)).toBe(3);
    expect(at("2|x|", -4)).toBe(8);
    expect(at("ln(e)", 0)).toBeCloseTo(1, 12);
    expect(at("log(x)", 1000)).toBeCloseTo(3, 12);
    expect(at("exp(x)", 1)).toBeCloseTo(Math.E, 12);
    expect(at("e^x", 2)).toBeCloseTo(Math.E ** 2, 12);
    expect(at("pi", 0)).toBe(Math.PI);
    expect(at("π x", 2)).toBe(2 * Math.PI);
    expect(at("cos(pi)", 0)).toBeCloseTo(-1, 12);
    expect(at("tan(x)", Math.PI / 4)).toBeCloseTo(1, 12);
    expect(at("asin(1)", 0)).toBeCloseTo(Math.PI / 2, 12);
  });

  it("reads a function name without brackets like a calculator", () => {
    expect(at("sin x", Math.PI / 2)).toBeCloseTo(1, 12);
    expect(at("sin 2x", Math.PI / 4)).toBeCloseTo(1, 12); // sin(2x)
    expect(at("sinx", Math.PI / 2)).toBeCloseTo(1, 12);
    expect(at("sin x cos x", 0.3)).toBeCloseTo(Math.sin(0.3) * Math.cos(0.3), 12);
    expect(at("sin x^2", 2)).toBeCloseTo(Math.sin(4), 12);
    expect(at("sin x + 1", 0)).toBe(1);
    expect(at("sin²x + cos²x", 0.7)).toBeCloseTo(1, 12);
    expect(at("sin^2 x", 0.5)).toBeCloseTo(Math.sin(0.5) ** 2, 12);
    expect(at("sin(x)^2", 0.5)).toBeCloseTo(Math.sin(0.5) ** 2, 12);
    expect(at("ln x", Math.E)).toBeCloseTo(1, 12);
  });

  it("accepts y =, symbols from the keypad, capitals and a decimal comma", () => {
    expect(at("y = 2x + 1", 3)).toBe(7);
    expect(at("f(x) = x²", 3)).toBe(9);
    expect(at("x³ − 2 × x ÷ 4", 2)).toBe(7);
    expect(at("SIN(X)", 0)).toBe(0);
    expect(at("0,5x", 4)).toBe(2);
    expect(at("1.5x", 2)).toBe(3);
  });

  it("works in degrees, exactly at quarter turns", () => {
    expect(at("sin x", 30, "deg")).toBeCloseTo(0.5, 15);
    expect(at("sin x", 180, "deg")).toBe(0);
    expect(at("cos x", 90, "deg")).toBe(0);
    expect(at("cos x", -360, "deg")).toBe(1);
    expect(at("tan x", 45, "deg")).toBeCloseTo(1, 15);
    expect(at("tan x", 90, "deg")).toBeNaN();
    expect(at("asin x", 1, "deg")).toBeCloseTo(90, 12);
    expect(at("sin x", Math.PI / 2, "rad")).toBe(1);
  });

  it("has no value outside a function's domain", () => {
    expect(at("sqrt(x)", -1)).toBeNaN();
    expect(at("ln x", -1)).toBeNaN();
    expect(at("ln x", 0)).toBe(-Infinity);
    expect(at("1/x", 0)).toBe(Infinity);
    expect(at("asin x", 2)).toBeNaN();
  });

  it("gives real odd roots of negative numbers", () => {
    expect(realPow(-8, 1 / 3)).toBeCloseTo(-2, 12);
    expect(at("x^(2/3)", -8)).toBeCloseTo(4, 12);
    expect(at("x^(1/2)", -4)).toBeNaN();
    expect(at("x^0.5", 4)).toBe(2);
    expect(at("x^2", -3)).toBe(9);
  });

  it("explains what is wrong", () => {
    expect(parseFunction("").tree).toBeNull();
    expect(parseFunction("y = ").tree).toBeNull();
    expect(errorOf("2y")).toEqual({ code: "unknown", near: "y" });
    expect(errorOf("sec x")).toEqual({ code: "unknown", near: "sec" });
    expect(errorOf("(x + 1")).toEqual({ code: "unclosed", near: "" });
    expect(errorOf("x +")).toEqual({ code: "end", near: "" });
    expect(errorOf("x + * 2")).toEqual({ code: "unexpected", near: "*" });
    expect(errorOf("x)")).toEqual({ code: "unexpected", near: ")" });
    expect(errorOf("2 # x")).toEqual({ code: "unexpected", near: "#" });
    expect(errorOf("sin")).toEqual({ code: "end", near: "" });
  });

  it("cannot run code", () => {
    expect(errorOf("alert(1)")).toEqual({ code: "unknown", near: "alert" });
    expect(errorOf("constructor")).toEqual({ code: "unknown", near: "constructor" });
    expect(errorOf("x; 1")).toEqual({ code: "unexpected", near: ";" });
  });

  it("tells which functions use angles", () => {
    expect(usesTrig(parseFunction("2x + sin(x)").tree)).toBe(true);
    expect(usesTrig(parseFunction("x^2 + ln x").tree)).toBe(false);
  });
});
