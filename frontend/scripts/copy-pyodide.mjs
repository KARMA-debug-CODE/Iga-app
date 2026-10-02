// Copies the Pyodide runtime from node_modules into public/pyodide so the app
// serves Python itself (no third-party CDN; the service worker can cache it for offline use).
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const from = join(root, "node_modules", "pyodide");
const to = join(root, "public", "pyodide");
const FILES = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"];

if (!existsSync(from)) {
  console.warn("pyodide is not installed; skipping copy (Python playground will be unavailable).");
  process.exit(0);
}
mkdirSync(to, { recursive: true });
for (const file of FILES) copyFileSync(join(from, file), join(to, file));
console.log(`Copied Pyodide runtime to public/pyodide (${FILES.length} files).`);
