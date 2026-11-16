(() => {
  const scope = document.querySelector('[data-ledger-scope-form]');
  if (scope) {
    const company = scope.querySelector('[name=company]');
    const account = scope.querySelector('[name=account]');
    const filter = () => {
      [...account.options].forEach((option) => {
        const allowed = !option.value || !company.value || option.dataset.companyId === company.value;
        option.hidden = !allowed; option.disabled = !allowed;
        if (!allowed && option.selected) account.value = '';
      });
    };
    company?.addEventListener('change', filter); filter();
  }
  let dirty = false;
  document.querySelectorAll('[data-ledger-command-form]').forEach((form) => {
    form.addEventListener('input', () => { dirty = true; });
    form.addEventListener('change', () => { dirty = true; });
    form.addEventListener('submit', (event) => {
      if (event.defaultPrevented) return;
      if (form.dataset.ledgerSubmitting) { event.preventDefault(); return; }
      form.dataset.ledgerSubmitting = 'true'; dirty = false;
      form.querySelectorAll('button[type=submit]').forEach((button) => {
        button.dataset.ledgerBusy = 'true';
        button.dataset.ledgerOriginalDisabled = String(button.disabled);
        button.dataset.ledgerOriginalLabel = button.textContent;
      });
      const submitter = event.submitter;
      if (submitter?.name && !submitter.disabled) {
        const action = document.createElement('input'); action.type = 'hidden';
        action.dataset.ledgerSubmitter = ''; action.name = submitter.name;
        action.value = submitter.value; form.append(action); submitter.disabled = true;
      }
    }, true);
  });
  window.addEventListener('beforeunload', (event) => {
    if (dirty) { event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('pageshow', () => {
    dirty = false;
    document.querySelectorAll('[data-ledger-submitter]').forEach((node) => node.remove());
    document.querySelectorAll('[data-ledger-submitting]').forEach((form) => delete form.dataset.ledgerSubmitting);
    document.querySelectorAll('[data-ledger-busy]').forEach((button) => {
      button.disabled = button.dataset.ledgerOriginalDisabled === 'true';
      button.textContent = button.dataset.ledgerOriginalLabel; button.removeAttribute('aria-busy');
      delete button.dataset.ledgerBusy; delete button.dataset.ledgerOriginalDisabled;
      delete button.dataset.ledgerOriginalLabel;
    });
  });
  const rows = [...document.querySelectorAll('[data-ledger-status-url]')];
  let rounds = 0;
  const refresh = async () => {
    if (document.hidden) { window.setTimeout(refresh, 10000); return; }
    rounds += 1;
    await Promise.allSettled(rows.map(async (row) => {
      if (!row.dataset.ledgerStatusUrl) return;
      const response = await fetch(row.dataset.ledgerStatusUrl, {credentials: 'same-origin', cache: 'no-store', headers: {'Accept': 'application/json'}});
      if (!response.ok) return;
      const data = await response.json();
      row.querySelector('[data-ledger-state]').textContent = data.label;
      row.querySelector('[data-ledger-detail]').textContent = data.detail || '';
      const link = row.querySelector('[data-ledger-conference]');
      if (data.conference_url) {
        const target = new URL(data.conference_url, window.location.href);
        if (target.origin === window.location.origin) { link.href = target.href; link.hidden = false; }
      }
      const actions = row.querySelector('[data-ledger-actions]');
      if (data.can_retry && data.retry_url && !actions.querySelector('form')) {
        const target = new URL(data.retry_url, window.location.href);
        const csrf = document.querySelector('input[name=csrfmiddlewaretoken]');
        if (target.origin === window.location.origin && csrf) {
          const form = document.createElement('form'); form.method = 'post'; form.action = target.href;
          Object.entries({csrfmiddlewaretoken: csrf.value, request_key: data.retry_key,
            expected_mapping_revision: data.mapping_revision}).forEach(([name, value]) => {
            const input = document.createElement('input'); input.type = 'hidden';
            input.name = name; input.value = value; form.append(input);
          });
          const button = document.createElement('button'); button.type = 'submit';
          button.className = 'row-action-button'; button.textContent = 'Tentar novamente';
          form.append(button); actions.append(form);
          form.addEventListener('submit', () => { button.disabled = true; button.textContent = 'Retomando…'; });
        }
      }
      if (!data.poll) delete row.dataset.ledgerStatusUrl;
    }));
    if (rounds < 60 && rows.some((row) => row.dataset.ledgerStatusUrl)) window.setTimeout(refresh, 10000);
  };
  if (rows.length) window.setTimeout(refresh, 10000);
})();
