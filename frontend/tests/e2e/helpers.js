import { expect } from "@playwright/test";

export const PASSWORD = "Iga-demo-2026";

export async function login(page, username) {
  await page.goto("/login");
  await page.getByLabel(/username or email/i).fill(username);
  await page.getByLabel(/^password$/i).fill(PASSWORD);
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/hi /i);
}

export async function logout(page) {
  await page.goto("/profile");
  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page).toHaveURL(/\/($|login)/);
}
