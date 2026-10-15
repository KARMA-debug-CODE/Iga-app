// The browser never talks to the database: it only calls /api/, and Django makes every query. So no
// database URL, password or key, and no other server secret, may ever be part of the app. This test reads
// everything that goes into the built app (Vite only puts VITE_* variables into the bundle) and fails
// with file:line for anything that looks like one.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const FRONTEND = join(dirname(fileURLToPath(import.meta.url)), "..");
const CHECKED = ["src", "index.html", "public", "vite.config.js", "Dockerfile", "nginx.conf"];
const SKIPPED_DIRS = new Set(["node_modules", "pyodide", "runtimes", "dist"]);
const BINARY = new Set([".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf", ".pdf", ".wasm"]);
const THIS_FILE = "src/no-server-secrets.test.js";

// The only build-time values the app may read: none of them is a secret.
const ALLOWED_ENV = new Set(["VITE_API_BASE", "VITE_SHOW_DEMO_ACCOUNTS", "DEV", "PROD", "MODE", "BASE_URL", "SSR"]);

const SECRET_PATTERNS = [
  [/\b(postgres(ql)?|mysql|redis|sqlite):\/\//i, "a database or cache URL"],
  // No \b before these: "_" is a word character, so VITE_DATABASE_URL must still match.
  [/DATABASE_URL|DB_(OWNER|APP)_URL|POSTGRES_[A-Z_]*PASSWORD/, "database settings"],
  [/DJANGO_SECRET_KEY|(?<!FLUTTERWAVE_)SECRET_KEY/, "Django's secret key"],
  [/FLWSECK[-_]|FLUTTERWAVE_(SECRET_KEY|WEBHOOK_HASH)/, "a Flutterwave secret"],
  [/SANTA_API_KEY|CODE_RUNNER_TOKEN|HF_TOKEN/, "an internal service secret"],
  [/FIELD_ENCRYPTION_KEYS?/, "the database field encryption key"],
  [/\bservice_role\b|\bsupabase\b/i, "a hosted-database key"],
  [/-----BEGIN [A-Z ]*PRIVATE KEY-----/, "a private key"],
];

function files(path) {
  const stat = statSync(path, { throwIfNoEntry: false });
  if (!stat) return [];
  if (stat.isFile()) return BINARY.has(extname(path).toLowerCase()) ? [] : [path];
  return readdirSync(path)
    .filter((name) => !SKIPPED_DIRS.has(name))
    .flatMap((name) => files(join(path, name)));
}

export function findSecrets(text) {
  const found = [];
  text.split("\n").forEach((line, i) => {
    for (const [pattern, what] of SECRET_PATTERNS) {
      if (pattern.test(line)) found.push({ line: i + 1, what });
    }
    for (const [, name] of line.matchAll(/import\.meta\.env\.([A-Za-z_][A-Za-z0-9_]*)/g)) {
      if (!ALLOWED_ENV.has(name)) found.push({ line: i + 1, what: `build-time variable ${name}` });
    }
    if (/import\.meta\.env\s*\[|\{\s*\.\.\.import\.meta\.env\s*\}|JSON\.stringify\(\s*import\.meta\.env\s*\)/.test(line)) {
      found.push({ line: i + 1, what: "the whole build environment" });
    }
  });
  return found;
}

describe("no server secrets in the app", () => {
  it("knows a secret when it sees one", () => {
    expect(findSecrets('const db = "postgres://iga:pw@db:5432/iga";').map((f) => f.what)).toEqual(["a database or cache URL"]);
    expect(findSecrets("fetch(import.meta.env.VITE_DATABASE_URL)").map((f) => f.what)).toEqual([
      "database settings",
      "build-time variable VITE_DATABASE_URL",
    ]);
    expect(findSecrets("const all = { ...import.meta.env };")).toHaveLength(1);
    expect(findSecrets('const BASE = import.meta.env.VITE_API_BASE || "/api";')).toEqual([]);
  });

  it("finds none in the frontend's files", () => {
    const problems = CHECKED.flatMap((entry) => files(join(FRONTEND, entry)))
      .filter((path) => relative(FRONTEND, path).split("\\").join("/") !== THIS_FILE)
      .flatMap((path) => findSecrets(readFileSync(path, "utf8")).map(({ line, what }) => `${relative(FRONTEND, path)}:${line} ${what}`));
    expect(problems).toEqual([]);
  });

  it("keeps Vite's rule that only VITE_ variables reach the browser", () => {
    const config = readFileSync(join(FRONTEND, "vite.config.js"), "utf8");
    expect(config).not.toMatch(/envPrefix/);
    expect(config).not.toMatch(/define\s*:/);
  });
});
