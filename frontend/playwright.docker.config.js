import { defineConfig, devices } from "@playwright/test";

// Tests the production build behind the real nginx, with its security headers on: start the Docker stack
// first (docker compose up -d --build, then load_curriculum and seed_demo as in README.md), then
//   npx playwright test -c playwright.docker.config.js
// IGA_URL points elsewhere than http://localhost:8080.
export default defineConfig({
  testDir: "tests/docker",
  timeout: 120_000,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.IGA_URL || "http://localhost:8080",
    locale: "en-GB",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"] } }],
});
