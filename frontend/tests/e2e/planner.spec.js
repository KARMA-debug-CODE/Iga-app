import { expect, test } from "@playwright/test";

import { login } from "./helpers";

test.use({ contextOptions: { reducedMotion: "reduce" } });

test("study planner: set a weekly goal, add an exam, see the countdown, remove it", async ({ page }) => {
  // The two browser projects share one demo database, so this works from whatever state the other left.
  const title = `Mock exam ${Date.now()}`;
  await login(page, "grace");
  await page.goto("/planner");
  await expect(page.getByRole("heading", { level: 1, name: /study plan/i })).toBeVisible();

  // Set a weekly goal to a value different from the current one.
  const goal = page.getByLabel(/lessons per week/i);
  const current = Number(await goal.inputValue());
  const next = current >= 50 ? current - 1 : current + 1;
  await goal.fill(String(next));
  await page.getByRole("button", { name: /^save$/i }).click();
  await expect(page.getByText(/^saved$/i)).toBeVisible();

  // Add an exam far in the future.
  await page.getByLabel(/exam name/i).fill(title);
  await page.getByLabel(/^date$/i).fill("2030-11-15");
  await page.getByRole("button", { name: /add an exam/i }).click();
  const row = page.locator("li", { hasText: title });
  await expect(row).toBeVisible();
  await expect(row.getByText(/days left/i)).toBeVisible();

  // The dashboard's study-plan block shows this week's progress.
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /study plan/i })).toBeVisible();
  await expect(page.getByText(/lessons this week/i)).toBeVisible();

  // Remove the exam we added.
  await page.goto("/planner");
  await page.locator("li", { hasText: title }).getByRole("button", { name: /remove this exam/i }).click();
  await expect(page.getByText(title)).toHaveCount(0);
});
