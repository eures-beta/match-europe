if ('serviceWorker' in navigator) {
  const workerUrl = document.currentScript.dataset.workerUrl;
  navigator.serviceWorker.register(workerUrl).catch((error) => {
    console.warn('Match Europe service worker registration failed.', error);
  });
}
