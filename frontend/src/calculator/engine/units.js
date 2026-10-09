// Unit converters, like the Windows calculator (without Currency, which needs live rates).
// Every factor is exact, as defined by the SI and by international agreement (the inch is
// 2.54 cm, the pound 0.45359237 kg, the US gallon 231 cubic inches, the standard
// atmosphere 101325 Pa), and the arithmetic uses decimal.js: 1 mile = 1.609344 km exactly.
import { D, PI, fin, guarded } from "./decimal.js";

/** "a*b/c" -> a Decimal, so derived units are written as their definitions. */
function exact(text) {
  const parts = text.split(/([*/])/);
  let v = new D(parts[0]);
  for (let i = 1; i < parts.length; i += 2) v = parts[i] === "*" ? v.times(parts[i + 1]) : v.div(parts[i + 1]);
  return v;
}

const GALLON_US = "3.785411784"; // litres
const GALLON_UK = "4.54609"; // litres
const POUND = "0.45359237"; // kilograms
const POUND_FORCE = `${POUND}*9.80665`; // newtons
const FOOT_POUND = `0.3048*${POUND_FORCE}`; // joules
const BTU = "1055.05585262"; // joules (International Table)

// Each category: its units as [id, size in the category's base unit], the two units shown
// first, and a few others listed under "About equal to".
const DEFINITIONS = {
  volume: {
    units: [
      ["mL", "0.001"],
      ["cm3", "0.001"],
      ["L", "1"],
      ["m3", "1000"],
      ["tspUS", `${GALLON_US}/768`],
      ["tbspUS", `${GALLON_US}/256`],
      ["flozUS", `${GALLON_US}/128`],
      ["cupUS", `${GALLON_US}/16`],
      ["ptUS", `${GALLON_US}/8`],
      ["qtUS", `${GALLON_US}/4`],
      ["galUS", GALLON_US],
      ["in3", "0.016387064"],
      ["ft3", "28.316846592"],
      ["yd3", "764.554857984"],
      ["flozUK", `${GALLON_UK}/160`],
      ["ptUK", `${GALLON_UK}/8`],
      ["qtUK", `${GALLON_UK}/4`],
      ["galUK", GALLON_UK],
    ],
    pair: ["L", "mL"],
    also: ["m3", "cupUS", "galUS", "L"],
  },
  length: {
    units: [
      ["nm", "1e-9"],
      ["um", "1e-6"],
      ["mm", "0.001"],
      ["cm", "0.01"],
      ["m", "1"],
      ["km", "1000"],
      ["in", "0.0254"],
      ["ft", "0.3048"],
      ["yd", "0.9144"],
      ["mi", "1609.344"],
      ["nmi", "1852"],
    ],
    pair: ["m", "cm"],
    also: ["km", "ft", "in", "mm"],
  },
  weight: {
    units: [
      ["ct", "0.0002"],
      ["mg", "0.000001"],
      ["cg", "0.00001"],
      ["dg", "0.0001"],
      ["g", "0.001"],
      ["dag", "0.01"],
      ["hg", "0.1"],
      ["kg", "1"],
      ["t", "1000"],
      ["oz", `${POUND}/16`],
      ["lb", POUND],
      ["st", `${POUND}*14`],
      ["tonUS", `${POUND}*2000`],
      ["tonUK", `${POUND}*2240`],
    ],
    pair: ["kg", "g"],
    also: ["t", "lb", "oz", "kg"],
  },
  temperature: {
    // Not a simple factor: see TEMPERATURE below.
    units: [["C"], ["F"], ["K"]],
    pair: ["C", "F"],
    also: ["K", "C", "F"],
    signed: true,
  },
  energy: {
    units: [
      ["eV", "1.602176634e-19"],
      ["J", "1"],
      ["kJ", "1000"],
      ["cal", "4.184"],
      ["kcal", "4184"],
      ["ftlb", FOOT_POUND],
      ["btu", BTU],
      ["kWh", "3600000"],
    ],
    pair: ["kJ", "kcal"],
    also: ["J", "kWh", "cal", "kJ"],
  },
  area: {
    units: [
      ["mm2", "0.000001"],
      ["cm2", "0.0001"],
      ["m2", "1"],
      ["ha", "10000"],
      ["km2", "1000000"],
      ["in2", "0.00064516"],
      ["ft2", "0.09290304"],
      ["yd2", "0.83612736"],
      ["ac", "4046.8564224"],
      ["mi2", "2589988.110336"],
    ],
    pair: ["m2", "cm2"],
    also: ["ha", "km2", "ft2", "m2"],
  },
  speed: {
    units: [
      ["cms", "0.01"],
      ["ms", "1"],
      ["kmh", "1000/3600"],
      ["fts", "0.3048"],
      ["mph", "1609.344/3600"],
      ["kn", "1852/3600"],
    ],
    pair: ["kmh", "ms"],
    also: ["mph", "kn", "ms", "kmh"],
  },
  time: {
    units: [
      ["us", "0.000001"],
      ["msec", "0.001"],
      ["s", "1"],
      ["min", "60"],
      ["h", "3600"],
      ["d", "86400"],
      ["wk", "604800"],
      ["yr", "31536000"],
    ],
    pair: ["h", "min"],
    also: ["s", "d", "wk", "h"],
  },
  power: {
    units: [
      ["W", "1"],
      ["kW", "1000"],
      ["hp", `550*${FOOT_POUND}`],
      ["ftlbmin", `${FOOT_POUND}/60`],
      ["btumin", `${BTU}/60`],
    ],
    pair: ["kW", "W"],
    also: ["hp", "W", "kW"],
  },
  data: {
    units: [
      ["bit", "1"],
      ["nibble", "4"],
      ["B", "8"],
      ["kbit", "1000"],
      ["Kibit", "1024"],
      ["kB", "8000"],
      ["KiB", "8192"],
      ["Mbit", "1e6"],
      ["Mibit", "1048576"],
      ["MB", "8e6"],
      ["MiB", "8388608"],
      ["Gbit", "1e9"],
      ["Gibit", "1073741824"],
      ["GB", "8e9"],
      ["GiB", "8589934592"],
      ["Tbit", "1e12"],
      ["Tibit", "1099511627776"],
      ["TB", "8e12"],
      ["TiB", "8796093022208"],
      ["Pbit", "1e15"],
      ["Pibit", "1125899906842624"],
      ["PB", "8e15"],
      ["PiB", "9007199254740992"],
    ],
    pair: ["GB", "MB"],
    also: ["GiB", "kB", "B", "MiB"],
  },
  pressure: {
    units: [
      ["atm", "101325"],
      ["bar", "100000"],
      ["kPa", "1000"],
      ["hPa", "100"],
      // The torr (1/760 atm), within 0.00002 % of the mercury millimetre: 1 atm = 760 mmHg, as in textbooks.
      ["mmHg", "101325/760"],
      ["Pa", "1"],
      ["psi", `${POUND_FORCE}/0.00064516`],
    ],
    pair: ["atm", "kPa"],
    also: ["Pa", "bar", "mmHg", "psi"],
  },
  angle: {
    units: [
      ["deg", "1"],
      ["rad", "rad"],
      ["grad", "0.9"],
    ],
    pair: ["deg", "rad"],
    also: ["grad", "deg", "rad"],
    signed: true,
  },
};

const ZERO_CELSIUS = new D("273.15");

// Temperatures through kelvin; multiply before dividing so 212 °F is exactly 100 °C.
const TEMPERATURE = {
  C: { toK: (v) => v.plus(ZERO_CELSIUS), fromK: (k) => k.minus(ZERO_CELSIUS) },
  F: {
    toK: (v) => v.minus(32).times(5).div(9).plus(ZERO_CELSIUS),
    fromK: (k) => k.minus(ZERO_CELSIUS).times(9).div(5).plus(32),
  },
  K: { toK: (v) => v, fromK: (k) => k },
};

export const CATEGORIES = Object.fromEntries(
  Object.entries(DEFINITIONS).map(([id, def]) => [
    id,
    {
      id,
      units: def.units.map(([unit]) => unit),
      factors: Object.fromEntries(
        def.units
          .filter(([, size]) => size)
          .map(([unit, size]) => [unit, size === "rad" ? new D(180).div(PI) : exact(size)]),
      ),
      pair: def.pair,
      also: def.also,
      signed: Boolean(def.signed),
    },
  ]),
);

export const CONVERTERS = Object.keys(CATEGORIES);

export function hasUnit(category, unit) {
  return Boolean(CATEGORIES[category]?.units.includes(unit));
}

/** Convert a Decimal from one unit to another of the same category (32 significant digits kept). */
export function convert(category, from, to, value) {
  const cat = CATEGORIES[category];
  if (!cat || !hasUnit(category, from) || !hasUnit(category, to)) throw new Error(`unknown unit ${category}:${from}:${to}`);
  if (from === to) return fin(value);
  return guarded(() => {
    if (category === "temperature") return fin(TEMPERATURE[to].fromK(TEMPERATURE[from].toK(value)));
    return fin(value.times(cat.factors[from]).div(cat.factors[to]));
  });
}

/** Up to `count` other units to show the value in, leaving out the two being converted. */
export function alsoUnits(category, from, to, count = 3) {
  const cat = CATEGORIES[category];
  return cat.also.filter((unit) => unit !== from && unit !== to).slice(0, count);
}
