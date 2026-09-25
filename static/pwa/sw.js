const CACHE = 'dora-dental-static-v7';
const STATIC_ASSETS = [
  '/offline/',
  '/static/pwa/manifest.webmanifest',
  '/static/css/app.css',
  '/static/css/portal.css',
  '/static/pwa/icon-192.png',
  '/static/pwa/icon-512.png',
  '/static/pwa/icon-maskable-192.png',
  '/static/pwa/icon-maskable-512.png',
  '/static/pwa/apple-touch-icon.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key.startsWith('dora-dental-static-') && key !== CACHE)
          .map(key => caches.delete(key))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match('/offline/')));
    return;
  }
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
        const copy = response.clone();
        caches.open(CACHE).then(cache => cache.put(event.request, copy));
        return response;
      }))
    );
  }
});

self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = {title: 'Dora\'s Dental Gem', body: event.data ? event.data.text() : ''}; }
  const title = data.title || "Dora's Dental Gem";
  const options = {
    body: data.body || '',
    icon: '/static/pwa/icon-192.png',
    badge: '/static/pwa/icon-192.png',
    data: { url: data.url || '/' },
    vibrate: [200, 100, 200],
    tag: 'dora-dental-notification-' + (data.notification_id || Date.now()),
    renotify: true
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil(clients.matchAll({type: 'window', includeUncontrolled: true}).then(clientList => {
    for (const client of clientList) {
      if ('focus' in client) {
        client.navigate(target);
        return client.focus();
      }
    }
    if (clients.openWindow) return clients.openWindow(target);
  }));
});
