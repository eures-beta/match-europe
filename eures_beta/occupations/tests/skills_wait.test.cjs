const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('announce before submitting once, and restore the form after history navigation', () => {
  const handlers = {};
  const button = { disabled: false };
  const status = {
    hidden: true,
    focus() {
      this.focused = true;
    },
  };
  const form = {
    dataset: {},
    querySelector(selector) {
      return selector.includes('button') ? button : status;
    },
    addEventListener(name, fn) {
      handlers[name] = fn;
    },
  };
  let pageshow;
  let submitted = 0;
  const frames = [];
  const context = {
    document: {
      querySelectorAll(selector) {
        return selector === '[data-resolve-skills]' ? [form] : [];
      },
    },
    window: {
      addEventListener(name, fn) {
        pageshow = fn;
      },
    },
    requestAnimationFrame(fn) {
      frames.push(fn);
    },
    HTMLFormElement: {
      prototype: {
        submit() {
          assert.equal(this, form);
          submitted += 1;
        },
      },
    },
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, '../static/occupations/skills-pilot.js'), 'utf8'),
    context,
  );
  const event = { preventDefault() {} };
  handlers.submit(event);
  assert.equal(status.hidden, false);
  assert.equal(status.focused, true);
  assert.equal(button.disabled, true);
  assert.equal(submitted, 0);
  handlers.submit(event);
  assert.equal(frames.length, 1);
  frames.shift()();
  frames.shift()();
  assert.equal(submitted, 1);
  pageshow();
  assert.equal(button.disabled, false);
  assert.equal(status.hidden, true);
  handlers.submit(event);
  assert.equal(frames.length, 1);
});
