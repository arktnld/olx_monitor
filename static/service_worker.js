// Service Worker para OLX Monitor PWA
// Foca em permitir instalação, não em funcionalidade offline (precisa do backend Python)

const CACHE_NAME = 'olx-monitor-v1';

// Arquivos para cache (apenas estáticos)
const urlsToCache = [
  '/',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/manifest.json'
];

// Instalação
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
  self.skipWaiting();
});

// Ativação
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch - passa para rede, mas com handler registrado (necessário para alguns browsers)
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() => {
      // Se offline, retorna resposta básica
      return new Response('Offline - conecte à internet', {
        status: 503,
        statusText: 'Service Unavailable'
      });
    })
  );
});
