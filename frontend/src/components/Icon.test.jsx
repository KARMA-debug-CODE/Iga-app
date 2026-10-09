// Subject and badge icons are names sent by the server; unknown or old values must still draw something.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BadgeIcon, Icon, SubjectIcon } from "./Icon";

const html = (element) => renderToStaticMarkup(element);

describe("Icon", () => {
  it("draws a decorative line icon, or a labelled one", () => {
    expect(html(<Icon name="sigma" />)).toMatch(/^<svg[^>]*aria-hidden="true"/);
    expect(html(<Icon name="lock" label="Private" />)).toMatch(/role="img"/);
    expect(html(<Icon name="no-such-icon" />)).toBe("");
  });

  it("falls back for unknown names, old emojis and object keys", () => {
    const book = html(<SubjectIcon name="book" />);
    const award = html(<BadgeIcon name="award" />);
    expect(html(<SubjectIcon name="sigma" />)).not.toBe(book);
    for (const name of ["no-such-icon", "\u{1F4D0}", "constructor", "toString", undefined, ""]) {
      expect(html(<SubjectIcon name={name} />)).toBe(book);
      expect(html(<BadgeIcon name={name} />)).toBe(award);
    }
  });
});
