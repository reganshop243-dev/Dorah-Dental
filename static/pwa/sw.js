const CACHE = 'dora-dental-static-v5';
const STATIC_ASSETS = ['/offline/', '/static/pwa/manifest.webmanifest', '/static/css/app.css', '/static/pwa/icon-192.png', '/static/pwa/icon-512.png'];
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  // Never cache authenticated/dynamic HTML or API responses.
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match('/offline/')));
    return;
  }
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(caches.match(event.request).then(r => r || fetch(event.request).then(resp => {
      const copy = resp.clone(); caches.open(CACHE).then(c => c.put(event.request, copy)); return resp;
    })));
  }
});
