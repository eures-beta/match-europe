// No upload, LinkedIn request, persistence or profile creation in this first screen.
(() => {
  const status = document.getElementById('candidate-status');
  const choices = document.querySelectorAll('[data-candidate-choice]');
  choices.forEach(button => button.addEventListener('click', () => {
    choices.forEach(choice => choice.classList.toggle('is-selected', choice === button));
    status.hidden = false;
    status.textContent = status.dataset.selectionNotice;
  }));
  document.querySelector('[data-candidate-account]').addEventListener('click', () => {
    status.hidden = false;
    status.textContent = status.dataset.accountNotice;
  });
})();
