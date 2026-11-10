const panel = document.querySelector('[data-candidate-install]');
const isPhone =
  /iPhone|iPod/i.test(navigator.userAgent) ||
  (/Android/i.test(navigator.userAgent) && /Mobile/i.test(navigator.userAgent));
const isInstalled =
  window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;

if (isPhone && isInstalled) {
  panel.querySelector('[data-install-complete]').hidden = false;
} else {
  panel.querySelector(isPhone ? '[data-install-phone]' : '[data-install-handoff]').open = true;
}
