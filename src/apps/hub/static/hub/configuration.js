(() => {
  'use strict';
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
