const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.resolve(__dirname, '../../eures_beta/static/admin/filter-toggle.js'),
  'utf8',
);

function page(storage, missingFilters = false) {
  const attributes = {};
  const button = {
    hidden: true,
    dataset: { showLabel: 'Afficher les filtres', hideLabel: 'Masquer les filtres' },
    setAttribute: (name, value) => (attributes[name] = value),
    addEventListener: (name, callback) => (button[name] = callback),
  };
  const filters = { hidden: false };
  const classes = new Set();
  const changelist = {
    classList: {
      toggle: (name, enabled) => (enabled ? classes.add(name) : classes.delete(name)),
    },
  };
  const elements = {
    'admin-filter-toggle': button,
    'changelist-filter': missingFilters ? null : filters,
    changelist,
  };
  vm.runInNewContext(source, {
    document: { getElementById: (id) => elements[id] },
    localStorage: storage,
  });
  return { button, filters, classes, attributes };
}

test('collapse, restore and reopen without losing the display preference', () => {
  const data = new Map();
  const storage = {
    getItem: (key) => data.get(key),
    setItem: (key, value) => data.set(key, value),
  };
  const first = page(storage);
  assert.equal(first.button.hidden, false);
  assert.equal(first.filters.hidden, false);
  first.button.click();
  assert.equal(first.filters.hidden, true);
  assert.equal(first.attributes['aria-expanded'], 'false');
  assert.equal(first.button.textContent, 'Afficher les filtres');
  assert.equal(first.classes.has('filters-collapsed'), true);
  const next = page(storage);
  assert.equal(next.filters.hidden, true);
  next.button.click();
  assert.equal(next.filters.hidden, false);
  assert.equal(next.attributes['aria-expanded'], 'true');
  assert.equal(next.button.textContent, 'Masquer les filtres');
  assert.equal(page(storage).filters.hidden, false);
  assert.equal(data.size, 1);
});

test('the button works when browser storage is unavailable', () => {
  const denied = () => {
    throw new Error('Storage unavailable');
  };
  const current = page({ getItem: denied, setItem: denied });
  current.button.click();
  assert.equal(current.filters.hidden, true);
  current.button.click();
  assert.equal(current.filters.hidden, false);
});

test('lists without filters keep the button hidden', () => {
  const current = page({}, true);
  assert.equal(current.button.hidden, true);
});
