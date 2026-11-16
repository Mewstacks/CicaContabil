(() => {
  const forms = [...document.querySelectorAll('form[data-title-review-form]')];
  let dirty = false;
  forms.forEach((form) => {
    form.addEventListener('input', () => { dirty = true; });
    form.addEventListener('change', () => { dirty = true; });
    form.addEventListener('submit', (event) => {
      if (event.defaultPrevented) return;
      dirty = false;
      // hub.js shows a busy state by disabling the submitted button. Preserve
      // its named action before native form serialization drops disabled inputs.
      const button = event.submitter;
      if (button instanceof HTMLButtonElement && button.name && !button.disabled) {
        const action = document.createElement('input');
        action.type = 'hidden'; action.name = button.name; action.value = button.value;
        action.dataset.titleSubmitAction = 'true'; form.append(action);
        button.dataset.titleSubmitted = 'true';
        button.dataset.titleOriginalLabel = button.textContent;
        button.disabled = true;
      }
    }, { capture: true });
  });
  window.addEventListener('beforeunload', (event) => {
    if (!dirty) return;
    event.preventDefault(); event.returnValue = '';
  });
  window.addEventListener('pageshow', () => {
    dirty = false;
    document.querySelectorAll('[data-title-submit-action]').forEach((input) => input.remove());
    document.querySelectorAll('[data-title-submitted]').forEach((button) => {
      button.disabled = false; button.removeAttribute('aria-busy');
      button.textContent = button.dataset.titleOriginalLabel;
      delete button.dataset.titleSubmitted; delete button.dataset.titleOriginalLabel;
    });
  });
})();
