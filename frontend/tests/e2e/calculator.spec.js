import { expect, test } from "@playwright/test";

import { login } from "./helpers";

// The calculator page: Standard, Scientific and Programmer modes, keys and keyboard,
// history, memory and what stays in the browser; then Graphing, Date calculation and
// the unit converters.

/** Pick a mode from the calculator's menu, as in Windows. */
async function chooseMode(calc, name) {
  await calc.getByRole("button", { name: "Open navigation" }).click();
  await calc.getByRole("navigation", { name: "Calculator modes" }).getByRole("button", { name, exact: true }).click();
  await expect(calc.getByRole("heading", { level: 2 })).toHaveText(name);
}

test("student uses the calculator with keys and the keyboard", async ({ page }) => {
  await login(page, "aline");
  await page.goto("/calculator");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Calculator");
  const calc = page.getByRole("region", { name: "Calculator" });
  const display = calc.getByRole("status");
  const expression = calc.locator(".calc-expr");
  const key = (name) => calc.getByRole("button", { name, exact: true });
  async function type(keys) {
    for (const k of keys) await page.keyboard.press(k);
  }
  await expect(calc.getByRole("heading", { level: 2 })).toHaveText("Standard");

  // On-screen keys: decimals are exact.
  for (const name of ["0", "Decimal separator", "1", "Plus", "0", "Decimal separator", "2", "Equals"]) await key(name).click();
  await expect(display).toHaveText("Display is 0.3");
  await expect(expression).toHaveText("Expression is 0.1 + 0.2 =");

  // Keyboard, Standard mode: each operator is worked out at once, like Windows.
  await type(["Escape", "2", "+", "3", "*"]);
  await expect(display).toHaveText("Display is 5");
  await type(["4", "Enter"]);
  await expect(display).toHaveText("Display is 20");
  await expect(expression).toHaveText("Expression is (2 + 3) × 4 =");
  await type(["Enter"]); // = again repeats "× 4"
  await expect(display).toHaveText("Display is 80");
  await type(["2", "0", "0", "+", "1", "0", "%"]);
  await expect(expression).toHaveText("Expression is 200 + 20");
  await type(["="]);
  await expect(display).toHaveText("Display is 220");
  await type(["9", "@"]);
  await expect(display).toHaveText("Display is 3");
  await type(["1", "2", "3", "Backspace"]);
  await expect(display).toHaveText("Display is 12");

  // Dividing by zero locks the operators until C (Escape).
  await type(["Escape", "1", "/", "0", "Enter"]);
  await expect(display).toHaveText("Display is Cannot divide by zero");
  await expect(key("Plus")).toHaveAttribute("aria-disabled", "true");
  await type(["+"]);
  await expect(display).toHaveText("Display is Cannot divide by zero");
  await type(["Escape"]);
  await expect(display).toHaveText("Display is 0");
  await expect(key("Plus")).not.toHaveAttribute("aria-disabled", "true");

  // Memory: MS then MR.
  await type(["4", "2"]);
  await key("Memory store").click();
  await type(["Escape"]);
  await key("Memory recall").click();
  await expect(display).toHaveText("Display is 42");

  // Paste a number written with grouping.
  await page.evaluate(() => {
    const data = new DataTransfer();
    data.setData("text/plain", "1,234.5");
    document.dispatchEvent(new ClipboardEvent("paste", { clipboardData: data, bubbles: true }));
  });
  await expect(display).toHaveText("Display is 1,234.5");

  // History: reuse an earlier result (the panel opens over the keys on phones).
  const showHistory = calc.getByRole("button", { name: "Show history" });
  if (await showHistory.isVisible()) await showHistory.click();
  const history = calc.getByRole("complementary");
  await history.getByRole("tab", { name: "History" }).click();
  await history.getByRole("button", { name: /\(2 \+ 3\) × 4 =\s*20$/ }).click();
  await expect(display).toHaveText("Display is 20");
  await expect(expression).toHaveText("Expression is (2 + 3) × 4 =");

  // Scientific: precedence, brackets and exact trigonometry in degrees.
  await chooseMode(calc, "Scientific");
  await type(["Escape", "2", "+", "3", "*", "4", "Enter"]);
  await expect(display).toHaveText("Display is 14");
  await type(["(", "2", "+", "3", ")", "*", "4", "Enter"]);
  await expect(display).toHaveText("Display is 20");
  await type(["3", "0"]);
  await key("Sine").click();
  await expect(display).toHaveText("Display is 0.5");
  await expect(expression).toHaveText("Expression is sin(30°)");
  await type(["9", "0"]);
  await key("Tangent").click();
  await expect(display).toHaveText("Display is Invalid input");
  await type(["Escape", "5", "!"]);
  await expect(display).toHaveText("Display is 120");
  await calc.getByRole("button", { name: /^Angle unit: Degrees/ }).click();
  await expect(calc.getByRole("button", { name: /^Angle unit: Radians/ })).toHaveText("RAD");

  // Programmer: HEX DEC OCT BIN together; A-F only in HEX.
  await chooseMode(calc, "Programmer");
  await expect(key("A")).toHaveAttribute("aria-disabled", "true");
  await calc.getByRole("radio", { name: /^Hexadecimal/ }).check();
  await expect(key("A")).not.toHaveAttribute("aria-disabled", "true");
  await type(["Escape", "f", "f", "+", "1", "Enter"]);
  await expect(display).toHaveText("Display is 100");
  await expect(calc.getByRole("radio", { name: /^Decimal \(DEC\) 256$/ })).toBeVisible();
  await expect(calc.getByRole("radio", { name: /^Binary \(BIN\) 1 0000 0000$/ })).toBeVisible();
  // Two's complement in a byte: -1 is FF.
  for (let i = 0; i < 3; i += 1) await calc.getByRole("button", { name: /^Word size:/ }).click();
  await expect(calc.getByRole("button", { name: /^Word size: BYTE/ })).toBeVisible();
  await type(["Escape", "1"]);
  await key("Positive negative").click();
  await expect(display).toHaveText("Display is FF");
  await expect(calc.getByRole("radio", { name: /^Decimal \(DEC\) -1$/ })).toBeVisible();
  await key("Bitwise AND").click();
  await type(["F", "Enter"]);
  await expect(display).toHaveText("Display is F");

  // The mode and the history stay in this browser.
  await page.reload();
  await expect(calc.getByRole("heading", { level: 2 })).toHaveText("Programmer");
  await chooseMode(calc, "Standard");
  if (await showHistory.isVisible()) await showHistory.click();
  await expect(history.getByRole("button", { name: /0\.1 \+ 0\.2 =\s*0\.3$/ })).toBeVisible();
});

test("student graphs functions, works out dates and converts units", async ({ page }) => {
  await login(page, "aline");
  await page.goto("/calculator");
  const calc = page.getByRole("region", { name: "Calculator" });
  const menu = calc.getByRole("navigation", { name: "Calculator modes" });

  // Every mode is in the menu, without Currency.
  await calc.getByRole("button", { name: "Open navigation" }).click();
  for (const name of ["Graphing", "Date calculation", "Volume", "Weight and mass", "Energy", "Data", "Angle"]) {
    await expect(menu.getByRole("button", { name, exact: true })).toBeEnabled();
  }
  await expect(menu.getByRole("button", { name: "Currency" })).toHaveCount(0);
  await page.keyboard.press("Escape");

  // Graphing: type a function and trace it.
  await chooseMode(calc, "Graphing");
  const graph = calc.getByRole("img", { name: /^(Graph of|Empty graph)/ });
  const f1 = calc.getByRole("textbox", { name: "Function 1, y equals" });
  await f1.fill("x^2 - 2");
  await expect(graph).toHaveAttribute("aria-label", "Graph of y = x^2 - 2.");

  // The zoom buttons redraw the graph; Reset view goes back.
  const pixels = () => graph.evaluate((canvas) => canvas.toDataURL());
  const before = await pixels();
  await calc.getByRole("button", { name: "Zoom in" }).click();
  await expect.poll(pixels).not.toBe(before);
  await calc.getByRole("button", { name: "Reset view" }).click();
  await expect.poll(pixels).toBe(before);

  // Tap the parabola at x = 1, where y = -1 (the default window has x from -10 to 10, equal units).
  const box = await graph.boundingBox();
  const unit = Math.max(20 / box.width, 12 / box.height);
  await graph.click({ position: { x: box.width / 2 + 1 / unit, y: box.height / 2 + 1 / unit } });
  const readout = calc.locator(".calc-graph-readout");
  await expect(readout).toHaveText(/^f1: \(/);
  const [x, y] = ((await readout.textContent()).match(/[−-]?\d+(\.\d+)?/g) || []).slice(1).map((v) => Number(v.replace("−", "-")));
  expect(Math.abs(x - 1)).toBeLessThan(0.05);
  expect(Math.abs(y + 1)).toBeLessThan(0.1);

  // A second function with the maths keys, a third with a mistake.
  await calc.getByRole("button", { name: "Add a function" }).click();
  const f2 = calc.getByRole("textbox", { name: "Function 2, y equals" });
  await expect(f2).toBeFocused();
  await calc.getByRole("button", { name: "Insert Tangent" }).click();
  await page.keyboard.type("x)");
  await expect(f2).toHaveValue("tan(x)");
  await expect(graph).toHaveAttribute("aria-label", "Graph of y = x^2 - 2; y = tan(x).");
  await calc.getByRole("button", { name: "Add a function" }).click();
  await calc.getByRole("textbox", { name: "Function 3, y equals" }).fill("sqrt(x");
  await f1.focus();
  await expect(calc.getByText("A bracket is not closed.")).toBeVisible();
  // The colour chip shows or hides its function.
  const show1 = calc.getByRole("button", { name: "Show function 1" });
  await expect(show1).toHaveAttribute("aria-pressed", "true");
  await show1.click();
  await expect(show1).toHaveAttribute("aria-pressed", "false");
  await expect(graph).toHaveAttribute("aria-label", "Graph of y = tan(x).");
  await calc.getByRole("button", { name: "Angle unit: Radians. Press to change it." }).click();
  await expect(calc.getByRole("button", { name: "Angle unit: Degrees. Press to change it." })).toHaveText("DEG");

  // Date calculation: a leap year, and a month end.
  await chooseMode(calc, "Date calculation");
  await calc.getByLabel("From", { exact: true }).fill("2024-01-31");
  await calc.getByLabel("To", { exact: true }).fill("2024-03-01");
  await expect(calc.locator(".calc-date-main")).toHaveText("1 month, 1 day");
  await expect(calc.locator(".calc-date-detail")).toHaveText("30 days");
  await calc.getByLabel("Calculation").selectOption({ label: "Add or subtract days" });
  await calc.getByLabel("From", { exact: true }).fill("2024-02-29");
  await calc.getByLabel("Years", { exact: true }).fill("1");
  await expect(calc.locator(".calc-date-main")).toHaveText("Friday 28 February 2025");
  await calc.getByLabel("Subtract").check();
  await calc.getByLabel("Years", { exact: true }).fill("0");
  await calc.getByLabel("Days", { exact: true }).fill("1");
  await expect(calc.locator(".calc-date-main")).toHaveText("Wednesday 28 February 2024");

  // Converters: exact factors, linked boxes and the swap button.
  await chooseMode(calc, "Length");
  await calc.getByRole("combobox", { name: "Convert from" }).selectOption("mi");
  await calc.getByRole("combobox", { name: "Convert to" }).selectOption("km");
  const key = (name) => calc.getByRole("button", { name, exact: true });
  await key("1").click();
  await expect(calc.getByRole("textbox", { name: "Value in Kilometres" })).toHaveValue("1.609344");
  await calc.getByRole("button", { name: "Swap units" }).click();
  await expect(calc.getByRole("textbox", { name: "Value in Kilometres" })).toHaveValue("1");
  await expect(calc.getByRole("textbox", { name: "Value in Miles" })).toHaveValue("0.621371192237334");
  // Typing in the other box converts the other way.
  await calc.getByRole("textbox", { name: "Value in Miles" }).fill("26.2");
  await expect(calc.getByRole("textbox", { name: "Value in Kilometres" })).toHaveValue("42.1648128");
  // A length cannot be negative (the +/- key is off here too).
  await calc.getByRole("textbox", { name: "Value in Miles" }).fill("-3");
  await expect(calc.getByRole("textbox", { name: "Value in Miles" })).toHaveValue("3");
  await expect(key("Positive negative")).toHaveAttribute("aria-disabled", "true");

  await chooseMode(calc, "Temperature");
  await page.keyboard.type("100");
  await expect(calc.getByRole("textbox", { name: "Value in Celsius" })).toHaveValue("100");
  await expect(calc.getByRole("textbox", { name: "Value in Fahrenheit" })).toHaveValue("212");
  // Temperatures can be negative: F9 is +/-, as in the other modes.
  await page.keyboard.press("Escape");
  await page.keyboard.type("40");
  await page.keyboard.press("F9");
  await expect(calc.getByRole("textbox", { name: "Value in Fahrenheit" })).toHaveValue("-40");

  await chooseMode(calc, "Data");
  await calc.getByRole("combobox", { name: "Convert from" }).selectOption("KiB");
  await calc.getByRole("combobox", { name: "Convert to" }).selectOption("B");
  await calc.getByRole("textbox", { name: "Value in Kibibytes" }).fill("1");
  await expect(calc.getByRole("textbox", { name: "Value in Bytes" })).toHaveValue("1,024");
  await calc.getByRole("combobox", { name: "Convert from" }).selectOption("kB");
  await expect(calc.getByRole("textbox", { name: "Value in Bytes" })).toHaveValue("1,000");

  await chooseMode(calc, "Pressure");
  await calc.getByRole("combobox", { name: "Convert to" }).selectOption("Pa");
  await calc.getByRole("textbox", { name: "Value in Atmospheres" }).fill("1");
  await expect(calc.getByRole("textbox", { name: "Value in Pascals" })).toHaveValue("101,325");

  // The last mode and the graph stay in this browser.
  await page.reload();
  await expect(calc.getByRole("heading", { level: 2 })).toHaveText("Pressure");
  await chooseMode(calc, "Graphing");
  await expect(calc.getByRole("textbox", { name: "Function 2, y equals" })).toHaveValue("tan(x)");
  await expect(calc.getByRole("button", { name: "Angle unit: Degrees. Press to change it." })).toBeVisible();

  // A keypad mode saved as the last mode also gives its keys.
  await page.evaluate(() => localStorage.setItem("iga.calc.settings", JSON.stringify({ view: "scientific", mode: "standard" })));
  await page.reload();
  await expect(calc.getByRole("heading", { level: 2 })).toHaveText("Scientific");
  await expect(key("Sine")).toBeVisible();
});
