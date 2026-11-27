// On a phone the adviser tabs and lists are scrolling rows: bring the current item into view.
document.querySelectorAll('.adviser-workspace-tabs nav, .adviser-sidebar nav').forEach((nav) => {
  const current = nav.querySelector('[aria-current="page"]');
  if (current && nav.scrollWidth > nav.clientWidth) {
    nav.scrollLeft =
      current.offsetLeft - nav.offsetLeft - (nav.clientWidth - current.offsetWidth) / 2;
  }
});
