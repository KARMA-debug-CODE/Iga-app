import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n";
import TeachingPack from "../pages/TeachingPack";
import { packFixture, packWith } from "./fixture";
import PackPrint from "./PackPrint";

beforeEach(() => localStorage.setItem("iga.lang", "en"));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

function print(mode, pack = packFixture) {
  return render(
    <MemoryRouter>
      <I18nProvider>
        <PackPrint pack={pack} mode={mode} />
      </I18nProvider>
    </MemoryRouter>,
  );
}

describe("Teaching pack print layouts", () => {
  it("the student worksheet has no answers", () => {
    const { container } = print("worksheet");
    expect(screen.getByText("Easy speed question")).toBeInTheDocument();
    expect(screen.getByText("How do you work out speed?")).toBeInTheDocument();
    expect(screen.queryByText(/Explanation for/)).not.toBeInTheDocument();
    expect(container.querySelector(".is-correct")).toBeNull();
    expect(screen.getByText("Name")).toBeInTheDocument();
  });

  it("the answer key has the answers", () => {
    const { container } = print("key");
    expect(screen.getAllByText(/Explanation for/).length).toBe(2);
    expect(container.querySelectorAll(".is-correct").length).toBe(2);
    expect(screen.getByText(/Answer key: S2 Unit 3: Motion/)).toBeInTheDocument();
  });

  it("the quiz print ends with its key on a new page", () => {
    const { container } = print("quiz");
    const key = container.querySelector(".pack-page-break");
    expect(key).not.toBeNull();
    expect(key.textContent).toContain("Explanation for How do you work out speed?");
    expect(container.querySelectorAll(".pack-print-questions .is-correct").length).toBe(0);
  });

  it("the plan print shows the teacher's edits", () => {
    const pack = packWith();
    pack.document.plan.objective = "My own objective for today";
    print("plan", pack);
    expect(screen.getByText("My own objective for today")).toBeInTheDocument();
    expect(screen.getByText("Ask who ran fastest.")).toBeInTheDocument();
    expect(screen.getByText("Key unit competence")).toBeInTheDocument();
  });

  it("the insight print is headed Teacher only", () => {
    print("insight");
    expect(screen.getByRole("heading", { name: /Teacher only/ })).toBeInTheDocument();
    expect(screen.getByText("Aline M.")).toBeInTheDocument();
    expect(screen.getByText(/62% chose/)).toBeInTheDocument();
  });

  it("print view calls window.print once", async () => {
    const printSpy = vi.fn();
    vi.stubGlobal("print", printSpy);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(packFixture), { status: 200, headers: { "Content-Type": "application/json" } })),
    );
    render(
      <MemoryRouter initialEntries={["/teaching-packs/5?print=worksheet"]}>
        <I18nProvider>
          <Routes>
            <Route path="/teaching-packs/:id" element={<TeachingPack />} />
          </Routes>
        </I18nProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByText("Easy speed question")).toBeInTheDocument();
    await waitFor(() => expect(printSpy).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });
});
