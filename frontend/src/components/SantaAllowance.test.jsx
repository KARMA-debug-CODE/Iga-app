// What a student is told about their allowance for Santa's AI (the server counts it: backend/apps/tutor/usage.py).
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import { I18nProvider } from "../i18n";
import { SantaAllowance } from "./Santa";

const LEFT = {
  questions_left_today: 12,
  questions_per_day: 60,
  questions_left_month: 400,
  questions_per_month: 800,
  time_left_percent: 90,
  reached: "",
};

function html(allowance, lang = "en") {
  localStorage.setItem("iga.lang", lang);
  return renderToStaticMarkup(
    <I18nProvider>
      <SantaAllowance allowance={allowance} />
    </I18nProvider>,
  ).replace(/&#x27;/g, "'");
}

afterEach(() => localStorage.clear());

describe("SantaAllowance", () => {
  it("shows the questions left today, quietly", () => {
    expect(html(LEFT)).toBe('<p class="small muted santa-allowance">12 of 60 questions for Santa\'s AI left today</p>');
    expect(html(null)).toBe("");
  });

  it("adds the month and the time left when they are what runs out first", () => {
    const text = html({ ...LEFT, questions_left_month: 5, time_left_percent: 20 });
    expect(text).toContain("12 of 60 questions for Santa's AI left today · 5 left this month · 20% of your Santa time left");
  });

  it("says nothing when there is no limit", () => {
    const none = { ...LEFT, questions_left_today: null, questions_per_day: null, questions_left_month: null, time_left_percent: null };
    expect(html(none)).toBe("");
  });

  it("explains a used-up allowance, in English and French", () => {
    for (const [reached, en, fr] of [
      ["limit_day", "You've used today's questions for Santa's AI", "Jusqu'à demain"],
      ["limit_month", "You've used this month's questions for Santa's AI", "Jusqu'au mois prochain"],
      ["limit_school", "Your school has used today's time with Santa's AI", "Votre école a utilisé"],
    ]) {
      const allowance = { ...LEFT, questions_left_today: 0, reached };
      expect(html(allowance)).toContain(en);
      expect(html(allowance)).toContain('role="note"');
      expect(html(allowance, "fr")).toContain(fr);
    }
    expect(html({ ...LEFT, questions_left_today: 1 }, "fr")).toContain("Encore 1 question sur 60 pour l'IA de Santa");
  });
});
