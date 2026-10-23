import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n";
import { packFixture, packWith } from "../teaching/fixture";
import TeachingPack from "./TeachingPack";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

let calls;
let pack;
beforeEach(() => {
  calls = [];
  pack = packFixture;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, init = {}) => {
      const method = init.method || "GET";
      const body = init.body ? JSON.parse(init.body) : null;
      calls.push({ url: String(url), method, body });
      if (String(url).includes("/assign/")) return jsonResponse({ what: body.what, assignment_id: 9, quiz_id: 10, dropped: 1, created: true }, 201);
      if (String(url).includes("/teaching/packs/5/")) return jsonResponse(pack);
      throw new Error(`no route ${method} ${url}`);
    }),
  );
  localStorage.setItem("iga.lang", "en");
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  localStorage.clear();
});

function show() {
  return render(
    <MemoryRouter initialEntries={["/teaching-packs/5"]}>
      <I18nProvider>
        <Routes>
          <Route path="/teaching-packs/:id" element={<TeachingPack />} />
        </Routes>
      </I18nProvider>
    </MemoryRouter>,
  );
}

const tab = (name) => fireEvent.click(screen.getByRole("tab", { name }));

describe("Teaching pack page", () => {
  it("shows the four tabs from the pack", async () => {
    show();
    expect(await screen.findByText("S2 Unit 3: Motion")).toBeInTheDocument();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Insight", "Lesson plan", "Worksheet", "Quiz"]);
    expect(screen.getByText(/62% chose/)).toBeInTheDocument();
  });

  it("editing the objective saves after a pause", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    show();
    await screen.findByText("S2 Unit 3: Motion");
    tab("Lesson plan");
    const objective = screen.getByLabelText("Instructional objective");
    fireEvent.change(objective, { target: { value: "Ne" } });
    fireEvent.change(objective, { target: { value: "New" } });
    expect(calls.filter((c) => c.method === "PATCH")).toHaveLength(0);
    await act(async () => {
      vi.advanceTimersByTime(850);
    });
    await waitFor(() => expect(calls.filter((c) => c.method === "PATCH")).toHaveLength(1));
    expect(calls.find((c) => c.method === "PATCH").body).toEqual({ plan: { objective: "New" } });
    expect(await screen.findByText("Saved")).toBeInTheDocument();
  });

  it("keeps plan edits when the teacher switches tabs and comes back", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    show();
    await screen.findByText("S2 Unit 3: Motion");
    tab("Lesson plan");
    fireEvent.change(screen.getByLabelText("Instructional objective"), { target: { value: "Kept" } });
    await act(async () => {
      vi.advanceTimersByTime(850);
    });
    tab("Worksheet");
    tab("Lesson plan");
    expect(screen.getByLabelText("Instructional objective")).toHaveValue("Kept");
  });

  it("a step edit saves only that cell", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { container } = show();
    await screen.findByText("S2 Unit 3: Motion");
    tab("Lesson plan");
    fireEvent.change(container.querySelector("#step-0-teacher"), { target: { value: "Start" } });
    fireEvent.change(container.querySelector("#step-2-learners"), { target: { value: "Recap" } });
    await act(async () => {
      vi.advanceTimersByTime(850);
    });
    await waitFor(() => expect(calls.filter((c) => c.method === "PATCH")).toHaveLength(1));
    expect(calls.find((c) => c.method === "PATCH").body).toEqual({ plan: { steps: [{ teacher: "Start" }, {}, { learners: "Recap" }] } });
  });

  it("a save waits for the one before it", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let release;
    const stub = globalThis.fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init = {}) => {
        if (init.method === "PATCH" && !release) {
          calls.push({ url: String(url), method: "PATCH", body: JSON.parse(init.body) });
          await new Promise((resolve) => {
            release = resolve;
          });
          return jsonResponse(pack);
        }
        return stub(url, init);
      }),
    );
    show();
    await screen.findByText("S2 Unit 3: Motion");
    tab("Lesson plan");
    fireEvent.change(screen.getByLabelText("Instructional objective"), { target: { value: "First" } });
    await act(async () => {
      vi.advanceTimersByTime(850);
    });
    await waitFor(() => expect(calls.filter((c) => c.method === "PATCH")).toHaveLength(1));
    fireEvent.change(screen.getByLabelText("Learning materials"), { target: { value: "Chalk" } });
    await act(async () => {
      vi.advanceTimersByTime(850);
    });
    expect(calls.filter((c) => c.method === "PATCH")).toHaveLength(1);
    await act(async () => {
      release();
    });
    await waitFor(() => expect(calls.filter((c) => c.method === "PATCH")).toHaveLength(2));
    expect(calls.filter((c) => c.method === "PATCH")[1].body).toEqual({ plan: { materials: "Chalk" } });
  });

  it("shows maths in the misconceptions", async () => {
    pack = packWith();
    pack.document.insight.misconceptions[0].wrong_choice = "$2x$";
    const { container } = show();
    await screen.findByText("S2 Unit 3: Motion");
    expect(container.querySelector(".pack-misconceptions .pack-wrong .katex")).not.toBeNull();
    expect(container.textContent).not.toContain("$2x$");
  });

  it("assigning the quiz posts what and due date", async () => {
    show();
    await screen.findByText("S2 Unit 3: Motion");
    tab("Quiz");
    fireEvent.click(screen.getByRole("button", { name: "Assign to the class" }));
    fireEvent.change(screen.getByLabelText(/Due date/), { target: { value: "2026-11-01T10:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Assign" }));
    expect(await screen.findByText("Assigned to the class.")).toBeInTheDocument();
    const post = calls.find((c) => c.url.includes("/assign/"));
    expect(post.body.what).toBe("quiz");
    expect(new Date(post.body.due_at).getTime()).toBe(new Date("2026-11-01T10:00").getTime());
    expect(screen.getByText(/1 question was left out/)).toBeInTheDocument();
  });

  it("assign is disabled for a part with no questions", async () => {
    show();
    await screen.findByText("S2 Unit 3: Motion");
    tab("Worksheet");
    expect(screen.getByRole("button", { name: "Assign the stretch level to the class" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Assign the core level to the class" })).toBeEnabled();
    expect(screen.getByText("No stretch questions exist for this unit yet.")).toBeInTheDocument();
    expect(screen.getAllByText("1 question")).toHaveLength(2);
    expect(screen.getByText("0 questions")).toBeInTheDocument();
  });

  it("labels Santa's text only when it is AI", async () => {
    show();
    await screen.findByText("S2 Unit 3: Motion");
    tab("Lesson plan");
    expect(screen.getByText("Suggested by Santa")).toBeInTheDocument();
    cleanup();
    pack = packWith({ ai_used: false, document: { polish: { ai: false } } });
    show();
    await screen.findByText("S2 Unit 3: Motion");
    tab("Lesson plan");
    expect(screen.queryByText("Suggested by Santa")).not.toBeInTheDocument();
  });

  it("says when there are not enough answers and marks the diagnostic quiz", async () => {
    pack = packWith({ document: { insight: { data_enough: false, misconceptions: [], hardest: [] }, quiz: { diagnostic: true } } });
    show();
    expect(await screen.findByText(/Not enough answers yet/)).toBeInTheDocument();
    tab("Quiz");
    expect(screen.getByText("Diagnostic quiz")).toBeInTheDocument();
  });

  it("lists the students who need help", async () => {
    show();
    expect(await screen.findByText("Aline M.")).toBeInTheDocument();
    expect(screen.getByText("30%")).toBeInTheDocument();
  });
});
