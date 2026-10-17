import { expect, test } from "@playwright/test";

import { login } from "./helpers";

test("landing page switches language", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Every subject");
  await page.getByRole("button", { name: "Français" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Toutes les matières");
  await page.getByRole("button", { name: "English" }).click();
});

test("new student registers, reads a lesson, uses a lab and earns XP", async ({ page }) => {
  const username = `kid${Date.now()}`;
  await page.goto("/register");
  await page.getByLabel(/first name/i).fill("Keza");
  await page.getByLabel(/^username$/i).fill(username);
  await page.getByLabel(/^password/i).fill("Murakoze-2026");
  await page.getByLabel("Grade").selectOption("S1");
  await page.getByLabel(/i have read and accept/i).check();
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Hi Keza");

  await page.goto("/lessons/s1-maths-integers");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Integers and the number line");
  await expect(page.locator(".katex").first()).toBeVisible();
  await page.getByRole("button", { name: /mark as complete/i }).click();
  await expect(page.getByRole("status").filter({ hasText: "XP" })).toBeVisible();
  await expect(page.getByText("Completed").first()).toBeVisible();

  await page.goto("/labs/ohms-law-lab");
  await expect(page.getByRole("img", { name: /circuit/i })).toBeVisible();
  await expect(page.getByText(/0\.6 A/).first()).toBeVisible(); // 6 V / 10 Ω
});

test("student takes a practice quiz with instant feedback", async ({ page }) => {
  await login(page, "divine");
  await page.goto("/practice");
  const card = page.locator(".card", { hasText: "Straight-line graphs — practice" });
  await card.getByRole("button", { name: /start|try again/i }).click();
  await expect(page).toHaveURL(/\/attempts\/\d+/);

  // Questions are shuffled, so answer the first one whatever its type, then check it.
  await expect(page.getByText(/question 1 of/i)).toBeVisible();
  const radio = page.locator(".option input").first();
  if (await radio.count()) await radio.check();
  else await page.getByLabel(/your answer/i).fill("2");
  await page.getByRole("button", { name: /check answer/i }).click();
  await expect(page.locator(".feedback")).toContainText(/correct|not quite|partly/i);

  page.on("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: /^submit/i }).first().click();
  await expect(page.getByText(/your score/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: /review your answers/i })).toBeVisible();
});

test("search finds lessons and labs", async ({ page }) => {
  await login(page, "grace");
  await page.getByRole("searchbox").fill("ohm");
  await page.getByRole("searchbox").press("Enter");
  await expect(page.getByRole("link", { name: /Ohm's law/i }).first()).toBeVisible();
});
