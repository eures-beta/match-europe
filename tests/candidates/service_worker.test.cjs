const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../../eures_beta/static/sw.js'), 'utf8');

function worker() {
  const handlers = {};
  const notifications = [];
  const windows = [];
  const pending = [];
  const self = {
    addEventListener: (name, callback) => (handlers[name] = callback),
    location: { origin: 'https://match.example.invalid' },
    registration: {
      showNotification: async (title, options) => notifications.push({ title, ...options }),
    },
    clients: { openWindow: async (url) => windows.push(url) },
  };
  vm.runInNewContext(source, { self, URL });
  return {
    notifications,
    windows,
    async deliver(url) {
      handlers.push({
        data: { json: () => ({ url, body: 'A fictional notification' }) },
        waitUntil: (promise) => pending.push(promise),
      });
      await Promise.all(pending);
    },
    async click(url) {
      handlers.notificationclick({
        notification: { data: { url }, close() {} },
        waitUntil: (promise) => pending.push(promise),
      });
      await Promise.all(pending);
    },
  };
}

test('canonical candidate and matching notifications display and open on the same origin', async () => {
  for (const url of [
    '/candidate/offer-reviews/42/dialogue/',
    '/candidate/offer-reviews/42/dialogue/?question=schedule%3Aone#question-title',
    '/matching/conversations/71/',
  ]) {
    const app = worker();
    await app.deliver(url);
    await app.click(url);
    assert.equal(app.notifications[0].data.url, url);
    assert.deepEqual(app.windows, ['https://match.example.invalid' + url]);
  }
});

test('previously delivered notifications can still follow the retired routes', async () => {
  for (const url of [
    '/matching/candidate/42/dialogue/',
    '/matching/candidate/42/dialogue/?question=schedule%3Aone#question-title',
    '/matching/shared/71/',
  ]) {
    const app = worker();
    await app.click(url);
    assert.deepEqual(app.windows, ['https://match.example.invalid' + url]);
  }
});

test('external, unrelated and malformed notification destinations never display or open', async () => {
  for (const url of [
    'https://attacker.invalid/matching/conversations/71/',
    '//attacker.invalid/matching/conversations/71/',
    'javascript:alert(1)',
    '/accounts/me/',
    '/matching/conversations/71/?next=https://attacker.invalid',
    '/candidate/offer-reviews/42/dialogue/../../accounts/me/',
    '/matching/conversations/not-a-number/',
    null,
    undefined,
    { toString: () => '/matching/conversations/71/' },
  ]) {
    const app = worker();
    await app.deliver(url);
    await app.click(url);
    assert.equal(app.notifications.length, 0);
    assert.equal(app.windows.length, 0);
  }
});
