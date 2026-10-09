import { expect, test } from "@playwright/test";

import { login } from "./helpers";

// The calculator page: Standard, Scientific and Programmer modes, keys and keyboard,
// history, memory and what stays in the browser.
test("student uses the calculator with keys and the keyboard", async ({ page }) => {
  await login(page, "aline");
  await page.goto("/calculator");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Calculator");
  const calc = page.getByRole("region", { name: "Calculator" });
  const display = calc.getByRole("status");
  const expression = calc.locator(".calc-expr");
  const key = (name) => calc.getByRole("button", { name, exact: true });
  async function chooseMode(name) {
    await calc.getByRole("button", { name: "Open navigation" }).click();
    await calc.getByRole("navigation", { name: "Calculator modes" }).getByRole("button", { name, exact: true }).click();
    await expect(calc.getByRole("heading", { level: 2 })).toHaveText(name);
  }
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
  await chooseMode("Scientific");
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
  await chooseMode("Programmer");
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
  await chooseMode("Standard");
  if (await showHistory.isVisible()) await showHistory.click();
  await expect(history.getByRole("button", { name: /0\.1 \+ 0\.2 =\s*0\.3$/ })).toBeVisible();
});
