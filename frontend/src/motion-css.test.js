// The motion rules (motion.css): animations move only transform and opacity, so the browser never has to lay
// the page out again while something moves, and nothing moves for readers who ask for less motion.
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const SRC = dirname(fileURLToPath(import.meta.url));

function cssFiles(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return entry.name === "node_modules" ? [] : cssFiles(path);
    return entry.name.endsWith(".css") ? [path] : [];
  });
}

/** The text inside the braces that open at `start` (the index of "{"). */
function block(text, start) {
  let depth = 0;
  for (let i = start; i < text.length; i++) {
    if (text[i] === "{") depth++;
    else if (text[i] === "}" && --depth === 0) return text.slice(start + 1, i);
  }
  throw new Error("unbalanced braces");
}

const withoutComments = (css) => css.replace(/\/\*[\s\S]*?\*\//g, "");

// The score ring's fill (--ring-fill) is the one exception: a small repaint of one ring.
const MOVABLE = new Set(["transform", "opacity", "--ring-fill"]);

describe("animations", () => {
  const files = cssFiles(SRC);

  it("are found in the app's stylesheets", () => {
    expect(files.map((f) => relative(SRC, f))).toEqual(expect.arrayContaining(["styles.css", "motion.css"]));
  });

  it("only animate transform and opacity", () => {
    const offenders = [];
    for (const file of files) {
      const css = withoutComments(readFileSync(file, "utf8"));
      for (const match of css.matchAll(/@keyframes\s+([\w-]+)\s*\{/g)) {
        const body = block(css, match.index + match[0].length - 1);
        for (const [, property] of body.matchAll(/([\w-]+)\s*:/g)) {
          if (!MOVABLE.has(property)) offenders.push(`${relative(SRC, file)} @keyframes ${match[1]}: ${property}`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });

  it("in motion.css transition only transform and opacity", () => {
    const css = withoutComments(readFileSync(join(SRC, "motion.css"), "utf8"));
    const transitioned = [...css.matchAll(/transition(?:-property)?\s*:\s*([^;]+);/g)].flatMap(([, value]) =>
      value.split(",").map((part) => part.trim().split(/\s+/)[0]),
    );
    expect(transitioned.length).toBeGreaterThan(0);
    expect(transitioned.filter((p) => !MOVABLE.has(p))).toEqual([]);
  });

  it("stop for readers who ask for less motion", () => {
    const css = withoutComments(readFileSync(join(SRC, "motion.css"), "utf8"));
    const match = css.match(/@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{/);
    expect(match).not.toBeNull();
    const body = block(css, match.index + match[0].length - 1);
    for (const rule of ["animation-duration", "animation-iteration-count", "transition-duration", "animation-delay"]) {
      expect(body).toContain(rule);
    }
    expect(body).toMatch(/\.burst[\s\S]*display:\s*none/); // celebrations aren't drawn at all
  });

  it("use the shared duration tokens from styles.css", () => {
    const styles = readFileSync(join(SRC, "styles.css"), "utf8");
    for (const token of ["--motion-fast", "--motion-base", "--motion-slow", "--ease-out", "--ease-spring", "--stagger"]) {
      expect(styles).toContain(`${token}:`);
    }
    const motion = readFileSync(join(SRC, "motion.css"), "utf8");
    expect(motion).toContain("var(--motion-base)");
  });
});
