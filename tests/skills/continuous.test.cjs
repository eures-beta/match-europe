const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function harness(fetch, initial = '{}', role = 'candidate') {
  class Element {
    constructor(tag = 'div') {
      this.tag = tag;
      this.children = [];
      this.listeners = {};
      this.value = '';
      this.dataset = {};
    }
    append(node) {
      this.children.push(node);
      node.parent = this;
    }
    replaceChildren() {
      this.children = [];
    }
    setAttribute(key, value) {
      this[key] = value;
    }
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    }
    remove() {
      this.parent.children = this.parent.children.filter((node) => node !== this);
    }
  }
  const form = new Element('form');
  const root = new Element('section');
  const jobs = new Element();
  const field = new Element('input');
  field.value = initial;
  const selected = [];
  root.dataset = {
    role,
    skills: 'Skills',
    behaviours: 'Behaviours',
    wait: 'Please wait',
    error: 'Try later',
    retry: 'Retry',
    simulation: 'Simulation',
    heading: 'Skills',
  };
  root.closest = () => form;
  root.querySelector = () => jobs;
  form.querySelectorAll = () =>
    selected.map((uri) => ({
      value: uri.startsWith('rome:') ? uri : 'esco:' + uri,
      dataset: {
        skillReference:
          uri === 'rome:D1102'
            ? 'http://data.europa.eu/esco/occupation/1aadb308-432a-4d01-b54b-b4f7f76dd419'
            : uri,
      },
    }));
  form.querySelector = () => ({ value: 'private-draft-token' });
  const context = {
    document: {
      querySelector: () => root,
      getElementById: () => field,
      createElement: (tag) => new Element(tag),
      documentElement: { lang: 'en' },
      cookie: 'csrftoken=fixture',
    },
    window: { meOccupation: { collect: () => ({ uris: selected, skill_references: selected }) } },
    fetch,
    Map,
    AbortController,
    setTimeout: () => 1,
    clearTimeout: () => {},
  };
  vm.runInNewContext(
    fs.readFileSync(
      path.join(__dirname, '../../eures_beta/skills/static/skills/continuous.js'),
      'utf8',
    ),
    context,
  );
  const change = () =>
    role === 'candidate'
      ? form.listeners.change({ target: { name: 'occupation_references' } })
      : context.window.meOccupationSkills.update();
  const all = () => {
    const out = [];
    const walk = (node) => {
      out.push(node);
      node.children.forEach(walk);
    };
    walk(jobs);
    return out;
  };
  return { root, jobs, field, selected, change, all, context };
}
const settle = async () => {
  for (let i = 0; i < 12; i++) await Promise.resolve();
};
const response = {
  ok: true,
  json: async () => ({
    label: 'Official occupation',
    skills: Array.from({ length: 8 }, (_, i) => ['skill-' + i, 'Official skill ' + i]),
    behaviours: [],
    simulated: true,
  }),
};

test('starts empty, persists explicit choices with cap five, and clears deselected occupations', async () => {
  const requests = [];
  const h = harness(async (url, options) => {
    requests.push(JSON.parse(options.body));
    return response;
  }, 'null');
  assert.equal(h.jobs.children.length, 0);
  h.selected.push('occupation');
  h.change();
  await settle();
  assert.equal(requests[0].token, 'private-draft-token');
  assert.equal(requests[0].role, 'candidate');
  const inputs = h.all().filter((node) => node.tag === 'input');
  assert.equal(inputs.length, 8);
  assert.ok(inputs.every((input) => !input.checked));
  inputs.slice(0, 5).forEach((input) => {
    input.checked = true;
  });
  h.all()
    .find((node) => node.tag === 'fieldset')
    .listeners.change();
  assert.equal(JSON.parse(h.field.value).occupation.skills.length, 5);
  assert.equal(inputs[5].disabled, true);
  h.selected.pop();
  h.change();
  assert.equal(h.field.value, '{}');
  assert.equal(h.jobs.children.length, 0);
});

test('saved employer choices survive loading and failure offers an explicit retry', async () => {
  let fail = true;
  const h = harness(
    async () => {
      if (fail) throw Error('network');
      return response;
    },
    '{}',
    'employer',
  );
  h.selected.push('occupation');
  h.change();
  await settle();
  const retry = h.all().find((node) => node.tag === 'button');
  assert.ok(retry);
  h.context.window.meOccupationSkills.load({ occupation: { skills: ['skill-1'], behaviours: [] } });
  fail = false;
  retry.listeners.click();
  await settle();
  assert.equal(
    h
      .all()
      .filter((node) => node.tag === 'input')
      .find((input) => input.value === 'skill-1').checked,
    true,
  );
  assert.match(h.context.window.meOccupationSkills.summary(), /Official skill 1/);
});

test('late response after removing a selected occupation cannot restore its choices', async () => {
  let finish;
  const h = harness(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  h.selected.push('occupation');
  h.change();
  h.selected.pop();
  h.change();
  finish(response);
  await settle();
  assert.equal(h.jobs.children.length, 0);
  assert.equal(h.field.value, '{}');
});

test('ROME baker and ESCO baker share one list and preserve choices when one reference is removed', async () => {
  const uri = 'http://data.europa.eu/esco/occupation/1aadb308-432a-4d01-b54b-b4f7f76dd419';
  const calls = [];
  const h = harness(async (_url, options) => {
    calls.push(JSON.parse(options.body).occupation);
    return {
      ok: true,
      json: async () => ({ label: 'Baker', skills: [['s1', 'Knead']], behaviours: [] }),
    };
  });
  h.selected.push('rome:D1102', uri);
  h.change();
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(calls, [uri]);
  assert.equal(h.jobs.children.length, 1);
  h.selected.shift();
  h.change();
  assert.equal(h.jobs.children.length, 1);
  assert.deepEqual(calls, [uri]);
});
