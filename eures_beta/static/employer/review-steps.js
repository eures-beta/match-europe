// Local progressive review. Move existing controls without duplicating their values.
(() => {
  const form = document.getElementById('review-form');
  if (!form) return;
  const t = Object.fromEntries(
    [...document.querySelectorAll('#review-step-labels [data-key]')].map((el) => [
      el.dataset.key,
      el.textContent,
    ]),
  );
  const titles = ['post', 'conditions', 'profile', 'mobility', 'summary'].map((key) => t[key]);
  const nav = document.createElement('ol');
  nav.className = 'review-progress';
  nav.setAttribute('aria-label', t.progress);
  const shortTitles = [t.post, t.conditionsShort, t.profileShort, t.mobilityShort, t.summaryShort];
  const position = document.createElement('p');
  position.className = 'review-position';
  const meter = document.createElement('div');
  meter.className = 'review-meter';
  meter.setAttribute('aria-hidden', 'true');
  const fill = document.createElement('span');
  meter.append(fill);
  const panels = titles.map((title, i) => {
    const panel = document.createElement('section');
    panel.className = 'review-panel';
    panel.dataset.reviewPanel = i;
    const heading = document.createElement('h2');
    heading.textContent = title;
    heading.tabIndex = -1;
    panel.append(heading);
    form.prepend(panel);
    const item = document.createElement('li');
    const number = document.createElement('span');
    number.className = 'review-step-number';
    number.textContent = i + 1;
    const label = document.createElement('span');
    label.textContent = shortTitles[i];
    item.append(number, label);
    nav.append(item);
    return panel;
  });
  // Restore natural document order after creating the sections.
  form.prepend(position, nav, meter, ...panels);
  const move = (node, i) => {
    if (node) panels[i].append(node);
  };
  const field = (id, i) => move(document.getElementById(id)?.closest('.review-field'), i);
  const oldHeadings = [...form.children].filter((el) => ['H2', 'H3'].includes(el.tagName));
  oldHeadings.forEach((el) => (el.hidden = true));
  ['title', 'companyName', 'city', 'description'].forEach((name) => field('review-' + name, 0));
  document
    .getElementById('review-title')
    .closest('.review-field')
    .after(form.querySelector('.occupation-picker'));
  field('review-contractType', 1);
  field('review-desiredProfile', 2);
  // Existing clarification wrappers remain available for the import loader.
  const missing = document.getElementById('clarifications-missing');
  missing.hidden = true;
  document.getElementById('clarifications-known').hidden = true;
  const intro = missing.previousElementSibling?.previousElementSibling;
  if (intro?.tagName === 'P') intro.hidden = true;
  const requirements = form.querySelector('.requirements-fields');
  const work = requirements.querySelector('fieldset');
  move(work, 1);
  move(requirements, 2);
  const mobilityHeading = oldHeadings.find((el) => el.tagName === 'H3');
  let mobile = mobilityHeading?.nextElementSibling;
  if (mobile?.classList.contains('mobility-fields')) move(mobile, 3);
  move(form.querySelector('.arrival-aids'), 3);
  move(document.getElementById('aid-other-field'), 3);
  move(document.getElementById('clarify-commute')?.closest('.clarification-item'), 3);
  const summary = document.createElement('div');
  summary.className = 'review-summary';
  panels[4].append(summary);
  move(form.querySelector('.review-privacy-compact'), 4);
  move(form.querySelector('.review-confirm'), 4);
  const actions = form.querySelector('.landing-actions');
  const submit = actions.querySelector('[type=submit]');
  panels[4].append(submit);
  const previous = document.createElement('button');
  previous.type = 'button';
  previous.className = 'ghost-action';
  previous.textContent = t.previous;
  const next = document.createElement('button');
  next.type = 'button';
  next.className = 'primary-action';
  next.textContent = t.next;
  actions.prepend(previous, next);
  let active = 0;
  function arrange() {
    for (const item of form.querySelectorAll('.clarification-item')) {
      const name = item.dataset.clarification;
      move(item, ['frenchLevel', 'experience'].includes(name) ? 2 : name === 'commute' ? 3 : 1);
    }
    document.getElementById('clarifications-known').hidden = true;
    missing.hidden = true;
  }
  function renderSummary() {
    summary.replaceChildren();
    panels.slice(0, 4).forEach((panel, i) => {
      const section = document.createElement('section');
      const heading = document.createElement('h3');
      heading.textContent = titles[i];
      const edit = document.createElement('button');
      edit.type = 'button';
      edit.className = 'ghost-action';
      edit.textContent = t.edit + ' — ' + titles[i];
      edit.onclick = () => show(i);
      section.append(heading, edit);
      for (const input of panel.querySelectorAll('input,textarea,select')) {
        if (
          input.closest('.guided-condition') ||
          input.closest('[hidden]') !== panel ||
          input.disabled ||
          ['occupation-query'].includes(input.id) ||
          (['radio', 'checkbox'].includes(input.type) && !input.checked)
        )
          continue;
        let value =
          input.tagName === 'SELECT' ? input.selectedOptions[0]?.textContent : input.value.trim();
        let label =
          input.labels?.[0]?.textContent.trim() || input.closest('label')?.textContent.trim();
        if (['radio', 'checkbox'].includes(input.type)) {
          label = input.closest('fieldset')?.querySelector('legend')?.textContent || titles[i];
          value = input.closest('label')?.textContent.trim();
        }
        if (!label) continue;
        const row = document.createElement('p');
        const strong = document.createElement('strong');
        strong.textContent = label + ' : ';
        row.append(strong, document.createTextNode(value || t.empty));
        section.append(row);
      }
      summary.append(section);
    });
  }
  function show(index, focus = true) {
    active = index;
    panels.forEach((panel, i) => (panel.hidden = i !== active));
    [...nav.children].forEach((item, i) => {
      if (i === active) item.setAttribute('aria-current', 'step');
      else item.removeAttribute('aria-current');
    });
    [...nav.children].forEach((item, i) => item.classList.toggle('is-complete', i < active));
    position.textContent = `${active + 1} / ${titles.length} · ${titles[active]}`;
    fill.style.width = `${((active + 1) / titles.length) * 100}%`;
    previous.hidden = active === 0;
    next.hidden = active === 4;
    document.getElementById('review-draft').hidden = active !== 4;
    document.getElementById('review-back').hidden = active !== 0;
    const contact = document.getElementById('contact-editor');
    if (contact) contact.hidden = active !== 4;
    if (active === 4) renderSummary();
    if (focus) panels[active].querySelector('h2').focus();
  }
  previous.onclick = () => show(active - 1);
  function requireAnswers() {
    ['review-desiredProfile', 'clarify-experience', 'clarify-commute'].forEach((id) => {
      document.getElementById(id).required = true;
    });
    for (const name of ['permitRequired', 'crossBorder', 'relocation']) {
      const first = form.querySelector('[name=' + name + ']');
      if (first) first.required = true;
    }
    for (const name of ['workConditions', 'arrivalAids', 'permits']) {
      const first = form.querySelector('[name=' + name + ']');
      const needed =
        name !== 'permits' || form.querySelector('[name=permitRequired]:checked')?.value === 'yes';
      first.setCustomValidity(
        !needed || form.querySelector('[name=' + name + ']:checked') ? '' : t.answerRequired,
      );
    }
  }
  next.onclick = () => {
    requireAnswers();
    const invalid = [...panels[active].querySelectorAll('input,textarea,select')].find(
      (input) => !input.disabled && !input.checkValidity(),
    );
    if (invalid) {
      invalid.closest('details')?.setAttribute('open', '');
      invalid.reportValidity();
      return;
    }
    if (active === 0 && window.meOccupation && !window.meOccupation.validate()) return;
    show(active + 1);
  };
  form.addEventListener(
    'submit',
    (event) => {
      requireAnswers();
      if (active !== 4) {
        event.preventDefault();
        event.stopImmediatePropagation();
        next.click();
        return;
      }
      const invalid = [...form.querySelectorAll('input,textarea,select')].find(
        (input) => !input.disabled && !input.checkValidity(),
      );
      if (invalid) {
        const panel = invalid.closest('[data-review-panel]');
        if (panel) show(Number(panel.dataset.reviewPanel));
        invalid.closest('details')?.setAttribute('open', '');
      }
    },
    true,
  );
  document.addEventListener('me-step-change', (event) => {
    if (event.detail === 'review-step') {
      arrange();
      show(0, false);
    }
  });
  window.meReviewSteps = { arrange };
  arrange();
  show(0, false);
})();
