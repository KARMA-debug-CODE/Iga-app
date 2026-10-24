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

  it("the quiz print is a student copy, with no key", () => {
    const { container } = print("quiz");
    expect(screen.getByText("How do you work out speed?")).toBeInTheDocument();
    expect(screen.queryByText(/Explanation for/)).not.toBeInTheDocument();
    expect(container.querySelector(".is-correct")).toBeNull();
    expect(screen.getByText("Name")).toBeInTheDocument();
  });

  it("the quiz key prints on its own, with the answers", () => {
    const { container } = print("quizKey");
    expect(screen.getByText("Explanation for How do you work out speed?")).toBeInTheDocument();
    expect(container.querySelectorAll(".is-correct").length).toBeGreaterThan(0);
    expect(screen.getByText(/Quiz answer key: S2 Unit 3: Motion/)).toBeInTheDocument();
    expect(screen.queryByText("Name")).not.toBeInTheDocument();
  });

  it("answer options and misconceptions print their maths, not raw LaTeX", () => {
    const pack = packWith();
    pack.document.worksheet.core[0].choices[0].text = "$x^2$";
    pack.document.insight.misconceptions[0].wrong_choice = "$2x$";
    pack.document.insight.misconceptions[0].correct = "$x^2$";
    const { container } = print("worksheet", pack);
    expect(container.querySelector(".pack-choices .katex")).not.toBeNull();
    expect(container.textContent).not.toContain("$x^2$");
    cleanup();
    const insight = print("insight", pack);
    expect(insight.container.querySelectorAll("ol .katex").length).toBeGreaterThanOrEqual(2);
    expect(insight.container.textContent).not.toMatch(/\$2x\$|\$x\^2\$/);
  });

  it("the plan print keeps the lines of multi-line fields", () => {
    const pack = packWith();
    pack.document.plan.references = "Book one\nBook two";
    print("plan", pack);
    expect(screen.getByText(/Book one/).closest("td")).toHaveClass("pack-print-text");
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
