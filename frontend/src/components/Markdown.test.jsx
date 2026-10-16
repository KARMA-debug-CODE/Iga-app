// What people write (shared notes, questions, Santa's answers) is shown through this Markdown renderer:
// it must never run a script, follow an unsafe link or load pictures from other sites.
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Markdown from "./Markdown";

function show(text, interactive = false) {
  return render(<Markdown interactive={interactive}>{text}</Markdown>).container;
}

describe("Markdown from people", () => {
  it("shows raw HTML as text instead of running it", () => {
    const html = '<script>window.hacked = 1</script> <img src=x onerror="window.hacked = 2"> <a href="javascript:alert(1)">x</a>';
    const box = show(html);
    expect(box.querySelector("script")).toBeNull();
    expect(box.querySelector("img")).toBeNull();
    expect(box.querySelector("a")).toBeNull();
    expect(box.textContent).toContain("<script>window.hacked = 1</script>");
    expect(window.hacked).toBeUndefined();
  });

  it.each([
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    " javascript:alert(1)",
    "java\tscript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
  ])("drops the unsafe link target %s", (target) => {
    const box = show(`[click me](${target}) and <${target}>`);
    for (const a of box.querySelectorAll("a")) {
      const href = a.getAttribute("href") || "";
      expect(href).not.toMatch(/^\s*(javascript|data|vbscript|file):/i);
      expect(href.replace(/\s/g, "")).not.toMatch(/script:/i);
    }
  });

  it.each(["https://www.reb.rw/", "//www.reb.rw/", "HTTP://www.reb.rw/", "mailto:info@reb.rw"])(
    "opens %s in a new tab without giving it this page",
    (href) => {
      const link = show(`[REB](${href})`).querySelector("a");
      expect(link.getAttribute("href")).toBe(href);
      expect(link.getAttribute("target")).toBe("_blank");
      expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    },
  );

  it("keeps links to this site's pages in the same tab", () => {
    for (const href of ["/lessons/forces", "#answer", "lessons/forces"]) {
      const link = show(`[here](${href})`).querySelector("a");
      expect(link.getAttribute("href")).toBe(href);
      expect(link.getAttribute("target")).toBeNull();
    }
  });

  it.each(["https://tracker.example/pixel.png", "//tracker.example/p.png", "http://10.0.0.1/a.png"])(
    "turns a picture from another site into a link: %s",
    (src) => {
      const box = show(`![a diagram](${src})`);
      expect(box.querySelector("img")).toBeNull();
      expect(box.querySelector("a")?.textContent).toBe("a diagram");
    },
  );

  it("keeps pictures in reviewed lessons, without sending the page address", () => {
    const img = show("![a diagram](https://upload.wikimedia.org/a.png)", true).querySelector("img");
    expect(img.getAttribute("src")).toBe("https://upload.wikimedia.org/a.png");
    expect(img.getAttribute("referrerpolicy")).toBe("no-referrer");
    expect(show("![logo](/icon.svg)").querySelector("img").getAttribute("src")).toBe("/icon.svg");
    // "/\host" would be another site, but the renderer encodes the backslash: it stays a path here.
    expect(show("![x](/\\tracker.example/p.png)").querySelector("img").getAttribute("src")).toBe("/%5Ctracker.example/p.png");
  });

  it("does not turn maths into links", () => {
    const box = show("$\\href{javascript:alert(1)}{click}$ and $\\url{javascript:alert(2)}$");
    expect(box.querySelector("a")).toBeNull();
  });
});
