(() => {
  const button = document.querySelector('.menu-toggle');
  const menu = document.querySelector('#primary-navigation');
  if (!button || !menu) return;

  const setOpen = (open) => {
    menu.classList.toggle('open', open);
    button.setAttribute('aria-expanded', String(open));
  };

  button.addEventListener('click', () => {
    setOpen(button.getAttribute('aria-expanded') !== 'true');
  });
  menu.addEventListener('click', (event) => {
    if (event.target.closest('a')) setOpen(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menu.classList.contains('open')) {
      setOpen(false);
      button.focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.nav')) setOpen(false);
  });
  window.matchMedia('(max-width: 730px)').addEventListener('change', () => setOpen(false));
})();
