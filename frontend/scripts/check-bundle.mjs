// Runs after every build (npm's "postbuild", so the web image's build too): the built app is public, so
// it must hold no server secret, no internal address of the Docker network and no source map. The source
// side is checked by src/no-server-secrets.test.js; this checks what Vite actually wrote to dist/.
// The self-hosted runtimes (dist/pyodide, dist/runtimes) are third-party files copied as they are.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const DIST = join(dirname(fileURLToPath(import.meta.url)), "..", "dist");
const SKIPPED = new Set(["pyodide", "runtimes"]);
const TEXT = new Set([".js", ".mjs", ".css", ".html", ".json", ".webmanifest", ".svg", ".txt", ".map"]);

const PATTERNS = [
  [/\b(?:postgres(?:ql)?|mysql|redis):\/\/\S/i, "a database or cache URL"],
  [/\b(?:backend:8000|coderunner:2000|santa:8080|db:5432|redis:6379)\b/, "an address inside the Docker network"],
  [/\b(?:DJANGO_SECRET_KEY|CODE_RUNNER_TOKEN|SANTA_API_KEY|FIELD_ENCRYPTION_KEYS?|LEDGER_HMAC_KEY|DATABASE_URL|POSTGRES_[A-Z_]*PASSWORD|FLUTTERWAVE_SECRET_KEY|FLUTTERWAVE_WEBHOOK_HASH|EMAIL_HOST_PASSWORD|HF_TOKEN)\b/, "a server setting's name"],
  [/FLWSECK(?:_TEST)?-[0-9a-f]/i, "a Flutterwave secret key"],
  [/-----BEGIN [A-Z ]*PRIVATE KEY-----/, "a private key"],
  [/\b(?:AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|hf_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{30,}|xox[abp]-[A-Za-z0-9-]{10,})\b/, "an API token"],
  [/^\/\/[#@] sourceMappingURL=/m, "a source map link"],
];

/** Problems in one file's text. `secrets` are values that must not appear (the build's own secrets). */
export function scanText(text, secrets = []) {
  const found = PATTERNS.filter(([pattern]) => pattern.test(text)).map(([, what]) => what);
  if (secrets.some((value) => text.includes(value))) found.push("the value of a secret in the build's environment");
  return found;
}

/** Secrets set where the app is built (a CI runner, a server): their values must not reach the bundle. */
export function buildSecrets(env = process.env) {
  return Object.entries(env)
    .filter(([name, value]) => /SECRET|TOKEN|PASSWORD|PRIVATE|_KEY|_KEYS|HASH/.test(name) && !name.startsWith("npm_") && value && value.length >= 12)
    .map(([, value]) => value);
}

function files(folder, top = true) {
  return readdirSync(folder).flatMap((name) => {
    const path = join(folder, name);
    if (statSync(path).isDirectory()) return top && SKIPPED.has(name) ? [] : files(path, false);
    return [path];
  });
}

export function checkDist(dist = DIST, secrets = buildSecrets()) {
  const problems = [];
  for (const path of files(dist)) {
    const name = relative(dist, path);
    if (extname(path) === ".map") problems.push(`${name}: a source map`);
    else if (TEXT.has(extname(path))) problems.push(...scanText(readFileSync(path, "utf8"), secrets).map((what) => `${name}: ${what}`));
  }
  return problems;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const problems = checkDist();
  if (problems.length) {
    console.error(`The built app must not contain these (see scripts/check-bundle.mjs):\n  ${problems.join("\n  ")}`);
    process.exit(1);
  }
  console.log("Bundle check: no secrets, internal addresses or source maps in dist/.");
}
