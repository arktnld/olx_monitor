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

// Push notifications handler
self.addEventListener('push', event => {
  if (!event.data) return;

  try {
    const data = event.data.json();

    const options = {
      body: data.body || 'Alerta de preço!',
      icon: data.icon || '/static/icon-192.png',
      badge: '/static/icon-192.png',
      image: data.image,
      tag: data.tag || 'price-alert',
      requireInteraction: true,
      data: {
        url: data.url,
        adId: data.adId
      },
      actions: [
        { action: 'open', title: 'Ver anúncio' },
        { action: 'dismiss', title: 'Dispensar' }
      ]
    };

    event.waitUntil(
      self.registration.showNotification(data.title || 'OLX Monitor', options)
    );
  } catch (e) {
    console.error('Error showing push notification:', e);
  }
});

// Notification click handler
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  const url = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(windowClients => {
        // Check if there's already a window open
        for (const client of windowClients) {
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});
