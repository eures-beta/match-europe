'use strict';

// Keep Django's native toggle and remembered choices; only change its default.
try {
  const key = 'django.admin.navSidebarIsOpen';
  if (localStorage.getItem(key) === null) {
    localStorage.setItem(key, 'false');
  }
} catch {
  // Storage restrictions must not stop other administration scripts loading.
}
