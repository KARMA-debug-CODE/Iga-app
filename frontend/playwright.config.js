import { defineConfig, devices } from "@playwright/test";

// Runs the real Django API (fresh SQLite DB with demo data) and the Vite dev server.
// E2E_API_PORT / E2E_WEB_PORT let two checkouts run their tests at the same time.
const python = process.env.PYTHON || "../backend/.venv/bin/python";
const apiPort = process.env.E2E_API_PORT || "8000";
const webPort = process.env.E2E_WEB_PORT || "5173";
const backendCmd = [
  "rm -f e2e.sqlite3",
  `${python} manage.py migrate -v0`,
  `${python} manage.py seed_demo > /dev/null`,
  `${python} manage.py runserver 127.0.0.1:${apiPort} --noreload`,
].join(" && ");

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    // French browsers would switch the app to French; the assertions are in English.
    locale: "en-GB",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "mobile", use: { ...devices["Pixel 7"] } },
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      command: `cd ../backend && ${backendCmd}`,
      url: `http://127.0.0.1:${apiPort}/api/health/`,
      env: { DATABASE_URL: "sqlite:///e2e.sqlite3", DJANGO_DEBUG: "true", THROTTLE_AUTH: "1000/min", THROTTLE_LOGIN: "1000/min", THROTTLE_ANON: "10000/min", THROTTLE_USER: "10000/min" },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${webPort} --strictPort`,
      url: `http://127.0.0.1:${webPort}`,
      env: { VITE_BACKEND_URL: `http://127.0.0.1:${apiPort}` },
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
