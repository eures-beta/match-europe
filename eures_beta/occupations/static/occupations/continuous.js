// One reference component, independent declarations for each business form.
(() => {
  const root = document.querySelector('[data-occupation-skills]');
  if (!root) return;
  const role = root.dataset.role;
  const field = document.getElementById('id_occupation_skills');
  const jobs = root.querySelector('[data-occupation-skill-jobs]');
  const form = root.closest('form');
  const records = new Map();
  let state = {};
  try {
    state = JSON.parse(field.value || '{}') || {};
    if (typeof state !== 'object' || Array.isArray(state)) state = {};
  } catch {
    state = {};
  }
  function selected() {
    if (role === 'employer')
      return (
        window.meOccupation?.collect().uris ||
        (root.dataset.occupations || '').split(' ').filter(Boolean)
      );
    return [...form.querySelectorAll('input[name="occupation_references"]:checked')]
      .map((input) => input.value)
      .filter((value) => value.startsWith('esco:'))
      .map((value) => value.slice(5));
  }
  function store() {
    field.value = JSON.stringify(state);
  }
  function element(tag, text, parent) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (parent) parent.append(node);
    return node;
  }
  function render(uri, record) {
    const data = record.data;
    record.box.replaceChildren();
    element('h3', data.label, record.box);
    if (data.simulated) element('p', root.dataset.simulation, record.box);
    state[uri] ||= { skills: [], behaviours: [] };
    for (const [name, maximum] of [
      ['skills', 5],
      ['behaviours', 3],
    ]) {
      const options = data[name];
      if (!options.length) continue;
      const group = element('fieldset', '', record.box);
      const legend = element('legend', root.dataset[name] + ' ', group);
      const count = element('span', '', legend);
      count.setAttribute('role', 'status');
      const inputs = [];
      for (const [key, label] of options) {
        const row = element('label', '', group);
        row.className = 'pilot-choice';
        const input = element('input', '', row);
        input.type = 'checkbox';
        input.value = key;
        input.checked = (state[uri][name] || []).includes(key);
        element('span', label, row);
        inputs.push(input);
      }
      function update() {
        state[uri][name] = inputs.filter((input) => input.checked).map((input) => input.value);
        count.textContent = state[uri][name].length + ' / ' + maximum;
        inputs.forEach((input) => {
          input.disabled = !input.checked && state[uri][name].length >= maximum;
        });
        store();
      }
      group.addEventListener('change', update);
      update();
    }
    store();
  }
  async function prepare(uri, record) {
    record.box.replaceChildren();
    const status = element('p', root.dataset.wait, record.box);
    status.setAttribute('role', 'status');
    const csrf =
      document.cookie
        .split('; ')
        .find((value) => value.startsWith('csrftoken='))
        ?.split('=')[1] || '';
    const controller = new AbortController();
    record.controller = controller;
    const deadline = setTimeout(() => controller.abort(), 45000);
    try {
      const response = await fetch('/api/occupation-skills/', {
        method: 'POST',
        credentials: 'same-origin',
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({
          role,
          occupation: uri,
          language: document.documentElement.lang,
          token: form.querySelector('input[name="token"]')?.value || '',
        }),
      });
      if (!response.ok) throw new Error('unavailable');
      const data = await response.json();
      if (records.get(uri) !== record) return;
      record.data = data;
      render(uri, record);
    } catch {
      if (records.get(uri) !== record) return;
      status.textContent = root.dataset.error;
      status.setAttribute('role', 'alert');
      const retry = element('button', root.dataset.retry, record.box);
      retry.type = 'button';
      retry.addEventListener('click', () => prepare(uri, record));
    } finally {
      clearTimeout(deadline);
    }
  }
  function update() {
    const uris = selected();
    for (const [uri, record] of records) {
      if (!uris.includes(uri)) {
        record.controller?.abort();
        record.box.remove();
        records.delete(uri);
        delete state[uri];
      }
    }
    for (const uri of Object.keys(state)) if (!uris.includes(uri)) delete state[uri];
    for (const uri of uris) {
      if (records.has(uri)) continue;
      const record = { box: element('section', '', jobs) };
      records.set(uri, record);
      prepare(uri, record);
    }
    store();
  }
  if (role === 'employer') {
    window.meOccupationSkills = {
      update,
      collect() {
        return JSON.parse(field.value || '{}');
      },
      load(value) {
        state = value || {};
        update();
        records.forEach((record, uri) => {
          if (record.data) render(uri, record);
        });
      },
      summary() {
        return [...records]
          .filter(([, record]) => record.data)
          .map(([uri, record]) => {
            const labels = ['skills', 'behaviours'].flatMap((name) =>
              record.data[name]
                .filter(([key]) => state[uri]?.[name]?.includes(key))
                .map(([, label]) => label),
            );
            return labels.length ? record.data.label + ' : ' + labels.join(', ') : '';
          })
          .filter(Boolean)
          .join('\n');
      },
      summaryLabel: root.dataset.heading,
    };
    update();
  } else {
    form.addEventListener('change', (event) => {
      if (event.target.name === 'occupation_references') update();
    });
    update();
  }
})();
