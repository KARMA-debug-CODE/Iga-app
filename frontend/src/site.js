// What the public pages show besides their own text, from GET /api/site/: the legal pages' version, owner
// and contact address, how long records are kept, the server's price list (never written twice) and whether
// maintenance mode is on. Fetched once per page load and shared by every page that asks.
import { useEffect, useState } from "react";

import { api } from "./api";

let cached = null;
let pending = null;

export function loadSiteInfo() {
  if (cached) return Promise.resolve(cached);
  if (!pending) {
    pending = api("/site/")
      .then((data) => {
        cached = data;
        return data;
      })
      .finally(() => {
        pending = null;
      });
  }
  return pending;
}

/** {data, error}: the site information (null while it loads or when it couldn't be loaded). */
export function useSiteInfo() {
  const [state, setState] = useState(() => ({ data: cached, error: null }));
  useEffect(() => {
    if (cached) return undefined;
    let alive = true;
    loadSiteInfo()
      .then((data) => alive && setState({ data, error: null }))
      .catch((error) => alive && setState({ data: null, error }));
    return () => {
      alive = false;
    };
  }, []);
  return state;
}

/** For tests: forget what was loaded. */
export function resetSiteInfo() {
  cached = null;
  pending = null;
}
