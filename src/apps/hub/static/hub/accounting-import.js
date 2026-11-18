(() => {
  const form = document.querySelector('[data-import-receipt-form]');
  if (!(form instanceof HTMLFormElement)) return;
  let changed = false;
  form.addEventListener('input', () => { changed = true; });
  form.addEventListener('change', () => { changed = true; });
  window.addEventListener('beforeunload', event => {
    if (!changed) return;
    event.preventDefault();
    event.returnValue = '';
  });
  form.addEventListener('submit', () => {
    if (!form.checkValidity()) return;
    changed = false;
    form.setAttribute('aria-busy', 'true');
    const button = form.querySelector('button[type="submit"]');
    if (button instanceof HTMLButtonElement) {
      button.disabled = true;
      button.textContent = 'Registrando…';
    }
  });
})();
