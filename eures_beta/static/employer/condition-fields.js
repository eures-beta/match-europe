// Guided inputs over the existing clarification contract; imported text is preserved explicitly.
(() => {
  const form = document.getElementById('review-form');
  const t = Object.fromEntries(
    [...document.querySelectorAll('#condition-labels [data-key]')].map((el) => [
      el.dataset.key,
      el.textContent,
    ]),
  );
  const widgets = [];
  function make(name, title, modes, specs) {
    const original = document.getElementById('clarify-' + name);
    const item = original.closest('.clarification-item');
    const box = document.createElement('fieldset');
    box.className = 'guided-condition';
    const legend = document.createElement('legend');
    legend.textContent = t[title];
    box.append(legend);
    const source = document.createElement('p');
    source.className = 'mini-note';
    box.append(source);
    const controls = {};
    function control(key, label, type, options) {
      const row = document.createElement('div');
      row.className = 'review-field';
      const lab = document.createElement('label');
      lab.htmlFor = 'condition-' + name + '-' + key;
      lab.textContent = t[label];
      const input = document.createElement(options ? 'select' : 'input');
      input.id = lab.htmlFor;
      if (options)
        for (const value of options) {
          const opt = document.createElement('option');
          opt.value = value;
          opt.textContent = t[value] || value;
          input.append(opt);
        }
      else {
        input.type = type;
        if (type === 'number') {
          input.min = '0.01';
          input.step = '0.01';
          if (name === 'hours') input.max = '168';
        }
      }
      if (key === 'mode') lab.className = 'visually-hidden';
      if (key === 'notes') input.maxLength = 500;
      row.append(lab, input);
      box.append(row);
      controls[key] = input;
      return input;
    }
    const mode = control('mode', title, '', ['unknown', ...modes]);
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = '—';
    mode.prepend(placeholder);
    mode.required = true;
    for (const [key, label, type, options] of specs) control(key, label, type, options);
    item.append(box);
    if (name === 'hours')
      form
        .querySelector('.requirements-fields fieldset')
        .append(controls.notes.closest('.review-field'));
    let kept = '',
      last = null;
    function visibility() {
      const enabled = modes.includes(mode.value);
      for (const [key, input] of Object.entries(controls))
        if (key !== 'mode') {
          const visible =
            key === 'notes' ||
            (enabled &&
              !(name === 'startDate' && mode.value === 'asap') &&
              (key !== 'maximum' || mode.value === 'range' || mode.value === 'variable'));
          input.closest('.review-field').hidden = !visible;
          input.disabled = !visible;
          input.required = visible && !['notes'].includes(key);
        }
      if (controls.amount)
        controls.amount.labels[0].textContent = t[mode.value === 'range' ? 'minimum' : 'amount'];
      const min = controls.amount || controls.minimum;
      if (controls.maximum)
        controls.maximum.setCustomValidity(
          controls.maximum.disabled ||
            !min?.value ||
            !controls.maximum.value ||
            Number(controls.maximum.value) >= Number(min.value)
            ? ''
            : t.maximum + ' ≥ ' + t.minimum,
        );
    }
    function write() {
      visibility();
      const c = (key) => controls[key]?.value || '';
      let value = kept + (name === 'hours' && c('notes') ? ' · ' + c('notes') : '');
      if (mode.value !== 'keep') {
        if (mode.value === 'unknown') value = name === 'hours' ? c('notes') : '';
        else if (name === 'salary')
          value = [
            c('amount') + (mode.value === 'range' ? '–' + c('maximum') : ''),
            c('currency'),
            t[c('basis')],
            t[c('period')],
          ].join(' · ');
        else if (name === 'hours')
          value = [
            t[mode.value],
            c('minimum') + (mode.value === 'variable' ? '–' + c('maximum') : ''),
            t.hours,
            c('notes'),
          ]
            .filter(Boolean)
            .join(' · ');
        else value = mode.value === 'asap' ? t.asap : t[mode.value] + ' · ' + c('calendar');
      }
      original.value = value;
      last = value;
      original.dispatchEvent(new Event('input', { bubbles: true }));
    }
    if (controls.notes) controls.notes.addEventListener('input', write);
    box.addEventListener('input', write);
    box.addEventListener('change', write);
    function load() {
      if (original.value === last) return;
      kept = original.value;
      last = kept;
      for (const [key, input] of Object.entries(controls))
        if (key !== 'mode') input.value = input.tagName === 'SELECT' ? input.options[0].value : '';
      const old = mode.querySelector('[value=keep]');
      old?.remove();
      if (kept) {
        const opt = document.createElement('option');
        opt.value = 'keep';
        opt.textContent = t.keep;
        mode.prepend(opt);
      }
      mode.value = kept ? 'keep' : '';
      source.textContent = kept ? t.source + ' : ' + kept : '';
      source.hidden = !kept;
      const parts = kept.split(' · ');
      const number = /^\d+(?:[.,]\d+)?$/;
      if (name === 'salary' && parts.length === 4 && ['EUR', 'CHF', 'GBP'].includes(parts[1])) {
        const amounts = parts[0].split('–');
        const basis = ['unknown', 'gross', 'net'].find((key) => t[key] === parts[2]);
        const period = ['unknown', 'hour', 'month', 'year'].find((key) => t[key] === parts[3]);
        if (amounts.every((value) => number.test(value)) && basis && period) {
          mode.value = amounts.length === 2 ? 'range' : 'fixed';
          controls.amount.value = amounts[0];
          controls.maximum.value = amounts[1] || '';
          controls.currency.value = parts[1];
          controls.basis.value = basis;
          controls.period.value = period;
        }
      } else if (name === 'hours' && parts[2] === t.hours) {
        const amounts = parts[1].split('–');
        const kind = ['exact', 'variable'].find((key) => t[key] === parts[0]);
        if (kind && amounts.every((value) => number.test(value))) {
          mode.value = kind;
          controls.minimum.value = amounts[0];
          controls.maximum.value = amounts[1] || '';
          controls.notes.value = parts.slice(3).join(' · ');
        }
      } else if (name === 'startDate') {
        if (kept === t.asap) mode.value = 'asap';
        else {
          const kind = ['date', 'flexible'].find((key) => t[key] === parts[0]);
          if (kind && /^\d{4}-\d{2}-\d{2}$/.test(parts[1] || '')) {
            mode.value = kind;
            controls.calendar.value = parts[1];
          }
        }
      }
      visibility();
    }
    widgets.push(load);
    load();
  }
  make(
    'salary',
    'pay',
    ['fixed', 'range'],
    [
      ['amount', 'amount', 'number'],
      ['maximum', 'maximum', 'number'],
      ['currency', 'currency', '', ['EUR', 'CHF', 'GBP']],
      ['basis', 'basis', '', ['unknown', 'gross', 'net']],
      ['period', 'period', '', ['unknown', 'hour', 'month', 'year']],
    ],
  );
  make(
    'hours',
    'duration',
    ['exact', 'variable'],
    [
      ['minimum', 'hours', 'number'],
      ['maximum', 'maximum', 'number'],
      ['notes', 'notes', 'text'],
    ],
  );
  make('startDate', 'start', ['asap', 'date', 'flexible'], [['calendar', 'calendar', 'date']]);
  // Immediate start needs no calendar date.
  const start = document.getElementById('condition-startDate-mode');
  function calendar() {
    const input = document.getElementById('condition-startDate-calendar');
    const hide = ['unknown', 'keep', 'asap'].includes(start.value);
    input.closest('.review-field').hidden = hide;
    input.disabled = hide;
    input.required = !hide;
  }
  start.addEventListener('change', calendar);
  document.addEventListener('me-step-change', (event) => {
    if (event.detail === 'review-step') {
      widgets.forEach((load) => load());
      calendar();
    }
  });
  calendar();
})();
