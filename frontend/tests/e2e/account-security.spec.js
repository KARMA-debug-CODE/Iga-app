import { expect, test } from "@playwright/test";

import { login, PASSWORD } from "./helpers";

test("forgot password: the same answer for any name, and an unusable link says so", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("link", { name: /forgot your password/i }).click();
  await page.getByLabel(/username or email/i).fill("divine");
  await page.getByRole("button", { name: /send the link/i }).click();
  const answer = page.getByRole("status");
  // Often the run's first request: a freshly started server loads its code on it, which can take a few seconds.
  await expect(answer).toContainText(/if an account matches/i, { timeout: 15000 });
  const realText = await answer.innerText();

  await page.goto("/forgot-password");
  await page.getByLabel(/username or email/i).fill(`nobody-${Date.now()}`);
  await page.getByRole("button", { name: /send the link/i }).click();
  await expect(page.getByRole("status")).toHaveText(realText);

  // A made-up link: refused, with a way to ask again. The secret leaves the address bar at once.
  await page.goto("/reset-password#not-a-real-link");
  await expect(page).toHaveURL(/\/reset-password$/);
  await page.getByLabel(/^new password$/i).fill("Nkunda-imibare-2026");
  await page.getByLabel(/new password again/i).fill("Nkunda-imibare-2026");
  await page.getByRole("button", { name: /save my new password/i }).click();
  await expect(page.getByRole("alert")).toContainText(/not valid or has expired/i);
  await expect(page.getByRole("link", { name: /ask for a new link/i })).toBeVisible();
});

test("a student adds an email (with their password) and logs out everywhere", async ({ page, browser }, testInfo) => {
  await login(page, "eric");
  // Another device, signed in at the same time.
  const other = await browser.newContext({ baseURL: testInfo.project.use.baseURL, locale: "en-GB" });
  const phone = await other.newPage();
  await login(phone, "eric");

  // The session cookie keeps the student signed in across a reload.
  await page.reload();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/hi /i);

  await page.goto("/profile#security");
  const email = page.locator("form", { has: page.getByRole("heading", { name: /email address/i }) });
  await email.getByLabel(/^email$/i).fill(`eric.${testInfo.project.name}@example.com`);
  await email.getByLabel(/current password/i).fill("not-my-password");
  await email.getByRole("button", { name: /save/i }).click();
  await expect(email.getByRole("alert")).toContainText(/current password/i);
  await email.getByLabel(/current password/i).fill(PASSWORD);
  await email.getByRole("button", { name: /save/i }).click();
  await expect(email.getByText(/saved/i)).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: /log out everywhere/i }).click();
  await expect(page).toHaveURL(/\/($|login)/);
  await phone.reload();
  await expect(phone.getByRole("link", { name: /log in/i }).first()).toBeVisible();
  await other.close();
});
