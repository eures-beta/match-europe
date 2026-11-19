// Shared local catalogue, explicit employer choices, no external request.
(() => {
  const strings = document.getElementById('occupation-strings');
  if (!strings) return;
  const t = JSON.parse(strings.textContent);
  const title = document.getElementById('review-title');
  const lang = document.documentElement.lang;
  const form = document.getElementById('review-form');
  const node = (tag, text, parent) => {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (parent) parent.append(el);
    return el;
  };
  const box = node('section');
  box.className = 'occupation-picker';
  box.style.gridColumn = '1 / -1';
  title.closest('.review-field').after(box);
  box.setAttribute('aria-label', t.proposals);
  const feedback = node('div', '', box);
  feedback.className = 'occupation-feedback';
  const error = node('p', '', feedback);
  error.id = 'occupation-error';
  error.setAttribute('role', 'alert');
  error.className = 'import-error';
  const retry = node('button', t.retry, feedback);
  retry.type = 'button';
  retry.className = 'ghost-action occupation-change';
  retry.hidden = true;
  const fallback = node('section', '', box);
  fallback.hidden = true;
  const fallbackIntro = node('p', t.manualIntro, fallback);
  const queryLabel = node('label', t.conciseQuery, fallback);
  queryLabel.htmlFor = 'occupation-query';
  const query = node('input', '', fallback);
  query.id = 'occupation-query';
  query.type = 'text';
  query.maxLength = 150;
  query.autocomplete = 'off';
  query.placeholder = t.searchExample;
  query.setAttribute('aria-describedby', 'occupation-query-help occupation-error');
  query.setAttribute('aria-controls', 'occupation-results');
  query.style.width = '100%';
  const help = node('p', t.conciseHelp, fallback);
  help.id = 'occupation-query-help';
  const status = node('p', '', box);
  status.setAttribute('role', 'status');
  node('p', t.commonHelp, box);
  const list = node('div', '', box);
  list.id = 'occupation-results';
  const near = node('button', t.near, box);
  near.type = 'button';
  near.className = 'ghost-action occupation-change';
  near.hidden = true;
  const custom = node('div', '', box);
  custom.hidden = true;
  node('p', t.personalHelp, custom);
  const label = node('label', t.personal, custom);
  label.htmlFor = 'occupation-personal';
  const personal = node('textarea', '', custom);
  personal.id = 'occupation-personal';
  personal.maxLength = 2000;
  personal.rows = 3;
  let version = '1.2.1',
    searchedTitle = '',
    cards = [],
    choices = new Set(),
    offered = [],
    serial = 0,
    timer = null,
    controller = null,
    fromDocument = false;
  let romeChoices = new Set();
  const isChosen = (job) =>
    (job.references || [job.value]).some((ref) =>
      ref.startsWith('rome:')
        ? romeChoices.has(ref.slice(5))
        : choices.has(ref.startsWith('esco:') ? ref.slice(5) : ref),
    );
  function choose(job, selected) {
    if (!selected) {
      for (const ref of job.references || [job.value]) {
        if (ref.startsWith('rome:')) romeChoices.delete(ref.slice(5));
        else choices.delete(ref.startsWith('esco:') ? ref.slice(5) : ref);
      }
    } else if (job.value.startsWith('rome:')) romeChoices.add(job.value.slice(5));
    else choices.add(job.value.startsWith('esco:') ? job.value.slice(5) : job.value);
  }
  function render() {
    list.replaceChildren();
    for (const selected of [true, false]) {
      const groupCards = cards.filter((job) => isChosen(job) === selected);
      if (!groupCards.length) continue;
      const group = node('section', '', list);
      node('h4', selected ? t.saved : t.proposals, group);
      for (const job of groupCards) {
        const article = node('article', '', group);
        article.className = 'review-question';
        const label = node('label', '', article);
        label.className = 'review-check';
        const check = node('input', '', label);
        check.type = 'checkbox';
        check.value = job.value;
        check.checked = isChosen(job);
        const text = node('span', '', label);
        const heading = node('strong', job.label, text);
        heading.lang = job.labelLanguage || lang;
        const description = node('span', job.description, text);
        description.lang = job.descriptionLanguage || lang;
        description.style.display = 'block';
        check.addEventListener('change', () => {
          choose(job, check.checked);
          error.textContent = '';
          window.meOccupationSkills?.update();
        });
      }
    }
    if (!cards.length) node('p', t.empty, list);
  }
  function cancel() {
    clearTimeout(timer);
    controller?.abort();
    serial++;
    near.disabled = false;
  }
  function clear() {
    cancel();
    retry.hidden = true;
    romeChoices = new Set();
    searchedTitle = '';
    cards = [];
    choices = new Set();
    offered = [];
    personal.value = '';
    custom.hidden = true;
    near.hidden = true;
    list.replaceChildren();
    error.textContent = '';
    window.meOccupationSkills?.update();
  }
  function manual(message = t.manualIntro, focus = false) {
    fallback.hidden = false;
    fallbackIntro.textContent = message;
    fallbackIntro.hidden = message === t.manualHelp;
    if (focus) query.focus();
  }
  let detectedQuery = '';
  async function find(mode = 'search', useContext = false, fromTitle = false) {
    clearTimeout(timer);
    const q = (fromTitle ? detectedQuery || title.value : query.value).trim();
    if (!q) {
      manual(t.manualHelp);
      status.textContent = '';
      return;
    }
    cancel();
    const request = serial;
    const boundTitle = title.value.trim();
    controller = new AbortController();
    if (mode === 'near') {
      offered = [
        ...new Set([
          ...offered,
          ...cards.filter((row) => !row.groupKey.startsWith('rome:')).map((row) => row.groupKey),
        ]),
      ];
    } else {
      offered = [];
    }
    status.textContent = t.busy;
    status.className = '';
    error.textContent = '';
    retry.hidden = true;
    // Keep an escape route available even while the network request is pending.
    manual(t.manualHelp);
    custom.hidden = false;
    let deadline;
    try {
      const context = useContext
        ? [
            document.getElementById('review-description').value,
            document.getElementById('review-desiredProfile').value,
          ]
            .join('\n')
            .slice(0, 20000)
        : '';
      const csrf =
        document.cookie
          .split('; ')
          .find((value) => value.startsWith('csrftoken='))
          ?.split('=')[1] || '';
      const pending = fetch('/api/occupations/', {
        method: 'POST',
        credentials: 'same-origin',
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ q, lang, mode, excluded: offered, context, unified: true }),
      });
      const result = await Promise.race([
        pending.then(async (response) => {
          if (!response.ok) throw new Error('catalogue');
          return response.json();
        }),
        new Promise((_, reject) => {
          deadline = setTimeout(() => {
            reject(new Error('catalogue timeout'));
            if (request === serial) controller.abort();
          }, 15000);
        }),
      ]);
      if (request !== serial || title.value.trim() !== boundTitle) return;
      version = result.version;
      searchedTitle = boundTitle;
      const fresh = result.unified_results;
      const aliasMap = new Map(
        fresh.flatMap((row) => (row.references || [row.value]).map((ref) => [ref, row.groupKey])),
      );
      const retained = cards
        .filter(isChosen)
        .map((row) => ({ ...row, groupKey: aliasMap.get(row.value) || row.groupKey }));
      const combined = [...fresh, ...retained];
      cards = [
        ...combined
          .reduce((map, row) => {
            if (!map.has(row.groupKey)) map.set(row.groupKey, row);
            return map;
          }, new Map())
          .values(),
      ];
      render();
      if (fromTitle && !fresh.length) manual(fromDocument ? t.automaticFailure : t.manualIntro);
      if (!fromTitle) fallbackIntro.hidden = true;
      const count = fresh.length;
      status.textContent = count
        ? t.resultsFound.replace('{count}', String(count))
        : fromTitle
          ? ''
          : t.empty;
      status.className = count ? 'visually-hidden' : '';
      if (result.total > fresh.length) status.textContent += ' ' + t.limited;
      custom.hidden = (fromTitle || fresh.length > 0) && !personal.value;
      near.hidden = mode === 'near' || !fresh.length;
    } catch (exc) {
      if (request === serial && exc.name !== 'AbortError') {
        manual(t.manualHelp);
        status.textContent = '';
        error.textContent = t.searchFailed;
        retry.hidden = false;
        custom.hidden = false;
      }
    } finally {
      clearTimeout(deadline);
    }
  }
  function schedule(mode) {
    cancel();
    fallbackIntro.hidden = true;
    status.className = 'visually-hidden';
    cards = cards.filter(isChosen);
    render();
    near.hidden = true;
    const q = query.value.trim();
    if (q.length < 2) {
      status.textContent = t.startTyping;
      return;
    }
    status.textContent = t.busy;
    timer = setTimeout(() => find(mode), 300);
  }
  retry.addEventListener('click', () => find('search', true, true));
  query.addEventListener('input', () => schedule('search'));
  query.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      find();
    }
  });
  near.addEventListener('click', () => {
    manual(t.manualHelp, true);
    status.textContent = '';
    cards = cards.filter(isChosen);
    render();
    near.hidden = true;
  });
  personal.addEventListener('input', () => {
    searchedTitle = title.value.trim();
    error.textContent = '';
  });
  title.addEventListener('input', () => {
    detectedQuery = '';
    clear();
    fallback.hidden = true;
    query.value = '';
    status.textContent = t.busy;
    timer = setTimeout(() => find('search', true, true), 300);
  });
  window.meOccupation = {
    load(value, detected = false, occupationQuery = '') {
      detectedQuery = occupationQuery;
      fromDocument = detected;
      clear();
      fallback.hidden = true;
      query.value = '';
      status.textContent = '';
      document.querySelector('label[for=review-title]').textContent = detected
        ? t.detectedTitle
        : t.ownTitle;
      if (value && value.title === title.value.trim()) {
        version = value.version;
        searchedTitle = value.title;
        choices = new Set(value.uris || []);
        cards = value.common_jobs || [
          ...(value.jobs || []).map((row) => ({
            ...row,
            value: 'esco:' + row.uri,
            groupKey: row.uri,
            references: ['esco:' + row.uri],
          })),
          ...(value.rome_jobs || []).map((row) => ({
            ...row,
            value: 'rome:' + row.code,
            groupKey: 'rome:' + row.code,
            references: ['rome:' + row.code],
          })),
        ];
        romeChoices = new Set(value.rome_codes || []);
        personal.value = value.personal || '';
        custom.hidden = !personal.value;
        render();
      }
      find('search', true, true);
      window.meOccupationSkills?.update();
    },
    reset: clear,
    collect() {
      return {
        version,
        title: title.value.trim(),
        language: lang,
        rome_codes: searchedTitle === title.value.trim() ? [...romeChoices] : [],
        uris: searchedTitle === title.value.trim() ? [...choices] : [],
        skill_references:
          searchedTitle === title.value.trim()
            ? [...new Set(cards.filter(isChosen).map((row) => row.groupKey))]
            : [],
        personal: searchedTitle === title.value.trim() ? personal.value.trim() : '',
      };
    },
    validate() {
      const value = this.collect();
      if (!value.uris.length && !value.rome_codes.length && !value.personal) {
        error.textContent = t.required;
        box.scrollIntoView({ block: 'center' });
        if (fallback.hidden) {
          near.focus();
        } else {
          query.focus();
        }
        return false;
      }
      return true;
    },
    summary(value) {
      const rows = value?.common_jobs || cards.filter(isChosen);
      return [...rows.map((job) => job.label + ' — ' + job.description), value?.personal]
        .filter(Boolean)
        .join('\n\n');
    },
    summaryLabel: t.saved,
  };
})();
