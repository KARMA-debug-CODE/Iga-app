import { describe, expect, it } from "vitest";

import { safeUrl, sitePath } from "./safeUrl";

describe("safeUrl", () => {
  it.each([
    ["https://www.reb.rw/books/maths.pdf", "https://www.reb.rw/books/maths.pdf"],
    ["  http://elearning.reb.rw/x ", "http://elearning.reb.rw/x"],
    ["/api/files/resources/abc/", "/api/files/resources/abc/"],
  ])("keeps the web address %s", (value, expected) => {
    expect(safeUrl(value)).toBe(expected);
  });

  it.each([
    "javascript:alert(document.cookie)",
    " JaVaScRiPt:alert(1)",
    "java\tscript:alert(1)",
    "\u0000javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "blob:https://iga.rw/0b1c",
    "//evil.example/x",
    "/\\evil.example/x",
    "evil.example",
    "",
    null,
    undefined,
    42,
    { toString: () => "https://x.example" },
  ])("refuses %s", (value) => {
    expect(safeUrl(value)).toBeUndefined();
  });

  it("can insist on https", () => {
    expect(safeUrl("http://phet.colorado.edu/x", { httpsOnly: true })).toBeUndefined();
    expect(safeUrl("https://phet.colorado.edu/x", { httpsOnly: true })).toBe("https://phet.colorado.edu/x");
  });
});

describe("sitePath", () => {
  it("keeps only paths on this site", () => {
    expect(sitePath("/lessons/forces")).toBe("/lessons/forces");
    for (const value of ["javascript:alert(1)", "//evil.example", "/\\evil.example", "https://evil.example", 7, null]) {
      expect(sitePath(value)).toBeUndefined();
    }
  });
});
