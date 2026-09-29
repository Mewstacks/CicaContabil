(() => {
  const form = document.querySelector('[data-radar-analysis-form]');
  if (!(form instanceof HTMLFormElement)) return;
  const button = form.querySelector('button[type="submit"]');
  let dirty = false;
  let submitting = false;
  form.addEventListener('input', () => { dirty = true; });
  form.addEventListener('change', () => { dirty = true; });
  form.addEventListener('submit', () => {
    if (!form.checkValidity()) return;
    submitting = true;
    form.setAttribute('aria-busy', 'true');
    if (button instanceof HTMLButtonElement) {
      button.disabled = true;
      button.textContent = 'Preparando análise…';
    }
  });
  window.addEventListener('beforeunload', event => {
    if (!dirty || submitting) return;
    event.preventDefault();
    event.returnValue = '';
  });
  window.addEventListener('pageshow', () => {
    submitting = false;
    form.removeAttribute('aria-busy');
    if (button instanceof HTMLButtonElement) {
      button.disabled = false;
      button.textContent = 'Criar ou retomar análise';
    }
  });
})();
