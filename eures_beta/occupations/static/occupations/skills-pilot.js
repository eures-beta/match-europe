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
