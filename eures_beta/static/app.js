/* No private data is cached or sent to third parties. */
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
const chat = document.querySelector('[data-feed]');
if (chat) {
  setInterval(async () => {
    if (document.hidden) return;
    try {
      const response = await fetch(chat.dataset.feed, {
        cache: 'no-store',
        credentials: 'same-origin',
      });
      if (!response.ok) return;
      const data = await response.json();
      if (data.count > Number(chat.dataset.count))
        document.querySelector('#new-messages').hidden = false;
    } catch (_) {
      /* The existing conversation remains visible while disconnected. */
    }
  }, 5000);
}
