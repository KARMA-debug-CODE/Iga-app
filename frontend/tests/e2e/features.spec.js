import { expect, test } from "@playwright/test";

import { login, logout } from "./helpers";

test("AI tutor answers questions about a lesson", async ({ page }) => {
  // The E2E server has no Anthropic key, so the tutor endpoints are mocked here;
  // the backend side is covered by tests/test_tutor.py.
  await page.route("**/api/tutor/status/", (route) => route.fulfill({ json: { enabled: true } }));
  let asked = null;
  await page.route("**/api/tutor/ask/", async (route) => {
    asked = route.request().postDataJSON();
    await route.fulfill({ json: { reply: "The **gradient** is the number in front of $x$: here it is $3$." } });
  });

  await login(page, "aline");
  await page.goto("/lessons/s2-maths-linear-graphs");
  await page.getByRole("button", { name: /ask the ai tutor/i }).click();
  const panel = page.getByRole("region", { name: /tutor/i });
  await panel.getByRole("textbox").fill("What is the gradient of y = 3x + 2?");
  await panel.getByRole("button", { name: /^send$/i }).click();
  await expect(panel.getByText(/number in front of/)).toBeVisible();
  await expect(panel.locator(".katex").first()).toBeVisible();
  expect(asked.lesson).toBeTruthy();
  expect(asked.message).toContain("gradient");
});

test("a parent links to their child with a code and sees progress", async ({ page }) => {
  await login(page, "eric");
  await page.goto("/profile");
  await page.getByRole("button", { name: /create a code for my parent/i }).click();
  const code = (await page.locator(".code-display").innerText()).trim();
  expect(code).toMatch(/^[A-Z0-9]{8}$/);
  await logout(page);

  await login(page, "parent");
  await page.getByLabel(/code from your child/i).fill(code);
  await page.getByRole("button", { name: /^link$/i }).click();
  const card = page.locator("a.card", { hasText: /Eric/ });
  await expect(card).toBeVisible();
  await card.click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Eric/);
});

test("Python runs in the browser", async ({ page }) => {
  await login(page, "aline");
  await page.goto("/playground");
  await page.getByRole("tab", { name: /python/i }).click();
  await page.getByLabel("Python code editor").fill("total = sum(range(1, 11))\nprint('Total:', total)");
  await page.getByRole("button", { name: /run/i }).click();
  await expect(page.locator(".python-output")).toContainText("Total: 55", { timeout: 45_000 });
});

test("teacher opens results analysis for a class quiz", async ({ page }) => {
  await login(page, "teacher");
  await page.goto("/classes");
  await page.getByRole("link", { name: /S2 Mathematics — Stream A/ }).click();
  await page.getByRole("link", { name: /results analysis/i }).first().click();
  await expect(page.getByText(/students attempted/i)).toBeVisible();
  await expect(page.getByText(/score distribution|no one in this group has finished/i)).toBeVisible();
});

test("teacher creates accounts from a list and the student sets a password", async ({ page }, testInfo) => {
  const surname = `Test${testInfo.project.name}${Date.now()}`;
  await login(page, "teacher");
  await page.goto("/classes");
  await page.getByRole("link", { name: /S2 Mathematics — Stream A/ }).click();
  await page.getByRole("tab", { name: /students/i }).click();
  await page.getByText(/add students from a list/i).click();
  await page.getByRole("textbox", { name: /add students from a list/i }).fill(`first_name,last_name\nKeza,${surname}\n`);
  await page.getByRole("button", { name: /check the list/i }).click();
  await page.getByRole("button", { name: /create 1 accounts/i }).click();
  await expect(page.getByText(/shown only once/i)).toBeVisible();
  const row = page.locator("tbody tr", { hasText: surname });
  const username = (await row.locator(".small").innerText()).replace("@", "").trim();
  const temporary = (await row.locator("code").innerText()).trim();
  await logout(page);

  await page.goto("/login");
  await page.getByLabel(/username or email/i).fill(username);
  await page.getByLabel(/^password$/i).fill(temporary);
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page.getByText(/temporary password/i).first()).toBeVisible();
  await page.getByLabel(/temporary password/i).fill(temporary);
  await page.getByLabel(/^new password$/i).fill("Nkunda-imibare-2026");
  await page.getByLabel(/new password again/i).fill("Nkunda-imibare-2026");
  await page.getByRole("button", { name: /save my password/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/hi keza/i);
});
