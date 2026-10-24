import { expect, test } from "@playwright/test";

import { login, logout } from "./helpers";

// Santa's model is not running in these tests, so its endpoints are mocked here (a streamed answer is a
// text/event-stream body); the server side is covered by backend/tests/test_tutor.py.
const READY = { enabled: true, reason: "", state: "ready", exam: null };

function santaStream(reply, extra = {}) {
  const pieces = reply.match(/[\s\S]{1,12}/g) || [];
  const events = [
    { type: "start" },
    ...pieces.map((text) => ({ type: "delta", text })),
    { type: "done", reply, sources: [], fallback: null, tools: [], ...extra },
  ];
  return {
    status: 200,
    headers: { "Content-Type": "text/event-stream; charset=utf-8" },
    body: events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join(""),
  };
}

test("Santa answers questions about a lesson, with its sources", async ({ page }) => {
  await page.route("**/api/tutor/status/", (route) => route.fulfill({ json: READY }));
  let asked = null;
  await page.route("**/api/tutor/stream/", async (route) => {
    asked = route.request().postDataJSON();
    await route.fulfill(
      santaStream("The **gradient** is the number in front of $x$: here it is $3$.", {
        sources: [
          {
            slug: "s2-maths-linear-graphs",
            title: "Straight-line graphs",
            section: "Gradient",
            url: "/lessons/s2-maths-linear-graphs",
          },
        ],
        tools: [{ expression: "3 * 2 + 2", result: "8" }],
      }),
    );
  });

  await login(page, "aline");
  await page.goto("/lessons/s2-maths-linear-graphs");
  await page.getByRole("button", { name: /^ask santa$/i }).click();
  const panel = page.getByRole("region", { name: /santa/i });
  await expect(panel.getByText(/runs on your school's server and can make mistakes/i)).toBeVisible();
  await expect(panel.getByRole("textbox")).toBeFocused();
  await panel.getByRole("textbox").fill("What is the gradient of y = 3x + 2?");
  await panel.getByRole("button", { name: /^send$/i }).click();
  await expect(panel.locator(".santa-answer").getByText(/number in front of/)).toBeVisible();
  await expect(panel.locator(".katex").first()).toBeVisible();
  await expect(panel.getByText("Calculator: 3 * 2 + 2 = 8")).toBeVisible();
  await expect(panel.getByRole("link", { name: "Straight-line graphs" })).toHaveAttribute("href", "/lessons/s2-maths-linear-graphs");
  await expect(page.getByRole("status").filter({ hasText: /santa answered/i })).toHaveCount(1);
  expect(asked.lesson).toBeTruthy();
  expect(asked.message).toContain("gradient");
});

test("Santa page: choose a subject, ask, keep the chat for the tab, start again", async ({ page }) => {
  await page.route("**/api/tutor/status/", (route) => route.fulfill({ json: READY }));
  const asked = [];
  await page.route("**/api/tutor/stream/", async (route) => {
    asked.push(route.request().postDataJSON());
    await route.fulfill(santaStream("Photosynthesis makes **glucose**: $6CO_2 + 6H_2O \\to C_6H_{12}O_6 + 6O_2$"));
  });

  await login(page, "aline");
  await page.goto("/ask");
  await expect(page.getByRole("heading", { level: 1, name: /^santa$/i })).toBeVisible();
  await page.getByLabel(/^subject$/i).selectOption("biology");
  await page.getByRole("button", { name: /explain a topic to me/i }).click();
  await expect(page.locator(".santa-answer").getByText(/makes glucose/i)).toBeVisible();
  await expect(page.locator(".ask .katex").first()).toBeVisible();
  expect(asked[0]).toMatchObject({ subject: "biology", history: [] });

  await page.getByLabel(/type your question/i).fill("And where does it happen?");
  await page.getByLabel(/type your question/i).press("Enter");
  await expect(page.locator(".ask .bubble.mine")).toHaveCount(2);
  await expect(page.locator(".ask .santa-answer")).toHaveCount(2);
  expect(asked[1].history.map((m) => m.role)).toEqual(["user", "assistant"]);

  await page.reload();
  await expect(page.locator(".ask .bubble.mine")).toHaveCount(2);
  await page.getByRole("button", { name: /new chat/i }).click();
  await expect(page.locator(".ask .bubble")).toHaveCount(0);
});

test("Santa page: waking up, answers from the lessons, and Stop gives the question back", async ({ page }) => {
  await page.route("**/api/tutor/status/", (route) => route.fulfill({ json: { ...READY, state: "loading" } }));
  let slow = false;
  await page.route("**/api/tutor/stream/", async (route) => {
    if (slow) {
      await new Promise((resolve) => setTimeout(resolve, 5000));
      return route.fulfill(santaStream("Too late.")).catch(() => {});
    }
    await route.fulfill(
      santaStream("*Santa is still waking up.* Here is what your lessons say:\n\n> A cell is the basic unit of life.", {
        fallback: "loading",
        sources: [{ slug: "s1-biology-the-cell", title: "The cell, the unit of life", section: "", url: "/lessons/s1-biology-the-cell" }],
      }),
    );
  });

  await login(page, "aline");
  await page.goto("/ask");
  await expect(page.getByText(/santa is waking up/i)).toBeVisible();
  const box = page.getByLabel(/type your question/i);
  await box.fill("What is a cell?");
  await box.press("Enter");
  await expect(page.locator(".santa-answer").getByText(/basic unit of life/)).toBeVisible();
  await expect(page.getByRole("link", { name: "The cell, the unit of life" })).toBeVisible();

  slow = true;
  await box.fill("And a tissue?");
  await page.getByRole("button", { name: /^send$/i }).click();
  await expect(page.locator(".santa-typing")).toContainText(/santa is thinking/i);
  const stop = page.getByRole("button", { name: /^stop$/i });
  await expect(stop).toBeFocused();
  await stop.click();
  await expect(box).toHaveValue("And a tissue?");
  await expect(page.locator(".ask .bubble.mine")).toHaveCount(1);
  await expect(page.getByRole("button", { name: /^send$/i })).toBeVisible();
});

test("Santa page shows what is left of the student's questions, and says when today's are used up", async ({ page }) => {
  const left = (n, reached = "") => ({
    questions_left_today: n,
    questions_per_day: 60,
    questions_left_month: 700,
    questions_per_month: 800,
    time_left_percent: 80,
    reached,
  });
  await page.route("**/api/tutor/status/", (route) => route.fulfill({ json: { ...READY, allowance: left(1) } }));
  const answers = [
    santaStream("A cell is the basic unit of life.", { allowance: left(0) }),
    santaStream("*You have used today's questions for Santa's AI. It can answer fully again tomorrow.* Here is what your lessons say:", {
      fallback: "limit_day",
      allowance: left(0, "limit_day"),
    }),
  ];
  await page.route("**/api/tutor/stream/", (route) => route.fulfill(answers.shift()));

  await login(page, "aline");
  await page.goto("/ask");
  await expect(page.getByText("1 of 60 questions for Santa's AI left today")).toBeVisible();
  const box = page.getByLabel(/type your question/i);
  await box.fill("What is a cell?");
  await box.press("Enter");
  await expect(page.locator(".santa-answer").getByText(/basic unit of life/)).toBeVisible();
  await expect(page.getByText("0 of 60 questions for Santa's AI left today")).toBeVisible();
  await box.fill("And a tissue?");
  await box.press("Enter");
  const note = page.getByRole("note").filter({ hasText: /used today's questions for santa's ai/i });
  await expect(note).toContainText(/until tomorrow, santa answers with passages from your lessons/i);
  await expect(page.locator(".santa-answer").last().getByText(/here is what your lessons say/i)).toBeVisible();
});

test("Santa page is switched off while an exam is open", async ({ page }) => {
  await page.route("**/api/tutor/status/", (route) =>
    route.fulfill({ json: { ...READY, state: "exam", exam: { attempt: 12345, quiz: "Linear graphs test" } } }),
  );
  await login(page, "aline");
  await page.goto("/ask");
  await expect(page.getByText(/santa is off during your exam/i)).toBeVisible();
  await expect(page.getByText(/Linear graphs test/)).toBeVisible();
  await expect(page.getByRole("link", { name: /go to the open exam/i })).toHaveAttribute("href", "/attempts/12345");
  await expect(page.getByLabel(/type your question/i)).toHaveCount(0);
});

test("logging out in one tab ends the session and the Santa chat in the others", async ({ page, context }) => {
  await context.route("**/api/tutor/status/", (route) => route.fulfill({ json: READY }));
  await context.route("**/api/tutor/stream/", (route) => route.fulfill(santaStream("A cell is the basic unit of life.")));
  await login(page, "aline");
  const other = await context.newPage();
  await other.goto("/ask");
  await other.getByLabel(/type your question/i).fill("What is a cell?");
  await other.getByLabel(/type your question/i).press("Enter");
  await expect(other.locator(".santa-answer").getByText(/basic unit of life/)).toBeVisible();

  await logout(page);
  await expect(other).toHaveURL(/\/login/);
  expect(await other.evaluate(() => Object.keys(sessionStorage).filter((k) => k.startsWith("iga.ask.")))).toEqual([]);
});

test("Santa page explains when the student's school hasn't subscribed", async ({ page }) => {
  await page.route("**/api/tutor/status/", (route) =>
    route.fulfill({ json: { enabled: false, reason: "subscription_required", state: "", exam: null } }),
  );
  await login(page, "samuel");
  await page.goto("/ask");
  await expect(page.locator(".locked-notice")).toBeVisible();
  await expect(page.getByLabel(/type your question/i)).toHaveCount(0);
});

test("without its model, Santa answers from the lessons through the real stream", async ({ page }) => {
  // Nothing mocked: the test server has no SANTA_URL, so Django streams an answer made of lesson passages.
  await login(page, "aline");
  await page.goto("/ask");
  await expect(page.getByText(/santa's ai model isn't installed yet/i)).toBeVisible();
  const box = page.getByLabel(/type your question/i);
  await box.fill("What does the cell membrane control?");
  await box.press("Enter");
  const answer = page.locator(".santa-answer").last();
  await expect(answer.getByText(/here is what your lessons say/i)).toBeVisible();
  await expect(answer.getByText(/controls what enters and leaves/i).first()).toBeVisible();
  await expect(answer.getByRole("link", { name: "The cell, the unit of life" })).toHaveAttribute("href", "/lessons/s1-biology-the-cell");
  await expect(page.getByRole("button", { name: /^send$/i })).toBeVisible();
});

test("a parent links to their child with a code and sees progress", async ({ page }) => {
  await login(page, "eric");
  await page.goto("/profile#security");
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

test("Python asks for input in the console like a real interpreter, and indents automatically", async ({ page }) => {
  await login(page, "aline");
  await page.goto("/playground");
  await page.getByRole("tab", { name: /python/i }).click();
  const console_ = page.locator(".console");

  // The starter program asks for a name: the question appears in the console and waits for the answer.
  await page.getByRole("button", { name: /^run$/i }).click();
  await expect(console_).toContainText("What is your name?", { timeout: 45_000 });
  await page.getByLabel("Your answer").fill("Aline");
  await page.getByLabel("Your answer").press("Enter");
  await expect(console_).toContainText("Muraho, Aline!");
  await expect(console_).toContainText("Average mark: 77.8");

  // Enter after a line ending with ":" indents the next line, like a real editor.
  const editor = page.getByLabel("Python code editor");
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.press("Delete");
  // Each line goes in as one text input, like a phone keyboard sends it: with Android emulated, CodeMirror's
  // guards against keyboard composition glitches can drop keys that a script types a few milliseconds apart.
  // It also ignores an Enter less than 50 ms after the last change, so the test pauses as a person would.
  await page.keyboard.insertText("for i in range(3):");
  await expect(editor).toHaveText("for i in range(3):");
  await page.waitForTimeout(100);
  await page.keyboard.press("Enter");
  await expect(editor.locator(".cm-line")).toHaveCount(2);
  await page.keyboard.insertText("print(i * 2)");
  expect(await editor.innerText()).toMatch(/for i in range\(3\):\n {4}print\(i \* 2\)/);
  await page.getByRole("button", { name: /^run$/i }).click();
  await expect(console_).toContainText(/0\s+2\s+4/);
});

test("the HTML playground shows the page and runs its scripts in a sandboxed preview", async ({ page }) => {
  await login(page, "aline");
  await page.goto("/playground");
  const editor = page.getByLabel(/code editor/i).first();
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.press("Delete");
  await page.keyboard.insertText(
    '<h1 id="title">Muraho</h1><p id="out"></p>' +
      "<script>document.getElementById('out').textContent = 'answer ' + (6 * 7);" +
      "try { document.cookie; localStorage.length; document.getElementById('out').textContent += ' with storage'; } catch (e) {}</script>",
  );
  await page.getByRole("button", { name: /^run$/i }).click();
  const preview = page.frameLocator('iframe[title="Preview"]');
  await expect(preview.locator("#title")).toHaveText("Muraho");
  // The script ran, and the sandbox kept it away from Iga's storage.
  await expect(preview.locator("#out")).toHaveText("answer 42");
  // Running again shows the new version.
  await page.keyboard.insertText("<p id=\"again\">again</p>");
  await page.getByRole("button", { name: /^run$/i }).click();
  await expect(preview.locator("#again")).toHaveText("again");
});

test("Python programs can't use the student's session or the app's offline data", async ({ page }) => {
  // Lessons' "python-run" blocks are written by teachers and run in a worker with the app's origin: a
  // program must not be able to ask the API for a new session with the student's cookie, read the
  // offline caches, or start a fresh worker that has those powers again.
  await login(page, "aline");
  await page.goto("/playground");
  await page.getByRole("tab", { name: /python/i }).click();
  const console_ = page.locator(".console");
  const editor = page.getByLabel("Python code editor");

  async function runLine(line) {
    await editor.click();
    await page.keyboard.press("ControlOrMeta+a");
    await page.keyboard.press("Delete");
    await page.keyboard.insertText(line);
    await page.getByRole("button", { name: /^run$/i }).click();
  }

  const names = '"fetch", "XMLHttpRequest", "WebSocket", "EventSource", "Worker", "SharedWorker", "caches", "indexedDB"';
  await runLine(`import js; print("reachable:", [n for n in (${names}) if getattr(js, n, None) is not None] or "none")`);
  await expect(console_).toContainText("reachable: none", { timeout: 45_000 });

  await runLine(
    'import js; from pyodide.ffi import to_js; r = await js.fetch("/api/auth/refresh/", to_js({"method": "POST", "credentials": "include"}, dict_converter=js.Object.fromEntries)); print("refresh", r.status)',
  );
  await expect(console_).toContainText(/(AttributeError|TypeError)/);
  await expect(console_).not.toContainText("refresh 200");

  // Ordinary programs still run.
  await runLine("print(sum(range(5)))");
  await expect(console_).toContainText("10");
});

test("HTML and JavaScript previews can't reach the page, the session or its storage", async ({ page }) => {
  // Lessons' "playground" blocks run as soon as the lesson opens, in a sandboxed frame with no origin of
  // its own: their scripts must not touch the app, its cookies or storage, or get a session from the API.
  await login(page, "aline");
  await page.goto("/playground");
  const editor = page.getByLabel("Code editor", { exact: true });
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.press("Delete");
  await page.keyboard.insertText(
    '<p id="out">running</p><script>(async () => { const r = []; ' +
      'try { r.push("parent:" + (parent.document ? "open" : "blocked")); } catch { r.push("parent:blocked"); } ' +
      'try { localStorage.getItem("iga.user"); r.push("storage:open"); } catch { r.push("storage:blocked"); } ' +
      'try { r.push("cookie:" + (document.cookie ? "open" : "blocked")); } catch { r.push("cookie:blocked"); } ' +
      'try { const res = await fetch("/api/auth/refresh/", { method: "POST", credentials: "include" }); r.push("refresh:" + res.status); } catch { r.push("refresh:blocked"); } ' +
      'document.getElementById("out").textContent = r.join(" "); })();</script>',
  );
  await page.getByRole("button", { name: /^run$/i }).click();
  const out = page.frameLocator('iframe[title="Preview"]').locator("#out");
  await expect(out).toHaveText("parent:blocked storage:blocked cookie:blocked refresh:blocked", { timeout: 15_000 });
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

  await page.getByLabel("SQL editor").click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.insertText("CREATE TABLE t (x INTEGER);\nSELEC x FROM t;");
  await page.getByRole("button", { name: /run/i }).click();
  await expect(output.locator(".sql-error")).toContainText(/syntax error/i);
});

test("C++ and Java run on the code runner and wait for answers in the console", async ({ page }) => {
  // The E2E server has no code runner, so its API is mocked here; tests/test_coderun.py and
  // coderunner/test_server.py cover the real thing.
  await page.route("**/api/code/status/", (route) => route.fulfill({ json: { enabled: true, languages: ["cpp", "java"] } }));
  const sent = [];
  await page.route("**/api/code/run/", async (route) => {
    const body = route.request().postDataJSON();
    sent.push(body);
    if (body.code.includes("oops")) {
      return route.fulfill({
        json: { state: "finished", verdict: "compile_error", output: [{ stream: "compile", text: "main.cpp:2:3: error: 'oops' was not declared in this scope\n" }] },
      });
    }
    if (body.language === "java") {
      return route.fulfill({ json: { session: "j1", state: "waiting", output: [{ stream: "stdout", text: "What is your name? " }] } });
    }
    return route.fulfill({ json: { session: "c1", state: "waiting", output: [{ stream: "stdout", text: "What is your name? " }] } });
  });
  await page.route("**/api/code/input/", async (route) => {
    const body = route.request().postDataJSON();
    sent.push(body);
    route.fulfill({
      json: { session: body.session, state: "finished", verdict: "ok", exit_code: 0, output: [{ stream: "stdout", text: `\nMuraho, ${body.text}!\n` }] },
    });
  });

  await login(page, "aline");
  await page.goto("/playground");
  await page.getByRole("tab", { name: /c\+\+/i }).click();
  const console_ = page.locator(".console");
  await page.getByRole("button", { name: /^run$/i }).click();
  await expect(console_).toContainText("What is your name?");
  await page.getByLabel("Your answer").fill("Aline");
  await page.getByLabel("Your answer").press("Enter");
  await expect(console_).toContainText("Muraho, Aline!");
  await expect(console_).toContainText("Finished");
  expect(sent[0].language).toBe("cpp");
  expect(sent[1]).toEqual({ session: "c1", text: "Aline" });

  const editor = page.getByLabel("C++ code editor");
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.insertText("int main() {\noops;\n}");
  await page.getByRole("button", { name: /^run$/i }).click();
  await expect(console_).toContainText("did not compile");
  await expect(console_).toContainText("'oops' was not declared");

  await page.getByRole("tab", { name: /java/i }).click();
  await page.getByRole("button", { name: /^run$/i }).click();
  await page.getByLabel("Your answer").fill("Eric");
  await page.getByLabel("Your answer").press("Enter");
  await expect(page.locator(".console")).toContainText("Muraho, Eric!");
});

test("C++ says when the student has used today's time on the code runner", async ({ page }) => {
  const detail =
    "You have used today's time on the code runner. C++ and Java can run again tomorrow; Python, SQL and web pages still run in your browser.";
  await page.route("**/api/code/status/", (route) => route.fulfill({ json: { enabled: true, languages: ["cpp", "java"] } }));
  await page.route("**/api/code/run/", (route) => route.fulfill({ status: 429, json: { detail, code: "daily_limit" } }));
  await login(page, "aline");
  await page.goto("/playground");
  await page.getByRole("tab", { name: /c\+\+/i }).click();
  await page.getByRole("button", { name: /^run$/i }).click();
  await expect(page.locator(".console")).toContainText("used today's time on the code runner");
  await expect(page.getByRole("button", { name: /^run$/i })).toBeEnabled(); // nothing left running
});

test("C++ and Java say when the server has no code runner", async ({ page }) => {
  await login(page, "aline");
  await page.goto("/playground");
  await page.getByRole("tab", { name: /java/i }).click();
  await expect(page.getByText(/not switched on for this server yet/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /^run$/i })).toBeDisabled();
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
  // A roster account accepts the Terms of Use and Privacy Policy at its first sign-in, with its new password.
  await page.getByLabel(/i have read and accept/i).check();
  await page.getByRole("button", { name: /save my password/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/hi keza/i);
});
