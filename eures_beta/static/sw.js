// Private pages, messages, documents and API responses are NEVER cached.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
// No fetch interception: network-only workspaces; no misleading offline promises.

const dialogueUrl =
  /^\/candidate\/offer-reviews\/\d+\/dialogue\/(?:\?question=[\w%:-]+#question-title)?$/;

const sharedUrl = /^\/matching\/conversations\/\d+\/$/;
// Compatibility only for notifications already delivered before the route rename.
// New notifications use Django's canonical named routes; HTTP redirects retain old links.
const legacyNotificationUrl =
  /^\/matching\/(?:candidate\/\d+\/dialogue\/(?:\?question=[\w%:-]+#question-title)?|shared\/\d+\/)$/;
const allowedUrl = (url) =>
  typeof url === 'string' &&
  (dialogueUrl.test(url) || sharedUrl.test(url) || legacyNotificationUrl.test(url));

self.addEventListener('push', (event) => {
  const { url, body } = event.data.json();
  if (!allowedUrl(url)) return;
  event.waitUntil(self.registration.showNotification('Match Europe', { body, data: { url } }));
});

self.addEventListener('notificationclick', (event) => {
  const url = event.notification.data?.url;
  event.notification.close();
  if (!allowedUrl(url)) return;
  event.waitUntil(self.clients.openWindow(new URL(url, self.location.origin).href));
});
