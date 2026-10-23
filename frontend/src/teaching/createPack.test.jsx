import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n";
import PackTeaser from "./PackTeaser";
import TeachingPackCard from "./TeachingPackCard";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const WEAK = [{ unit: "S2 Unit 1: Graphs", average: 25, unit_id: 7 }];
const UNITS = [
  { unit_id: 7, label: "S2 Unit 1: Graphs", subject: "Mathematics", average: 25, answered: 6, misconceptions_found: 2 },
  { unit_id: 8, label: "S2 Unit 2: Angles", subject: "Mathematics", average: 80, answered: 6, misconceptions_found: 0 },
  { unit_id: 9, label: "S2 Unit 3: Triangles", subject: "Mathematics", average: null, answered: 0, misconceptions_found: 0 },
];

let calls;
let createReply;
beforeEach(() => {
  calls = [];
  createReply = () => jsonResponse({ id: 42 }, 201);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, init = {}) => {
      const method = init.method || "GET";
      calls.push({ url: String(url), method, body: init.body ? JSON.parse(init.body) : null });
      if (String(url).includes("/teaching/classes/3/units/")) return jsonResponse(UNITS);
      if (String(url).includes("/teaching/packs/") && method === "POST") return createReply();
      throw new Error(`no route ${method} ${url}`);
    }),
  );
  localStorage.setItem("iga.lang", "en");
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

function show(weakUnits = WEAK) {
  return render(
    <MemoryRouter initialEntries={["/classes/3"]}>
      <I18nProvider>
        <Routes>
          <Route path="/classes/:id" element={<TeachingPackCard classroomId={3} weakUnits={weakUnits} />} />
          <Route path="/teaching-packs/:id" element={<p>PACK PAGE</p>} />
        </Routes>
      </I18nProvider>
    </MemoryRouter>,
  );
}

describe("Teaching packs from the class report", () => {
  it("each weak unit offers a teaching pack and opens the new pack", async () => {
    show();
    fireEvent.click(screen.getByRole("button", { name: "Make a teaching pack for S2 Unit 1: Graphs" }));
    expect(await screen.findByText("PACK PAGE")).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST");
    expect(post.body).toEqual({ classroom: 3, unit: 7 });
  });

  it("an unpaid school sees the teaser with the misconception count", async () => {
    createReply = () =>
      jsonResponse(
        {
          detail: "Teaching packs are part of your school's Iga subscription.",
          code: "subscription_required",
          teaser: { unit: "S2 Unit 1: Graphs", average: 25, misconceptions_found: 3 },
        },
        403,
      );
    show();
    fireEvent.click(screen.getByRole("button", { name: "Make a teaching pack for S2 Unit 1: Graphs" }));
    expect(await screen.findByText(/Misconceptions Iga found in S2 Unit 1: Graphs: 3/)).toBeInTheDocument();
    expect(screen.getByText(/part of your school's Iga subscription/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /subscription/i })).not.toBeInTheDocument();
  });

  it("shows school administrators the way to the subscription", () => {
    render(
      <MemoryRouter>
        <I18nProvider>
          <PackTeaser teaser={{ unit: "S2 Unit 1: Graphs", average: 25, misconceptions_found: 3 }} isSchoolAdmin />
        </I18nProvider>
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: /subscription/i })).toHaveAttribute("href", "/school/billing");
  });

  it("the unit picker lists the class's units weakest first", async () => {
    show([]);
    fireEvent.click(screen.getByRole("button", { name: "Choose a unit" }));
    const buttons = await screen.findAllByRole("button", { name: /Make a teaching pack for/ });
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Make a teaching pack for S2 Unit 1: Graphs",
      "Make a teaching pack for S2 Unit 2: Angles",
      "Make a teaching pack for S2 Unit 3: Triangles",
    ]);
    expect(screen.getByText("No answers yet")).toBeInTheDocument();
    fireEvent.click(buttons[1]);
    await waitFor(() => expect(calls.find((c) => c.method === "POST").body).toEqual({ classroom: 3, unit: 8 }));
  });
});
