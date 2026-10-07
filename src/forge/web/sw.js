// FORGE PWA service worker v5: NEVER caches app code or data (stale JS caused a blank dashboard once).
// Purges every older cache on activation and takes control immediately.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil((async () => {
  for (const k of await caches.keys()) await caches.delete(k);
  await self.clients.claim();
})()));
self.addEventListener("fetch", () => {});   // network only (installability requires a fetch handler)
