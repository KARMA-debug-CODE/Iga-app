// Motion: placeholders while lists load, the sliding tab underline and menu, and celebrations. Nothing here
// waits for an animation to finish before the next click, and with reduced motion nothing moves.
import { expect, test } from "@playwright/test";

import { login } from "./helpers";

async function newStudent(page) {
  await page.goto("/register");
  await page.getByLabel(/first name/i).fill("Keza");
  await page.getByLabel(/^username$/i).fill(`move${Date.now()}`);
  await page.getByLabel(/^password/i).fill("Murakoze-2026");
  await page.getByLabel("Grade").selectOption("S1");
  await page.getByLabel(/i have read and accept/i).check();
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Hi Keza");
}

/** Records every class the menus get, so a class that lasts a fraction of a second is still seen. */
async function watchMenuClasses(page) {
  await page.evaluate(() => {
    window.__menuClasses = [];
    new MutationObserver((records) => {
      for (const r of records) if (r.target.matches?.(".sidebar, .bottom-nav")) window.__menuClasses.push(r.target.className);
    }).observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class"] });
  });
}

const menuClasses = (page) => page.evaluate(() => window.__menuClasses.join(" "));

test("a list shows placeholders shaped like it while it loads", async ({ page }) => {
  await login(page, "divine");
  let release;
  const held = new Promise((resolve) => (release = resolve));
  await page.route(/\/api\/subjects\/\?/, async (route) => {
    await held;
    await route.continue();
  });
  await page.getByRole("link", { name: "Learn", exact: true }).first().click();
  const placeholder = page.locator('[role="status"]', { has: page.locator(".card.skeleton") });
  await expect(placeholder).toBeVisible();
  await expect(placeholder).toContainText("Loading");
  release();
  await expect(page.getByRole("link", { name: /Mathematics/ }).first()).toBeVisible();
  await expect(page.locator(".skeleton")).toHaveCount(0);
});

test("the tab underline slides to the chosen tab, and the menu slides away and back", async ({ page }) => {
  await login(page, "divine");
  await page.goto("/leaderboard");
  const bar = page.locator(".tab-indicator");
  const allTime = page.getByRole("tab", { name: /all time/i });
  await expect(bar).toBeVisible();
  await allTime.click(); // no waiting for the underline: the click works at once
  await expect(allTime).toHaveAttribute("aria-selected", "true");
  await expect
    .poll(async () => {
      const [b, t] = [await bar.boundingBox(), await allTime.boundingBox()];
      return Math.abs(b.x - t.x) < 1.5 && Math.abs(b.width - t.width) < 1.5;
    })
    .toBe(true);

  await watchMenuClasses(page);
  const learn = page.getByRole("link", { name: "Learn", exact: true });
  await page.getByRole("button", { name: /hide the menu/i }).click();
  await expect(learn).toBeHidden();
  expect(await menuClasses(page)).toContain("is-leaving");
  await page.getByRole("button", { name: /show the menu/i }).click();
  await expect(learn).toBeVisible();
  expect(await menuClasses(page)).toContain("is-entering");
});

test("finishing a first lesson bursts, and the new badge is celebrated, then goes", async ({ page }) => {
  await newStudent(page);
  await page.goto("/lessons/s1-maths-integers");
  await page.getByRole("button", { name: /mark as complete/i }).click();
  await expect(page.locator(".celebrate .burst")).toBeAttached();
  const badge = page.getByRole("status").filter({ hasText: "New badge: First Steps" });
  await expect(badge).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "XP" })).toBeVisible();
  await expect(badge).toBeHidden({ timeout: 6000 });
});

test.describe("with reduced motion", () => {
  test.use({ contextOptions: { reducedMotion: "reduce" } });

  test("nothing moves, and the news is still told", async ({ page }) => {
    await newStudent(page);
    // The menu goes at once, without sliding.
    await watchMenuClasses(page);
    await page.getByRole("button", { name: /hide the menu/i }).click();
    await expect(page.getByRole("link", { name: "Learn", exact: true })).toBeHidden();
    expect(await menuClasses(page)).not.toContain("is-leaving");
    await page.getByRole("button", { name: /show the menu/i }).click();

    await page.goto("/lessons/s1-maths-integers");
    await page.getByRole("button", { name: /mark as complete/i }).click();
    await expect(page.getByRole("status").filter({ hasText: "New badge: First Steps" })).toBeVisible();
    await expect(page.locator(".burst")).toHaveCount(0);

    // Numbers are shown as they are, not counted up.
    await page.goto("/");
    await expect(page.locator(".stat strong").first()).toHaveText("10");
    // Reduced motion shortens animations to 1ms rather than removing them: none may last longer than that.
    const moving = await page.evaluate(
      () => document.getAnimations().filter((a) => a.playState === "running" && a.effect?.getComputedTiming().duration > 1).length,
    );
    expect(moving).toBe(0);
  });
});
