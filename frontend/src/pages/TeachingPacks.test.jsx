import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n";
import TeachingPacks from "./TeachingPacks";

function jsonResponse(body, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const PACKS = [
  { id: 1, classroom: 3, classroom_name: "S2 A", unit_label: "S2 Unit 1: Graphs", lesson_title: "Graphs", created_at: "2026-10-20T10:00:00Z", ai_used: false },
  { id: 2, classroom: 4, classroom_name: "S3 B", unit_label: "S3 Unit 2: Cells", lesson_title: "", created_at: "2026-10-21T10:00:00Z", ai_used: true },
];

let calls;
beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, init = {}) => {
      const method = init.method || "GET";
      const href = String(url);
      calls.push({ url: href, method });
      if (href.includes("/teaching/packs/") && method === "DELETE") return jsonResponse(null, 204);
      if (href.includes("/teaching/packs/")) return jsonResponse(href.includes("classroom=3") ? [PACKS[0]] : PACKS);
      if (href.includes("/classes/")) return jsonResponse([{ id: 3, name: "S2 A" }, { id: 4, name: "S3 B" }]);
      throw new Error(`no route ${method} ${url}`);
    }),
  );
  vi.stubGlobal("confirm", vi.fn(() => true));
  localStorage.setItem("iga.lang", "en");
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("My teaching packs", () => {
  it("lists, filters by class and deletes", async () => {
    render(
      <MemoryRouter>
        <I18nProvider>
          <TeachingPacks />
        </I18nProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByText("S2 Unit 1: Graphs")).toBeInTheDocument();
    expect(screen.getByText("S3 Unit 2: Cells")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /S2 Unit 1: Graphs/ })).toHaveAttribute("href", "/teaching-packs/1");

    fireEvent.change(await screen.findByLabelText("Class"), { target: { value: "3" } });
    await waitFor(() => expect(screen.queryByText("S3 Unit 2: Cells")).not.toBeInTheDocument());
    expect(calls.some((c) => c.url.includes("classroom=3"))).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Delete S2 Unit 1: Graphs" }));
    await waitFor(() => expect(screen.queryByText("S2 Unit 1: Graphs")).not.toBeInTheDocument());
    expect(calls.some((c) => c.method === "DELETE" && c.url.includes("/teaching/packs/1/"))).toBe(true);
  });
});
