const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function harness(response) {
  const events = {};
  const timers = new Map();
  const requests = [];
  let sequence = 0;
  const form = {
    querySelector: (selector) => ({
      value: selector.includes('csrfmiddlewaretoken') ? 'csrf-token' : 'draft-token',
    }),
  };
  const timeout = { hidden: true, dataset: { seconds: '7200', warningSeconds: '120' } };
  const extend = {
    dataset: { done: 'Extended', failed: 'Not extended' },
    addEventListener: (name, handler) => (events[name] = handler),
    focus() {},
  };
  const status = { textContent: '' };
  const ids = {
    'journey-timeout': timeout,
    'journey-timeout-extend': extend,
    'journey-timeout-status': status,
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, '../static/candidate/guided-journey.js'), 'utf8'),
    {
      document: {
        getElementById: (id) => ids[id] || null,
        querySelectorAll: () => [],
        querySelector: (selector) => (selector.startsWith('form') ? { form } : null),
        addEventListener() {},
      },
      window: { location: { href: 'https://example.invalid/candidate/prepare/?step=3' } },
      URLSearchParams,
      setTimeout: (callback, delay) => {
        timers.set(++sequence, { callback, delay });
        return sequence;
      },
      clearTimeout: (id) => timers.delete(id),
      fetch: async (...args) => {
        requests.push(args);
        return response;
      },
    },
  );
  const warning = [...timers.values()][0];
  assert.equal(warning.delay, 7080000);
  warning.callback();
  return { timeout, extend, status, requests, click: events.click };
}

test('extension uses a protected POST and only confirms an explicit server acknowledgement', async () => {
  const ui = harness({ ok: true, json: async () => ({ extended: true, seconds: 7200 }) });
  await ui.click();
  const [, options] = ui.requests[0];
  assert.equal(options.method, 'POST');
  assert.equal(options.headers['X-CSRFToken'], 'csrf-token');
  assert.equal(options.body.get('action'), 'extend');
  assert.equal(options.body.get('token'), 'draft-token');
  assert.equal(ui.timeout.hidden, true);
  assert.equal(ui.status.textContent, 'Extended');
  assert.equal(ui.extend.disabled, false);
});

for (const [name, response] of [
  ['expired draft', { ok: false, status: 409 }],
  [
    'HTML page after a redirect',
    {
      ok: true,
      json: async () => {
        throw new Error('HTML');
      },
    },
  ],
  ['response without acknowledgement', { ok: true, json: async () => ({}) }],
]) {
  test(`extension never claims success for ${name}`, async () => {
    const ui = harness(response);
    await ui.click();
    assert.equal(ui.timeout.hidden, false);
    assert.equal(ui.status.textContent, 'Not extended');
    assert.equal(ui.extend.disabled, false);
  });
}
