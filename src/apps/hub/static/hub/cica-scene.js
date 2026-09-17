const root = document.querySelector('[data-cica-demo]');

if (root) {
  const panels = [...root.querySelectorAll('[data-demo-panel]')];
  const navItems = [...root.querySelectorAll('[data-demo-nav]')];
  const sidebar = root.querySelector('.demo-sidebar');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const requestedDemo = new URLSearchParams(window.location.search).get('demo');
  const initialIndex = Math.max(0, panels.findIndex((panel) => panel.dataset.demoPanel === requestedDemo));

  const activate = (index, syncUrl = false) => {
    const key = panels[index].dataset.demoPanel;
    root.dataset.demoView = key;
    panels.forEach((panel) => {
      const isActive = panel.dataset.demoPanel === key;
      panel.classList.toggle('is-active', isActive);
      panel.setAttribute('aria-hidden', String(!isActive));
    });
    navItems.forEach((item) => {
      const isActive = item.dataset.demoNav === key;
      item.classList.toggle('is-active', isActive);
      item.setAttribute('aria-selected', String(isActive));
      item.tabIndex = isActive ? 0 : -1;
    });
    if (syncUrl) {
      const url = new URL(window.location.href);
      url.searchParams.set('demo', key);
      window.history.replaceState(window.history.state, '', url);
    }
    const activeNav = navItems.find((item) => item.dataset.demoNav === key);
    if (sidebar && activeNav && sidebar.scrollWidth > sidebar.clientWidth) {
      sidebar.scrollTo({
        left: activeNav.offsetLeft - (sidebar.clientWidth - activeNav.clientWidth) / 2,
        behavior: reducedMotion.matches ? 'auto' : 'smooth',
      });
    }
  };

  activate(initialIndex);
  navItems.forEach((item, index) => {
    item.addEventListener('click', () => {
      activate(index, true);
    });
    item.addEventListener('keydown', (event) => {
      const direction = {ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1}[event.key];
      if (!direction && event.key !== 'Home' && event.key !== 'End') return;
      let nextIndex = index;
      if (direction) nextIndex = (index + direction + navItems.length) % navItems.length;
      if (event.key === 'Home') nextIndex = 0;
      if (event.key === 'End') nextIndex = navItems.length - 1;
      event.preventDefault();
      if (nextIndex !== index) {
        navItems[nextIndex].focus();
        activate(nextIndex, true);
      }
    });
  });
}
