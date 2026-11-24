(() => {
  'use strict';
  const page = document.querySelector('.configuration-page');
  const nav = page?.querySelector('.configuration-nav');
  const panels = [...(page?.querySelectorAll('[data-config-group]') || [])];

  if (nav && panels.length) {
    const links = [...nav.querySelectorAll('a[href^="#config-"]')];
    const groups = new Set(panels.map(panel => panel.dataset.configGroup));
    const groupFromHash = () => {
      const requested = window.location.hash.replace('#config-', '');
      if (groups.has(requested)) return requested;
      // An empty hash is a string, not a node, and a malformed hash makes querySelector throw.
      let target = null;
      try {
        target = window.location.hash ? document.querySelector(window.location.hash) : null;
      } catch {
        target = null;
      }
      return target?.closest('[data-config-group]')?.dataset.configGroup || '';
    };
    const groupWithError = panels.find(panel => panel.querySelector('[data-form-errors]'))
      ?.dataset.configGroup;
    const showGroup = group => {
      const selected = groups.has(group) ? group : 'mewstack';
      panels.forEach(panel => {
        panel.hidden = panel.dataset.configGroup !== selected;
      });
      links.forEach(link => {
        const active = link.hash === `#config-${selected}`;
        link.toggleAttribute('aria-current', active);
      });
    };

    showGroup(groupFromHash() || groupWithError || 'mewstack');
    if (groupWithError) {
      window.setTimeout(() => {
        page.querySelector('[data-form-errors]')?.focus();
      }, 0);
    }
    window.addEventListener('hashchange', () => showGroup(groupFromHash()));
  }

  const dirty = new Set();
  document.querySelectorAll('.configuration-page form').forEach(form => {
    form.addEventListener('input', () => dirty.add(form));
    form.addEventListener('change', () => dirty.add(form));
    form.addEventListener('submit', () => dirty.delete(form));
  });
  window.addEventListener('beforeunload', event => {
    if (!dirty.size) return;
    event.preventDefault();
    event.returnValue = '';
  });
})();
