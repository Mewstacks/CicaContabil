(() => {
  const form = document.querySelector('[data-import-form]');
  if (!form) return;
  const kind = form.querySelector('[data-import-field="kind"] select');
  const company = form.querySelector('[data-import-field="company"]');
  const snapshot = form.querySelector('[data-import-field="source_snapshot_at"]');
  const key = form.querySelector('[data-import-field="backup_key"]');
  const errorSummary = form.querySelector('[data-form-errors]');
  function render() {
    const value = kind.value;
    company.hidden = !['fiscal_xml','bank_ofx'].includes(value);
    snapshot.hidden = value !== 'dominio_backup';
    key.hidden = value !== 'dominio_backup';
  }
  kind.addEventListener('change', render);
  render();
  if (errorSummary) requestAnimationFrame(() => errorSummary.focus({preventScroll:true}));
})();
