document.querySelectorAll('[data-choice-group]').forEach((group) => {
  const inputs = [...group.querySelectorAll('input[type="checkbox"]')];
  const maximum = Number(group.dataset.maximum);
  const count = group.querySelector('[data-count]');
  function update() {
    const selected = inputs.filter((input) => input.checked).length;
    count.textContent = `${selected} / ${maximum}`;
    inputs.forEach((input) => {
      input.disabled = !input.checked && selected >= maximum;
    });
  }
  group.addEventListener('change', update);
  update();
});

document.querySelectorAll('[data-resolve-skills]').forEach((form) => {
  const button = form.querySelector('button[type="submit"]');
  const status = form.querySelector('[data-resolve-status]');
  window.addEventListener('pageshow', () => {
    delete form.dataset.pending;
    button.disabled = false;
    status.hidden = true;
  });
  form.addEventListener('submit', (event) => {
    if (form.dataset.pending) {
      event.preventDefault();
      return;
    }
    event.preventDefault();
    form.dataset.pending = '1';
    status.hidden = false;
    status.focus();
    button.disabled = true;
    // Give the live message a paint before starting the server request.
    requestAnimationFrame(() =>
      requestAnimationFrame(() => HTMLFormElement.prototype.submit.call(form)),
    );
  });
});
