// Private notes are kept on the server, but a note written offline must not be lost. A note that could
// not be sent is held in this browser (like the saved-units list in offline.js) and sent again when the
// connection is back; the server stays the source of truth, so a note clears from here as soon as it saves.
import { api, NetworkError } from "./api";

const KEY = "iga.notes.pending";

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

function write(value) {
  try {
    if (Object.keys(value).length) localStorage.setItem(KEY, JSON.stringify(value));
    else localStorage.removeItem(KEY);
  } catch {
    /* storage full or blocked: the note stays in the page until it is sent */
  }
}

/** The note body waiting to be sent for this lesson, if any. */
export function pendingNote(slug) {
  const record = read()[slug];
  return record ? record.body : null;
}

/** Hold a note body in this browser until it can be sent. */
export function queueNote(slug, body) {
  const all = read();
  all[slug] = { body, savedAt: new Date().toISOString() };
  write(all);
}

function clearPending(slug) {
  const all = read();
  if (slug in all) {
    delete all[slug];
    write(all);
  }
}

/**
 * Send one note for a lesson. On a network failure the note is kept in this browser and `queued` is
 * returned, so the caller can show that it will sync later; any other error is thrown.
 */
export async function saveNote(slug, body) {
  try {
    const result = await api("/notes/", { method: "POST", body: { lesson: slug, body } });
    clearPending(slug);
    return { saved: true, note: result.deleted ? null : result };
  } catch (e) {
    if (e instanceof NetworkError) {
      queueNote(slug, body);
      return { queued: true };
    }
    throw e;
  }
}

/** Send every note held in this browser (called when the connection comes back). Returns the slugs sent. */
export async function syncNotes() {
  const all = read();
  const sent = [];
  for (const [slug, record] of Object.entries(all)) {
    try {
      await api("/notes/", { method: "POST", body: { lesson: slug, body: record.body } });
      clearPending(slug);
      sent.push(slug);
    } catch (e) {
      if (e instanceof NetworkError) break; // still offline: stop and try again later
      clearPending(slug); // the server refused this one (e.g. too long); don't keep retrying it forever
    }
  }
  return sent;
}

/** Forget notes waiting on this device (called on logout, like the rest of the offline data). */
export function clearPendingNotes() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
