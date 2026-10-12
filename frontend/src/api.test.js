import { afterEach, describe, expect, it, vi } from "vitest";

import { api, setAccessToken } from "./api";

function reply(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body };
}

afterEach(() => {
  vi.unstubAllGlobals();
  setAccessToken(null);
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
