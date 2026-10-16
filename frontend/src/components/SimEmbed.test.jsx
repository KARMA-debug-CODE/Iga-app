// Simulations are framed with scripts allowed, so the frame's address must be an https page on another
// site: never javascript:, data:, http: or a page of this site (which allow-same-origin would let out).
import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../api", () => ({ api: vi.fn(() => Promise.resolve({})) }));

import SimEmbed, { frameUrl } from "./SimEmbed";

const sim = (embed_url) => ({ slug: "lab", title: "Lab", provider: "external", provider_id: "x", embed_url });

describe("simulation frames", () => {
  it("frames an https page on another site", () => {
    const url = "https://phet.colorado.edu/sims/html/forces/latest/forces_all.html?locale=en";
    const frame = render(<SimEmbed slug="lab" sim={sim(url)} autoLaunch />).container.querySelector("iframe");
    expect(frame.getAttribute("src")).toBe(url);
  });

  it.each([
    "javascript:alert(document.domain)",
    "data:text/html,<script>alert(1)</script>",
    "http://phet.colorado.edu/x",
    "/api/auth/me/",
    `${window.location.origin}/lessons/forces`,
    "//evil.example/x",
  ])("refuses to frame %s", (url) => {
    expect(frameUrl(url)).toBeUndefined();
    const box = render(<SimEmbed slug="lab" sim={sim(url)} autoLaunch />).container;
    expect(box.querySelector("iframe")).toBeNull();
    expect(box.querySelector(".alert-error")).not.toBeNull();
  });
});
