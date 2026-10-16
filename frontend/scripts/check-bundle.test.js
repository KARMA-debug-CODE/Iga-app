// scripts/check-bundle.mjs runs after every build and fails it if the built app holds a secret, an
// internal address or a source map. These tests feed it a made-up bundle.
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { buildSecrets, checkDist, scanText } from "./check-bundle.mjs";

let dist;
afterEach(() => dist && rmSync(dist, { recursive: true, force: true }));

function bundle(files) {
  dist = mkdtempSync(join(tmpdir(), "iga-dist-"));
  for (const [name, text] of Object.entries(files)) {
    mkdirSync(join(dist, name, ".."), { recursive: true });
    writeFileSync(join(dist, name), text);
  }
  return dist;
}

describe("the bundle check", () => {
  it("passes the app as it is built", () => {
    expect(scanText('const BASE = "/api"; fetch(`${BASE}/tutor/status/`); new URL("http://localhost");')).toEqual([]);
  });

  it("finds secrets, internal addresses and source maps", () => {
    expect(scanText('fetch("http://backend:8000/api/")')).toEqual(["an address inside the Docker network"]);
    expect(scanText('const db = "postgres://iga_app:pw@db:5432/iga"')).toEqual([
      "a database or cache URL",
      "an address inside the Docker network",
    ]);
    expect(scanText("const k = 'FLWSECK-1a2b3c'")).toEqual(["a Flutterwave secret key"]);
    expect(scanText("x.CODE_RUNNER_TOKEN")).toEqual(["a server setting's name"]);
    expect(scanText("var a=1;\n//# sourceMappingURL=index.js.map")).toEqual(["a source map link"]);
    expect(scanText("const t = 'abc-the-real-runner-token-value'", ["the-real-runner-token-value"])).toEqual([
      "the value of a secret in the build's environment",
    ]);
  });

  it("takes the secrets of the build's own environment", () => {
    const env = { DJANGO_SECRET_KEY: "a-long-secret-value-1234", npm_config_cache_key: "ignored-npm-setting", PATH: "/usr/bin", SHORT_TOKEN: "abc" };
    expect(buildSecrets(env)).toEqual(["a-long-secret-value-1234"]);
  });

  it("checks every file of dist/ except the third-party runtimes", () => {
    const root = bundle({
      "index.html": "<script src='/assets/index.js'></script>",
      "assets/index.js": "fetch('/api/')",
      "assets/index.js.map": "{}",
      "assets/leak.js": "const url = 'redis://redis:6379/0'",
      "pyodide/pyodide.asm.js": "redis://whatever (third-party, not checked)",
    });
    expect(checkDist(root, []).sort()).toEqual(
      [
        "assets/index.js.map: a source map",
        "assets/leak.js: a database or cache URL",
        "assets/leak.js: an address inside the Docker network",
      ].sort(),
    );
  });
});
