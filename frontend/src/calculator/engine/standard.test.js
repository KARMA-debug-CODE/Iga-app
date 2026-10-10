import { describe, expect, it } from "vitest";

import { isEnabled } from "./machine.js";
import { expr, keys, shows } from "./testkit.js";

describe("Standard mode", () => {
  it("adds decimals exactly: 0.1 + 0.2 = 0.3", () => {
    const s = keys("0.1 add 0.2 equals");
    expect(shows(s)).toBe("0.3");
    expect(expr(s)).toBe("0.1 + 0.2 =");
  });

  it("works each operator out at once, like Windows: 2 + 3 × 4 = 20", () => {
    let s = keys("2 add 3 mul");
    expect(shows(s)).toBe("5");
    expect(expr(s)).toBe("(2 + 3) ×");
    s = keys("4 equals", s);
    expect(shows(s)).toBe("20");
    expect(expr(s)).toBe("(2 + 3) × 4 =");
  });

  it("only adds brackets when the order really changes", () => {
    const s = keys("2 mul 3 add 4 equals");
    expect(expr(s)).toBe("2 × 3 + 4 =");
    expect(shows(s)).toBe("10");
  });

  it("changes the operator when another one is pressed straight away", () => {
    expect(shows(keys("6 add mul 3 equals"))).toBe("18");
  });

  it("uses the display number when = follows an operator: 2 + = 4", () => {
    const s = keys("2 add equals");
    expect(shows(s)).toBe("4");
    expect(expr(s)).toBe("2 + 2 =");
  });

  it("repeats the last operation when = is pressed again", () => {
    let s = keys("2 add 3 equals equals");
    expect(shows(s)).toBe("8");
    expect(expr(s)).toBe("5 + 3 =");
    s = keys("10 equals", s);
    expect(shows(s)).toBe("13");
    expect(shows(keys("100 div 2 equals equals equals"))).toBe("12.5");
  });

  it("continues from a result with a new operator", () => {
    const s = keys("2 add 3 equals mul 2 equals");
    expect(shows(s)).toBe("10");
    expect(expr(s)).toBe("5 × 2 =");
  });

  describe("percent, like Windows", () => {
    it("with + and − is a percentage of the first number: 200 + 10 % = 220", () => {
      let s = keys("200 add 10 percent");
      expect(shows(s)).toBe("20");
      expect(expr(s)).toBe("200 + 20");
      s = keys("equals", s);
      expect(shows(s)).toBe("220");
      expect(shows(keys("50 sub 10 percent equals"))).toBe("45");
    });

    it("with × and ÷ is the number divided by 100", () => {
      expect(shows(keys("50 mul 10 percent equals"))).toBe("5");
      expect(shows(keys("50 div 50 percent equals"))).toBe("100");
    });

    it("alone gives 0, and with no second number uses the first", () => {
      expect(shows(keys("10 percent"))).toBe("0");
      expect(shows(keys("200 add percent"))).toBe("400");
    });
  });

  describe("errors", () => {
    it('shows "Cannot divide by zero" and locks the keys until cleared', () => {
      let s = keys("5 div 0 equals");
      expect(shows(s)).toBe("divzero");
      expect(expr(s)).toBe("5 ÷ 0 =");
      for (const key of ["add", "sqrt", "percent", "neg", "point", "equals", "ms", "mplus"]) expect(isEnabled(s, key)).toBe(false);
      expect(shows(keys("add sqrt neg percent equals", s))).toBe("divzero");
      s = keys("c", s);
      expect(shows(s)).toBe("0");
      expect(expr(s)).toBe("");
    });

    it("starts a new number when a digit is typed after an error, as in Windows", () => {
      expect(shows(keys("5 div 0 add 7"))).toBe("7");
    });

    it("says the result is undefined for 0 ÷ 0", () => {
      expect(shows(keys("0 div 0 equals"))).toBe("undefined");
    });

    it('gives "Invalid input" for the square root of a negative number', () => {
      const s = keys("4 neg sqrt");
      expect(shows(s)).toBe("invalid");
      expect(expr(s)).toBe("√(-4)");
    });

    it("cannot take 1/x of zero", () => {
      expect(shows(keys("0 inv"))).toBe("divzero");
    });
  });

  describe("functions", () => {
    it("squares, takes square roots and reciprocals", () => {
      let s = keys("9 sqrt");
      expect(shows(s)).toBe("3");
      expect(expr(s)).toBe("√(9)");
      s = keys("5 sqr");
      expect(shows(s)).toBe("25");
      expect(expr(s)).toBe("5²");
      s = keys("4 inv");
      expect(shows(s)).toBe("0.25");
      expect(expr(s)).toBe("1/(4)");
    });

    it("applies a function to the second number: 2 + √(9) = 5", () => {
      const s = keys("2 add 9 sqrt equals");
      expect(expr(s)).toBe("2 + √(9) =");
      expect(shows(s)).toBe("5");
    });

    it("nests functions and brackets negative squares", () => {
      expect(expr(keys("3 neg sqr"))).toBe("(-3)²");
      expect(expr(keys("3 sqr neg"))).toBe("−(3²)");
      expect(expr(keys("16 sqrt sqrt"))).toBe("√(√(16))");
    });

    it("changes the sign of the number being typed with ±", () => {
      const s = keys("12 neg");
      expect(shows(s)).toBe("-12");
      expect(expr(s)).toBe("");
      expect(shows(keys("neg", s))).toBe("12");
    });

    it("negates a result as a function", () => {
      const s = keys("2 add 3 equals neg");
      expect(shows(s)).toBe("-5");
      expect(expr(s)).toBe("−(5)");
    });
  });

  describe("typing", () => {
    it("groups thousands and keeps the decimals typed", () => {
      expect(shows(keys("1234567.50"))).toBe("1,234,567.50");
      expect(shows(keys("1234567.50"), "fr")).toBe("1 234 567,50");
    });

    it("stops at 16 digits", () => {
      expect(shows(keys("12345678901234567890"))).toBe("1,234,567,890,123,456");
    });

    it("backspace removes the last digit; CE clears the number; C clears everything", () => {
      let s = keys("123 back");
      expect(shows(s)).toBe("12");
      s = keys("add 45 ce", s);
      expect(shows(s)).toBe("0");
      expect(expr(s)).toBe("12 +");
      s = keys("7 equals", s);
      expect(shows(s)).toBe("19");
      s = keys("back", s);
      expect(expr(s)).toBe("");
      expect(shows(s)).toBe("19");
      expect(shows(keys("c", s))).toBe("0");
    });

    it("CE removes a function result from the expression", () => {
      const s = keys("2 add 9 sqrt ce");
      expect(expr(s)).toBe("2 +");
      expect(shows(s)).toBe("0");
    });

    it("rounds the display to 16 digits but keeps more inside", () => {
      let s = keys("1 div 3 equals");
      expect(shows(s)).toBe("0.3333333333333333");
      s = keys("mul 3 equals", s);
      expect(shows(s)).toBe("1");
      expect(shows(keys("2 div 3 equals"))).toBe("0.6666666666666667");
    });

    it("uses exponent form for very large numbers", () => {
      expect(shows(keys("9999999999999999 mul 10 equals"))).toBe("9.999999999999999e+16");
      expect(shows(keys("1000000000000000 mul 10 equals"))).toBe("1.e+16");
      expect(shows(keys("1000000000000000 mul 10 equals"), "fr")).toBe("1,e+16");
    });
  });
});
