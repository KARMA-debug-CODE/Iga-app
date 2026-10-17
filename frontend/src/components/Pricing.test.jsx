// The pricing section shows the server's price list (/api/site/), never a price written in the app.
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n";
import { resetSiteInfo } from "../site";
import Pricing, { monthList } from "./Pricing";

function serve(site) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(site), { status: 200, headers: { "Content-Type": "application/json" } })),
  );
}

function show(lang = "en") {
  localStorage.setItem("iga.lang", lang);
  return render(
    <MemoryRouter>
      <I18nProvider>
        <Pricing />
      </I18nProvider>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  resetSiteInfo();
  localStorage.clear();
});

describe("Pricing", () => {
  it("shows the server's prices, month options and grace period", async () => {
    serve({ pricing: { prices: { USD: "150", RWF: "190000" }, month_options: [1, 6], grace_days: 5 }, legal: {}, retention: {} });
    show();
    expect(await screen.findByText("US$150.00")).toBeInTheDocument();
    expect(screen.getByText(/or RWF\s?190,000/)).toBeInTheDocument();
    expect(screen.getByText("Pay for 1 or 6 months at a time.")).toBeInTheDocument();
    expect(screen.getByText("Renewing late? Access continues for 5 days.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Register your school" })).toHaveAttribute("href", "/register?role=school_admin");
    expect(fetch).toHaveBeenCalledWith("/api/site/", expect.anything());
  });

  it("says so when the prices can't be loaded", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("offline"))));
    show();
    await waitFor(() => expect(screen.getByText(/could not be loaded/)).toBeInTheDocument());
  });

  it("lists month options in plain words", () => {
    const t = (key, vars) => (key === "pricing.monthsOr" ? `${vars.list} or ${vars.last}` : key);
    expect(monthList([1, 3, 6, 12], t)).toBe("1, 3, 6 or 12");
    expect(monthList([3], t)).toBe("3");
  });
});
