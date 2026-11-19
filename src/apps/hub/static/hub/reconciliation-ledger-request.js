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
  const notice = document.querySelector('[data-ledger-poll-notice]');
  const announce = (text) => { if (notice) { notice.textContent = text; notice.hidden = !text; } };
  const localTarget = (value) => {
    if (typeof value !== 'string') throw new Error('invalid-target');
    if (!value) return '';
    const target = new URL(value, window.location.href);
    if (target.origin !== window.location.origin) throw new Error('invalid-target');
    return target.href;
  };
  let rounds = 0;
  const autoOpen = new URLSearchParams(window.location.search).get('auto') === '1';
  const refreshRow = async (row) => {
    if (!row.dataset.ledgerStatusUrl) return;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(row.dataset.ledgerStatusUrl, {
        credentials: 'same-origin', cache: 'no-store', headers: {'Accept': 'application/json'},
        signal: controller.signal,
      });
      if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error('unavailable');
      const data = await response.json();
      if (!data || typeof data.label !== 'string' || typeof data.detail !== 'string'
          || typeof data.status !== 'string' || typeof data.poll !== 'boolean'
          || typeof data.can_retry !== 'boolean') throw new Error('invalid-status');
      const conferenceUrl = localTarget(data.conference_url);
      const retryUrl = data.can_retry ? localTarget(data.retry_url) : '';
      if (data.can_retry && (!retryUrl || typeof data.retry_key !== 'string'
          || typeof data.mapping_revision !== 'string')) throw new Error('invalid-retry');
      // Do not change any retained state or action until the complete response is validated.
      const label = row.querySelector('[data-ledger-state]');
      label.textContent = data.label;
      label.className = `status-badge ${['imported', 'empty'].includes(data.status) ? 'is-active' : ['review', 'failed'].includes(data.status) ? 'is-warning' : 'is-muted'}`;
      row.querySelector('[data-ledger-detail]').textContent = data.detail;
      const link = row.querySelector('[data-ledger-conference]');
      link.hidden = !conferenceUrl;
      if (conferenceUrl) link.href = conferenceUrl;
      // D-386: after an import, open the conference as soon as the Razão arrives.
      if (autoOpen && conferenceUrl && ['imported', 'empty'].includes(data.status)) {
        window.location.assign(conferenceUrl);
      }
      const actions = row.querySelector('[data-ledger-actions]');
      if (data.can_retry && !actions.querySelector('form')) {
        const csrf = document.querySelector('input[name=csrfmiddlewaretoken]');
        if (csrf) {
          const form = document.createElement('form'); form.method = 'post'; form.action = retryUrl;
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
    } finally { window.clearTimeout(timeout); }
  };
  const refresh = async () => {
    if (document.hidden) { window.setTimeout(refresh, 10000); return; }
    rounds += 1;
    const results = await Promise.allSettled(rows.map(refreshRow));
    if (results.some((result) => result.status === 'rejected')) {
      announce('Não foi possível atualizar agora. A última situação foi preservada; use Atualizar situação para conferir novamente.');
    } else {
      announce('Situação das solicitações atualizada.');
    }
    if (rows.some((row) => row.dataset.ledgerStatusUrl)) {
      if (rounds < 60) window.setTimeout(refresh, 10000);
      else announce('A atualização automática foi pausada. Use Atualizar situação para continuar acompanhando.');
    }
  };
  if (rows.length) window.setTimeout(refresh, autoOpen ? 3000 : 10000);
  else if (autoOpen) {
    const ready = document.querySelector('[data-ledger-conference]:not([hidden])');
    if (ready && ready.href) window.location.assign(ready.href);
  }
})();
