/* Parts counter shell SW — cache static shell only. Never caches API/DMS JSON. */
const CACHE = "parrts-shell-v1";
const SHELL = ["/", "/manifest.webmanifest", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // Never intercept API — live DMS only
  if (url.pathname.startsWith("/api") || url.port === "8000") return;
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    fetch(req)
      .then((res) => {
        // optional: cache navigations shell
        if (req.mode === "navigate" && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put("/", copy)).catch(() => {});
        }
        return res;
      })
      .catch(async () => {
        const cached = await caches.match(req);
        if (cached) return cached;
        if (req.mode === "navigate") {
          const home = await caches.match("/");
          if (home) return home;
        }
        return new Response("Offline — API/DMS unavailable", {
          status: 503,
          headers: { "Content-Type": "text/plain" },
        });
      })
  );
});
