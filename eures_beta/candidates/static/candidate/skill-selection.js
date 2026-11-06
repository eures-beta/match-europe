// Progressive enhancement: every choice remains available without JavaScript.
(() => {
  const normalise = (value) =>
    value
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLocaleLowerCase();
  const modeInputs = [...document.querySelectorAll('input[name="project_mode"]')];
  const openProject = document.querySelector('[data-open-project]');
  if (!openProject) return;
  function updateMode() {
    const open = modeInputs.some((input) => input.checked && input.value === 'open');
    openProject.hidden = !open;
    openProject.querySelectorAll('input,button').forEach((input) => {
      input.disabled = !open;
    });
    document.querySelectorAll('[data-occupation-only]').forEach((section) => {
      section.hidden = open;
      section.querySelectorAll('input,button').forEach((input) => {
        input.disabled = open;
      });
    });
    if (open)
      openProject
        .querySelectorAll('[data-skill-section]')
        .forEach((section) => updateSelection(section));
  }
  function updateSelection(section, restoreFocus = false) {
    const inputs = [...section.querySelectorAll('input[type="checkbox"]')];
    const selected = inputs.filter((input) => input.checked);
    const maximum = Number(section.dataset.maximum);
    section.querySelector('[data-skill-count]').textContent = `${selected.length} / ${maximum}`;
    const tags = section.querySelector('[data-skill-tags]');
    tags.replaceChildren();
    selected.forEach((input) => {
      const label = input.closest('label').querySelector('span').textContent;
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = `${label} ×`;
      button.setAttribute('aria-label', section.dataset.remove.replace('{label}', label));
      button.addEventListener('click', () => {
        input.checked = false;
        updateSelection(section, true);
      });
      tags.append(button);
    });
    inputs.forEach((input) => {
      input.disabled = !input.checked && selected.length >= maximum;
    });
    if (restoreFocus) (tags.querySelector('button') || section).focus();
  }
  openProject.querySelectorAll('[data-skill-section]').forEach((section) => {
    const search = section.querySelector('[data-skill-search]');
    const results = section.querySelector('[data-skill-results]');
    section.querySelector('[data-skill-search-wrapper]').hidden = false;
    function filter() {
      const query = normalise(search.value.trim());
      let count = 0;
      section.querySelectorAll('[data-skill-category]').forEach((category) => {
        let visible = 0;
        category.querySelectorAll('[data-skill-choice]').forEach((choice) => {
          choice.hidden = !normalise(choice.dataset.search).includes(query);
          if (!choice.hidden) visible++;
        });
        category.hidden = visible === 0;
        count += visible;
      });
      results.textContent = results.dataset.template.replace('{count}', count);
    }
    search.addEventListener('input', filter);
    section.addEventListener('change', () => updateSelection(section));
    updateSelection(section);
    filter();
  });
  modeInputs.forEach((input) => input.addEventListener('change', updateMode));
  updateMode();
})();
