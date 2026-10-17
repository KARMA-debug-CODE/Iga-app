import { expect, test } from "@playwright/test";

import { login } from "./helpers";

// The demo database seeds no review deck (it fills from wrong answers over time), so the deck endpoints
// are mocked here, like the other server-dependent features in features.spec.js. The grading itself is
// covered by backend/apps/review.
test.use({ contextOptions: { reducedMotion: "reduce" } });

const DUE = {
  due: [
    {
      id: 1,
      box: 1,
      subject: { name: "Mathematics", icon: "sigma" },
      question: { id: 11, type: "mcq", prompt: "What is 2 + 2?", choices: [{ id: 101, text: "4" }, { id: 102, text: "5" }] },
    },
    {
      id: 2,
      box: 2,
      subject: { name: "Mathematics", icon: "sigma" },
      question: { id: 12, type: "numeric", prompt: "What is 3 + 4?", choices: [] },
    },
  ],
  due_count: 2,
  total: 5,
};

function graded(id) {
  return {
    is_correct: true,
    xp_gained: id === 1 ? 1 : 0,
    retired: false,
    box: 3,
    due_on: "2030-01-01",
    due_count: id === 1 ? 1 : 0,
    solution: {
      correct_choice_ids: id === 1 ? [101] : [],
      numeric_answer: id === 2 ? 7 : null,
      accepted_answers: [],
      explanation: id === 1 ? "Two plus two is four." : "Three plus four is seven.",
    },
  };
}

test("review deck: step through due items, graded on the server, with a summary", async ({ page }) => {
  await page.route("**/api/review/", (route) => route.fulfill({ json: DUE }));
  await page.route(/\/api\/review\/\d+\/answer\/$/, (route) => {
    const id = Number(/review\/(\d+)\/answer/.exec(route.request().url())[1]);
    route.fulfill({ json: graded(id) });
  });

  await login(page, "aline");
  await page.goto("/practice?tab=review");

  // Entry card: counts and an honest note that reviews earn little XP.
  await expect(page.getByRole("button", { name: /start review/i })).toBeVisible();
  await expect(page.getByText(/only a little xp/i)).toBeVisible();
  await page.getByRole("button", { name: /start review/i }).click();

  // First card (multiple choice): pick the right answer, check it, see the explanation.
  await expect(page.getByText(/what is 2 \+ 2/i)).toBeVisible();
  await page.getByRole("radio").first().check();
  await page.getByRole("button", { name: /check answer/i }).click();
  await expect(page.locator(".feedback")).toContainText(/correct/i);
  await expect(page.getByText(/two plus two is four/i)).toBeVisible();
  await page.getByRole("button", { name: /^next$/i }).click();

  // Second card (numeric): answer, check, then finish.
  await expect(page.getByText(/what is 3 \+ 4/i)).toBeVisible();
  await page.getByLabel(/your answer/i).fill("7");
  await page.getByRole("button", { name: /check answer/i }).click();
  await expect(page.locator(".feedback")).toBeVisible();
  await page.getByRole("button", { name: /finish/i }).click();

  await expect(page.getByText(/review done/i)).toBeVisible();
  await expect(page.getByText(/you got 2 of 2 right/i)).toBeVisible();
});
