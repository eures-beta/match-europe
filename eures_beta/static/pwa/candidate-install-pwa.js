const panel = document.querySelector('[data-candidate-install-pwa]');
const isPhone =
  /iPhone|iPod/i.test(navigator.userAgent) ||
  (/Android/i.test(navigator.userAgent) && /Mobile/i.test(navigator.userAgent));
const isInstalled =
  window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;

if (isPhone && isInstalled) {
  panel.querySelector('[data-install-pwa-complete]').hidden = false;
} else {
  panel.querySelector(isPhone ? '[data-install-pwa-phone]' : '[data-install-pwa-handoff]').open =
    true;
}
