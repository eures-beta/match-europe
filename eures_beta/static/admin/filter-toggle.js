'use strict';

(() => {
  const button = document.getElementById('admin-filter-toggle');
  const filters = document.getElementById('changelist-filter');
  const changelist = document.getElementById('changelist');
  if (!button || !filters || !changelist) return;

  // Only a display preference is stored, never filter values or account data.
  const storageKey = 'matchEurope.admin.filtersCollapsed';
  let collapsed = false;
  try {
    collapsed = localStorage.getItem(storageKey) === 'true';
  } catch {
    // Storage can be unavailable; the control still works on the current page.
  }

  function render() {
    filters.hidden = collapsed;
    changelist.classList.toggle('filters-collapsed', collapsed);
    button.setAttribute('aria-expanded', String(!collapsed));
    button.textContent = collapsed ? button.dataset.showLabel : button.dataset.hideLabel;
  }

  button.addEventListener('click', () => {
    collapsed = !collapsed;
    render();
    try {
      localStorage.setItem(storageKey, String(collapsed));
    } catch {
      // Do not make browser storage a prerequisite for using the filters.
    }
  });
  render();
  button.hidden = false;
})();
