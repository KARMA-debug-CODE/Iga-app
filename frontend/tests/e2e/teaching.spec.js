import { expect, test } from "@playwright/test";

import { login, logout } from "./helpers";

test.use({ contextOptions: { reducedMotion: "reduce" } });

test("a teacher makes, edits, prints and assigns a teaching pack", async ({ page }) => {
  // The print view opens the browser's print dialog; replace it so the test can look at the page.
  await page.addInitScript(() => {
    window.print = () => {};
  });
  await login(page, "teacher");
  await page.goto("/classes");
  await page.getByRole("link", { name: /S2 Mathematics/ }).first().click();
  await page.getByRole("tab", { name: /progress report/i }).click();

  // Make a pack from the unit picker (the demo class may have no answers yet: then the quiz is diagnostic).
  await page.getByRole("button", { name: /choose a unit/i }).click();
  await page.getByRole("button", { name: /make a teaching pack for/i }).first().click();
  await expect(page).toHaveURL(/\/teaching-packs\/\d+$/, { timeout: 30000 });
  const packUrl = page.url();
  await expect(page.getByRole("tab", { name: "Insight" })).toBeVisible();
  for (const name of ["Lesson plan", "Worksheet", "Quiz"]) await expect(page.getByRole("tab", { name })).toBeVisible();

  // Edit the lesson plan: it saves on its own.
  const objective = `Learners can read a graph ${Date.now()}`;
  await page.getByRole("tab", { name: "Lesson plan" }).click();
  await page.getByLabel("Instructional objective").fill(objective);
  await expect(page.locator(".pack-save-status")).toHaveText(/saved/i, { timeout: 15000 });

  // The student worksheet prints without the app around it and without answers; the plan keeps the edit.
  await page.emulateMedia({ media: "print" });
  await page.goto(`${packUrl}?print=worksheet`);
  await expect(page.locator(".pack-print-worksheet")).toBeVisible();
  await expect(page.locator(".topbar")).toBeHidden();
  await expect(page.locator(".pack-print-worksheet .pack-answer")).toHaveCount(0);
  await page.goto(`${packUrl}?print=plan`);
  await expect(page.getByText(objective)).toBeVisible();
  await page.emulateMedia({ media: "screen" });

  // Assign the quiz to the class.
  await page.goto(packUrl);
  await page.getByRole("tab", { name: "Quiz" }).click();
  const quizTitle = (await page.locator(".pack-section h3").first().textContent()).trim();
  await page.getByRole("button", { name: "Assign to the class" }).click();
  await page.getByRole("button", { name: "Assign", exact: true }).click();
  await expect(page.getByText(/assigned to the class/i)).toBeVisible();

  // A student of the class sees the new assignment.
  await logout(page);
  await login(page, "aline");
  await page.goto("/classes");
  await page.getByRole("link", { name: /S2 Mathematics/ }).first().click();
  await expect(page.getByText(new RegExp(quizTitle)).first()).toBeVisible();
});

test("an unpaid school sees the teaser", async ({ page }) => {
  await page.route("**/api/teaching/packs/", (route) => {
    if (route.request().method() !== "POST") return route.continue();
    return route.fulfill({
      status: 403,
      contentType: "application/json",
      body: JSON.stringify({
        detail: "Teaching packs are part of your school's Iga subscription.",
        code: "subscription_required",
        teaser: { unit: "S2 Unit 1: Linear graphs", average: 40, misconceptions_found: 2 },
      }),
    });
  });
  await login(page, "teacher");
  await page.goto("/classes");
  await page.getByRole("link", { name: /S2 Mathematics/ }).first().click();
  await page.getByRole("tab", { name: /progress report/i }).click();
  await page.getByRole("button", { name: /choose a unit/i }).click();
  await page.getByRole("button", { name: /make a teaching pack for/i }).first().click();
  await expect(page.getByText(/misconceptions iga found in S2 Unit 1: Linear graphs: 2/i)).toBeVisible();
  await expect(page.getByText(/part of your school's iga subscription/i)).toBeVisible();
});
