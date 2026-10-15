// Small fetch wrapper for the Django API.
// The access token lives only in memory; the refresh token is an httpOnly
// cookie the browser sends to /api/auth/refresh/ automatically.

import { currentLanguage, hasTranslation, translateNow } from "./i18n";

const BASE = import.meta.env.VITE_API_BASE || "/api";

// Auth endpoints where a 401 is the answer itself rather than an expired access token.
const NO_REFRESH = new Set([
  "/auth/login/",
  "/auth/register/",
  "/auth/refresh/",
  "/auth/logout/",
  "/auth/password-reset/",
  "/auth/password-reset/confirm/",
]);
// Security changes end every session, this one's access token included: the answer carries a new one.
const ISSUES_ACCESS_TOKEN = new Set(["/auth/password/", "/auth/2fa/enable/", "/auth/2fa/disable/"]);

let accessToken = null;
let refreshing = null;
let onSessionExpired = () => {};

export function setAccessToken(token) {
  accessToken = token;
}

export function setSessionExpiredHandler(fn) {
  onSessionExpired = fn;
}

export class ApiError extends Error {
  constructor(status, data) {
    super(messageFrom(data) || translateNow("errors.requestFailed", { status }));
    this.status = status;
    this.data = data;
  }
}

/** The server couldn't be reached (offline, or the connection dropped): not an answer from it. */
export class NetworkError extends Error {
  constructor() {
    super(translateNow("errors.network"));
  }
}

// Field names in validation errors, shown as the form's labels rather than as code.
function fieldLabel(field) {
  const key = `field.${field}`;
  return hasTranslation(key) ? translateNow(key) : field.replace(/_/g, " ");
}

function messageFrom(data) {
  if (!data) return "";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  if (Array.isArray(data)) return data.map((item) => (typeof item === "object" ? messageFrom(item) : item)).join(" ");
  const first = Object.entries(data)[0];
  if (!first) return "";
  const [field, value] = first;
  if (value && typeof value === "object" && !Array.isArray(value)) return messageFrom(value); // nested form, e.g. new_school
  const text = Array.isArray(value) ? value.join(" ") : value;
  return field === "non_field_errors" ? text : `${fieldLabel(field)}: ${text}`;
}

// Refresh tokens work once. Tabs take turns (Web Locks) so a second tab sends
// the cookie the first tab's refresh just set, not the one it used up.
function postRefresh() {
  const send = () => fetch(`${BASE}/auth/refresh/`, { method: "POST", credentials: "include" });
  return typeof navigator !== "undefined" && navigator.locks ? navigator.locks.request("iga-refresh", send) : send();
}

export async function refreshSession() {
  if (!refreshing) {
    refreshing = postRefresh()
      .then(async (res) => {
        if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null));
        const data = await res.json();
        accessToken = data.access;
        return data;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

export async function api(path, { method = "GET", body, params, retry = true, signal } = {}) {
  let url = `${BASE}${path}`;
  if (params) {
    const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ""));
    if ([...query].length) url += `?${query}`;
  }
  // The server answers in the reader's language (its own error messages included).
  const headers = { "Accept-Language": currentLanguage() };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";

  let res;
  try {
    res = await fetch(url, {
      method,
      headers,
      credentials: "include",
      signal,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch (err) {
    if (err?.name === "AbortError") throw err;
    throw new NetworkError(); // instead of the browser's English "Failed to fetch"
  }

  if (res.status === 401 && retry && !NO_REFRESH.has(path)) {
    await refreshAfter401();
    return api(path, { method, body, params, retry: false, signal });
  }

  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  if (ISSUES_ACCESS_TOKEN.has(path) && data?.access) {
    accessToken = data.access;
    delete data.access; // kept in memory here only, never in page state
  }
  return data;
}

// The access token has expired: refresh the session, or end it when the server refuses.
async function refreshAfter401() {
  try {
    await refreshSession();
  } catch (err) {
    // Only a refusal from the server means the session is over; a network blip or 5xx doesn't.
    if (!(err instanceof ApiError) || ![401, 403].includes(err.status)) throw err;
    onSessionExpired();
    throw new ApiError(401, { detail: translateNow("errors.sessionExpired") });
  }
}

/**
 * A POST whose answer is read while it arrives (Server-Sent Events). Resolves with the Response once the
 * server starts answering; refusals before that (403, 429, ...) are thrown as ApiError, like api().
 */
export async function apiStream(path, { body, signal, retry = true } = {}) {
  const headers = { "Accept-Language": currentLanguage(), Accept: "text/event-stream", "Content-Type": "application/json" };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  let res;
  try {
    res = await fetch(`${BASE}${path}`, { method: "POST", headers, credentials: "include", signal, body: JSON.stringify(body) });
  } catch (err) {
    if (err?.name === "AbortError") throw err;
    throw new NetworkError();
  }
  if (res.status === 401 && retry) {
    await refreshAfter401();
    return apiStream(path, { body, signal, retry: false });
  }
  if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null));
  return res;
}

/** Calls onEvent(data) for each `data: {json}` event of a Server-Sent Events response; ":" lines are pings. */
export async function readEvents(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const flush = (block) => {
    const data = block
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (data) onEvent(JSON.parse(data));
  };
  for (;;) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n?/g, "\n");
    let end;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      flush(buffer.slice(0, end));
      buffer = buffer.slice(end + 2);
    }
    if (done) break;
  }
  flush(buffer);
}

// DRF paginated responses have {results}; plain lists don't.
export const results = (data) => (Array.isArray(data) ? data : data?.results ?? []);
