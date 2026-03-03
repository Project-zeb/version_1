const CACHE_NAME = "disaster-guard-mobile-sos-v6";
const APP_ASSETS = [
  "/mobile/sos",
  "/mobile/manifest.json",
  "/static/offline-sos.html"
];

const MOBILE_SCOPE_PATH = "/mobile/";
const SOS_PATH = "/mobile/sos";
const OFFLINE_SOS_FALLBACK = "/static/offline-sos.html";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((oldKey) => caches.delete(oldKey))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const requestUrl = new URL(event.request.url);
  if (requestUrl.origin !== self.location.origin) {
    return;
  }

  if (event.request.mode === "navigate" && requestUrl.pathname.startsWith(MOBILE_SCOPE_PATH)) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(async () => {
          const cachedRequestedPage = await caches.match(event.request);
          if (cachedRequestedPage) {
            return cachedRequestedPage;
          }

          const cachedSosPage = await caches.match(SOS_PATH);
          if (cachedSosPage) {
            return cachedSosPage;
          }

          return caches.match(OFFLINE_SOS_FALLBACK);
        })
    );
    return;
  }

  if (event.request.mode === "navigate") {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        return cached;
      }

      return fetch(event.request)
        .then((networkResponse) => {
          const copy = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return networkResponse;
        });
    })
  );
});
