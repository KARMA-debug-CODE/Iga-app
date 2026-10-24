/**
 * Motion helpers. CSS does the moving (motion.css, with the duration and easing tokens in styles.css);
 * these hooks only decide when. Everything is skipped when the reader asks for less motion.
 */
import { useEffect, useRef, useState } from "react";

/** The durations in styles.css (--motion-fast, --motion-base, --motion-slow), for timers in JS. */
export const MOTION_MS = { fast: 120, base: 200, slow: 360 };

const REDUCE = "(prefers-reduced-motion: reduce)";

/** True when the reader asked for less motion, or when the browser can't say (then nothing moves). */
export function prefersReducedMotion() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
  try {
    return window.matchMedia(REDUCE).matches;
  } catch {
    return true;
  }
}

/**
 * Keeps something on screen for `ms` after `show` turns false, so it can animate out.
 * Returns {mounted, leaving}: render while `mounted`, add a leaving class while `leaving`.
 */
export function usePresence(show, ms = MOTION_MS.base) {
  const [state, setState] = useState({ mounted: show, leaving: false });
  useEffect(() => {
    const set = (mounted, leaving) => setState((s) => (s.mounted === mounted && s.leaving === leaving ? s : { mounted, leaving }));
    if (show) {
      set(true, false);
      return undefined;
    }
    if (prefersReducedMotion()) {
      set(false, false);
      return undefined;
    }
    setState((s) => (s.mounted && !s.leaving ? { mounted: true, leaving: true } : s));
    const timer = setTimeout(() => set(false, false), ms);
    return () => clearTimeout(timer);
  }, [show, ms]);
  // No render lags behind `show`: it is mounted as soon as it is shown, and leaving as soon as it is hidden.
  if (show) return { mounted: true, leaving: false };
  return state.mounted ? { mounted: true, leaving: !prefersReducedMotion() } : state;
}

/**
 * Slides `element` from where it was (`before`, a DOMRect measured before a layout change) to where it is
 * now, with a transform only (FLIP). Used when the side menu opens or closes and the page moves over.
 */
export function slideFrom(element, before, ms = MOTION_MS.base) {
  if (!element || !before || prefersReducedMotion() || typeof element.animate !== "function") return;
  const after = element.getBoundingClientRect();
  const dx = before.left - after.left;
  if (Math.abs(dx) < 1) return;
  element.animate([{ transform: `translateX(${dx}px)` }, { transform: "none" }], {
    duration: ms,
    easing: "cubic-bezier(0.22, 1, 0.36, 1)",
  });
}

// The last value each counter showed during this visit: coming back to a page doesn't count from zero
// again, it counts only what changed (XP gained since, say).
const lastShown = new Map();

/** Forget what the counters showed (tests). */
export function resetCounters() {
  lastShown.clear();
}

/**
 * A whole number that counts up to `value` the first time it is shown (from what it showed last time,
 * under the same `key`, or from 0). Later changes count from the number on screen.
 */
export function useCountUp(value, key, ms = 700) {
  const target = Math.round(Number(value)) || 0;
  const shown = useRef(null);
  if (shown.current === null) {
    shown.current = prefersReducedMotion() ? target : key && lastShown.has(key) ? lastShown.get(key) : 0;
  }
  const [display, setDisplay] = useState(shown.current);
  useEffect(() => {
    if (key) lastShown.set(key, target);
    const from = shown.current;
    const show = (n) => {
      shown.current = n;
      setDisplay(n);
    };
    if (from === target || prefersReducedMotion() || typeof requestAnimationFrame !== "function") {
      show(target);
      return undefined;
    }
    let frame = 0;
    const begin = performance.now();
    const step = (now) => {
      const progress = Math.min(1, (now - begin) / ms);
      const eased = 1 - (1 - progress) ** 3;
      show(Math.round(from + (target - from) * eased));
      if (progress < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, key, ms]);
  return display;
}
