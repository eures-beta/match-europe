(() => {
  const text = JSON.parse(document.getElementById('push-test-strings').textContent);
  const state = document.getElementById('status'),
    enable = document.getElementById('enable'),
    send = document.getElementById('send'),
    stop = document.getElementById('stop');
  let registration, config;
  const local = document.getElementById('local'),
    diagnostic = document.getElementById('diagnostic');
  const csrf = () =>
    document.cookie
      .split('; ')
      .find((v) => v.startsWith('csrftoken='))
      ?.split('=')[1];
  async function api(action, data) {
    const r = await fetch('/api/push-test/' + action + '/', {
      method: data ? 'POST' : 'GET',
      credentials: 'same-origin',
      headers: data ? { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() } : undefined,
      body: data ? JSON.stringify(data) : undefined,
    });
    if (!r.ok) throw Error(text.serverError);
    return r.json();
  }
  const bytes = (text) =>
    Uint8Array.from(
      atob(text.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (text.length % 4)) % 4)),
      (c) => c.charCodeAt(0),
    );
  enable.addEventListener('click', async () => {
    enable.disabled = true;
    try {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') throw Error(text.permissionDenied);
      const sub =
        (await registration.pushManager.getSubscription()) ||
        (await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: bytes(config.publicKey),
        }));
      await api('subscribe', sub.toJSON());
      send.disabled = false;
      stop.disabled = false;
      local.disabled = false;
      state.textContent = text.enabled;
    } catch (e) {
      state.textContent = e.message;
      enable.disabled = false;
    }
  });
  send.addEventListener('click', async () => {
    send.disabled = true;
    try {
      const cache = await caches.open('me-push-test-diagnostics');
      await cache.delete('push-report');
      await api('send', { language: document.documentElement.lang });
      state.textContent = text.scheduled;
    } catch (e) {
      state.textContent = e.message;
      send.disabled = false;
    }
  });
  stop.addEventListener('click', async () => {
    try {
      const sub = await registration.pushManager.getSubscription();
      if (sub) await sub.unsubscribe();
      await api('stop', {});
      send.disabled = true;
      stop.disabled = true;
      enable.disabled = false;
      state.textContent = text.stopped;
    } catch (e) {
      state.textContent = e.message;
    }
  });
  local.addEventListener('click', async () => {
    diagnostic.textContent = text.creating;
    try {
      await registration.showNotification(text.localTitle, {
        body: text.localBody,
        tag: 'me-local-display-' + Date.now(),
        renotify: true,
      });
      const list = await registration.getNotifications();
      diagnostic.textContent = text.displayCount.replace('{count}', String(list.length));
    } catch (e) {
      diagnostic.textContent = text.displayError + e.name + ' — ' + e.message;
    }
  });
  setInterval(async () => {
    try {
      const cache = await caches.open('me-push-test-diagnostics');
      const r = await cache.match('push-report');
      if (!r) return;
      const d = await r.json();
      diagnostic.textContent =
        d.stage === 'displayed'
          ? text.displayed
          : d.stage === 'received'
            ? text.received
            : text.browserError + d.message;
    } catch {}
  }, 2000);
  (async () => {
    try {
      if (
        !isSecureContext ||
        !('serviceWorker' in navigator) ||
        !('PushManager' in window) ||
        !('Notification' in window)
      )
        throw Error(text.unsupported);
      config = await api('config');
      registration = await navigator.serviceWorker.register('push-test-sw.js', { scope: './' });
      await registration.update();
      await navigator.serviceWorker.ready;
      if (Notification.permission === 'granted') local.disabled = false;
      const previous = await api('status');
      state.textContent =
        previous.state === 'sent'
          ? text.lastSent
          : previous.state === 'failed'
            ? text.lastFailed
            : text.ready;
    } catch (e) {
      state.textContent = e.message;
      enable.disabled = true;
    }
  })();
})();
