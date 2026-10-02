import { expect, test } from "@playwright/test";

import { login } from "./helpers";

test("admin sees platform stats and the audit log", async ({ page }) => {
  await login(page, "admin");
  await page.goto("/admin");
  await expect(page.getByText(/active this week/i)).toBeVisible();
  await page.getByRole("tab", { name: /audit log/i }).click();
  await expect(page.locator("table")).toBeVisible();
});

test("students cannot open teacher or admin pages", async ({ page }) => {
  await login(page, "grace");
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/teach");
  await expect(page).toHaveURL(/\/$/);
});
