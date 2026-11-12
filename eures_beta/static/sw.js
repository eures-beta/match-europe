// Private pages, messages, documents and API responses are NEVER cached.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
// No fetch interception: network-only workspaces; no misleading offline promises.

self.addEventListener('push', (event) => {
  const { url } = event.data.json();
  if (!/^\/matching\/candidate\/\d+\/dialogue\/$/.test(url)) return;
  event.waitUntil(self.registration.showNotification('Match Europe', { data: { url } }));
});

self.addEventListener('notificationclick', (event) => {
  const url = event.notification.data?.url;
  event.notification.close();
  if (!/^\/matching\/candidate\/\d+\/dialogue\/$/.test(url)) return;
  event.waitUntil(self.clients.openWindow(new URL(url, self.location.origin).href));
});
