import { describe, expect, it } from "vitest";

import { baseValues, copyText, isEnabled, setBase, setBits } from "./machine.js";
import { fromBase, toBase } from "./programmer.js";
import { expr, inMode, keys, shows } from "./testkit.js";

const prog = (text, settings) => keys(text, inMode("programmer", settings));
const bases = (s) => Object.fromEntries(baseValues(s).map((b) => [b.base, b.text]));

describe("Programmer mode", () => {
  it("shows the number in HEX, DEC, OCT and BIN together", () => {
    expect(bases(prog("255"))).toEqual({ 16: "FF", 10: "255", 8: "377", 2: "1111 1111" });
    expect(bases(prog("1234"))).toEqual({ 16: "4D2", 10: "1,234", 8: "2 322", 2: "100 1101 0010" });
  });

  it("types in the chosen base, and converts the number being typed when the base changes", () => {
    let s = prog("", { base: 16 });
    s = keys("F F", s);
    expect(shows(s)).toBe("FF");
    expect(bases(s)[10]).toBe("255");
    s = setBase(s, 2);
    expect(shows(s)).toBe("1111 1111");
    s = keys("1", s);
    expect(bases(s)[10]).toBe("511");
    s = setBase(s, 10);
    expect(shows(s)).toBe("511");
  });

  it("only allows the digits of the base: A-F in HEX, 0-7 in OCT, 0-1 in BIN", () => {
    const dec = inMode("programmer");
    expect(isEnabled(dec, "A")).toBe(false);
    expect(isEnabled(dec, "9")).toBe(true);
    expect(isEnabled(dec, "point")).toBe(false);
    expect(isEnabled(setBase(dec, 16), "F")).toBe(true);
    expect(isEnabled(setBase(dec, 8), "8")).toBe(false);
    expect(isEnabled(setBase(dec, 8), "7")).toBe(true);
    expect(isEnabled(setBase(dec, 2), "2")).toBe(false);
    expect(shows(keys("A 7", dec))).toBe("7");
  });

  describe("two's complement in each word size", () => {
    it("stores −1 as all bits set", () => {
      expect(bases(prog("1 neg", { bits: 8 }))).toEqual({ 16: "FF", 10: "-1", 8: "377", 2: "1111 1111" });
      expect(bases(prog("1 neg", { bits: 16 }))[16]).toBe("FFFF");
      expect(bases(prog("1 neg", { bits: 32 }))[16]).toBe("FFFF FFFF");
      expect(bases(prog("1 neg", { bits: 64 }))[16]).toBe("FFFF FFFF FFFF FFFF");
      expect(bases(prog("1 neg", { bits: 64 }))[8]).toBe("1 777 777 777 777 777 777 777");
    });

    it("wraps around past the largest number", () => {
      expect(shows(prog("127 add 1 equals", { bits: 8 }))).toBe("-128");
      expect(shows(prog("32767 add 1 equals", { bits: 16 }))).toBe("-32,768");
      expect(shows(prog("2147483647 add 1 equals", { bits: 32 }))).toBe("-2,147,483,648");
      expect(shows(prog("9223372036854775807 add 1 equals"))).toBe("-9,223,372,036,854,775,808");
      expect(shows(prog("100 mul 2 equals", { bits: 8 }))).toBe("-56");
    });

    it("reads FF as −1 in a byte and 255 in a word", () => {
      expect(fromBase("FF", 16, 8)).toBe(-1n);
      expect(fromBase("FF", 16, 16)).toBe(255n);
      expect(toBase(-1n, 16, 8)).toBe("FF");
      expect(toBase(-1n, 2, 16)).toBe("1111111111111111");
      expect(fromBase("12G", 16, 64)).toBeNull();
    });

    it("cuts the value when the word size gets smaller", () => {
      let s = prog("300");
      s = setBits(s, 8);
      expect(shows(s)).toBe("44");
      s = prog("200 equals");
      s = setBits(s, 8);
      expect(shows(s)).toBe("-56");
      s = setBits(s, 16);
      expect(shows(s)).toBe("-56");
    });

    it("stops typing at the size of the word", () => {
      expect(shows(prog("1289", { bits: 8 }))).toBe("12");
      expect(shows(prog("127", { bits: 8 }))).toBe("127");
      expect(shows(prog("1 2 3 4", { bits: 8, base: 16 }))).toBe("12");
      expect(shows(prog("111111111", { bits: 8, base: 2 }))).toBe("1111 1111");
    });
  });

  describe("bitwise operators", () => {
    it("has AND, OR, XOR, NAND and NOR", () => {
      expect(shows(prog("12 and 10 equals"))).toBe("8");
      expect(shows(prog("12 or 10 equals"))).toBe("14");
      expect(shows(prog("12 xor 10 equals"))).toBe("6");
      expect(shows(prog("12 nand 10 equals"))).toBe("-9");
      expect(shows(prog("12 nor 10 equals"))).toBe("-15");
      expect(bases(prog("12 nand 10 equals", { bits: 8 }))[2]).toBe("1111 0111");
      expect(expr(prog("12 and 10 equals"))).toBe("12 AND 10 =");
    });

    it("has NOT", () => {
      expect(shows(prog("0 not"))).toBe("-1");
      expect(bases(prog("5 not", { bits: 8 }))[16]).toBe("FA");
      expect(expr(prog("5 not"))).toBe("NOT(5)");
    });

    it("shifts left and right (arithmetic shift keeps the sign)", () => {
      expect(shows(prog("1 lsh 4 equals"))).toBe("16");
      expect(shows(prog("256 rsh 4 equals"))).toBe("16");
      expect(shows(prog("8 neg rsh 1 equals"))).toBe("-4");
      expect(shows(prog("1 lsh 7 equals", { bits: 8 }))).toBe("-128");
      expect(shows(prog("1 lsh 64 equals"))).toBe("0");
      expect(shows(prog("8 neg rsh 70 equals"))).toBe("-1");
      expect(expr(prog("1 lsh 4 equals"))).toBe("1 Lsh 4 =");
    });

    it("follows the Windows order: shifts and × before +, before AND, before OR and XOR", () => {
      expect(shows(prog("2 add 3 mul 4 equals"))).toBe("14");
      expect(shows(prog("1 or 2 and 3 equals"))).toBe("3");
      expect(shows(prog("1 add 1 lsh 2 equals"))).toBe("5");
      expect(shows(prog("open 1 add 1 close lsh 2 equals"))).toBe("8");
    });
  });

  describe("arithmetic", () => {
    it("divides whole numbers towards zero, and mod keeps the sign of the first number", () => {
      expect(shows(prog("7 div 2 equals"))).toBe("3");
      expect(shows(prog("7 neg div 2 equals"))).toBe("-3");
      expect(shows(prog("7 mod 3 equals"))).toBe("1");
      expect(shows(prog("7 neg mod 3 equals"))).toBe("-1");
      expect(shows(prog("7 div 0 equals"))).toBe("divzero");
      expect(shows(prog("7 mod 0 equals"))).toBe("divzero");
    });

    it("shows HEX results in the current base", () => {
      const s = prog("F add 1 equals", { base: 16 });
      expect(shows(s)).toBe("10");
      expect(expr(s)).toBe("F + 1 =");
      expect(copyText(s)).toBe("10");
    });
  });
});
