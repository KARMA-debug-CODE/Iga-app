import { expect, test } from "@playwright/test";

import { login, logout } from "./helpers";

const PREMIUM_LESSON = "/lessons/s2-maths-linear-graphs";

async function registerStudent(page, firstName, { school, code } = {}) {
  await page.goto("/register");
  await page.getByLabel(/first name/i).fill(firstName);
  await page.getByLabel(/^username$/i).fill(`${firstName.toLowerCase()}${Date.now()}`);
  await page.getByLabel(/^password/i).fill("Murakoze-2026");
  await page.getByLabel("Grade").selectOption("S2");
  if (school) {
    await page.getByLabel(/search for your school/i).fill(school.slice(0, 5));
    await page.getByRole("button", { name: new RegExp(school) }).click();
    if (code) await page.getByLabel(/school code/i).fill(code);
  }
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(`Hi ${firstName}`);
}

test("a student who joins with the school code gets full access", async ({ page }) => {
  await login(page, "lkadmin", "Lycée de Kigali");
  const code = (await page.locator(".code-display").innerText()).trim();
  expect(code).toMatch(/^[A-Z2-9]{8}$/);
  await logout(page);

  await registerStudent(page, "Ineza", { school: "Lycée de Kigali", code });
  await expect(page.locator(".access-banner")).toHaveCount(0);
  await page.goto(PREMIUM_LESSON);
  await expect(page.locator(".katex").first()).toBeVisible();
  await expect(page.getByText(/part of the full iga library/i)).toHaveCount(0);
});

test("a student waiting for an unpaid school sees free lessons and locked ones", async ({ page }) => {
  await registerStudent(page, "Mugisha", { school: "APADE" });
  await expect(page.locator(".access-banner")).toContainText(/waiting for APADE/i);
  await page.goto(PREMIUM_LESSON);
  await expect(page.getByText(/part of the full iga library/i)).toBeVisible();
  await expect(page.locator(".katex")).toHaveCount(0);
  await page.goto("/lessons/s1-maths-integers"); // free for everyone
  await expect(page.locator(".katex").first()).toBeVisible();
});

test("APADE pays for the month and its students get full access", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Paying changes shared demo data, so it runs once.");
  await login(page, "samuel");
  await page.goto(PREMIUM_LESSON);
  await expect(page.getByText(/hasn't subscribed/i)).toBeVisible();
  await logout(page);

  await login(page, "apadeadmin", "APADE");
  await page.getByRole("link", { name: /subscribe now/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Subscription");
  await page.getByRole("button", { name: /pay now/i }).click();
  await page.getByRole("button", { name: /pay \(test\)/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/payment received/i);
  await page.getByRole("link", { name: /back to subscription/i }).click();
  await expect(page.getByRole("cell", { name: "Paid" }).first()).toBeVisible();
  await logout(page);

  await login(page, "samuel");
  await page.goto(PREMIUM_LESSON);
  await expect(page.locator(".katex").first()).toBeVisible();
});

test("the Iga team verifies a new school", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Verifying changes shared demo data, so it runs once.");
  await login(page, "gsadmin", "Almost there");
  await logout(page);

  await login(page, "admin");
  await page.goto("/admin");
  await page.getByRole("tab", { name: "Schools" }).click();
  await page.getByRole("button", { name: /GS Remera Catholique/ }).click();
  await page.getByRole("button", { name: /verify school/i }).click();
  await expect(page.getByText("Verified").first()).toBeVisible();
  await logout(page);

  await login(page, "gsadmin", "GS Remera Catholique");
  await expect(page.locator(".code-display")).toBeVisible();
});
