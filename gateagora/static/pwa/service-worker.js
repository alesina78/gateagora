// service-worker.js — Gate 4
// Salve em: static/pwa/service-worker.js

const CACHE = 'gate4-v1';

const SHELL = [
  '/minhas-aulas/',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.allSettled(SHELL.map(u => c.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const { request } = e;

  if (request.method !== 'GET') {
    e.respondWith(fetch(request));
    return;
  }

  if (request.mode === 'navigate') {
    e.respondWith(
      fetch(request)
        .then(res => {
          caches.open(CACHE).then(c => c.put(request, res.clone()));
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  const url = new URL(request.url);
  if (
    url.hostname.includes('googleapis.com') ||
    url.hostname.includes('gstatic.com') ||
    url.hostname.includes('cdnjs.cloudflare.com') ||
    url.hostname.includes('tailwindcss.com')
  ) {
    e.respondWith(
      caches.match(request).then(cached =>
        cached || fetch(request).then(res => {
          caches.open(CACHE).then(c => c.put(request, res.clone()));
          return res;
        })
      )
    );
    return;
  }

  if (url.pathname.startsWith('/static/')) {
    e.respondWith(
      caches.match(request).then(cached => cached || fetch(request))
    );
    return;
  }

  if (request.destination === 'image') {
    e.respondWith(
      caches.open(CACHE).then(c =>
        c.match(request).then(cached => {
          const fresh = fetch(request).then(res => { c.put(request, res.clone()); return res; });
          return cached || fresh;
        })
      )
    );
    return;
  }

  e.respondWith(fetch(request));
});
