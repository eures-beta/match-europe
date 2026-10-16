// Private pages, messages, documents and API responses are NEVER cached.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
// No fetch interception: network-only workspaces; no misleading offline promises.
