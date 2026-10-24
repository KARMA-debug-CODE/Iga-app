// Motion helpers (motion.js) and the components built on them: they move only when the reader allows it,
// and what screen readers and tests see is always the real value.
import { act, cleanup, render, renderHook, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Burst, Celebration, celebrationsFor } from "./components/Celebrate";
import { CountUp, Loader, Skeleton, SkeletonCards, Tabs } from "./components/ui";
import { I18nProvider } from "./i18n";
import { prefersReducedMotion, resetCounters, slideFrom, useCountUp, usePresence } from "./motion";

/** Pretend the browser answers the reduced-motion question with `reduce`. */
function mockMotion(reduce) {
  window.matchMedia = vi.fn((query) => ({ matches: query.includes("reduce") && reduce, media: query, addEventListener() {}, removeEventListener() {} }));
}

const withI18n = (ui) => <I18nProvider>{ui}</I18nProvider>;

beforeEach(() => {
  localStorage.setItem("iga.lang", "en");
  resetCounters();
});

afterEach(() => {
  cleanup();
  delete window.matchMedia;
  vi.useRealTimers();
  localStorage.clear();
});

describe("prefersReducedMotion", () => {
  it("is true when the browser can't say, so nothing moves", () => {
    delete window.matchMedia;
    expect(prefersReducedMotion()).toBe(true);
  });

  it("follows the reader's setting", () => {
    mockMotion(true);
    expect(prefersReducedMotion()).toBe(true);
    mockMotion(false);
    expect(prefersReducedMotion()).toBe(false);
  });
});

describe("usePresence", () => {
  it("keeps something on screen while it animates out, then removes it", () => {
    vi.useFakeTimers();
    mockMotion(false);
    const { result, rerender } = renderHook(({ show }) => usePresence(show, 200), { initialProps: { show: true } });
    expect(result.current).toEqual({ mounted: true, leaving: false });
    rerender({ show: false });
    expect(result.current).toEqual({ mounted: true, leaving: true });
    act(() => vi.advanceTimersByTime(200));
    expect(result.current).toEqual({ mounted: false, leaving: false });
    rerender({ show: true });
    expect(result.current).toEqual({ mounted: true, leaving: false });
  });

  it("removes it at once with reduced motion", () => {
    mockMotion(true);
    const { result, rerender } = renderHook(({ show }) => usePresence(show, 200), { initialProps: { show: true } });
    rerender({ show: false });
    expect(result.current.mounted).toBe(false);
  });
});

describe("useCountUp", () => {
  it("shows the number straight away with reduced motion", () => {
    mockMotion(true);
    const { result } = renderHook(() => useCountUp(120, "xp"));
    expect(result.current).toBe(120);
  });

  it("counts up from zero the first time, and only what changed after that", () => {
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"] });
    mockMotion(false);
    const first = renderHook(() => useCountUp(120, "xp"));
    expect(first.result.current).toBe(0);
    act(() => vi.advanceTimersByTime(350));
    expect(first.result.current).toBeGreaterThan(0);
    expect(first.result.current).toBeLessThan(120);
    act(() => vi.advanceTimersByTime(500));
    expect(first.result.current).toBe(120);
    first.unmount();

    // Back on the page: no count from zero again...
    const same = renderHook(() => useCountUp(120, "xp"));
    expect(same.result.current).toBe(120);
    same.unmount();
    // ...but XP gained since counts up from where it was.
    const more = renderHook(() => useCountUp(130, "xp"));
    expect(more.result.current).toBe(120);
    act(() => vi.advanceTimersByTime(800));
    expect(more.result.current).toBe(130);
  });
});

describe("CountUp", () => {
  it("gives screen readers the real number while it counts", () => {
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"] });
    mockMotion(false);
    const { container } = render(<CountUp value={42} format={(n) => `${n}%`} />);
    expect(container.querySelector(".sr-only").textContent).toBe("42%");
    expect(container.querySelector('[aria-hidden="true"]').textContent).toBe("0%");
    act(() => vi.advanceTimersByTime(800));
    expect(container.textContent).toBe("42%");
    expect(container.querySelector(".sr-only")).toBeNull();
  });

  it("is plain text when nothing moves", () => {
    const { container } = render(<CountUp value={7} />);
    expect(container.innerHTML).toBe("7");
  });
});

describe("slideFrom", () => {
  it("slides an element over from where it was, with a transform", () => {
    mockMotion(false);
    const element = document.createElement("div");
    element.getBoundingClientRect = () => ({ left: 100 });
    element.animate = vi.fn();
    slideFrom(element, { left: 340 }, 200);
    expect(element.animate).toHaveBeenCalledWith([{ transform: "translateX(240px)" }, { transform: "none" }], expect.objectContaining({ duration: 200 }));
  });

  it("does nothing with reduced motion or when nothing moved", () => {
    const element = document.createElement("div");
    element.getBoundingClientRect = () => ({ left: 100 });
    element.animate = vi.fn();
    mockMotion(true);
    slideFrom(element, { left: 340 });
    mockMotion(false);
    slideFrom(element, { left: 100 });
    expect(element.animate).not.toHaveBeenCalled();
  });
});

describe("Skeleton", () => {
  it("says Loading to screen readers and hides its shapes from them", () => {
    render(withI18n(<SkeletonCards count={3} progress />));
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Loading…");
    const shapes = status.querySelector('[aria-hidden="true"]');
    expect(shapes.querySelectorAll(".card.skeleton")).toHaveLength(3);
    expect(shapes.querySelectorAll(".sk-bar")).toHaveLength(3);
  });

  it("is what Loader shows while loading, if given", () => {
    const state = { loading: true, data: null };
    render(withI18n(<Loader state={state} skeleton={<Skeleton className="grid">shapes</Skeleton>}>{() => "data"}</Loader>));
    expect(screen.getByRole("status")).toHaveTextContent("Loading…shapes");
    expect(screen.queryByText("data")).toBeNull();
  });
});

describe("Tabs", () => {
  const TABS = [
    { value: "week", label: "This week" },
    { value: "all", label: "All time" },
  ];

  it("keeps the plain underline where the tabs can't be measured", () => {
    const { container } = render(<Tabs tabs={TABS} value="week" onChange={() => {}} />);
    expect(container.querySelector(".tab-indicator")).toBeNull();
    expect(container.querySelector(".tabs")).not.toHaveClass("has-indicator");
  });

  it("slides one underline to the chosen tab", () => {
    const sizes = { "This week": [0, 120], "All time": [124, 90] };
    const left = vi.spyOn(HTMLElement.prototype, "offsetLeft", "get").mockImplementation(function () {
      return sizes[this.textContent]?.[0] ?? 0;
    });
    const width = vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockImplementation(function () {
      return sizes[this.textContent]?.[1] ?? 0;
    });
    try {
      const { container, rerender } = render(<Tabs tabs={TABS} value="week" onChange={() => {}} />);
      const bar = () => container.querySelector(".tab-indicator");
      expect(container.querySelector(".tabs")).toHaveClass("has-indicator");
      expect(bar().style.transform).toBe("translateX(0px) scaleX(1.2)");
      expect(bar()).not.toHaveClass("is-moving"); // placed, not slid, the first time
      expect(bar()).toHaveAttribute("aria-hidden", "true");
      rerender(<Tabs tabs={TABS} value="all" onChange={() => {}} />);
      expect(bar().style.transform).toBe("translateX(124px) scaleX(0.9)");
      expect(bar()).toHaveClass("is-moving");
    } finally {
      left.mockRestore();
      width.mockRestore();
    }
  });
});

describe("Celebrations", () => {
  it("turn what a lesson or quiz earned into one celebration each, the level first", () => {
    expect(celebrationsFor({ level: 3, badges: ["first-lesson", "quiz-whiz"] })).toEqual([
      { kind: "level", level: 3 },
      { kind: "badge", code: "first-lesson" },
      { kind: "badge", code: "quiz-whiz" },
    ]);
    expect(celebrationsFor({ level: null, badges: [] })).toEqual([]);
    expect(celebrationsFor(undefined)).toEqual([]);
  });

  it("say the new badge or level, in the reader's language", () => {
    render(withI18n(<Celebration item={{ kind: "badge", code: "first-lesson" }} onDone={() => {}} />));
    expect(screen.getByRole("status")).toHaveTextContent("New badge: First Steps");
  });

  it("say it in French too", () => {
    localStorage.setItem("iga.lang", "fr");
    render(withI18n(<Celebration item={{ kind: "level", level: 4 }} onDone={() => {}} />));
    expect(screen.getByRole("status")).toHaveTextContent("Niveau 4 atteint");
  });

  it("go away by themselves", () => {
    vi.useFakeTimers();
    const done = vi.fn();
    const { container } = render(withI18n(<Celebration item={{ kind: "level", level: 2 }} onDone={done} ms={1000} />));
    act(() => vi.advanceTimersByTime(850));
    expect(container.querySelector(".celebration")).toHaveClass("is-leaving");
    act(() => vi.advanceTimersByTime(150));
    expect(done).toHaveBeenCalledOnce();
  });

  it("draw a decorative burst, and none at all with reduced motion", () => {
    mockMotion(false);
    const { container, unmount } = render(<Burst size={80} />);
    const svg = container.querySelector("svg.burst");
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg.querySelectorAll(".burst-ray")).toHaveLength(10);
    unmount();
    mockMotion(true);
    expect(render(<Burst />).container.innerHTML).toBe("");
  });
});
