import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, confirmIdentity, newIdempotencyKey, setAccessToken, setStepUpHandler } from "./api";

function reply(status, body) {
  return Promise.resolve(new Response(body === undefined ? null : JSON.stringify(body), { status }));
}

const STEP_UP = { detail: "For your security, enter your password again to continue.", code: "step_up_required" };

afterEach(() => {
  vi.unstubAllGlobals();
  setStepUpHandler(null);
  setAccessToken(null);
});

describe("step-up for privileged actions", () => {
  it("asks for the password once, then retries with the new token", async () => {
    setAccessToken("old");
    const fetchMock = vi.fn((url, options) => {
      if (url.endsWith("/auth/step-up/")) return reply(200, { access: "stepped-up" });
      return options.headers.Authorization === "Bearer stepped-up" ? reply(200, { ok: true }) : reply(403, STEP_UP);
    });
    vi.stubGlobal("fetch", fetchMock);
    const prompt = vi.fn(() => confirmIdentity("my-password"));
    setStepUpHandler(prompt);

    const [first, second] = await Promise.all([
      api("/admin/stats/"),
      api("/admin/users/", { method: "PATCH", body: { teacher_approved: true } }),
    ]);
    expect(first).toEqual({ ok: true });
    expect(second).toEqual({ ok: true });
    expect(prompt).toHaveBeenCalledTimes(1); // two refused requests, one prompt
    const stepUpCall = fetchMock.mock.calls.find(([url]) => url.endsWith("/auth/step-up/"));
    expect(JSON.parse(stepUpCall[1].body)).toEqual({ password: "my-password" });
  });

  it("gives up with the server's answer when the person cancels", async () => {
    vi.stubGlobal("fetch", vi.fn(() => reply(403, STEP_UP)));
    setStepUpHandler(() => Promise.reject(new Error("cancelled")));
    await expect(api("/admin/stats/")).rejects.toMatchObject({ status: 403, data: STEP_UP });
  });

  it("leaves other refusals alone", async () => {
    vi.stubGlobal("fetch", vi.fn(() => reply(403, { detail: "Only administrators can do this." })));
    const prompt = vi.fn();
    setStepUpHandler(prompt);
    await expect(api("/admin/stats/")).rejects.toBeInstanceOf(ApiError);
    expect(prompt).not.toHaveBeenCalled();
  });

  it("does not prompt again when the retried request is refused too", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url) => (url.endsWith("/auth/step-up/") ? reply(200, { access: "t" }) : reply(403, STEP_UP))),
    );
    const prompt = vi.fn(() => confirmIdentity("pw"));
    setStepUpHandler(prompt);
    await expect(api("/admin/stats/")).rejects.toMatchObject({ status: 403 });
    expect(prompt).toHaveBeenCalledTimes(1);
  });
});

describe("money actions", () => {
  it("send the same Idempotency-Key again when retried after the password prompt", async () => {
    const fetchMock = vi.fn((url, options) => {
      if (url.endsWith("/auth/step-up/")) return reply(200, { access: "stepped-up" });
      return options.headers.Authorization === "Bearer stepped-up" ? reply(201, { sequence: 7 }) : reply(403, STEP_UP);
    });
    vi.stubGlobal("fetch", fetchMock);
    setStepUpHandler(() => confirmIdentity("pw"));
    const key = newIdempotencyKey();
    await api("/admin/schools/1/ledger/", { method: "POST", body: { kind: "refund" }, headers: { "Idempotency-Key": key } });
    const sent = fetchMock.mock.calls.filter(([url]) => url.endsWith("/ledger/")).map(([, options]) => options.headers);
    expect(sent).toHaveLength(2);
    expect(sent.every((headers) => headers["Idempotency-Key"] === key)).toBe(true);
  });

  it("make a new key each time, in the form the server accepts", () => {
    const keys = new Set(Array.from({ length: 50 }, newIdempotencyKey));
    expect(keys.size).toBe(50);
    expect([...keys].every((key) => /^[A-Za-z0-9_-]{8,80}$/.test(key))).toBe(true);
  });

  it("can download a file instead of reading JSON", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("sequence,gross\n1,200.00\n", { status: 200 }))));
    const blob = await api("/admin/ledger/export/", { as: "blob" });
    expect(await blob.text()).toBe("sequence,gross\n1,200.00\n");
  });
});

describe("security changes", () => {
  it("switch to the new access token the answer carries, and keep it out of page state", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(reply(200, { detail: "Password updated.", access: "new-token" }));
    fetch.mockResolvedValueOnce(reply(200, { username: "aline" }));
    vi.stubGlobal("fetch", fetch);
    setAccessToken("old-token");

    const data = await api("/auth/password/", { method: "POST", body: { current_password: "a", new_password: "b" } });
    expect(data).toEqual({ detail: "Password updated." });
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer old-token");

    await api("/auth/me/");
    expect(fetch.mock.calls[1][1].headers.Authorization).toBe("Bearer new-token");
  });

  it("leave other answers that mention access alone", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(200, { access: { premium: true } })));
    setAccessToken("token");
    expect(await api("/auth/me/")).toEqual({ access: { premium: true } });
  });
});

describe("password reset", () => {
  it("never tries to refresh a session on its answers", async () => {
    const fetch = vi.fn().mockResolvedValue(reply(401, { detail: "No." }));
    vi.stubGlobal("fetch", fetch);
    await expect(api("/auth/password-reset/confirm/", { method: "POST", body: {} })).rejects.toThrow("No.");
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
