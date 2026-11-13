const form = document.querySelector('[data-preview-push]');
const button = form.querySelector('button');
const status = form.querySelector('[role="status"]');

const standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
form.closest('[data-preview-push-step]').hidden = !standalone;

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  button.disabled = true;
  try {
    if (!standalone || !('PushManager' in window) || !('Notification' in window)) {
      throw new Error('Push is unavailable');
    }
    if ((await Notification.requestPermission()) !== 'granted') {
      throw new Error('Push permission was denied');
    }
    const registration = await navigator.serviceWorker.ready;
    const existing = await registration.pushManager.getSubscription();
    const publicKey = form.dataset.previewPush;
    const encoded = publicKey.replace(/-/g, '+').replace(/_/g, '/');
    const applicationServerKey = Uint8Array.from(atob(encoded), (char) => char.charCodeAt(0));
    const subscription =
      existing ||
      (await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey }));
    const response = await fetch(form.action, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': form.elements.csrfmiddlewaretoken.value,
      },
      body: JSON.stringify(subscription),
    });
    if (!response.ok || !(await response.json()).ok) {
      throw new Error('Push subscription was not saved');
    }
    status.textContent = form.dataset.success;
  } catch {
    status.textContent = form.dataset.failure;
  } finally {
    button.disabled = false;
  }
});
