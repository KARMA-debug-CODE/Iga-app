import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n";
import MyNotes from "./MyNotes";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const NOTE = {
  id: 1,
  lesson: { slug: "s1-bio-cells", title: "The cell", subject: "Biology", icon: "dna", grade: "S1" },
  body: "membrane controls what enters",
  updated_at: "2026-01-02",
};
const BOOKMARK = { id: 2, lesson: { slug: "s2-maths-graphs", title: "Straight-line graphs", subject: "Mathematics", icon: "sigma", grade: "S2" }, created_at: "2026-01-01" };

let calls;
function serve() {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, init = {}) => {
      const method = init.method || "GET";
      calls.push({ url, method });
      if (url.includes("/bookmarks/")) return jsonResponse(method === "GET" ? [BOOKMARK] : [], method === "GET" ? 200 : 204);
      if (url.includes("/notes/")) {
        if (method === "DELETE") return jsonResponse([], 204);
        return jsonResponse(url.includes("q=") ? [] : [NOTE]);
      }
      throw new Error(`no route ${method} ${url}`);
    }),
  );
}

function show() {
  localStorage.setItem("iga.lang", "en");
  return render(
    <MemoryRouter>
      <I18nProvider>
        <MyNotes />
      </I18nProvider>
    </MemoryRouter>,
  );
}

beforeEach(serve);
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("My notes", () => {
  it("lists notes and searches them", async () => {
    show();
    expect(await screen.findByText("The cell")).toBeInTheDocument();
    expect(screen.getByText(/membrane controls what enters/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/search your notes/i), { target: { value: "nothing" } });
    await waitFor(() => expect(screen.getByText(/no notes match/i)).toBeInTheDocument());
  });

  it("shows bookmarks on their tab", async () => {
    show();
    await screen.findByText("The cell");
    fireEvent.click(screen.getByRole("tab", { name: /bookmarks/i }));
    expect(await screen.findByText("Straight-line graphs")).toBeInTheDocument();
  });
});
