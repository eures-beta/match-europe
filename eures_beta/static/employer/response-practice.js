'use strict';
(() => {
  const box = document.getElementById('response-practice');
  if (!box) return;
  const form = document.getElementById('response-practice-form');
  const summary = document.getElementById('response-practice-summary');
  const edit = document.getElementById('response-practice-edit');
  const cancel = document.getElementById('response-practice-cancel');
  const status = document.getElementById('response-practice-status');
  const error = document.getElementById('response-practice-error');
  const submit = form.querySelector('[type="submit"]');
  const names = ['response_coverage', 'response_time'];
  const fields = names.map((name) => form.elements.namedItem(name));
  const messages = Object.fromEntries(
    [...document.querySelectorAll('#response-practice-messages [data-key]')].map((item) => [
      item.dataset.key,
      item.textContent,
    ]),
  );
  let saved = JSON.parse(document.getElementById('response-practice-values').textContent);
  function render() {
    names.forEach((name, index) => {
      fields[index].value = saved[name];
      const selected = fields[index].selectedOptions[0];
      box.querySelector('[data-practice-value="' + name + '"]').textContent = saved[name]
        ? selected.textContent
        : '';
    });
    summary.hidden = !saved.revision;
    form.hidden = Boolean(saved.revision);
    cancel.hidden = !saved.revision;
    edit.setAttribute('aria-expanded', 'false');
  }
  edit.addEventListener('click', () => {
    render();
    summary.hidden = true;
    form.hidden = false;
    edit.setAttribute('aria-expanded', 'true');
    status.textContent = error.textContent = '';
    fields[0].focus();
  });
  cancel.addEventListener('click', () => {
    render();
    status.textContent = error.textContent = '';
    edit.focus();
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submit.disabled = cancel.disabled = true;
    status.textContent = error.textContent = '';
    const payload = { revision: saved.revision };
    names.forEach((name, index) => {
      payload[name] = fields[index].value;
    });
    try {
      const csrf =
        document.cookie
          .split('; ')
          .find((part) => part.startsWith('csrftoken='))
          ?.split('=')[1] || '';
      const response = await fetch('/api/employer/response-practice/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify(payload),
      });
      if (!response.ok)
        throw Object.assign(new Error('save'), { conflict: response.status === 409 });
      saved = await response.json();
      render();
      status.textContent = messages.saved;
      edit.focus();
    } catch (exc) {
      error.textContent = exc.conflict ? messages.conflict : messages.error;
    } finally {
      submit.disabled = cancel.disabled = false;
    }
  });
  render();
})();
