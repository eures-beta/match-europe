const form = document.querySelector('[data-candidate-push]');
const button = form.querySelector('button');
const status = form.querySelector('[role="status"]');

const standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
form.closest('[data-candidate-push-step]').hidden = !standalone;

let updating = false;

function sameKey(existing, expected) {
  const key = existing?.options?.applicationServerKey;
  if (!key) return false;
  const bytes = new Uint8Array(key);
  return bytes.length === expected.length && bytes.every((byte, index) => byte === expected[index]);
}

async function updateSubscription({ existingOnly = false } = {}) {
  if (updating) return;
  updating = true;
  button.disabled = true;
  try {
    if (!standalone || !('PushManager' in window) || !('Notification' in window)) {
      throw new Error('Push is unavailable');
    }
    if (!existingOnly && (await Notification.requestPermission()) !== 'granted') {
      throw new Error('Push permission was denied');
    }
    const registration = existingOnly
      ? await navigator.serviceWorker.getRegistration()
      : await navigator.serviceWorker.ready;
    if (!registration) return;
    let existing = await registration.pushManager.getSubscription();
    // Automatic renewal is only for this candidate's stored browser endpoint.
    // A shared browser's permission must not opt a different account in.
    if (
      existingOnly &&
      (!existing ||
        existing.endpoint !== form.dataset.candidatePushEndpoint ||
        Notification.permission !== 'granted')
    )
      return;
    const publicKey = form.dataset.candidatePush;
    const encoded = publicKey.replace(/-/g, '+').replace(/_/g, '/');
    const applicationServerKey = Uint8Array.from(atob(encoded), (char) => char.charCodeAt(0));
    if (existingOnly && sameKey(existing, applicationServerKey)) return;
    if (existing && !sameKey(existing, applicationServerKey)) {
      if (!(await existing.unsubscribe())) {
        throw new Error('Previous Push subscription could not be removed');
      }
      existing = null;
    }
    if (existingOnly && Notification.permission !== 'granted') return;
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
    updating = false;
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  return updateSubscription();
});

// Refresh an already-consented subscription, including after a VAPID rotation.
// Never prompt or subscribe for the first time without the user's action.
if (
  standalone &&
  form.dataset.candidatePushEndpoint &&
  'PushManager' in window &&
  'Notification' in window &&
  Notification.permission === 'granted'
) {
  void updateSubscription({ existingOnly: true });
}
