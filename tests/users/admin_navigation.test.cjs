const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.resolve(__dirname, '../../eures_beta/static/admin/nav-sidebar-default.js'),
  'utf8',
);
const key = 'django.admin.navSidebarIsOpen';

test('navigation is closed by default, without changing the filter preference', () => {
  const data = new Map([['matchEurope.admin.filtersCollapsed', 'false']]);
  vm.runInNewContext(source, {
    localStorage: {
      getItem: (name) => data.get(name) ?? null,
      setItem: (name, value) => data.set(name, value),
    },
  });
  assert.equal(data.get(key), 'false');
  assert.equal(data.get('matchEurope.admin.filtersCollapsed'), 'false');
});

test('an explicit open or closed navigation choice is preserved', () => {
  for (const value of ['true', 'false']) {
    const data = new Map([[key, value]]);
    vm.runInNewContext(source, {
      localStorage: {
        getItem: (name) => data.get(name),
        setItem: () => assert.fail('Existing preference must not be overwritten'),
      },
    });
    assert.equal(data.get(key), value);
  }
});

test('unavailable storage does not throw', () => {
  assert.doesNotThrow(() =>
    vm.runInNewContext(source, {
      localStorage: {
        getItem: () => {
          throw new Error('Storage unavailable');
        },
      },
    }),
  );
});
