(() => {
  const picker = document.querySelector('[data-company-options]');
  if (picker) {
    const boxes = [...picker.querySelectorAll('input[type="checkbox"]')];
    const output = document.querySelector('[data-selected-count]');
    const update = () => { const count = boxes.filter((box) => box.checked).length; output.textContent = `${count} empresa${count === 1 ? '' : 's'} selecionada${count === 1 ? '' : 's'}`; };
    picker.addEventListener('change', update); update();
    const normalize = (value) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
    document.querySelector('[data-company-search]').addEventListener('input', (event) => {
      const query = normalize(event.target.value.trim());
      boxes.forEach((box) => { box.closest('label').parentElement.hidden = !normalize(box.closest('label').textContent).includes(query); });
      document.querySelector('[data-no-companies]').hidden = boxes.some((box) => !box.closest('label').parentElement.hidden);
    });
    document.querySelector('[data-select-companies]').addEventListener('click', () => { boxes.forEach((box) => { if (!box.closest('label').parentElement.hidden) box.checked = true; }); update(); });
    document.querySelector('[data-clear-companies]').addEventListener('click', () => { boxes.forEach((box) => { box.checked = false; }); update(); });
  }
  document.querySelector('[data-collection-errors]')?.focus();
  document.querySelector('[data-collection-preview]')?.focus();
  document.querySelectorAll('form[data-collection-form], form[data-job-retry]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (event.defaultPrevented) return;
      if (form.dataset.collectionSubmitting) { event.preventDefault(); return; }
      form.dataset.collectionSubmitting = 'true';
      form.querySelectorAll('button[type="submit"]').forEach((button) => {
        button.dataset.collectionBusy = '';
        button.dataset.collectionOriginalDisabled = String(button.disabled);
        button.dataset.collectionOriginalLabel = button.textContent;
      });
      const button = event.submitter;
      if (!(button instanceof HTMLButtonElement) || !button.name || button.disabled) return;
      const input = document.createElement('input'); input.type = 'hidden'; input.name = button.name; input.value = button.value;
      input.dataset.collectionAction = ''; form.append(input); button.disabled = true;
    }, { capture: true });
  });
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('[data-collection-action]').forEach((input) => input.remove());
    document.querySelectorAll('[data-collection-submitting]').forEach((form) => delete form.dataset.collectionSubmitting);
    document.querySelectorAll('[data-collection-busy]').forEach((button) => {
      button.disabled = button.dataset.collectionOriginalDisabled === 'true';
      button.textContent = button.dataset.collectionOriginalLabel; button.removeAttribute('aria-busy');
      delete button.dataset.collectionBusy; delete button.dataset.collectionOriginalDisabled;
      delete button.dataset.collectionOriginalLabel;
    });
  });
  const panel = document.querySelector('[data-title-requests]');
  if (!panel) return;
  const notice = panel.querySelector('[data-poll-notice]');
  let rounds = 0;
  const update = async () => {
    const rows = [...panel.querySelectorAll('[data-title-job][data-poll="true"]')];
    if (!rows.length || rounds >= 60) {
      if (rows.length) notice.textContent = 'A atualização automática foi pausada. Use Atualizar buscas para continuar acompanhando.';
      return;
    }
    if (document.hidden) { window.setTimeout(update, 15000); return; }
    rounds += 1;
    const url = new URL(panel.dataset.statusUrl, location.origin);
    rows.forEach((row) => url.searchParams.append('job', row.dataset.titleJob));
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' }, signal: controller.signal });
      if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error('unavailable');
      const data = await response.json();
      if (!Array.isArray(data.jobs) || data.jobs.length !== rows.length) throw new Error('incomplete');
      let changed = false;
      data.jobs.forEach((job) => {
        const row = rows.find((item) => item.dataset.titleJob === job.id); if (!row) throw new Error('scope');
        const label = row.querySelector('[data-job-label]'); changed ||= label.textContent !== job.label;
        label.textContent = job.label;
        label.className = `status-badge ${['captured', 'empty'].includes(job.status) ? 'is-active' : ['review', 'failed'].includes(job.status) ? 'is-warning' : 'is-muted'}`;
        row.querySelector('[data-job-detail]').textContent = job.detail;
        row.querySelector('[data-job-connection]').textContent = job.connection_detail;
        row.dataset.poll = job.poll ? 'true' : 'false';
        const source = row.querySelector('[data-job-source]'); source.hidden = !job.source_url; if (job.source_url) source.href = job.source_url;
        const retry = row.querySelector('[data-job-retry]');
        if (retry) { retry.hidden = !job.can_retry; retry.action = job.retry_url; retry.querySelector('[name="request_key"]').value = job.retry_key; }
        row.querySelector('[data-job-wait]').hidden = !!job.source_url || !!(retry && job.can_retry);
      });
      if (changed) notice.textContent = 'Situação das buscas atualizada.';
      window.setTimeout(update, 15000);
    } catch (_) {
      notice.textContent = 'Não foi possível atualizar agora. Suas buscas continuam registradas; use Atualizar buscas para tentar novamente.';
    } finally { window.clearTimeout(timeout); }
  };
  window.setTimeout(update, 15000);
})();
