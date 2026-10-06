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

test("Ask AI page: choose a subject, ask, keep the chat for the tab, start again", async ({ page }) => {
  await page.route("**/api/tutor/status/", (route) => route.fulfill({ json: { enabled: true, reason: "" } }));
  const asked = [];
  await page.route("**/api/tutor/ask/", async (route) => {
    asked.push(route.request().postDataJSON());
    await route.fulfill({ json: { reply: "Photosynthesis makes **glucose**: $6CO_2 + 6H_2O \\to C_6H_{12}O_6 + 6O_2$" } });
  });

  await login(page, "aline");
  await page.goto("/ask");
  await expect(page.getByRole("heading", { name: /ask ai/i })).toBeVisible();
  await page.getByLabel(/^subject$/i).selectOption("biology");
  await page.getByRole("button", { name: /explain a topic to me/i }).click();
  await expect(page.getByText(/makes glucose/i)).toBeVisible();
  await expect(page.locator(".ask .katex").first()).toBeVisible();
  expect(asked[0]).toMatchObject({ subject: "biology", history: [] });

  await page.getByLabel(/type your question/i).fill("And where does it happen?");
  await page.getByLabel(/type your question/i).press("Enter");
  await expect(page.locator(".ask .bubble.mine")).toHaveCount(2);
  expect(asked[1].history.map((m) => m.role)).toEqual(["user", "assistant"]);

  await page.reload();
  await expect(page.locator(".ask .bubble.mine")).toHaveCount(2);
  await page.getByRole("button", { name: /new chat/i }).click();
  await expect(page.locator(".ask .bubble")).toHaveCount(0);
});

test("logging out in one tab ends the session and the Ask AI chat in the others", async ({ page, context }) => {
  await context.route("**/api/tutor/status/", (route) => route.fulfill({ json: { enabled: true, reason: "" } }));
  await context.route("**/api/tutor/ask/", (route) => route.fulfill({ json: { reply: "A cell is the basic unit of life." } }));
  await login(page, "aline");
  const other = await context.newPage();
  await other.goto("/ask");
  await other.getByLabel(/type your question/i).fill("What is a cell?");
  await other.getByLabel(/type your question/i).press("Enter");
  await expect(other.getByText(/basic unit of life/)).toBeVisible();

  await logout(page);
  await expect(other).toHaveURL(/\/login/);
  expect(await other.evaluate(() => Object.keys(sessionStorage).filter((k) => k.startsWith("iga.ask.")))).toEqual([]);
});

test("Ask AI page explains when the student's school hasn't subscribed", async ({ page }) => {
  await page.route("**/api/tutor/status/", (route) =>
    route.fulfill({ json: { enabled: false, reason: "subscription_required" } }),
  );
  await login(page, "samuel");
  await page.goto("/ask");
  await expect(page.locator(".locked-notice")).toBeVisible();
  await expect(page.getByLabel(/type your question/i)).toHaveCount(0);
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

test("SQL runs in the browser: tables, joins and errors", async ({ page }) => {
  await login(page, "aline");
  await page.goto("/playground");
  await page.getByRole("tab", { name: /sql/i }).click();
  await page.getByRole("button", { name: /run/i }).click();
  const output = page.locator(".sql-output");
  // The starter script: 4 + 6 rows inserted, then two queries.
  await expect(output.locator("table").first()).toContainText("Aline", { timeout: 30_000 });
  await expect(output.locator("table").nth(1)).toContainText("Grace90Aline71Eric63Jean48"); // best average first
  await expect(output).toContainText("4 rows changed");

  await page.getByLabel("SQL editor").fill("CREATE TABLE t (x INTEGER);\nSELEC x FROM t;");
  await page.getByRole("button", { name: /run/i }).click();
  await expect(output.locator(".sql-error")).toContainText(/syntax error/i);
});

test("C++ and Java run on the code runner, with clear messages for errors", async ({ page }) => {
  // The E2E server has no Piston code runner, so it is mocked here; tests/test_coderun.py covers the server side.
  await page.route("**/api/code/status/", (route) => route.fulfill({ json: { enabled: true, languages: ["cpp", "java"] } }));
  const sent = [];
  await page.route("**/api/code/run/", async (route) => {
    const body = route.request().postDataJSON();
    sent.push(body);
    if (body.language === "cpp" && body.code.includes("oops")) {
      return route.fulfill({
        json: { verdict: "compile_error", compile: { stdout: "", stderr: "main.cpp:3:5: error: 'oops' was not declared", code: 1 }, run: null },
      });
    }
    if (body.language === "java") {
      return route.fulfill({
        json: { verdict: "runtime_error", compile: null, run: { stdout: "", stderr: "error: can't find main(String[]) method in class: Student", code: 1, signal: null } },
      });
    }
    return route.fulfill({ json: { verdict: "ok", compile: { stdout: "", stderr: "", code: 0 }, run: { stdout: `Muraho, ${body.stdin}!\n`, stderr: "", code: 0 } } });
  });

  await login(page, "aline");
  await page.goto("/playground");
  await page.getByRole("tab", { name: /c\+\+/i }).click();
  await page.getByRole("button", { name: /^▶ run$/i }).click();
  const output = page.locator(".python-output");
  await expect(output).toContainText("Muraho, Aline!");
  await expect(output).toContainText("Finished");
  expect(sent[0]).toMatchObject({ language: "cpp", stdin: "Aline" });

  await page.getByLabel("C++ code editor").fill("int main() {\n  oops;\n}");
  await page.getByRole("button", { name: /^▶ run$/i }).click();
  await expect(output).toContainText("did not compile");
  await expect(output).toContainText("'oops' was not declared");

  await page.getByRole("tab", { name: /java/i }).click();
  await page.getByRole("button", { name: /^▶ run$/i }).click();
  await expect(output).toContainText(/class that has main\(\) first/i);
});

test("C++ and Java say when the server has no code runner", async ({ page }) => {
  await login(page, "aline");
  await page.goto("/playground");
  await page.getByRole("tab", { name: /java/i }).click();
  await expect(page.getByText(/not switched on for this server yet/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /^▶ run$/i })).toBeDisabled();
});

test("books: every lesson lists the official textbook, and empty units point to it", async ({ page }) => {
  await login(page, "aline");
  await page.goto("/lessons/s2-maths-linear-graphs");
  const books = page.locator("#books");
  await expect(books.getByRole("heading", { name: /books for this lesson/i })).toBeVisible();
  const official = books.locator("li", { hasText: /official/i }).first();
  await expect(official).toContainText(/senior 2/i);
  await expect(official).toContainText(/look for the unit about/i);
  await expect(official.getByRole("link")).toHaveAttribute("href", /^https:\/\/elearning\.reb\.rw\//);

  // Kinyarwanda has no Iga lessons yet: each unit sends students to the official book.
  await page.goto("/learn/kinyarwanda?grade=S1");
  await page.locator("details.unit summary").first().click();
  await expect(page.getByText(/no iga lesson for this unit yet/i).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /books for s1/i })).toBeVisible();
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
