'use strict';
(() => {
  const box = document.getElementById('employer-profile');
  if (!box) return;
  const form = document.getElementById('employer-profile-form');
  const summary = document.getElementById('employer-profile-summary');
  const edit = document.getElementById('employer-profile-edit');
  const cancel = document.getElementById('employer-profile-cancel');
  const status = document.getElementById('employer-profile-status');
  const error = document.getElementById('employer-profile-error');
  const submit = form.querySelector('[type="submit"]');
  const names = ['response_coverage', 'response_time'];
  const fields = names.map((name) => form.elements.namedItem(name));
  const messages = Object.fromEntries(
    [...document.querySelectorAll('#employer-profile-messages [data-key]')].map((item) => [
      item.dataset.key,
      item.textContent,
    ]),
  );
  let saved = JSON.parse(document.getElementById('employer-profile-values').textContent);
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
      const response = await fetch('/api/employer/profile/', {
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
