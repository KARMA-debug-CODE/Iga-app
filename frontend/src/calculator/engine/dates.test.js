import { describe, expect, it } from "vitest";

import {
  addMonths,
  addToDate,
  dateDifference,
  dayNumber,
  daysInMonth,
  fromDayNumber,
  isLeap,
  parseISO,
  toISO,
  today,
} from "./dates.js";

const d = (text) => parseISO(text);
const add = (text, amounts, sign = 1) => {
  const result = addToDate(d(text), amounts, sign);
  return result && toISO(result);
};
const diff = (a, b) => dateDifference(d(a), d(b));

describe("Date calculation", () => {
  it("knows leap years and month lengths", () => {
    expect([2024, 2000, 2023, 1900, 2100].map(isLeap)).toEqual([true, true, false, false, false]);
    expect(daysInMonth(2024, 2)).toBe(29);
    expect(daysInMonth(2025, 2)).toBe(28);
    expect(daysInMonth(2025, 4)).toBe(30);
    expect(daysInMonth(2025, 12)).toBe(31);
  });

  it("numbers days without time zones", () => {
    expect(dayNumber({ y: 1970, m: 1, d: 1 })).toBe(0);
    expect(dayNumber({ y: 2000, m: 3, d: 1 })).toBe(11017);
    expect(fromDayNumber(11017)).toEqual({ y: 2000, m: 3, d: 1 });
    // Round trip across the whole range, including years before 100 (where Date.UTC goes wrong).
    for (const text of ["0001-01-01", "0099-12-31", "1600-02-29", "2024-02-29", "9999-12-31"]) {
      expect(toISO(fromDayNumber(dayNumber(d(text))))).toBe(text);
    }
  });

  it("reads and writes date-box values", () => {
    expect(d("2026-10-09")).toEqual({ y: 2026, m: 10, d: 9 });
    expect(d("2025-02-29")).toBeNull();
    expect(d("2026-13-01")).toBeNull();
    expect(d("")).toBeNull();
    expect(d("0000-01-01")).toBeNull();
    expect(toISO({ y: 5, m: 3, d: 7 })).toBe("0005-03-07");
    expect(today(new Date(2026, 9, 9, 23, 30))).toEqual({ y: 2026, m: 10, d: 9 });
  });

  it("adds a month at a month end: 31 Jan + 1 month is the last day of February", () => {
    expect(add("2025-01-31", { months: 1 })).toBe("2025-02-28");
    expect(add("2024-01-31", { months: 1 })).toBe("2024-02-29");
    expect(add("2025-03-31", { months: 1 })).toBe("2025-04-30");
    expect(add("2025-01-31", { months: 2 })).toBe("2025-03-31");
    expect(toISO(addMonths({ y: 2025, m: 11, d: 30 }, 3))).toBe("2026-02-28");
    expect(toISO(addMonths({ y: 2025, m: 1, d: 15 }, -1))).toBe("2024-12-15");
  });

  it("adds and subtracts years, months and days", () => {
    expect(add("2024-02-29", { years: 1 })).toBe("2025-02-28");
    expect(add("2024-02-29", { years: 4 })).toBe("2028-02-29");
    expect(add("2026-10-09", { days: 100 })).toBe("2027-01-17");
    expect(add("2024-02-28", { days: 1 })).toBe("2024-02-29");
    expect(add("2025-02-28", { days: 1 })).toBe("2025-03-01");
    expect(add("2026-10-09", { years: 1, months: 2, days: 3 })).toBe("2027-12-12");
    expect(add("2026-03-31", { months: 1 }, -1)).toBe("2026-02-28");
    expect(add("2026-01-01", { days: 1 }, -1)).toBe("2025-12-31");
    expect(add("2026-10-09", { years: 1, months: 1, days: 10 }, -1)).toBe("2025-08-30");
  });

  it("refuses dates outside years 1 to 9999", () => {
    expect(add("9999-12-31", { days: 1 })).toBeNull();
    expect(add("0001-01-01", { days: 1 }, -1)).toBeNull();
    expect(add("9000-01-01", { years: 999 })).toBe("9999-01-01");
    expect(add("9500-01-01", { years: 999 })).toBeNull();
  });

  it("finds the difference in years, months, weeks and days", () => {
    expect(diff("2026-10-09", "2026-10-09")).toEqual({ years: 0, months: 0, weeks: 0, days: 0, totalDays: 0 });
    expect(diff("2026-10-09", "2026-10-10")).toMatchObject({ days: 1, totalDays: 1 });
    expect(diff("2000-01-01", "2026-10-09")).toEqual({ years: 26, months: 9, weeks: 1, days: 1, totalDays: 9778 });
    // The order of the dates does not matter.
    expect(diff("2026-10-09", "2000-01-01")).toEqual(diff("2000-01-01", "2026-10-09"));
    expect(diff("2025-01-01", "2026-01-01")).toMatchObject({ years: 1, months: 0, weeks: 0, days: 0, totalDays: 365 });
    expect(diff("2024-01-01", "2025-01-01").totalDays).toBe(366);
  });

  it("counts months on the calendar at month ends", () => {
    expect(diff("2025-01-31", "2025-02-28")).toMatchObject({ months: 1, weeks: 0, days: 0, totalDays: 28 });
    expect(diff("2025-01-31", "2025-02-27")).toMatchObject({ months: 0, weeks: 3, days: 6 });
    expect(diff("2025-01-31", "2025-03-31")).toMatchObject({ months: 2, days: 0 });
    expect(diff("2023-02-28", "2023-03-31")).toMatchObject({ months: 1, weeks: 0, days: 3 });
    expect(diff("2024-02-29", "2025-02-28")).toMatchObject({ years: 1, months: 0, days: 0, totalDays: 365 });
  });
});
