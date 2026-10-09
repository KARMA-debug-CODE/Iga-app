import { describe, expect, it } from "vitest";

import { D } from "./decimal.js";
import { press } from "./machine.js";
import { factorial } from "./scientific.js";
import { expr, inMode, keys, shows } from "./testkit.js";

const sci = (text, settings) => keys(text, inMode("scientific", settings));
const deg = (text) => shows(sci(text));
const rad = (text) => shows(sci(text, { angle: "rad" }));
const grad = (text) => shows(sci(text, { angle: "grad" }));

describe("Scientific mode", () => {
  describe("order of operations", () => {
    it("multiplies before adding: 2 + 3 × 4 = 14", () => {
      let s = sci("2 add 3 mul");
      expect(shows(s)).toBe("3");
      s = keys("4 equals", s);
      expect(shows(s)).toBe("14");
      expect(expr(s)).toBe("2 + 3 × 4 =");
    });

    it("works out a finished product straight away: 2 × 3 + shows 6", () => {
      expect(deg("2 mul 3 add")).toBe("6");
    });

    it("uses brackets: (2 + 3) × 4 = 20", () => {
      let s = sci("open 2 add 3 close");
      expect(shows(s)).toBe("5");
      s = keys("mul 4 equals", s);
      expect(shows(s)).toBe("20");
      expect(expr(s)).toBe("(2 + 3) × 4 =");
    });

    it("closes brackets left open when = is pressed", () => {
      const s = sci("2 mul open 3 add 4 equals");
      expect(shows(s)).toBe("14");
      expect(expr(s)).toBe("2 × (3 + 4) =");
    });

    it("reads 2( as 2 × (", () => {
      expect(deg("2 open 3 add 1 close equals")).toBe("8");
    });

    it("works powers out from the right: 2 ^ 3 ^ 2 = 512", () => {
      expect(deg("2 pow 3 pow 2 equals")).toBe("512");
      expect(deg("2 add 3 pow 2 mul 2 equals")).toBe("20");
    });

    it("repeats the last operation with =", () => {
      expect(deg("2 add 3 mul 4 equals equals")).toBe("56");
    });

    it("applies a function to a bracket", () => {
      const s = sci("open 1 add 3 close sqrt");
      expect(shows(s)).toBe("2");
      expect(expr(s)).toBe("√(1 + 3)");
    });
  });

  describe("trigonometry", () => {
    it("is exact at the angles students learn, in degrees", () => {
      expect(deg("30 sin")).toBe("0.5");
      expect(deg("60 cos")).toBe("0.5");
      expect(deg("45 tan")).toBe("1");
      expect(deg("90 sin")).toBe("1");
      expect(deg("90 cos")).toBe("0");
      expect(deg("180 sin")).toBe("0");
      expect(deg("180 cos")).toBe("-1");
      expect(deg("30 neg sin")).toBe("-0.5");
      expect(deg("390 sin")).toBe("0.5");
      expect(deg("150 sin")).toBe("0.5");
      expect(deg("360 tan")).toBe("0");
    });

    it("says tan 90° is Invalid input", () => {
      expect(deg("90 tan")).toBe("invalid");
      expect(deg("270 tan")).toBe("invalid");
      expect(deg("90 neg tan")).toBe("invalid");
    });

    it("shows the angle unit in the expression", () => {
      expect(expr(sci("30 sin"))).toBe("sin(30°)");
      expect(expr(sci("1 sin", { angle: "rad" }))).toBe("sin(1)");
      expect(expr(sci("50 sin", { angle: "grad" }))).toBe("sin(50ᵍ)");
    });

    it("works in radians", () => {
      expect(rad("pi sin")).toBe("0");
      expect(rad("pi cos")).toBe("-1");
      expect(rad("pi div 6 equals sin")).toBe("0.5");
      expect(rad("pi div 2 equals tan")).toBe("invalid");
      expect(rad("1 sin")).toBe("0.8414709848078965");
      expect(rad("1 asin")).toBe("1.570796326794897");
    });

    it("works in gradians (a right angle is 100)", () => {
      expect(grad("100 sin")).toBe("1");
      expect(grad("200 cos")).toBe("-1");
      expect(grad("100 tan")).toBe("invalid");
      expect(grad("50 sin")).toBe(deg("45 sin"));
      expect(grad("1 atan")).toBe("50");
    });

    it("has inverse functions, in the chosen unit", () => {
      expect(deg("0.5 asin")).toBe("30");
      expect(deg("0.5 acos")).toBe("60");
      expect(deg("1 atan")).toBe("45");
      expect(deg("2 asin")).toBe("invalid");
      expect(expr(sci("0.5 asin"))).toBe("sin⁻¹(0.5)");
    });

    it("has hyperbolic functions and their inverses", () => {
      expect(deg("0 sinh")).toBe("0");
      expect(deg("0 cosh")).toBe("1");
      expect(deg("1 sinh")).toBe("1.175201193643801");
      expect(deg("100 tanh")).toBe("1");
      expect(deg("1 cosh acosh")).toBe("1");
      expect(deg("0.5 neg atanh")).toBe("-0.5493061443340548");
      expect(deg("0.5 acosh")).toBe("invalid");
      expect(deg("1 atanh")).toBe("invalid");
      expect(deg("100000 sinh")).toBe("overflow");
    });

    it("cycles DEG, RAD and GRAD with the angle key", () => {
      let s = inMode("scientific");
      expect(s.angle).toBe("deg");
      s = press(s, "angle");
      expect(s.angle).toBe("rad");
      s = press(s, "angle");
      expect(s.angle).toBe("grad");
      s = press(s, "angle");
      expect(s.angle).toBe("deg");
    });
  });

  describe("factorial", () => {
    it("multiplies whole numbers", () => {
      expect(deg("5 fact")).toBe("120");
      expect(deg("0 fact")).toBe("1");
      expect(deg("1 fact")).toBe("1");
      expect(deg("10 fact")).toBe("3,628,800");
      expect(deg("20 fact")).toBe("2.43290200817664e+18");
      expect(factorial(new D(25)).toFixed()).toBe("15511210043330985984000000");
      expect(expr(sci("5 fact"))).toBe("5!");
    });

    it("refuses negative whole numbers and overflows after 3248!", () => {
      expect(deg("1 neg fact")).toBe("invalid");
      expect(deg("3248 fact")).toMatch(/e\+9997$/);
      expect(deg("3249 fact")).toBe("overflow");
    });

    it("uses the gamma function between whole numbers, like Windows", () => {
      // 0.5! = Γ(1.5) = √π / 2
      expect(deg("0.5 fact")).toBe("0.886226925452758");
      expect(factorial(new D("0.5")).toString()).toBe("0.88622692545275801364908374167057");
      // (−0.5)! = Γ(0.5) = √π
      expect(factorial(new D("-0.5")).toString()).toBe("1.7724538509055160272981674833411");
      expect(factorial(new D("4.5")).toString()).toBe("52.342777784553520181149008492418");
      expect(deg("1.5 neg fact")).toBe("-3.544907701811032");
    });
  });

  describe("powers, roots and logarithms", () => {
    it("works out powers", () => {
      expect(deg("2 pow 10 equals")).toBe("1,024");
      expect(deg("2 pow 0.5 equals")).toBe("1.414213562373095");
      expect(deg("2 pow 1 neg equals")).toBe("0.5");
      expect(deg("3 sqr")).toBe("9");
      expect(deg("3 cube")).toBe("27");
      expect(deg("3 tenx")).toBe("1,000");
      expect(deg("10 twox")).toBe("1,024");
      expect(deg("1 ex")).toBe("2.718281828459045");
      expect(deg("0 pow 1 neg equals")).toBe("divzero");
      expect(deg("10 pow 10001 equals")).toBe("overflow");
    });

    it("takes roots, including odd roots of negative numbers", () => {
      expect(deg("27 cbrt")).toBe("3");
      expect(deg("27 neg cbrt")).toBe("-3");
      expect(deg("16 yroot 4 equals")).toBe("2");
      expect(deg("8 neg yroot 3 equals")).toBe("-2");
      expect(deg("16 neg yroot 4 equals")).toBe("invalid");
      expect(deg("8 neg pow 3 inv equals")).toBe("-2");
      expect(deg("4 neg pow 0.5 equals")).toBe("invalid");
      expect(deg("4 yroot 0 equals")).toBe("invalid");
    });

    it("takes logarithms", () => {
      expect(deg("1000 log")).toBe("3");
      expect(deg("e ln")).toBe("1");
      expect(deg("2 ln")).toBe("0.6931471805599453");
      expect(deg("8 logy 2 equals")).toBe("3");
      expect(deg("0 log")).toBe("invalid");
      expect(deg("1 neg ln")).toBe("invalid");
      expect(deg("8 logy 1 equals")).toBe("invalid");
    });

    it("has mod, absolute value and 1/x", () => {
      expect(deg("7 mod 3 equals")).toBe("1");
      expect(deg("7 neg mod 3 equals")).toBe("2");
      expect(deg("5.5 mod 2 equals")).toBe("1.5");
      expect(deg("5 mod 0 equals")).toBe("divzero");
      expect(deg("3 neg abs")).toBe("3");
      expect(expr(sci("3 neg abs"))).toBe("|-3|");
      expect(deg("8 inv")).toBe("0.125");
    });
  });

  describe("numbers", () => {
    it("has pi and e to 32 digits", () => {
      expect(deg("pi")).toBe("3.141592653589793");
      expect(deg("e")).toBe("2.718281828459045");
      expect(deg("2 mul pi equals")).toBe("6.283185307179586");
    });

    it("types numbers in scientific notation with exp", () => {
      let s = sci("2 exp 3");
      expect(shows(s)).toBe("2.e+3");
      s = keys("equals", s);
      expect(shows(s)).toBe("2,000");
      expect(deg("2.5 exp 3 neg equals")).toBe("0.0025");
      expect(shows(sci("2 exp"))).toBe("2.e+0");
    });

    it("switches to exponent form with F-E", () => {
      let s = sci("1234 equals fe");
      expect(shows(s)).toBe("1.234e+3");
      s = press(s, "fe");
      expect(shows(s)).toBe("1,234");
    });

    it("uses exponent form only when a number does not fit", () => {
      expect(deg("1 div 7 equals")).toBe("0.1428571428571429");
      expect(deg("1 div 700 equals")).toBe("0.0014285714285714");
      expect(deg("1 div 7000 equals")).toBe("1.428571428571429e-4");
      expect(deg("0.0001 add 0 equals")).toBe("0.0001");
      expect(deg("2 pow 64 equals")).toBe("1.844674407370955e+19");
    });

    it("computes with about 32 digits", () => {
      // 1/3 × 3 − 1 is not exactly 0 with 32 digits, as in Windows, but sin(30°) is exactly 0.5.
      expect(deg("1 div 3 mul 3 sub 1 equals")).toBe("-1.e-32");
      expect(deg("30 sin sub 0.5 equals")).toBe("0");
    });
  });
});
