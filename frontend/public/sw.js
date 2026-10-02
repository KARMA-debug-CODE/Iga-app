/* Iga service worker: makes the app installable and keeps pages a student has
 * opened available offline (important where mobile data is patchy or costly).
 *
 * - App shell & built assets: cache-first (file names are content-hashed).
 * - GET /api/* for learning content: network-first, falling back to the last copy.
 * - Never caches auth, attempts, chat or anything that isn't a plain GET.
 */
const VERSION = "iga-v4";
const SHELL = ["/", "/index.html", "/manifest.webmanifest", "/icon.svg"];
const OFFLINE_API = [/^\/api\/(subjects|lessons|units|simulations|resources|meta|exam-papers)\b/];
const NEVER_CACHE = [/^\/api\/auth\//, /^\/api\/attempts\//, /^\/api\/groups\/\d+\/messages/, /^\/django-admin/];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function networkFirst(request) {
  const cache = await caches.open(VERSION);
  // Key by URL alone: never store the request's Authorization header on disk, and
  // let an offline request (which has no token) find the copy saved while online.
  const key = new Request(request.url);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(key, response.clone());
    if (response.status >= 500) {
      // Server unreachable behind the proxy (502/503/504): prefer the saved copy.
      const cached = await cache.match(key, { ignoreVary: true });
      if (cached) return cached;
    }
    return response;
  } catch (err) {
    const cached = await cache.match(key, { ignoreVary: true });
    if (cached) return cached;
    throw err;
  }
}

async function cacheFirst(request) {
  // Hashed assets never change, so match by URL alone (some servers add "Vary: Origin").
  const key = new Request(request.url);
  const cached = await caches.match(key, { ignoreVary: true });
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) (await caches.open(VERSION)).put(key, response.clone());
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (NEVER_CACHE.some((re) => re.test(url.pathname))) return;

  if (url.pathname.startsWith("/api/")) {
    if (OFFLINE_API.some((re) => re.test(url.pathname))) event.respondWith(networkFirst(request));
    return;
  }
  if (request.mode === "navigate") {
    // Single-page app: every route is served by index.html.
    event.respondWith(fetch(request).catch(() => caches.match("/index.html", { ignoreVary: true })));
    return;
  }
  // Built assets and the Python runtime never change under the same name.
  if (url.pathname.startsWith("/assets/") || url.pathname.startsWith("/pyodide/") || SHELL.includes(url.pathname)) {
    event.respondWith(cacheFirst(request));
  }
});
