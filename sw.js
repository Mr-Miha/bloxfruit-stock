// Офлайн-кэш оболочки приложения
const CACHE = "bfstock-v1";
const SHELL = ["./", "./index.html", "./manifest.webmanifest", "./icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;

  // данные: сначала сеть, при сбое — кэш
  if (url.pathname.endsWith("/data.json")) {
    e.respondWith(
      fetch(e.request)
        .then((r) => {
          const copy = r.clone();
          caches.open(CACHE).then((c) => c.put("./data.json", copy));
          return r;
        })
        .catch(() => caches.match("./data.json"))
    );
    return;
  }

  // оболочка: сначала кэш
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request))
  );
});
