// Execute the real browser module with a small DOM and a deterministic clock.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function harness(fetch) {
  class Element {
    constructor(tag = 'div') {
      this.tagName = tag;
      this.children = [];
      this.hidden = false;
      this.value = '';
      this.textContent = '';
      this.listeners = {};
      this.style = {};
    }
    append(...nodes) {
      this.children.push(...nodes);
    }
    after(node) {
      this.children.push(node);
    }
    setAttribute() {}
    closest() {
      return this;
    }
    replaceChildren() {
      this.children = [];
    }
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    }
    focus() {}
    scrollIntoView() {}
  }
  const ids = Object.fromEntries(
    [
      'review-title',
      'review-form',
      'review-description',
      'review-desiredProfile',
      'occupation-strings',
    ].map((id) => [id, new Element()]),
  );
  ids['review-title'].value = 'technicien';
  ids['occupation-strings'].textContent = JSON.stringify({
    busy: 'Finding descriptions…',
    searchFailed: 'Search failed',
    manualHelp: 'Manual search',
    required: 'Choose a description',
    personal: 'Personal description',
    retry: 'Retry',
    resultsFound: '{count} results',
  });
  const timers = new Map();
  let sequence = 0;
  const context = {
    document: {
      querySelector: () => new Element(),
      getElementById: (id) => ids[id],
      createElement: (tag) => new Element(tag),
      documentElement: { lang: 'en' },
      cookie: '',
    },
    window: {},
    AbortController,
    Set,
    console,
    setTimeout: (fn, ms) => {
      timers.set(++sequence, { fn, ms });
      return sequence;
    },
    clearTimeout: (id) => timers.delete(id),
    fetch,
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, '../static/employer/occupation-picker.js'), 'utf8'),
    context,
  );
  const all = () => {
    const out = [];
    const walk = (e) => {
      out.push(e);
      e.children.forEach(walk);
    };
    Object.values(ids).forEach(walk);
    return out;
  };
  return { context, ids, timers, all };
}
const settle = async () => {
  for (let i = 0; i < 12; i++) await Promise.resolve();
};

test('a stalled request stops loading and exposes a usable personal description', async () => {
  const h = harness(() => new Promise(() => {}));
  h.context.window.meOccupation.load(null);
  await settle();
  const watchdog = [...h.timers.values()].find((t) => t.ms >= 1000);
  assert.ok(watchdog, 'Every request needs a watchdog');
  watchdog.fn();
  await settle();
  const personal = h.all().find((e) => e.id === 'occupation-personal');
  assert.equal(h.all().find((e) => e.children.includes(personal)).hidden, false);
  assert.ok(h.all().some((e) => e.textContent === 'Search failed'));
  assert.ok(!h.all().some((e) => e.textContent === 'Finding descriptions…'));
  personal.value = 'Maintenance technician';
  personal.listeners.input();
  assert.equal(h.context.window.meOccupation.validate(), true);
});

test('HTTP failure exposes the same manual fallback', async () => {
  const h = harness(async () => ({ ok: false }));
  h.context.window.meOccupation.load(null);
  await settle();
  const personal = h.all().find((e) => e.id === 'occupation-personal');
  assert.equal(h.all().find((e) => e.children.includes(personal)).hidden, false);
});

test('successful API response renders selectable descriptions', async () => {
  const h = harness(async () => ({
    ok: true,
    json: async () => ({
      version: '1.2.1',
      results: [
        {
          uri: 'urn:example:job',
          label: 'Technician',
          description: 'Maintenance',
          esco_code: '123',
        },
      ],
      rome_results: [],
      total: 1,
    }),
  }));
  h.context.window.meOccupation.load(null);
  await settle();
  const choice = h.all().find((e) => e.type === 'checkbox');
  assert.ok(choice);
  choice.checked = true;
  choice.listeners.change();
  assert.equal(h.context.window.meOccupation.validate(), true);
  assert.equal(h.context.window.meOccupation.collect().uris[0], 'urn:example:job');
});
