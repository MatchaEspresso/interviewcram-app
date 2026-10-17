// Offline support. The app shell is precached; the page is network-first so
// updates show up when online, and Google Fonts are cached after first use.
// Bump VERSION when the precache list changes.
const VERSION = 'v1';
const SHELL = `ic-shell-${VERSION}`;
const FONTS = 'ic-fonts';
const PRECACHE = [
  './',
  'index.html',
  'manifest.webmanifest',
  'icons/icon.svg',
  'icons/icon-180.png',
  'icons/icon-192.png',
  'icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL && k !== FONTS).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Network with a timeout, so a weak signal falls back to the cached page quickly.
function networkFirst(request, cacheKey) {
  return new Promise((resolve) => {
    let settled = false;
    const fallback = () => {
      if (settled) return;
      settled = true;
      caches.match(cacheKey || request).then((hit) => resolve(hit || Response.error()));
    };
    const timer = setTimeout(fallback, 3000);
    fetch(request).then((res) => {
      if (res.ok) {
        const copy = res.clone();
        caches.open(SHELL).then((c) => c.put(cacheKey || request, copy));
      }
      clearTimeout(timer);
      if (!settled) { settled = true; resolve(res); }
    }).catch(() => { clearTimeout(timer); fallback(); });
  });
}

function cacheFirst(request) {
  return caches.open(FONTS).then((c) => c.match(request).then((hit) => hit || fetch(request).then((res) => {
    if (res.ok || res.type === 'opaque') c.put(request, res.clone());
    return res;
  })));
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  if (req.mode === 'navigate') {
    event.respondWith(networkFirst(req, 'index.html'));
  } else if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    event.respondWith(cacheFirst(req));
  } else if (url.origin === self.location.origin) {
    event.respondWith(caches.match(req).then((hit) => hit || networkFirst(req)));
  }
});
