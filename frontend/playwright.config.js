import { defineConfig, devices } from "@playwright/test";

// Runs the real Django API (fresh SQLite DB with demo data) and the Vite dev server.
const python = process.env.PYTHON || "../backend/.venv/bin/python";
const backendCmd = [
  "rm -f e2e.sqlite3",
  `${python} manage.py migrate -v0`,
  `${python} manage.py seed_demo > /dev/null`,
  `${python} manage.py runserver 127.0.0.1:8000 --noreload`,
].join(" && ");

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
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
      url: "http://127.0.0.1:8000/api/health/",
      env: { DATABASE_URL: "sqlite:///e2e.sqlite3", DJANGO_DEBUG: "true", THROTTLE_AUTH: "1000/min" },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
