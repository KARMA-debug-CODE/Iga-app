import { expect, test } from "@playwright/test";

// The app as nginx serves it in production, with its Content-Security-Policy and other security headers on:
// every feature that loads code, styles, workers, frames or streams must still work, and the browser must
// report no CSP violation (S41). Run against the Docker stack: see playwright.docker.config.js.

const PASSWORD = "Iga-demo-2026";
let violations;

test.beforeEach(async ({ page }) => {
  violations = [];
  page.on("console", (message) => {
    const text = message.text();
    if (/content security policy|csp violation/i.test(text)) violations.push(text);
  });
  // Also catch violations the console doesn't show as such (for example in frames).
  await page.addInitScript(() => {
    window.addEventListener("securitypolicyviolation", (event) => {
      console.error(`CSP violation: ${event.violatedDirective} blocked ${event.blockedURI || "inline code"} (${event.sourceFile}:${event.lineNumber})`);
    });
  });
});

test.afterEach(() => {
  expect(violations, "Content-Security-Policy violations").toEqual([]);
});

async function login(page, username = "aline") {
  await page.goto("/login");
  await page.getByLabel(/username or email/i).fill(username);
  await page.getByLabel(/^password$/i).fill(PASSWORD);
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/hi /i);
}

test("the app is served with its security headers", async ({ page }) => {
  const response = await page.goto("/");
  const headers = response.headers();
  expect(headers["content-security-policy"]).toContain("script-src 'self' 'wasm-unsafe-eval'");
  expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(headers["content-security-policy"]).not.toMatch(/script-src[^;]*'unsafe-(inline|eval)'/);
  expect(headers["x-frame-options"]).toBe("DENY");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(headers["cross-origin-opener-policy"]).toBe("same-origin");
  expect(headers["cross-origin-resource-policy"]).toBe("same-origin");
  expect(headers["permissions-policy"]).toContain("camera=()");
  const api = await page.request.get("/api/meta/");
  expect(api.headers()["content-security-policy"]).toContain("default-src 'none'");
  expect(api.headers()["x-frame-options"]).toBe("DENY");
});

test("signing in and a lesson with maths", async ({ page }) => {
  await login(page);
  await page.goto("/lessons/s2-maths-linear-graphs");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.locator(".katex").first()).toBeVisible();
  // KaTeX's fonts and styles load: a rendered fraction or symbol has a real size.
  const box = await page.locator(".katex").first().boundingBox();
  expect(box.width).toBeGreaterThan(0);
});

test("labs: a built-in lab, and the PhET and GeoGebra embeds are allowed to load", async ({ page }) => {
  await login(page);
  await page.goto("/labs/ohms-law-lab");
  await expect(page.getByRole("img", { name: /circuit/i })).toBeVisible();

  await page.goto("/labs/phet-ohms-law");
  await page.getByRole("button", { name: /launch simulation/i }).click();
  // The frame is created and the browser asks PhET for the page (frame-src allows it; a CSP refusal never
  // sends the request, whether or not this machine can reach phet.colorado.edu).
  await expect(page.locator('iframe[src^="https://phet.colorado.edu/"]')).toHaveCount(1);

  await page.goto("/labs/geogebra-graphing");
  const loader = page.waitForRequest((request) => request.url().startsWith("https://www.geogebra.org/apps/deployggb.js"));
  await page.getByRole("button", { name: /launch simulation/i }).click();
  await loader;
});

test("the Python playground runs Python in its worker", async ({ page }) => {
  await login(page);
  await page.goto("/playground");
  await page.getByRole("tab", { name: /python/i }).click();
  const output = page.locator(".console");
  await page.getByRole("button", { name: /^run$/i }).click();
  await expect(output).toContainText("What is your name?", { timeout: 90_000 });
  await page.getByLabel("Your answer").fill("Aline");
  await page.getByLabel("Your answer").press("Enter");
  await expect(output).toContainText("Muraho, Aline!");
});

test("the SQL playground runs SQLite in its worker", async ({ page }) => {
  await login(page);
  await page.goto("/playground");
  await page.getByRole("tab", { name: /sql/i }).click();
  await page.getByRole("button", { name: /^run$/i }).click();
  await expect(page.locator("table").first()).toBeVisible({ timeout: 60_000 });
});

test("the HTML playground runs the student's inline scripts and styles, sandboxed", async ({ page }) => {
  await login(page);
  await page.goto("/playground");
  const editor = page.getByLabel(/code editor/i).first();
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.press("Delete");
  await page.keyboard.insertText(
    '<p id="out">waiting</p><p id="storage"></p><style>#out { color: rgb(1, 2, 3); }</style>' +
      "<script>document.getElementById('out').textContent = 'script ran ' + 6 * 7;" +
      "try { localStorage.setItem('x', '1'); document.getElementById('storage').textContent = 'storage'; }" +
      " catch (e) { document.getElementById('storage').textContent = 'no storage'; }</script>",
  );
  await page.getByRole("button", { name: /^run$/i }).click();
  const preview = page.frameLocator('iframe[title="Preview"]');
  await expect(preview.locator("#out")).toHaveText("script ran 42");
  await expect(preview.locator("#out")).toHaveCSS("color", "rgb(1, 2, 3)");
  // Sandboxed: no access to Iga's storage (or cookies, or the page around it).
  await expect(preview.locator("#storage")).toHaveText("no storage");
});

test("Santa streams an answer (from the lessons, without its model)", async ({ page }) => {
  await login(page);
  await page.goto("/ask");
  await expect(page.getByText(/santa's ai model isn't installed yet/i)).toBeVisible();
  const box = page.getByLabel(/type your question/i);
  await box.fill("What does the cell membrane control?");
  await box.press("Enter");
  const answer = page.locator(".santa-answer").last();
  await expect(answer.getByText(/here is what your lessons say/i)).toBeVisible();
  await expect(answer.getByText(/controls what enters and leaves/i).first()).toBeVisible();
});

test("the calculator", async ({ page }) => {
  await login(page);
  await page.goto("/calculator");
  const calc = page.getByRole("region", { name: "Calculator" });
  for (const name of ["2", "Plus", "3", "Equals"]) await calc.getByRole("button", { name, exact: true }).click();
  await expect(calc.getByRole("status")).toHaveText("Display is 5");
});
