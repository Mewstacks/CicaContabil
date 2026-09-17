/* Native disclosure navigation: click, keyboard, and touch share one tree. */
(() => {
  const header = document.querySelector('.workspace-header');
  if (!header) return;
  const groups = [...header.querySelectorAll('[data-workspace-menu]')];
  const nav = header.querySelector('.workspace-navigation');
  const toggle = header.querySelector('[data-workspace-toggle]');
  const mobile = window.matchMedia('(max-width: 960px)');
  const closeGroups = (except) => groups.forEach(group => {
    if (group !== except) group.open = false;
  });
  const closeMobile = () => {
    header.classList.remove('is-menu-open');
    toggle.setAttribute('aria-expanded', 'false');
    closeGroups();
  };
  header.classList.add('is-enhanced');
  toggle.addEventListener('click', () => {
    const open = !header.classList.contains('is-menu-open');
    closeGroups();
    header.classList.toggle('is-menu-open', open);
    toggle.setAttribute('aria-expanded', String(open));
  });
  groups.forEach(group => {
    group.addEventListener('toggle', () => { if (group.open) closeGroups(group); });
    group.addEventListener('keydown', event => {
      const summary = group.querySelector('summary');
      const links = [...group.querySelectorAll('a[href]')];
      if (event.key === 'Escape' && group.open) {
        event.preventDefault();
        event.stopPropagation();
        group.open = false;
        summary.focus();
      } else if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
        event.preventDefault();
        group.open = true;
        closeGroups(group);
        const index = links.indexOf(document.activeElement);
        const next = event.key === 'ArrowDown'
          ? (index + 1) % links.length
          : (index <= 0 ? links.length - 1 : index - 1);
        links[next]?.focus();
      } else if (!mobile.matches && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
        const controls = [...nav.querySelectorAll(':scope > a, :scope > details > summary')];
        const index = controls.indexOf(summary);
        const step = event.key === 'ArrowRight' ? 1 : -1;
        event.preventDefault();
        closeGroups();
        controls[(index + step + controls.length) % controls.length]?.focus();
      }
    });
    group.addEventListener('focusout', () => {
      requestAnimationFrame(() => { if (!group.contains(document.activeElement)) group.open = false; });
    });
  });
  document.addEventListener('click', event => {
    if (!header.contains(event.target)) closeMobile();
    else if (!nav.contains(event.target) && !toggle.contains(event.target)) closeGroups();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && header.classList.contains('is-menu-open')) {
      closeMobile();
      toggle.focus();
    }
  });
  header.addEventListener('focusout', () => requestAnimationFrame(() => {
    if (!header.contains(document.activeElement)) closeMobile();
  }));
  mobile.addEventListener('change', () => {
    const focused = nav.contains(document.activeElement);
    closeMobile();
    if (mobile.matches && focused) toggle.focus();
  });
})();

/* Server-rendered validation returns a complete page. Move keyboard users to its
   summary once, after the new document has loaded; inline field errors remain in place. */
(() => {
  const summary = document.querySelector('[data-form-errors]');
  if (summary instanceof HTMLElement) summary.focus();
})();
