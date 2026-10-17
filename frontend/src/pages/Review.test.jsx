import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n";
import ReviewPanel from "./Review";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const DUE = {
  due: [
    {
      id: 1,
      box: 1,
      subject: { name: "Mathematics", icon: "sigma" },
      question: { id: 11, type: "mcq", prompt: "What is 2 + 2?", choices: [{ id: 101, text: "4" }, { id: 102, text: "5" }] },
    },
  ],
  due_count: 1,
  total: 1,
};

const GRADED = {
  is_correct: true,
  xp_gained: 1,
  retired: false,
  box: 2,
  due_on: "2030-01-02",
  due_count: 0,
  solution: { correct_choice_ids: [101], numeric_answer: null, accepted_answers: [], explanation: "Two plus two is four." },
};

function serve() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, init = {}) => {
      const method = init.method || "GET";
      if (method === "POST" && url.includes("/answer/")) return jsonResponse(GRADED);
      if (method === "GET" && url.includes("/api/review/")) return jsonResponse(DUE);
      throw new Error(`no route for ${method} ${url}`);
    }),
  );
}

function show() {
  localStorage.setItem("iga.lang", "en");
  return render(
    <MemoryRouter>
      <I18nProvider>
        <ReviewPanel />
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

describe("review session", () => {
  it("shows the deck counts and steps through a due item, grading on the server", async () => {
    show();
    // Entry card: one due, one in the deck, and an honest note about XP.
    expect(await screen.findByRole("button", { name: /start review/i })).toBeInTheDocument();
    expect(screen.getByText(/only a little XP/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /start review/i }));

    expect(await screen.findByText(/what is 2 \+ 2/i)).toBeInTheDocument();
    // Pick the correct choice and check it on the server.
    fireEvent.click(screen.getAllByRole("radio")[0]);
    fireEvent.click(screen.getByRole("button", { name: /check answer/i }));

    expect(await screen.findByText(/correct/i)).toBeInTheDocument();
    expect(screen.getByText(/two plus two is four/i)).toBeInTheDocument();
    expect(screen.getByText("+1 XP")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /finish/i }));
    await waitFor(() => expect(screen.getByText(/review done/i)).toBeInTheDocument());
    expect(screen.getByText(/you got 1 of 1 right/i)).toBeInTheDocument();
  });

  it("invites the student to come back when nothing is due", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ due: [], due_count: 0, total: 4 })));
    show();
    expect(await screen.findByText(/all caught up/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /start review/i })).not.toBeInTheDocument();
  });
});
