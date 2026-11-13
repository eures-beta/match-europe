const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

// Small DOM fixture: run the production script and observe its interactions.
class Element {
  constructor(dataset = {}) {
    this.dataset = dataset;
    this.children = [];
    this.events = {};
    this.hidden = false;
    this.disabled = false;
    this.checked = false;
    this.value = '';
    this.textContent = '';
    this.attributes = {};
    this.selectors = {};
    this.open = false;
  }
  querySelectorAll(selector) {
    if (selector === 'button') return this.children.filter((child) => child.type === 'button');
    return this.selectors[selector] || [];
  }
  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
  addEventListener(name, handler) {
    (this.events[name] ||= []).push(handler);
  }
  fire(name) {
    (this.events[name] || []).forEach((handler) => handler({ target: this }));
  }
  setAttribute(name, value) {
    this.attributes[name] = value;
  }
  hasAttribute(name) {
    return name === 'data-skill-sector' && this.dataset.skillSector !== undefined;
  }
  append(child) {
    this.children.push(child);
  }
  replaceChildren() {
    this.children = [];
  }
  focus() {
    this.focused = true;
  }
}

function fixture() {
  const sections = [10, 5, 3].map((maximum, sectionIndex) => {
    const section = new Element({ maximum: String(maximum), remove: 'Retirer : {label}' });
    const tags = new Element();
    const count = new Element();
    const search = new Element();
    const results = new Element({ template: '{count} choix' });
    const category = new Element({ skillSector: '' });
    const choices = Array.from({ length: maximum + 1 }, (_, index) => {
      const choice = new Element({
        search: index === 0 ? 'préparer des repas cuisine' : `autre activité ${index}`,
      });
      const input = new Element();
      const span = new Element();
      span.textContent =
        sectionIndex === 0 && index === 0 ? 'préparer des repas' : `Choix ${index}`;
      input.closest = () => choice;
      choice.selectors.span = [span];
      choice.input = input;
      return choice;
    });
    category.selectors['[data-skill-choice]'] = choices;
    section.selectors = {
      'input[type="checkbox"]': choices.map((choice) => choice.input),
      '[data-skill-tags]': [tags],
      '[data-skill-count]': [count],
      '[data-skill-search]': [search],
      '[data-skill-results]': [results],
      '[data-skill-search-wrapper]': [new Element()],
      '[data-skill-category]': [category],
      '[data-skill-sector]': [category],
    };
    return Object.assign(section, { tags, count, search, results, category, choices });
  });
  const mode = new Element();
  mode.value = 'open';
  mode.checked = true;
  const occupationMode = new Element();
  occupationMode.value = 'occupation';
  const occupationInput = new Element();
  const occupation = new Element();
  occupation.selectors['input,button'] = [occupationInput];
  const openProject = new Element();
  openProject.selectors['[data-skill-section]'] = sections;
  openProject.selectors['input,button'] = sections.flatMap((section) =>
    section.choices.map((choice) => choice.input),
  );
  const document = new Element();
  document.selectors = {
    'input[name="project_mode"]': [mode, occupationMode],
    '[data-open-project]': [openProject],
    '[data-occupation-only]': [occupation],
  };
  document.createElement = () => new Element();
  const source = fs.readFileSync(
    path.join(__dirname, '../../eures_beta/candidates/static/candidate/skill-selection.js'),
    'utf8',
  );
  vm.runInNewContext(source, { document });
  return { sections, mode, occupationMode, occupation, occupationInput, openProject };
}

test('independent accent-insensitive synonym search retains selected tags and inputs', () => {
  const { sections } = fixture();
  const [first, second] = sections;
  first.choices[0].input.checked = true;
  first.fire('change');
  first.search.value = 'PREPARER';
  first.search.fire('input');
  assert.equal(first.choices[0].hidden, false);
  assert.equal(first.choices[1].hidden, true);
  first.search.value = 'cuisine';
  first.search.fire('input');
  assert.equal(first.choices[0].hidden, false);
  first.search.value = 'absent';
  first.search.fire('input');
  assert.equal(first.category.hidden, true);
  assert.equal(first.results.textContent, '0 choix');
  assert.equal(first.tags.children.length, 1);
  assert.equal(first.choices[0].input.checked, true);
  assert.equal(second.choices[0].hidden, false);
});

test('sector search opens matches, restores collapsed sectors and keeps explicit choices', () => {
  const { sections } = fixture();
  const section = sections[0];
  assert.equal(section.category.open, false);
  section.choices[0].input.checked = true;
  section.fire('change');
  section.search.value = 'cuisine';
  section.search.fire('input');
  assert.equal(section.category.open, true);
  section.search.value = '';
  section.search.fire('input');
  assert.equal(section.category.open, false);
  assert.equal(section.results.hidden, true);
  assert.equal(section.choices[0].input.checked, true);
  assert.equal(section.tags.children.length, 1);
  section.category.open = true;
  section.search.value = 'absent';
  section.search.fire('input');
  section.search.value = '';
  section.search.fire('input');
  assert.equal(section.category.open, true);
});

test('each ceiling is enforced and removing a hidden choice restores capacity and focus', () => {
  const { sections } = fixture();
  for (const section of sections) {
    const maximum = Number(section.dataset.maximum);
    section.choices.slice(0, maximum).forEach((choice) => {
      choice.input.checked = true;
    });
    section.fire('change');
    assert.equal(section.count.textContent, `${maximum} / ${maximum}`);
    assert.equal(section.choices[maximum].input.disabled, true);
    assert.equal(section.choices[0].input.disabled, false);
    assert.ok(section.tags.children[0].attributes['aria-label'].startsWith('Retirer : '));
    section.search.value = 'absent';
    section.search.fire('input');
    section.tags.children[0].fire('click');
    assert.equal(section.choices[0].input.checked, false);
    assert.equal(section.choices[maximum].input.disabled, false);
    assert.equal(section.tags.children[0].focused, true);
  }
});

test('switching project mode retains choices but disables irrelevant controls', () => {
  const { sections, mode, occupationMode, occupation, occupationInput, openProject } = fixture();
  sections[0].choices[0].input.checked = true;
  mode.checked = false;
  occupationMode.checked = true;
  occupationMode.fire('change');
  assert.equal(openProject.hidden, true);
  assert.equal(sections[0].choices[0].input.disabled, true);
  assert.equal(occupation.hidden, false);
  assert.equal(occupationInput.disabled, false);
  mode.checked = true;
  occupationMode.checked = false;
  mode.fire('change');
  assert.equal(openProject.hidden, false);
  assert.equal(sections[0].choices[0].input.checked, true);
  assert.equal(sections[0].choices[0].input.disabled, false);
  assert.equal(occupationInput.disabled, true);
});
