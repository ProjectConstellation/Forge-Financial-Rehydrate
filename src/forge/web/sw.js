// FORGE PWA service worker: installable app shell; live data and authenticated pages always come from the network.
const C = "forge-v2"; const SHELL = ["/static/styles.css", "/static/app.js", "/static/login.js", "/static/icon.svg", "/manifest.webmanifest"];
self.addEventListener("install", (e) => { self.skipWaiting(); e.waitUntil(caches.open(C).then((c) => c.addAll(SHELL))); });
self.addEventListener("activate", (e) => e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== C).map((k) => caches.delete(k))))));
self.addEventListener("fetch", (e) => { const u = new URL(e.request.url);
  if (e.request.method !== "GET" || !u.pathname.startsWith("/static/")) return;     // never cache pages, API, auth or SSE
  e.respondWith(fetch(e.request).then((r) => { const cp = r.clone(); caches.open(C).then((c) => c.put(e.request, cp)); return r; })
    .catch(() => caches.match(e.request))); });
