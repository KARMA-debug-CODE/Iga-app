import { expect, test } from "@playwright/test";

import { login } from "./helpers";

test.use({ contextOptions: { reducedMotion: "reduce" } });

test("bookmark a lesson and keep a private note, then find them in My notes", async ({ page }) => {
  // The two browser projects share one demo database, so this does not assume a clean start.
  const token = `riseoverrun${Date.now()}`;
  await login(page, "aline");
  await page.goto("/lessons/s2-maths-linear-graphs");
  const notes = page.locator("#notes");
  await expect(notes.getByRole("heading", { name: /my notes/i })).toBeVisible();
  await expect(notes.getByText(/only you can see this/i)).toBeVisible();

  // The bookmark toggle flips state; leave it bookmarked at the end.
  const toggle = notes.getByRole("button", { name: /bookmark/i });
  const before = (await toggle.getAttribute("aria-pressed")) === "true";
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", String(!before));
  if ((await toggle.getAttribute("aria-pressed")) !== "true") await toggle.click();
  await expect(notes.getByRole("button", { name: /bookmarked/i })).toBeVisible();

  // Write a private note; it autosaves to the server.
  await notes.getByLabel(/your private note/i).fill(`Remember ${token}`);
  await notes.getByLabel(/your private note/i).blur();
  await expect(notes.locator(".note-status")).toContainText(/saved/i, { timeout: 15000 });

  // The note and bookmark appear in My notes, and search finds the note.
  await page.goto("/my-notes");
  await expect(page.getByText(new RegExp(token))).toBeVisible();
  await page.getByLabel(/search your notes/i).fill(token);
  await expect(page.getByText(new RegExp(token))).toBeVisible();
  await page.getByLabel(/search your notes/i).fill("zzznotfound");
  await expect(page.getByText(/no notes match/i)).toBeVisible();

  await page.getByRole("tab", { name: /bookmarks/i }).click();
  await expect(page.getByText(/straight-line graphs/i)).toBeVisible();
});

test("a note written offline is kept on the device and syncs when back online", async ({ page, context }, testInfo) => {
  // A value unique to this browser project, so it differs from whatever the other project left.
  const idea = `offline idea ${testInfo.project.name}`;
  await login(page, "aline");
  await page.goto("/lessons/s1-maths-integers");
  const notes = page.locator("#notes");
  await expect(notes.getByLabel(/your private note/i)).toBeVisible();

  await context.setOffline(true);
  await notes.getByLabel(/your private note/i).fill(idea);
  await notes.getByLabel(/your private note/i).blur();
  await expect(notes.locator(".note-status")).toContainText(/saved on this device/i, { timeout: 15000 });

  // Back online, the note syncs and is still there on reload.
  await context.setOffline(false);
  await page.reload();
  await expect(page.locator("#notes").getByLabel(/your private note/i)).toHaveValue(idea);
});
