import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n";
import { pendingNote } from "../notes-offline";
import LessonNotes from "./LessonNotes";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const state = (slug) => ({ lesson: { slug, title: "T" }, bookmarked: false, bookmark_id: null, note: null });

function show(slug) {
  localStorage.setItem("iga.lang", "en");
  return render(
    <I18nProvider>
      <LessonNotes slug={slug} />
    </I18nProvider>,
  );
}

beforeEach(() => localStorage.clear());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("LessonNotes", () => {
  it("writes a private note and saves it to the server", async () => {
    const calls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init = {}) => {
        const method = init.method || "GET";
        calls.push({ url, method, body: init.body });
        if (url.includes("/my-notes/")) return jsonResponse(state("note-ok"));
        if (url.includes("/notes/")) return jsonResponse({ id: 3, body: "my note", lesson: { slug: "note-ok" } }, 201);
        throw new Error(`no route ${method} ${url}`);
      }),
    );
    show("note-ok");

    expect(await screen.findByRole("heading", { name: /my notes/i })).toBeInTheDocument();
    expect(screen.getByText(/only you can see this/i)).toBeInTheDocument();

    const box = screen.getByLabelText(/your private note/i);
    fireEvent.change(box, { target: { value: "my note" } });
    expect(screen.getByText("7/5000")).toBeInTheDocument();
    fireEvent.blur(box);

    await waitFor(() => expect(screen.getByText(/^saved$/i)).toBeInTheDocument());
    const post = calls.find((c) => c.method === "POST" && c.url.includes("/notes/"));
    expect(JSON.parse(post.body)).toEqual({ lesson: "note-ok", body: "my note" });
    expect(pendingNote("note-ok")).toBeNull();
  });

  it("keeps a note on the device when offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url) => {
        if (url.includes("/my-notes/")) return jsonResponse(state("note-off"));
        if (url.includes("/notes/")) return Promise.reject(new TypeError("Failed to fetch"));
        throw new Error(`no route ${url}`);
      }),
    );
    show("note-off");

    const box = await screen.findByLabelText(/your private note/i);
    fireEvent.change(box, { target: { value: "offline thought" } });
    fireEvent.blur(box);

    await waitFor(() => expect(screen.getByText(/saved on this device/i)).toBeInTheDocument());
    expect(pendingNote("note-off")).toBe("offline thought");
  });

  it("toggles a bookmark", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init = {}) => {
        const method = init.method || "GET";
        if (url.includes("/my-notes/")) return jsonResponse(state("note-bm"));
        if (url.includes("/bookmarks/") && method === "POST") return jsonResponse({ id: 9, lesson: { slug: "note-bm" } }, 201);
        throw new Error(`no route ${method} ${url}`);
      }),
    );
    show("note-bm");

    const button = await screen.findByRole("button", { name: /^bookmark$/i });
    expect(button).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(button);
    await waitFor(() => expect(screen.getByRole("button", { name: /bookmarked/i })).toHaveAttribute("aria-pressed", "true"));
  });
});
