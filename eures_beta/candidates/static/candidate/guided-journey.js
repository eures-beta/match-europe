// Guided candidate choices; local catalogue API shared with the employer journey.
(() => {
  const query = document.getElementById('id_occupation_query');
  const multipleExclusive = {
    desired_countries: ['discuss'],
    transport_modes: ['discuss'],
    licences_held: ['none', 'discuss'],
    contract_types: ['discuss'],
    working_time: ['discuss'],
    working_conditions: ['none', 'discuss'],
  };
  for (const [name, exclusive] of Object.entries(multipleExclusive)) {
    document.querySelectorAll(`input[name="${name}"]`).forEach((input) => {
      input.addEventListener('change', () => {
        if (!input.checked) return;
        document.querySelectorAll(`input[name="${name}"]`).forEach((other) => {
          if (
            other !== input &&
            (exclusive.includes(input.value) || exclusive.includes(other.value))
          )
            other.checked = false;
        });
      });
    });
  }
  const visibility = {
    commute_time: ['mobility', ['commute', 'both']],
    transport_modes: ['mobility', ['commute', 'both']],
    transport_details: ['transport_modes', 'other'],
    available_from: ['availability', 'date'],
    contract_details: ['contract_types', 'other'],
    licence_details: ['licences_held', 'other'],
    salary_amount: ['salary_preference', 'minimum'],
    salary_currency: ['salary_preference', 'minimum'],
    salary_period: ['salary_preference', 'minimum'],
    salary_basis: ['salary_preference', 'minimum'],
  };
  const update = () => {
    const schedule = document.getElementById('candidate-weekly-schedule');
    if (schedule) {
      const specific = !!document.querySelector(
        'input[name="schedule_preference"][value="specific"]:checked',
      );
      schedule.hidden = !specific;
      schedule.querySelectorAll('input').forEach((input) => {
        input.disabled = !specific;
      });
    }
    for (const [name, [parent, value]] of Object.entries(visibility)) {
      const wrapper = document.querySelector(`[data-field="${name}"]`);
      if (!wrapper) continue;
      const active = (Array.isArray(value) ? value : [value]).some((item) =>
        document.querySelector(`input[name="${parent}"][value="${item}"]:checked`),
      );
      wrapper.hidden = !active;
      wrapper.querySelectorAll('input,select,textarea').forEach((input) => {
        input.disabled = !active;
      });
    }
  };
  document.addEventListener('change', update);
  update();
  const suggestionNotice = document.getElementById('schedule-suggestion-notice');
  if (suggestionNotice) {
    const derived = ['day', 'night', 'weekend'];
    const overridesInput = document.getElementById('id_condition_overrides');
    const automaticInput = document.getElementById('id_auto_conditions');
    const readSet = (input) => {
      try {
        const value = JSON.parse(input.value || '[]');
        return new Set(Array.isArray(value) ? value : []);
      } catch {
        return new Set();
      }
    };
    const overrides = readSet(overridesInput);
    const automatic = readSet(automaticInput);
    const condition = (value) =>
      document.querySelector(`input[name="working_conditions"][value="${value}"]`);
    const values = (name) =>
      Array.from(
        document.querySelectorAll(`input[name="${name}"]:checked`),
        (input) => input.value,
      );
    const label = (value) => condition(value)?.closest('label').textContent.trim() || value;
    const refresh = () => {
      const specific = values('schedule_preference').includes('specific');
      const slots = [
        'monday',
        'tuesday',
        'wednesday',
        'thursday',
        'friday',
        'saturday',
        'sunday',
      ].map((day) => values('schedule_' + day));
      const suggested = new Set();
      if (specific) {
        if (slots.some((row) => row.some((slot) => ['morning', 'afternoon'].includes(slot))))
          suggested.add('day');
        if (slots.some((row) => row.some((slot) => ['evening', 'night'].includes(slot))))
          suggested.add('night');
        if (slots[5].length || slots[6].length) suggested.add('weekend');
      }
      const exclusive = condition('none')?.checked || condition('discuss')?.checked;
      for (const value of derived) {
        if (overrides.has(value)) continue;
        if (automatic.has(value) && !suggested.has(value)) {
          condition(value).checked = false;
          automatic.delete(value);
        }
        if (suggested.has(value) && !exclusive && !condition(value).checked) {
          condition(value).checked = true;
          automatic.add(value);
        }
      }
      overridesInput.value = JSON.stringify([...overrides]);
      automaticInput.value = JSON.stringify([...automatic]);
      const strict = specific && document.getElementById('id_schedule_strict')?.checked;
      const conflicts = strict
        ? derived.filter((value) => condition(value).checked && !suggested.has(value))
        : [];
      const messages = [];
      if (suggested.size)
        messages.push(
          suggestionNotice.dataset.suggestion.replace(
            '%(choices)s',
            [...suggested].map(label).join(', '),
          ),
        );
      if (conflicts.length)
        messages.push(
          suggestionNotice.dataset.conflict.replace('%(choices)s', conflicts.map(label).join(', ')),
        );
      suggestionNotice.textContent = messages.join(' ');
    };
    document.addEventListener('change', (event) => {
      const input = event.target;
      if (input.name === 'working_conditions') {
        if (derived.includes(input.value)) {
          overrides.add(input.value);
          automatic.delete(input.value);
        }
        if (['none', 'discuss'].includes(input.value)) {
          derived.forEach((value) => overrides.add(value));
          automatic.clear();
        }
      }
      if (input.name === 'working_conditions' || input.name?.startsWith('schedule_')) refresh();
    });
    refresh();
  }
  if (!query) return;
  const form = query.form;
  const results = document.getElementById('candidate-occupation-results');
  const status = document.getElementById('candidate-search-status');
  const search = document.getElementById('candidate-search-button');
  const t = JSON.parse(document.getElementById('occupation-strings').textContent);
  let rows = JSON.parse(document.getElementById('candidate-reference-rows').textContent);
  let timer,
    controller,
    serial = 0;
  const selected = () =>
    new Set(
      Array.from(
        form.querySelectorAll('input[name="occupation_references"]:checked'),
        (input) => input.value,
      ),
    );
  const node = (tag, text, parent) => {
    const element = document.createElement(tag);
    if (text) element.textContent = text;
    parent.append(element);
    return element;
  };
  function render(checked) {
    results.replaceChildren();
    for (const [prefix, heading] of [
      ['esco:', t.escoHeading],
      ['rome:', t.romeHeading],
    ]) {
      node('h2', heading, results);
      const group = rows.filter((row) => row.value.startsWith(prefix));
      if (!group.length) node('p', prefix === 'esco:' ? t.noEsco : t.noRomeResult, results);
      for (const row of group) {
        const card = node('article', '', results);
        card.className = 'occupation-result';
        if (prefix === 'rome:') card.lang = 'fr';
        const label = node('label', '', card);
        const checkbox = node('input', '', label);
        checkbox.type = 'checkbox';
        checkbox.name = 'occupation_references';
        checkbox.value = row.value;
        checkbox.checked = checked.has(row.value);
        node('strong', row.label, label);
        if (row.description) node('p', row.description, card);
      }
    }
  }
  async function find() {
    clearTimeout(timer);
    controller?.abort();
    const current = ++serial;
    const value = query.value.trim();
    if (value.length < 2) {
      status.textContent = t.startTyping;
      return;
    }
    status.textContent = t.busy;
    controller = new AbortController();
    try {
      const response = await fetch('/api/occupations/', {
        method: 'POST',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': form.querySelector('[name="csrfmiddlewaretoken"]').value,
        },
        body: JSON.stringify({ q: value, lang: document.documentElement.lang, independent: true }),
      });
      if (!response.ok) throw new Error('search_failed');
      const data = await response.json();
      if (current !== serial) return;
      const checked = selected();
      const fresh = [
        ...data.results.map((row) => ({
          value: 'esco:' + row.uri,
          label: 'ESCO — ' + row.label,
          description: row.description,
        })),
        ...data.rome_results.map((row) => ({
          value: 'rome:' + row.code,
          label: 'ROME ' + row.code + ' — ' + row.label,
          description: '',
        })),
      ];
      rows = Array.from(
        new Map(
          [...rows.filter((row) => checked.has(row.value)), ...fresh].map((row) => [
            row.value,
            row,
          ]),
        ).values(),
      );
      render(checked);
      status.textContent = t.resultsFound.replace('{count}', String(fresh.length));
    } catch (error) {
      if (error.name !== 'AbortError' && current === serial) status.textContent = t.error;
    }
  }
  search.addEventListener('click', (event) => {
    event.preventDefault();
    find();
  });
  query.addEventListener('input', () => {
    clearTimeout(timer);
    controller?.abort();
    serial++;
    timer = setTimeout(find, 350);
  });
  query.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      find();
    }
  });
  form.addEventListener('submit', () => {
    clearTimeout(timer);
    controller?.abort();
    serial++;
  });
  if (rows.length) render(selected());
  else status.textContent = t.startTyping;
})();

// Error summary focus and draft expiry warning (WCAG 3.3.1, 2.2.1).
(() => {
  const summary = document.getElementById('journey-error-summary');
  if (summary) {
    summary.focus();
    summary.querySelectorAll('a[href^="#"]').forEach((link) => {
      link.addEventListener('click', (event) => {
        const target = document.getElementById(link.getAttribute('href').slice(1));
        if (!target) return;
        event.preventDefault();
        target.scrollIntoView({ block: 'center' });
        target.focus();
      });
    });
  }
  const timeout = document.getElementById('journey-timeout');
  const extend = document.getElementById('journey-timeout-extend');
  const status = document.getElementById('journey-timeout-status');
  if (!timeout || !extend) return;
  const seconds = Number(timeout.dataset.seconds);
  const warning = Number(timeout.dataset.warningSeconds);
  if (!seconds || !warning || warning >= seconds) return;
  let timer;
  const schedule = () => {
    clearTimeout(timer);
    timer = setTimeout(
      () => {
        timeout.hidden = false;
        extend.focus();
      },
      (seconds - warning) * 1000,
    );
  };
  extend.addEventListener('click', async () => {
    extend.disabled = true;
    try {
      const response = await fetch(window.location.href, { credentials: 'same-origin' });
      if (!response.ok) throw new Error(String(response.status));
      timeout.hidden = true;
      status.textContent = extend.dataset.done || '';
      schedule();
    } catch {
      status.textContent = extend.dataset.failed || '';
    } finally {
      extend.disabled = false;
    }
  });
  schedule();
})();
