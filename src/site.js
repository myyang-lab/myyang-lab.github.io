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


// Gallery photos and research figures share an accessible, in-page image viewer.
(() => {
  const triggers = document.querySelectorAll('[data-image-viewer]');
  if (!triggers.length) return;

  const viewer = document.createElement('dialog');
  viewer.className = 'image-viewer';
  viewer.setAttribute('aria-label', 'Enlarged image');
  viewer.innerHTML = `
    <button class="image-viewer-close" type="button" aria-label="Close enlarged image" autofocus>×</button>
    <img class="image-viewer-image" alt=""/>
    <p class="image-viewer-hint">Click image or background to close · Esc</p>`;
  const image = viewer.querySelector('img');
  let opener;
  let previousOverflow = '';

  triggers.forEach((trigger) => {
    trigger.addEventListener('click', (event) => {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      opener = trigger;
      image.alt = trigger.querySelector('img')?.alt || 'Enlarged image';
      image.src = trigger.href;
      previousOverflow = document.documentElement.style.overflow;
      document.documentElement.style.overflow = 'hidden';
      document.body.append(viewer);
      viewer.showModal();
    });
  });
  viewer.addEventListener('click', () => viewer.close());
  viewer.addEventListener('close', () => {
    document.documentElement.style.overflow = previousOverflow;
    image.removeAttribute('src');
    viewer.remove();
    opener?.focus({ preventScroll: true });
  });
})();
