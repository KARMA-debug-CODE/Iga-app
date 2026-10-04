// "Save for offline": fetch every lesson in a unit so the service worker keeps a copy.
// On logout everything cached is wiped, because school computers are often shared.
import { api } from "./api";

const KEY = "iga.offline.units";

function readSaved() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

function writeSaved(value) {
  try {
    localStorage.setItem(KEY, JSON.stringify(value));
  } catch {
    /* storage full or blocked: the lessons are still cached */
  }
}

export function offlineSupported() {
  return typeof navigator !== "undefined" && Boolean(navigator.serviceWorker?.controller) && "caches" in window;
}

export function savedUnits() {
  return readSaved();
}

function waitForStylesheets() {
  const links = [...document.querySelectorAll('link[rel="stylesheet"]')];
  return Promise.all(
    links.map((link) => (link.sheet ? null : new Promise((resolve) => link.addEventListener("load", resolve, { once: true })))),
  );
}

/** Fetch the maths fonts so formulas look right offline (the service worker caches them). */
async function cacheMathFonts() {
  await waitForStylesheets();
  const urls = new Set();
  for (const sheet of document.styleSheets) {
    let rules;
    try {
      rules = sheet.cssRules;
    } catch {
      continue; // cross-origin stylesheet
    }
    for (const rule of rules) {
      if (rule instanceof CSSFontFaceRule && /KaTeX/i.test(rule.style.getPropertyValue("font-family"))) {
        const match = /url\(["']?([^"')]+\.woff2)["']?\)/.exec(rule.style.getPropertyValue("src"));
        if (match) urls.add(new URL(match[1], sheet.href || window.location.href).href);
      }
    }
  }
  await Promise.all([...urls].map((url) => fetch(url).catch(() => null)));
}

export async function saveUnitOffline(unit, lang, onProgress = () => {}) {
  // Cache the code for lesson pages and built-in labs too, not just the lesson data.
  const { preloadBuiltinSims } = await import("./sims/registry");
  await Promise.all([import("./pages/Lesson"), import("./components/Markdown"), preloadBuiltinSims()]);
  await cacheMathFonts();
  // Only lessons the student can open: locked ones have no text to keep.
  const slugs = unit.lessons.filter((l) => !l.locked).map((l) => l.slug);
  let done = 0;
  for (const slug of slugs) {
    await api(`/lessons/${slug}/`, { params: { lang } });
    done += 1;
    onProgress(done, slugs.length);
  }
  const saved = readSaved();
  saved[unit.id] = { title: unit.title, grade: unit.grade, slugs, lang, savedAt: new Date().toISOString() };
  writeSaved(saved);
  return saved[unit.id];
}

/** True when every lesson of the unit the user can open now is in the saved copy. */
export function unitIsSaved(unit) {
  const record = readSaved()[unit.id];
  if (!record) return false;
  const kept = new Set(record.slugs);
  return unit.lessons.filter((l) => !l.locked).every((l) => kept.has(l.slug));
}

function lessonSlug(url) {
  const match = /\/api\/lessons\/([^/]+)\/$/.exec(new URL(url).pathname);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Delete saved copies of premium lessons when the user no longer has the subscription (the school
 * stopped paying, the student left it, or someone else signed in on this device), so they can't be
 * read by going offline. Free lessons stay saved.
 */
export async function forgetPremiumLessons() {
  if (typeof caches === "undefined") return;
  const gone = new Set();
  for (const name of (await caches.keys()).filter((n) => n.startsWith("iga-"))) {
    const cache = await caches.open(name);
    for (const request of await cache.keys()) {
      const slug = lessonSlug(request.url);
      if (!slug) continue;
      const response = await cache.match(request);
      const lesson = await response?.json().catch(() => null);
      if (lesson && !lesson.locked && lesson.is_free) continue;
      await cache.delete(request);
      gone.add(slug);
    }
  }
  if (!gone.size) return;
  const saved = readSaved();
  for (const [id, record] of Object.entries(saved)) {
    record.slugs = record.slugs.filter((slug) => !gone.has(slug));
    if (!record.slugs.length) delete saved[id];
  }
  writeSaved(saved);
}

export async function clearOfflineData() {
  try {
    localStorage.removeItem(KEY);
    localStorage.removeItem("iga.user");
  } catch {
    /* ignore */
  }
  if (typeof caches === "undefined") return;
  const names = await caches.keys();
  await Promise.all(names.filter((n) => n.startsWith("iga-")).map((n) => caches.delete(n)));
}
