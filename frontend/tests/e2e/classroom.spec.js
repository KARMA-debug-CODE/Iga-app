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

test("what one student writes can't run code in another student's browser", async ({ page }, testInfo) => {
  // Stored XSS: chat messages, note titles and Markdown notes are shown to the other members of a group.
  const stamp = `${testInfo.project.name}-${Date.now()}`;
  await login(page, "eric");
  await page.goto("/groups");
  await page.locator(".card", { hasText: "S2 Maths Squad" }).getByRole("link").first().click();
  await page.getByPlaceholder(/write a message/i).fill(`<img src=x onerror="window.__xss=1"><script>window.__xss=2</script> ${stamp}`);
  await page.getByRole("button", { name: /^send$/i }).click();
  await expect(page.locator(".bubble.mine", { hasText: stamp })).toBeVisible();
  await page.getByRole("tab", { name: /shared notes/i }).click();
  await page.getByLabel(/^title$/i).fill(`<b onmouseover="window.__xss=3">Note ${stamp}</b>`);
  await page
    .getByLabel(/^note/i)
    .fill(
      [
        '**Forces** <img src=x onerror="window.__xss=4"> <script>window.__xss=5</script>',
        "[click me](javascript:window.__xss=6) and <a href=\"javascript:window.__xss=7\">raw link</a>",
        "![pixel](https://tracker.example/p.png)",
        "$\\href{javascript:window.__xss=8}{maths link}$",
      ].join("\n\n"),
    );
  await page.getByRole("button", { name: /^save$/i }).click();
  await expect(page.getByText(`<b onmouseover="window.__xss=3">Note ${stamp}</b>`)).toBeVisible();
  await logout(page);

  let dialogs = 0;
  page.on("dialog", (dialog) => {
    dialogs += 1;
    dialog.dismiss();
  });
  await login(page, "aline");
  await page.goto("/groups");
  await page.locator(".card", { hasText: "S2 Maths Squad" }).getByRole("link").first().click();
  const bubble = page.locator(".bubble", { hasText: stamp });
  await expect(bubble).toContainText('<img src=x onerror="window.__xss=1">');
  await expect(bubble.locator("img, script")).toHaveCount(0);

  await page.getByRole("tab", { name: /shared notes/i }).click();
  const note = page.locator(".card", { hasText: `Note ${stamp}` });
  await expect(note.locator("strong").first()).toHaveText(`<b onmouseover="window.__xss=3">Note ${stamp}</b>`);
  await expect(note.locator(".prose strong")).toHaveText("Forces"); // Markdown still works
  await expect(note).toContainText("<script>window.__xss=5</script>"); // raw HTML is shown as text
  await expect(note.locator("img, script, b")).toHaveCount(0);
  for (const href of await note.locator("a").evaluateAll((links) => links.map((a) => a.getAttribute("href") || ""))) {
    expect(href.replace(/\s/g, "").toLowerCase()).not.toContain("javascript:");
  }
  await note.locator("strong").first().hover();
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
  expect(dialogs).toBe(0);
});
