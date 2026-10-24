import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearPendingNotes, pendingNote, queueNote, saveNote, syncNotes } from "./notes-offline";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function offlineFetch() {
  // What the browser throws when the request never reaches the server.
  return vi.fn(() => Promise.reject(new TypeError("Failed to fetch")));
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("offline-safe notes", () => {
  it("saves to the server and keeps nothing on the device", async () => {
    const note = { id: 7, body: "hi", lesson: { slug: "s1" } };
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse(note, 201)));
    vi.stubGlobal("fetch", fetchMock);

    const result = await saveNote("s1", "hi");

    expect(result).toEqual({ saved: true, note });
    expect(pendingNote("s1")).toBeNull();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/notes/");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ lesson: "s1", body: "hi" });
  });

  it("an empty body deletes the note, and keeps nothing", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse({ deleted: true }))));
    const result = await saveNote("s1", "");
    expect(result).toEqual({ saved: true, note: null });
  });

  it("keeps a note on the device when the save can't reach the server", async () => {
    vi.stubGlobal("fetch", offlineFetch());
    const result = await saveNote("s1", "written offline");
    expect(result).toEqual({ queued: true });
    expect(pendingNote("s1")).toBe("written offline");
  });

  it("sends everything held on the device when back online, then clears it", async () => {
    queueNote("s1", "first");
    queueNote("s2", "second");
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse({ id: 1 }, 201)));
    vi.stubGlobal("fetch", fetchMock);

    const sent = await syncNotes();

    expect(sent.sort()).toEqual(["s1", "s2"]);
    expect(pendingNote("s1")).toBeNull();
    expect(pendingNote("s2")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("stops syncing and keeps the note when still offline", async () => {
    queueNote("s1", "later");
    vi.stubGlobal("fetch", offlineFetch());
    const sent = await syncNotes();
    expect(sent).toEqual([]);
    expect(pendingNote("s1")).toBe("later");
  });

  it("drops a queued note the server refuses, so it is not retried forever", async () => {
    queueNote("s1", "x".repeat(99999));
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse({ body: ["Too long"] }, 400))));
    const sent = await syncNotes();
    expect(sent).toEqual([]);
    expect(pendingNote("s1")).toBeNull();
  });

  it("forgets everything on logout", () => {
    queueNote("s1", "mine");
    clearPendingNotes();
    expect(pendingNote("s1")).toBeNull();
  });
});
