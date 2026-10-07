const C = "forge-v1"; const SHELL = ["/", "/static/styles.css", "/static/app.js", "/static/icon.svg", "/manifest.webmanifest"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(C).then((c) => c.addAll(SHELL))));
self.addEventListener("fetch", (e) => { const u = new URL(e.request.url);
  if (u.pathname.startsWith("/api/")) return;                  // live data always from network
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request))); });
