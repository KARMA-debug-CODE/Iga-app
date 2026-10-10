// Iga uses line icons (components/Icon.jsx) or plain words, never emojis or pictographic "stickers".
// This test reads the app's own files and fails with file:line for every emoji it finds.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

// Folders and files to check, and folders inside them that are not ours (or old migrations, which never change).
const CHECKED = ["frontend/src", "frontend/index.html", "frontend/public", "backend/apps", "backend/content", "backend/templates", "docs", "README.md"];
const SKIPPED_DIRS = new Set(["node_modules", "__pycache__", "migrations", "pyodide", "runtimes", "dist"]);
const BINARY = new Set([".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf", ".pdf", ".zip", ".wasm", ".mo", ".sqlite3"]);

// Pictographs, skin tones, flag letters, and the invisible joiners left behind when an emoji is half deleted.
const EMOJI = /[\p{Extended_Pictographic}\p{Emoji_Modifier}\p{Regional_Indicator}\u{FE0F}\u{200D}]/gu;
const ALLOWED = new Set(["\u{A9}", "\u{AE}", "\u{2122}"]); // copyright, registered, trade mark

function files(path) {
  const stat = statSync(path, { throwIfNoEntry: false });
  if (!stat) return [];
  if (stat.isFile()) return BINARY.has(extname(path).toLowerCase()) ? [] : [path];
  return readdirSync(path)
    .filter((name) => !SKIPPED_DIRS.has(name))
    .flatMap((name) => files(join(path, name)));
}

export function findEmojis(text) {
  const found = [];
  text.split("\n").forEach((line, i) => {
    for (const [char] of line.matchAll(EMOJI)) {
      if (!ALLOWED.has(char)) found.push({ line: i + 1, char });
    }
  });
  return found;
}

describe("no emojis", () => {
  it("knows an emoji when it sees one", () => {
    expect(findEmojis("Hi \u{1F44B}\nSaved \u{2705}\nok \u{A9} \u{2122} \u{2192} \u{D7} \u{221A} \u{3C0} \u{B0} \u{AB} \u{BB}")).toEqual([
      { line: 1, char: "\u{1F44B}" },
      { line: 2, char: "\u{2705}" },
    ]);
    expect(findEmojis("\u{1F1F7}\u{1F1FC} \u{1F9D1}\u{1F3FD}\u{200D}\u{1F3EB} \u{26A0}\u{FE0F}")).toHaveLength(8);
  });

  it("finds none in the app, its content or its docs", () => {
    const checked = CHECKED.flatMap((path) => files(join(ROOT, path)));
    expect(checked.length).toBeGreaterThan(300);
    const problems = checked.flatMap((path) => {
      const name = relative(ROOT, path);
      return findEmojis(readFileSync(path, "utf8")).map(
        ({ line, char }) => `${name}:${line}: U+${char.codePointAt(0).toString(16).toUpperCase().padStart(4, "0")} ${char}`,
      );
    });
    expect(problems).toEqual([]);
  });
});
