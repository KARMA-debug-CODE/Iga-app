import { expect, test } from "@playwright/test";

import { login } from "./helpers";

// What Iga needs to go to market: public pages, consent, the account owner's rights, contact, maintenance.

test("the public pages: pricing from the server, questions, legal pages and their links", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Iga: every S1–S6 subject in one place");
  const pricing = page.locator("#pricing");
  await expect(pricing.getByText("US$200.00")).toBeVisible(); // seed_demo's server price list (SUBSCRIPTION_PRICE_USD)
  await page.getByText("Is Iga free?").click();
  await expect(page.getByText(/creating an account is free/i)).toBeVisible();

  await page.getByRole("navigation", { name: "About Iga" }).getByRole("link", { name: "Privacy Policy" }).click();
  await expect(page).toHaveURL(/\/privacy$/);
  await expect(page).toHaveTitle("Privacy Policy · Iga");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Privacy Policy");
  await expect(page.getByRole("note")).toContainText(/a lawyer must review this text/i);
  await expect(page.getByText(/Law N° 058\/2021/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /your rights/i })).toBeVisible();
  // The retention periods come from the server.
  await expect(page.getByText(/is erased 14 days later/).first()).toBeVisible();

  await page.getByRole("button", { name: "Français" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Politique de confidentialité");
  await expect(page).toHaveTitle("Politique de confidentialité · Iga");
  await page.getByRole("link", { name: "Lire les conditions d'utilisation" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Conditions d'utilisation");
  await page.getByRole("button", { name: "English" }).click();
});

test("registration needs the Terms and Privacy Policy accepted", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel(/first name/i).fill("Ganza");
  await page.getByLabel(/^username$/i).fill(`ganza${Date.now()}`);
  await page.getByLabel(/^password/i).fill("Murakoze-2026");
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page).toHaveURL(/\/register$/); // the browser asks for the box first
  const consent = page.getByLabel(/i have read and accept/i);
  await expect(consent).toBeVisible();
  await expect(page.getByRole("link", { name: /terms of use/i })).toHaveAttribute("target", "_blank");
  await consent.check();
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Hi Ganza");
});

test("a new version of the terms is accepted before the app opens", async ({ page }) => {
  // The server says this account hasn't accepted the current version (as after LEGAL_VERSION changes).
  await page.route("**/api/auth/login/", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.user.consent_required = true;
    await route.fulfill({ response, json: body });
  });
  await page.goto("/login");
  await page.getByLabel(/username or email/i).fill("divine");
  await page.getByLabel(/^password$/i).fill("Iga-demo-2026");
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("We have updated our terms");
  await page.getByLabel(/i have read and accept/i).check();
  await page.getByRole("button", { name: /accept and continue/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/hi divine/i);
});

test("download my data, then delete my account and change my mind by signing in", async ({ page }) => {
  const username = `leaver${Date.now()}`;
  await page.goto("/register");
  await page.getByLabel(/first name/i).fill("Leaver");
  await page.getByLabel(/^username$/i).fill(username);
  await page.getByLabel(/^password/i).fill("Murakoze-2026");
  await page.getByLabel(/i have read and accept/i).check();
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Hi Leaver");

  await page.goto("/profile#privacy");
  await expect(page.getByRole("tab", { name: "Privacy" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByText(/you accepted the version of/i)).toBeVisible();
  const downloading = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download my data" }).click();
  const file = await downloading;
  expect(file.suggestedFilename()).toMatch(/^iga-my-data-\d{4}-\d{2}-\d{2}\.json$/);
  await expect(page.getByText(/your file has been downloaded/i)).toBeVisible();

  await expect(page.getByText(/you have 14 days to change your mind/i)).toBeVisible();
  const remove = page.getByRole("button", { name: "Delete my account" });
  await expect(remove).toBeDisabled();
  await page.getByLabel(/i understand that my account will be deleted/i).check();
  page.once("dialog", (dialog) => dialog.accept());
  await remove.click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("status")).toContainText(/your account will be deleted on/i);

  await page.getByLabel(/username or email/i).fill(username);
  await page.getByLabel(/^password$/i).fill("Murakoze-2026");
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page.getByText("Welcome back. Your account will not be deleted.")).toBeVisible();
});

test("a visitor writes to the team, and a platform admin reads and answers it", async ({ page }) => {
  const marker = `Demo request ${Date.now()}`;
  await page.goto("/contact");
  await expect(page).toHaveTitle("Contact us · Iga");
  await page.getByLabel("Your name").fill("Jean Bosco");
  await page.getByLabel("Your email address").fill("head@example.rw");
  await page.getByLabel(/school \(optional\)/i).fill("GS Remera");
  await page.getByLabel("Message").fill(`${marker}: could you show Iga to our teachers?`);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("status")).toContainText(/we will answer you by email soon/i);

  await login(page, "admin");
  await page.goto("/admin");
  await page.getByRole("tab", { name: "Messages", exact: true }).click();
  const message = page.locator(".contact-message", { hasText: marker });
  await expect(message).toContainText("GS Remera");
  await expect(message.getByRole("link", { name: /reply by email/i })).toHaveAttribute("href", "mailto:head@example.rw");
  await message.getByRole("button", { name: /mark as answered/i }).click();
  await expect(page.locator(".contact-message", { hasText: marker })).toHaveCount(0);
  await page.getByRole("button", { name: "Answered" }).click();
  await expect(page.locator(".contact-message", { hasText: marker })).toContainText(/answered by/i);
});

test("maintenance mode shows the back-soon page, and the team can still log in", async ({ page }) => {
  await page.route("**/api/auth/refresh/", (route) =>
    route.fulfill({ status: 503, json: { detail: "Iga is being updated. We'll be back soon.", code: "maintenance" } }),
  );
  await page.goto("/learn");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Back soon");
  await expect(page.getByRole("button", { name: /try again/i })).toBeVisible();
  await page.getByRole("link", { name: /iga team: log in/i }).click();
  await expect(page).toHaveURL(/\/team$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Iga team");
  await page.unroute("**/api/auth/refresh/");
  await page.getByLabel(/username or email/i).fill("admin");
  await page.getByLabel(/^password$/i).fill("Iga-demo-2026");
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/hi /i);
});
