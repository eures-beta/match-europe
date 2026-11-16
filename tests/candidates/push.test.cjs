const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function harness({
  permission = 'default',
  existingKey,
  unsubscribe = true,
  save = true,
  hasRegistration = true,
  storedEndpoint = 'https://push.example.invalid/old',
} = {}) {
  const events = {};
  const calls = [];
  const button = { disabled: false };
  const status = { textContent: '' };
  const section = { hidden: true };
  let existing =
    existingKey === undefined
      ? null
      : {
          options: {
            applicationServerKey: existingKey === null ? null : new Uint8Array(existingKey).buffer,
          },
          endpoint: 'https://push.example.invalid/old',
          unsubscribe: async () => {
            calls.push('unsubscribe');
            if (unsubscribe) existing = null;
            return unsubscribe;
          },
        };
  const form = {
    action: '/candidate/push-subscriptions/',
    dataset: {
      candidatePush: 'AQID',
      candidatePushEndpoint: storedEndpoint,
      success: 'Enabled',
      failure: 'Try again',
    },
    elements: { csrfmiddlewaretoken: { value: 'fictional-csrf' } },
    querySelector: (selector) => (selector === 'button' ? button : status),
    closest: () => section,
    addEventListener: (name, handler) => {
      events[name] = handler;
    },
  };
  const pushManager = {
    getSubscription: async () => existing,
    subscribe: async (options) => {
      calls.push(['subscribe', options]);
      existing = {
        endpoint: 'https://push.example.invalid/new',
        keys: { p256dh: 'fictional', auth: 'fictional' },
        options,
      };
      return existing;
    },
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, '../../eures_beta/static/pwa/candidate-push.js'), 'utf8'),
    {
      document: { querySelector: () => form },
      window: { matchMedia: () => ({ matches: true }), PushManager: {}, Notification: {} },
      navigator: {
        serviceWorker: {
          ready: Promise.resolve({ pushManager }),
          getRegistration: async () => (hasRegistration ? { pushManager } : undefined),
        },
      },
      Notification: {
        permission,
        requestPermission: async () => {
          calls.push('permission');
          return permission === 'denied' ? 'denied' : 'granted';
        },
      },
      Uint8Array,
      atob,
      fetch: async (url, options) => {
        calls.push(['save', url, options]);
        return { ok: save, json: async () => ({ ok: save }) };
      },
    },
  );
  return {
    calls,
    button,
    status,
    section,
    submit: () => events.submit({ preventDefault() {} }),
    settle: () => new Promise(setImmediate),
  };
}

test('first subscription requires an explicit submit and a permission grant', async () => {
  const ui = harness();
  await ui.settle();
  assert.deepEqual(ui.calls, []);
  await ui.submit();
  assert.equal(ui.calls[0], 'permission');
  const [, options] = ui.calls.find((call) => call[0] === 'subscribe');
  assert.equal(options.userVisibleOnly, true);
  assert.deepEqual([...options.applicationServerKey], [1, 2, 3]);
  const [, url, request] = ui.calls.find((call) => call[0] === 'save');
  assert.equal(url, '/candidate/push-subscriptions/');
  assert.equal(request.method, 'POST');
  assert.equal(request.headers['X-CSRFToken'], 'fictional-csrf');
  assert.equal(JSON.parse(request.body).endpoint, 'https://push.example.invalid/new');
  assert.equal(ui.status.textContent, 'Enabled');
});

test('a granted permission without an existing subscription does not opt in automatically', async () => {
  const ui = harness({ permission: 'granted' });
  await ui.settle();
  assert.deepEqual(ui.calls, []);
  assert.equal(ui.button.disabled, false);
});

test('a removed service worker does not leave automatic renewal blocking the button', async () => {
  const ui = harness({ permission: 'granted', existingKey: [9], hasRegistration: false });
  await ui.settle();
  assert.deepEqual(ui.calls, []);
  assert.equal(ui.button.disabled, false);
});

for (const storedEndpoint of ['', 'https://push.example.invalid/another-browser']) {
  test(`a shared browser subscription is not migrated into another account: ${storedEndpoint}`, async () => {
    const ui = harness({ permission: 'granted', existingKey: [9], storedEndpoint });
    await ui.settle();
    assert.deepEqual(ui.calls, []);
    assert.equal(ui.button.disabled, false);
  });
}

test('an existing subscription with the current key causes no automatic write and is reused on submit', async () => {
  const ui = harness({ permission: 'granted', existingKey: [1, 2, 3] });
  await ui.settle();
  assert.deepEqual(ui.calls, []);
  await ui.submit();
  assert.equal(ui.calls.length, 2);
  assert.equal(ui.calls[0], 'permission');
  assert.equal(ui.calls[1][0], 'save');
  assert.equal(ui.status.textContent, 'Enabled');
});

for (const existingKey of [[4, 5, 6], [1, 2], null]) {
  test(`an old or unknown key is renewed before the new subscription is saved: ${existingKey}`, async () => {
    const ui = harness({ permission: 'granted', existingKey });
    await ui.settle();
    assert.equal(ui.calls[0], 'unsubscribe');
    assert.equal(ui.calls[1][0], 'subscribe');
    assert.equal(ui.calls[2][0], 'save');
    assert.equal(ui.calls.includes('permission'), false);
    assert.equal(ui.status.textContent, 'Enabled');
  });
}

test('a failed unsubscribe neither creates nor saves a replacement', async () => {
  const ui = harness({ permission: 'granted', existingKey: [9], unsubscribe: false });
  await ui.settle();
  assert.deepEqual(ui.calls, ['unsubscribe']);
  assert.equal(ui.status.textContent, 'Try again');
  assert.equal(ui.button.disabled, false);
});

test('a denied permission neither subscribes nor saves', async () => {
  const ui = harness({ permission: 'denied' });
  await ui.settle();
  assert.deepEqual(ui.calls, []);
  await ui.submit();
  assert.deepEqual(ui.calls, ['permission']);
  assert.equal(ui.status.textContent, 'Try again');
});

test('a failed server save reports failure and permits a retry', async () => {
  const ui = harness({ permission: 'granted', existingKey: [1, 2, 3], save: false });
  await ui.settle();
  await ui.submit();
  assert.equal(ui.status.textContent, 'Try again');
  assert.equal(ui.button.disabled, false);
});
