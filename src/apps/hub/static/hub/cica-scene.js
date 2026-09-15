const root = document.querySelector('[data-cica-demo]');

if (root) {
  const panels = [...root.querySelectorAll('[data-demo-panel]')];
  const navItems = [...root.querySelectorAll('[data-demo-nav]')];
  const sidebar = root.querySelector('.demo-sidebar');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const interval = 3400;
  let activeIndex = 0;
  let timer = 0;
  let visible = true;
  let progressAnimation = null;

  const restartProgress = () => {
    const progress = root.querySelector('.demo-progress span');
    progressAnimation?.cancel();
    progressAnimation = null;
    if (!progress || reducedMotion.matches) return;
    progressAnimation = progress.animate(
      [{transform: 'scaleX(0)'}, {transform: 'scaleX(1)'}],
      {duration: interval, easing: 'linear', fill: 'both'},
    );
  };

  const activate = (index) => {
    activeIndex = index % panels.length;
    const key = panels[activeIndex].dataset.demoPanel;
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
    });
    const activeNav = navItems.find((item) => item.dataset.demoNav === key);
    if (sidebar && activeNav && sidebar.scrollWidth > sidebar.clientWidth) {
      sidebar.scrollTo({
        left: activeNav.offsetLeft - (sidebar.clientWidth - activeNav.clientWidth) / 2,
        behavior: reducedMotion.matches ? 'auto' : 'smooth',
      });
    }

    restartProgress();
  };

  const stop = () => {
    window.clearInterval(timer);
    timer = 0;
  };

  const start = () => {
    stop();
    if (reducedMotion.matches || document.hidden || !visible || panels.length < 2) return;
    restartProgress();
    timer = window.setInterval(() => activate(activeIndex + 1), interval);
  };

  activate(0);
  start();

  const observer = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    start();
  }, {threshold: 0.2});

  observer.observe(root);
  navItems.forEach((item, index) => {
    item.addEventListener('click', () => {
      activate(index);
      start();
    });
    item.addEventListener('keydown', (event) => {
      const direction = {ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1}[event.key];
      let nextIndex = index;
      if (direction) nextIndex = (index + direction + navItems.length) % navItems.length;
      if (event.key === 'Home') nextIndex = 0;
      if (event.key === 'End') nextIndex = navItems.length - 1;
      if (nextIndex === index) return;
      event.preventDefault();
      navItems[nextIndex].focus();
      activate(nextIndex);
      start();
    });
  });
  root.addEventListener('mouseenter', () => {
    stop();
    progressAnimation?.pause();
  });
  root.addEventListener('mouseleave', start);
  root.addEventListener('focusin', () => {
    stop();
    progressAnimation?.pause();
  });
  root.addEventListener('focusout', (event) => {
    if (!root.contains(event.relatedTarget)) start();
  });
  document.addEventListener('visibilitychange', start);
  reducedMotion.addEventListener('change', () => {
    activate(0);
    start();
  });
  window.addEventListener('pagehide', () => {
    stop();
    progressAnimation?.cancel();
    observer.disconnect();
  }, {once: true});
}
