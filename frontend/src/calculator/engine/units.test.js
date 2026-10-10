import { describe, expect, it } from "vitest";

import { D } from "./decimal.js";
import { formatDecimal } from "./format.js";
import { CATEGORIES, CONVERTERS, alsoUnits, convert } from "./units.js";

/** Convert and show the result as the converter does (16 significant digits). */
const conv = (category, from, to, value) => formatDecimal(convert(category, from, to, new D(value)), { grouping: false });

describe("Converters", () => {
  it("has the Windows categories, without Currency", () => {
    expect(CONVERTERS).toEqual([
      "volume",
      "length",
      "weight",
      "temperature",
      "energy",
      "area",
      "speed",
      "time",
      "power",
      "data",
      "pressure",
      "angle",
    ]);
    for (const cat of Object.values(CATEGORIES)) {
      expect(cat.units).toContain(cat.pair[0]);
      expect(cat.units).toContain(cat.pair[1]);
      for (const unit of cat.also) expect(cat.units).toContain(unit);
    }
  });

  it("converts temperatures: 100 °C = 212 °F", () => {
    expect(conv("temperature", "C", "F", "100")).toBe("212");
    expect(conv("temperature", "F", "C", "212")).toBe("100");
    expect(conv("temperature", "F", "C", "-40")).toBe("-40");
    expect(conv("temperature", "C", "K", "0")).toBe("273.15");
    expect(conv("temperature", "K", "F", "0")).toBe("-459.67");
    expect(conv("temperature", "F", "C", "98.6")).toBe("37");
    expect(conv("temperature", "F", "C", "50")).toBe("10");
    expect(conv("temperature", "F", "C", "1")).toBe("-17.22222222222222");
  });

  it("converts lengths exactly: 1 mile = 1.609344 km", () => {
    expect(conv("length", "mi", "km", "1")).toBe("1.609344");
    expect(conv("length", "km", "mi", "1.609344")).toBe("1");
    expect(conv("length", "in", "cm", "1")).toBe("2.54");
    expect(conv("length", "ft", "m", "1")).toBe("0.3048");
    expect(conv("length", "m", "cm", "1.5")).toBe("150");
    expect(conv("length", "nmi", "m", "1")).toBe("1852");
    expect(conv("length", "km", "nm", "1")).toBe("1000000000000");
  });

  it("converts data with SI and binary prefixes: 1 KiB = 1024 bytes, 1 kB = 1000 bytes", () => {
    expect(conv("data", "KiB", "B", "1")).toBe("1024");
    expect(conv("data", "kB", "B", "1")).toBe("1000");
    expect(conv("data", "B", "bit", "1")).toBe("8");
    expect(conv("data", "GiB", "MiB", "1")).toBe("1024");
    expect(conv("data", "GB", "MB", "1")).toBe("1000");
    expect(conv("data", "GiB", "GB", "1")).toBe("1.073741824");
    expect(conv("data", "Mbit", "kB", "1")).toBe("125");
  });

  it("converts pressure: 1 atm = 101325 Pa", () => {
    expect(conv("pressure", "atm", "Pa", "1")).toBe("101325");
    expect(conv("pressure", "atm", "kPa", "1")).toBe("101.325");
    expect(conv("pressure", "bar", "hPa", "1")).toBe("1000");
    expect(conv("pressure", "atm", "mmHg", "1")).toBe("760");
    expect(conv("pressure", "psi", "Pa", "1")).toBe("6894.757293168361");
  });

  it("converts volume, weight, area, speed, time, energy, power and angle", () => {
    expect(conv("volume", "L", "mL", "1")).toBe("1000");
    expect(conv("volume", "galUS", "L", "1")).toBe("3.785411784");
    expect(conv("volume", "galUK", "L", "1")).toBe("4.54609");
    expect(conv("volume", "galUS", "in3", "1")).toBe("231");
    expect(conv("volume", "cupUS", "flozUS", "1")).toBe("8");
    expect(conv("volume", "tbspUS", "tspUS", "1")).toBe("3");
    expect(conv("volume", "galUK", "ptUK", "1")).toBe("8");
    expect(conv("weight", "lb", "kg", "1")).toBe("0.45359237");
    expect(conv("weight", "lb", "oz", "1")).toBe("16");
    expect(conv("weight", "st", "lb", "1")).toBe("14");
    expect(conv("weight", "t", "kg", "1")).toBe("1000");
    expect(conv("weight", "ct", "g", "5")).toBe("1");
    expect(conv("area", "ha", "m2", "1")).toBe("10000");
    expect(conv("area", "ac", "ft2", "1")).toBe("43560");
    expect(conv("area", "mi2", "ac", "1")).toBe("640");
    expect(conv("speed", "kmh", "ms", "36")).toBe("10");
    expect(conv("speed", "mph", "kmh", "1")).toBe("1.609344");
    expect(conv("speed", "kn", "kmh", "1")).toBe("1.852");
    expect(conv("time", "h", "min", "1.5")).toBe("90");
    expect(conv("time", "wk", "h", "1")).toBe("168");
    expect(conv("time", "yr", "d", "1")).toBe("365");
    expect(conv("energy", "kcal", "kJ", "1")).toBe("4.184");
    expect(conv("energy", "kWh", "J", "1")).toBe("3600000");
    expect(conv("energy", "ftlb", "J", "1")).toBe("1.3558179483314");
    expect(conv("power", "hp", "W", "1")).toBe("745.6998715822702");
    expect(conv("power", "kW", "W", "2.5")).toBe("2500");
    expect(conv("angle", "deg", "rad", "180")).toBe("3.141592653589793");
    expect(conv("angle", "rad", "deg", "1")).toBe("57.29577951308232");
    expect(conv("angle", "grad", "deg", "100")).toBe("90");
  });

  it("keeps the same unit unchanged and lists other units", () => {
    expect(conv("length", "m", "m", "12.5")).toBe("12.5");
    expect(alsoUnits("length", "m", "cm")).toEqual(["km", "ft", "in"]);
    expect(alsoUnits("length", "km", "ft")).toEqual(["in", "mm"]);
  });
});
