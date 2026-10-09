import { describe, expect, it } from "vitest";

import { readEvents } from "../api";
import { finishedMessages } from "./Santa";

/** A Response-like object whose body arrives in the given pieces. */
function streamOf(pieces) {
  const encoder = new TextEncoder();
  let i = 0;
  return {
    body: {
      getReader: () => ({
        read: async () => (i < pieces.length ? { value: encoder.encode(pieces[i++]), done: false } : { value: undefined, done: true }),
      }),
    },
  };
}

describe("readEvents", () => {
  it("reads events split anywhere, and skips pings", async () => {
    const events = [];
    const response = streamOf([
      'data: {"type": "start"}\n\n: ping\n\nda',
      'ta: {"type": "delta", "text": "Muraho "}\n',
      '\ndata: {"type": "delta", "text": "é"}\n\ndata: {"type": "done", "reply": "Muraho é"}\n\n',
    ]);
    await readEvents(response, (event) => events.push(event));
    expect(events.map((e) => e.type)).toEqual(["start", "delta", "delta", "done"]);
    expect(events[2].text).toBe("é");
  });

  it("reads a last event without the closing blank line", async () => {
    const events = [];
    await readEvents(streamOf(['data: {"type": "done", "reply": "ok"}']), (event) => events.push(event));
    expect(events).toEqual([{ type: "done", reply: "ok" }]);
  });
});

describe("finishedMessages", () => {
  it("keeps only answered questions", () => {
    const q = (content) => ({ role: "user", content });
    const a = (content, extra = {}) => ({ role: "assistant", content, ...extra });
    const messages = [q("one"), a("first"), q("two"), a("", { pending: true }), q("three"), a("half", { pending: true })];
    expect(finishedMessages(messages)).toEqual([q("one"), a("first")]);
    expect(finishedMessages([q("alone")])).toEqual([]);
  });
});
