// Small fetch wrapper for the Django API.
// The access token lives only in memory; the refresh token is an httpOnly
// cookie the browser sends to /api/auth/refresh/ automatically.

const BASE = import.meta.env.VITE_API_BASE || "/api";

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
    super(messageFrom(data) || `Request failed (${status})`);
    this.status = status;
    this.data = data;
  }
}

function messageFrom(data) {
  if (!data) return "";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  if (Array.isArray(data)) return data.join(" ");
  const first = Object.entries(data)[0];
  if (!first) return "";
  const [field, value] = first;
  const text = Array.isArray(value) ? value.join(" ") : typeof value === "object" ? messageFrom(value) : value;
  return field === "non_field_errors" ? text : `${field}: ${text}`;
}

export async function refreshSession() {
  if (!refreshing) {
    refreshing = fetch(`${BASE}/auth/refresh/`, { method: "POST", credentials: "include" })
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
  const headers = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";

  const res = await fetch(url, {
    method,
    headers,
    credentials: "include",
    signal,
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });

  if (res.status === 401 && retry && !path.startsWith("/auth/")) {
    try {
      await refreshSession();
    } catch (err) {
      if (!(err instanceof ApiError)) throw err; // network problem, not an expired session
      onSessionExpired();
      throw new ApiError(401, { detail: "Your session has expired. Please log in again." });
    }
    return api(path, { method, body, params, retry: false, signal });
  }

  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

// DRF paginated responses have {results}; plain lists don't.
export const results = (data) => (Array.isArray(data) ? data : data?.results ?? []);
