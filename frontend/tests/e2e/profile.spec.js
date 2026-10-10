import { expect, test } from "@playwright/test";

import { login } from "./helpers.js";

async function setGrade(page, grade) {
  await page.goto("/profile");
  await page.getByLabel("Grade").selectOption(grade);
  await expect(page.getByRole("note")).toContainText(`moves to ${grade}`);
  await page.getByRole("button", { name: /^save$/i }).click();
  await expect(page.getByRole("status")).toContainText(`now follows ${grade}`);
}

test("the profile: build an avatar, and changing level moves the student's classes", async ({ page }) => {
  await login(page, "aline");

  // Avatar: pick another hairstyle and save it; the header shows the same avatar.
  await page.goto("/profile#avatar");
  const hair = page.getByRole("radiogroup", { name: "Hairstyle" });
  const other = hair.locator('[aria-checked="false"]').first();
  const label = await other.getAttribute("aria-label");
  await other.click();
  await expect(hair.getByRole("radio", { name: label, exact: true })).toHaveAttribute("aria-checked", "true");
  const save = page.getByRole("button", { name: /^save$/i });
  await save.click();
  await expect(save).toBeDisabled();
  await page.reload();
  await expect(page.getByRole("radiogroup", { name: "Hairstyle" }).getByRole("radio", { name: label, exact: true })).toHaveAttribute(
    "aria-checked",
    "true",
  );

  // Moving from S2 to S3: the S2 class goes to "previous classes" and the app follows S3.
  await setGrade(page, "S3");
  await page.goto("/classes");
  await expect(page.getByText("Your classes for S3.")).toBeVisible();
  await expect(page.getByText("S2 Mathematics — Stream A")).toBeHidden();
  await page.getByText(/previous classes \(1\)/i).click();
  await page.getByText("S2 Mathematics — Stream A").click();
  await expect(page.getByRole("status")).toContainText("before you moved to S3");

  // Back to S2 (the other tests use this student): the class is current again.
  await setGrade(page, "S2");
  await page.goto("/classes");
  await expect(page.getByText("S2 Mathematics — Stream A")).toBeVisible();
  await expect(page.getByText(/previous classes/i)).toBeHidden();
});

test("the menu can be hidden for more room, and stays hidden", async ({ page }) => {
  await login(page, "aline");
  const learn = page.getByRole("link", { name: "Learn", exact: true });
  await expect(learn).toBeVisible();
  await page.getByRole("button", { name: /hide the menu/i }).click();
  await expect(learn).toBeHidden();
  await page.reload();
  await expect(page.getByRole("button", { name: /show the menu/i })).toBeVisible();
  await expect(learn).toBeHidden();
  await page.getByRole("button", { name: /show the menu/i }).click();
  await expect(learn).toBeVisible();
});

test("an A-level student's combination comes first in their subject lists", async ({ page }) => {
  await login(page, "aline");
  const group = (name) => page.locator(".subject-group", { has: page.getByRole("heading", { name }) });

  // S5 with MCE (Mathematics, Computer Science, Economics).
  await page.goto("/profile");
  await expect(page.getByLabel("Combination")).toBeHidden(); // only S4–S6 choose one
  await page.getByLabel("Grade").selectOption("S5");
  await page.getByLabel("Combination").selectOption("MCE");
  await expect(page.getByLabel("Combination").locator("option:checked")).toHaveText("MCE – Mathematics, Computer Science, Economics");
  await page.getByRole("button", { name: /^save$/i }).click();
  await expect(page.getByRole("status")).toContainText("now follows S5");

  // The dashboard lists the combination first, then everything else (ICT included).
  await page.goto("/");
  const mine = group("Your combination (MCE)");
  await expect(mine.getByRole("link")).toHaveCount(3);
  for (const name of ["Mathematics", "Computer Science", "Economics"]) await expect(mine.getByRole("link", { name })).toBeVisible();
  await expect(group("Other subjects").getByRole("link", { name: /^ICT/ })).toBeVisible();
  await expect(group("Other subjects").getByRole("link", { name: /^Physics/ })).toBeVisible();

  // The Learn page too, but not for an O-level grade.
  await page.goto("/learn?grade=S6");
  await expect(group("Your combination (MCE)").getByRole("link", { name: /Computer Science/ })).toBeVisible();
  await page.goto("/learn?grade=S2");
  await expect(page.getByRole("link", { name: /^ICT/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your combination (MCE)" })).toBeHidden();

  // Subject pickers group their options the same way.
  await page.goto("/practice");
  const picker = page.getByRole("combobox", { name: "Subject" });
  await expect(picker.locator('optgroup[label="Your combination (MCE)"] option')).toHaveText(["Mathematics", "Computer Science", "Economics"]);
  await expect(picker.locator('optgroup[label="Other subjects"] option', { hasText: "ICT" })).toHaveCount(1);

  // Back to S2 (the other tests use this student): the combination goes with A-level.
  await page.goto("/profile");
  await page.getByLabel("Grade").selectOption("S2");
  await expect(page.getByLabel("Combination")).toBeHidden();
  await page.getByRole("button", { name: /^save$/i }).click();
  await expect(page.getByRole("status")).toContainText("now follows S2");
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Your subjects · S2/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Your combination/ })).toBeHidden();
  await page.goto("/profile");
  await page.getByLabel("Grade").selectOption("S4");
  await expect(page.getByLabel("Combination")).toHaveValue("");
});
