import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, confirmIdentity, setAccessToken, setStepUpHandler } from "./api";

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
