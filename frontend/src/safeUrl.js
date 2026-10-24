// Addresses that come from data (a teacher's resource link, a lesson video, a past paper, a simulation,
// the payment page) before they become a link, a frame or a page change.
//
// Only web addresses (http, https) and paths on this site are used. javascript:, data:, vbscript:, file:
// and other schemes could run code in the page or open files on the device. React blocks javascript: in
// href and src, but not the others, and not window.location; the server also accepts only web addresses.

// A path on this site: "/x", but not "//host" or "/\host", which browsers read as another site.
const SAME_SITE_PATH = /^\/(?![/\\])/;

/** `value` if it is a web address or a path on this site, else undefined. httpsOnly refuses http:. */
export function safeUrl(value, { httpsOnly = false } = {}) {
  const text = typeof value === "string" ? value.trim() : "";
  if (!text) return undefined;
  if (SAME_SITE_PATH.test(text)) return text;
  let url;
  try {
    url = new URL(text);
  } catch {
    return undefined;
  }
  return url.protocol === "https:" || (url.protocol === "http:" && !httpsOnly) ? url.href : undefined;
}

/** A path on this site (for router links), else undefined. */
export function sitePath(value) {
  return typeof value === "string" && SAME_SITE_PATH.test(value) ? value : undefined;
}
