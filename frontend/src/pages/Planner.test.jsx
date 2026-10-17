import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n";
import Planner from "./Planner";

function jsonResponse(body, status = 200) {
  return body === null ? new Response(null, { status: 204 }) : new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const PLAN = {
  weekly_goal_lessons: 5,
  has_plan: true,
  exams: [{ id: 1, title: "Mock exam", date: "2030-06-01", created_at: "2026-01-01" }],
  summary: {
    has_plan: true,
    weekly_goal: 5,
    lessons_this_week: 2,
    next_exam: { title: "Mock exam", date: "2030-06-01", days_left: 100 },
    suggestions: [],
  },
};

let calls;
function serve() {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, init = {}) => {
      const method = init.method || "GET";
      calls.push({ url, method, body: init.body });
      if (url.includes("/planner/exams/")) return jsonResponse(method === "POST" ? { id: 2, title: "Final", date: "2030-12-01" } : null, method === "POST" ? 201 : 204);
      if (url.includes("/planner/")) return jsonResponse(PLAN);
      throw new Error(`no route ${method} ${url}`);
    }),
  );
}

function show() {
  localStorage.setItem("iga.lang", "en");
  return render(
    <MemoryRouter>
      <I18nProvider>
        <Planner />
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

describe("Planner", () => {
  it("shows the goal and exams, and saves a new weekly goal", async () => {
    show();
    const goal = await screen.findByLabelText(/lessons per week/i);
    expect(goal).toHaveValue(5);
    expect(screen.getByText("Mock exam")).toBeInTheDocument();
    expect(screen.getByText(/days left/i)).toBeInTheDocument();

    fireEvent.change(goal, { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    const put = calls.find((c) => c.method === "PUT");
    expect(JSON.parse(put.body)).toEqual({ weekly_goal_lessons: 7 });
  });

  it("adds and removes an exam date", async () => {
    show();
    await screen.findByText("Mock exam");

    fireEvent.change(screen.getByLabelText(/exam name/i), { target: { value: "Final" } });
    fireEvent.change(screen.getByLabelText(/^date$/i), { target: { value: "2030-12-01" } });
    fireEvent.click(screen.getByRole("button", { name: /add an exam/i }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    const post = calls.find((c) => c.method === "POST");
    expect(JSON.parse(post.body)).toEqual({ title: "Final", date: "2030-12-01" });

    fireEvent.click(screen.getByRole("button", { name: /remove this exam/i }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.url.includes("/planner/exams/1/"))).toBe(true));
  });
});
