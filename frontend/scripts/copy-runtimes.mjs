// Copies the in-browser language runtimes from node_modules into public/ so the app serves them itself
// (no third-party CDN, and the service worker can cache them for offline use):
//   public/pyodide/          Python (Pyodide)
//   public/runtimes/sqljs/   SQL (SQLite compiled to WebAssembly, sql.js)
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const RUNTIMES = [
  {
    name: "Pyodide",
    from: join(root, "node_modules", "pyodide"),
    to: join(root, "public", "pyodide"),
    files: ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"],
  },
  {
    name: "sql.js",
    from: join(root, "node_modules", "sql.js", "dist"),
    to: join(root, "public", "runtimes", "sqljs"),
    files: ["sql-wasm-browser.js", "sql-wasm-browser.wasm"],
  },
];

for (const runtime of RUNTIMES) {
  if (!existsSync(runtime.from)) {
    console.warn(`${runtime.name} is not installed; skipping (that playground language will be unavailable).`);
    continue;
  }
  mkdirSync(runtime.to, { recursive: true });
  for (const file of runtime.files) copyFileSync(join(runtime.from, file), join(runtime.to, file));
  console.log(`Copied ${runtime.name} to ${runtime.to.slice(root.length + 1)} (${runtime.files.length} files).`);
}
