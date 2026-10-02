import { expect, test } from "@playwright/test";

import { login, logout } from "./helpers";

test("teacher creates a class and a student joins it with the code", async ({ page }, testInfo) => {
  const name = `S1 Physics ${testInfo.project.name} ${Date.now()}`;
  await login(page, "teacher");
  await page.goto("/classes");
  await page.getByLabel(/class name/i).fill(name);
  await page.getByLabel("Grade").selectOption("S1");
  await page.getByRole("button", { name: /^create$/i }).click();
  const card = page.locator(".card", { hasText: name });
  const code = (await card.locator(".pill").innerText()).trim();
  expect(code).toMatch(/^[A-Z2-9]{6}$/);
  await logout(page);

  await login(page, "grace");
  await page.goto("/classes");
  await page.getByLabel(/class code/i).fill(code);
  await page.getByRole("button", { name: /join/i }).click();
  await expect(page.locator(".card", { hasText: name })).toBeVisible();
});

test("written exam answers are marked by the teacher", async ({ page }) => {
  // Aline (S2) is in the teacher's demo class.
  await login(page, "aline");
  await page.goto("/practice?tab=papers");
  const paper = page.locator(".card", { hasText: "O-Level Mathematics — Sample Paper A" });
  await expect(paper.getByText(/unofficial sample/i)).toBeVisible();
  await paper.getByRole("button", { name: /take it here/i }).click();
  await expect(page.getByRole("timer")).toBeVisible();

  // Jump to the last question (a Section B written answer) and answer it.
  await page.locator(".qnav button").last().click();
  await page.getByLabel(/your answer/i).fill("w(w+3)=40 so w=5 and the length is 8 m");
  await expect(page.getByText(/saved/i)).toBeVisible();
  page.on("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: /^submit/i }).first().click();
  await expect(page.getByText(/waiting for your teacher/i)).toBeVisible();
  await logout(page);

  await login(page, "teacher");
  await page.goto("/marking");
  const item = page.locator("form.card", { hasText: "w(w+3)=40" }).first();
  await expect(item).toBeVisible();
  await item.getByLabel(/marks/i).fill("3");
  await item.getByLabel(/feedback/i).fill("Good method — state both dimensions clearly.");
  await item.getByRole("button", { name: /save mark/i }).click();
  await expect(page.locator("form.card", { hasText: "w(w+3)=40" })).toHaveCount(0);
});

test("study group chat", async ({ page }, testInfo) => {
  const text = `Who wants to revise vectors? (${testInfo.project.name} ${Date.now()})`;
  await login(page, "eric");
  await page.goto("/groups");
  await page.locator(".card", { hasText: "S2 Maths Squad" }).getByRole("link").first().click();
  await expect(page.getByText(/rise over run/i)).toBeVisible();
  await page.getByPlaceholder(/write a message/i).fill(text);
  await page.getByRole("button", { name: /^send$/i }).click();
  await expect(page.locator(".bubble.mine", { hasText: text })).toBeVisible();
});
