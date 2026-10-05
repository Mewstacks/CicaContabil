(() => {
  const serverErrorSummary = document.querySelector('[data-error-summary]');
  if (serverErrorSummary instanceof HTMLElement) serverErrorSummary.focus();

  const tabs = [...document.querySelectorAll('[data-reconciliation-tab]')];
  const panels = [...document.querySelectorAll('[data-reconciliation-panel]')];

  const activateTab = (id, updateUrl = false) => {
    const selectedPanel = panels.find(panel => panel.id === id);
    if (!selectedPanel) return;
    panels.forEach(panel => { panel.hidden = panel !== selectedPanel; });
    tabs.forEach(tab => {
      const active = tab.getAttribute('href') === `#${id}`;
      if (active) tab.setAttribute('aria-current', 'page');
      else tab.removeAttribute('aria-current');
    });
    if (updateUrl) history.replaceState(null, '', `#${id}`);
  };

  if (tabs.length && panels.length) {
    const initial = window.location.hash.slice(1);
    activateTab(panels.some(panel => panel.id === initial) ? initial : 'visao-geral');
    tabs.forEach(tab => tab.addEventListener('click', event => {
      const id = tab.getAttribute('href').slice(1);
      if (!panels.some(panel => panel.id === id)) return;
      event.preventDefault();
      activateTab(id, true);
      document.getElementById(id)?.scrollIntoView({ block: 'start' });
    }));
    window.addEventListener('hashchange', () => activateTab(window.location.hash.slice(1)));
  }

  const ACCEPTED_EXTENSIONS = ['ofx', 'qfx', 'csv', 'xlsx', 'pdf'];
  const formatSize = bytes => (bytes >= 1048576
    ? `${(bytes / 1048576).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} MiB`
    : `${Math.max(1, Math.round(bytes / 1024)).toLocaleString('pt-BR')} KiB`);

  document.querySelectorAll('[data-reconciliation-dropzone]').forEach(dropzone => {
    const input = dropzone.querySelector('input[type=file]');
    if (!(input instanceof HTMLInputElement)) return;
    const list = document.getElementById(`${input.id}-files`);
    const form = dropzone.closest('form');
    const company = form?.querySelector('select[name="company"]');
    const error = form?.querySelector('[data-file-error]');
    const submit = form?.querySelector('[data-upload-submit]');
    if (!list || !form) return;
    const maxFiles = Number(dropzone.dataset.maxFiles || 20);
    const maxBytes = Number(dropzone.dataset.maxBytes || 26214400);

    const problemsFor = files => {
      const problems = [];
      if (files.length > maxFiles) problems.push(`Envie no máximo ${maxFiles} arquivos por vez.`);
      files.forEach(file => {
        const extension = file.name.split('.').pop()?.toLowerCase() || '';
        if (!ACCEPTED_EXTENSIONS.includes(extension)) problems.push(`${file.name}: formato não aceito.`);
        else if (file.size > maxBytes) problems.push(`${file.name}: acima de ${formatSize(maxBytes)}.`);
      });
      return problems;
    };

    const update = () => {
      const files = [...(input.files || [])];
      const problems = problemsFor(files);
      list.replaceChildren(...files.map(file => {
        const item = document.createElement('li');
        const extension = file.name.split('.').pop()?.toLowerCase() || '';
        if (!ACCEPTED_EXTENSIONS.includes(extension) || file.size > maxBytes) item.classList.add('is-invalid');
        const name = document.createElement('span');
        name.textContent = file.name;
        name.title = file.name;
        const size = document.createElement('span');
        size.textContent = formatSize(file.size);
        item.append(name, size);
        return item;
      }));
      list.hidden = files.length === 0;
      if (error) {
        error.textContent = problems.join(' ');
        error.hidden = problems.length === 0;
      }
      input.setCustomValidity(problems.join(' '));
      if (submit instanceof HTMLButtonElement) {
        submit.textContent = files.length > 1 ? `Importar ${files.length} arquivos` : 'Importar arquivos';
      }
    };
    input.addEventListener('change', update);
    company?.addEventListener('change', update);
    ['dragenter', 'dragover'].forEach(eventName => dropzone.addEventListener(eventName, event => {
      event.preventDefault();
      dropzone.classList.add('is-dragging');
    }));
    ['dragleave', 'drop'].forEach(eventName => dropzone.addEventListener(eventName, event => {
      event.preventDefault();
      dropzone.classList.remove('is-dragging');
    }));
    dropzone.addEventListener('drop', event => {
      if (!event.dataTransfer?.files?.length) return;
      input.files = event.dataTransfer.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    form.addEventListener('submit', event => {
      const company = form.querySelector('select[name="company"]');
      if (company instanceof HTMLSelectElement && !company.value) {
        event.preventDefault();
        company.setAttribute('aria-invalid', 'true');
        const companySearch = form.querySelector('[data-company-search]');
        if (companySearch instanceof HTMLInputElement && !companySearch.hidden) {
          companySearch.setAttribute('aria-invalid', 'true');
          companySearch.focus();
        } else {
          company.focus();
        }
        return;
      }
      if (!input.files?.length) {
        event.preventDefault();
        const message = 'Selecione ao menos um arquivo OFX, CSV, XLSX ou PDF.';
        input.setCustomValidity(message);
        if (error) {
          error.textContent = message;
          error.hidden = false;
        }
        input.focus();
        return;
      }
      if (problemsFor([...input.files]).length) {
        event.preventDefault();
        update();
        input.focus();
        return;
      }
      if (submit instanceof HTMLButtonElement) {
        submit.disabled = true;
        submit.setAttribute('aria-busy', 'true');
        submit.textContent = 'Enviando…';
      }
    });
    update();
  });

  document.querySelectorAll('[data-reconciliation-upload]').forEach(form => {
    const company = form.querySelector('select[name="company"]');
    const account = form.querySelector('[data-financial-account-select]');
    if (!(company instanceof HTMLSelectElement) || !(account instanceof HTMLSelectElement)) return;
    const help = form.querySelector('[data-financial-account-help]');
    const updateAccounts = () => {
      const companyId = company.value;
      if (companyId) {
        company.removeAttribute('aria-invalid');
        form.querySelector('[data-company-search]')?.removeAttribute('aria-invalid');
      }
      let available = 0;
      [...account.options].forEach(option => {
        const ownerId = option.dataset.companyId;
        const permitted = !ownerId || !companyId || ownerId === companyId;
        option.hidden = !permitted;
        option.disabled = !permitted;
        if (permitted && ownerId) available += 1;
      });
      if (account.selectedOptions[0]?.disabled) account.value = '';
      account.disabled = Boolean(companyId) && available === 0;
      if (!help) return;
      help.textContent = !companyId ? '' : available
        ? `${available} conta${available === 1 ? '' : 's'} da empresa`
        : 'Empresa sem conta cadastrada';
    };
    company.addEventListener('change', updateAccounts);
    updateAccounts();
  });

  // Running imports report progress in place; a finished run reloads the page so the
  // metrics and row actions reflect the final state, unless someone is mid-task.
  const liveRuns = [...document.querySelectorAll('tr[data-run-status-url]')]
    .filter(row => ['waiting', 'processing'].includes(row.dataset.runState));
  if (liveRuns.length) {
    const busy = () => {
      const active = document.activeElement;
      return active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement
        || active instanceof HTMLSelectElement
        || [...document.querySelectorAll('[data-modal]')].some(modal => !modal.hidden);
    };
    let finished = false;
    const poll = async () => {
      if (document.hidden) { window.setTimeout(poll, 4000); return; }
      await Promise.all(liveRuns.map(async row => {
        try {
          const response = await fetch(row.dataset.runStatusUrl, { headers: { Accept: 'application/json' }, credentials: 'same-origin' });
          if (!response.ok) return;
          const run = await response.json();
          const progress = row.querySelector('[data-run-progress]');
          const label = row.querySelector('[data-run-state-label]');
          if (progress) progress.textContent = `${run.processed}/${run.total ?? '?'}`;
          if (label) label.textContent = run.state_label;
          if (!['waiting', 'processing'].includes(run.state)) finished = true;
        } catch (_error) { /* next tick retries */ }
      }));
      if (finished && !busy()) { window.location.reload(); return; }
      window.setTimeout(poll, 4000);
    };
    window.setTimeout(poll, 4000);
  }

  document.querySelectorAll('[data-reconciliation-confirm-form]').forEach(form => {
    const entry = form.querySelector('select[name="entry_id"]');
    const amount = form.querySelector('input[name="amount_brl"]');
    const limit = form.querySelector('[data-reconciliation-allocation-limit]');
    if (!(entry instanceof HTMLSelectElement) || !(amount instanceof HTMLInputElement)) return;
    const updateLimit = () => {
      const maximum = entry.selectedOptions[0]?.dataset.allocationLimit;
      if (!maximum) return;
      amount.max = maximum;
      const current = Number(amount.value.replace(',', '.'));
      if (!Number.isFinite(current) || current <= 0 || current > Number(maximum)) amount.value = maximum;
      if (limit) limit.textContent = `Você pode alocar até R$ ${maximum} neste lançamento.`;
    };
    entry.addEventListener('change', updateLimit);
    updateLimit();
  });

  document.querySelectorAll('[data-reconciliation-mapping-form]').forEach(form => {
    const selects = Object.fromEntries(
      [...form.querySelectorAll('[data-mapping-field]')].map(select => [select.dataset.mappingField, select]),
    );
    const signedAmount = selects.amount;
    const debit = selects.debit;
    const credit = selects.credit;
    const feedback = form.querySelector('[data-mapping-strategy-error]');
    if (!(signedAmount instanceof HTMLSelectElement)
      || !(debit instanceof HTMLSelectElement)
      || !(credit instanceof HTMLSelectElement)) return;

    const validateStrategy = () => {
      const hasSignedAmount = Boolean(signedAmount.value);
      const hasSplitAmount = Boolean(debit.value || credit.value);
      const message = !hasSignedAmount && !hasSplitAmount
        ? 'Escolha Valor com sinal ou pelo menos uma coluna de débito/crédito.'
        : hasSignedAmount && hasSplitAmount
          ? 'Use uma única estratégia: Valor com sinal ou Débito/Crédito.'
          : '';
      signedAmount.setCustomValidity(message);
      signedAmount.toggleAttribute('aria-invalid', Boolean(message));
      if (feedback instanceof HTMLElement) {
        feedback.textContent = message;
        feedback.hidden = !message;
      }
      return !message;
    };
    [signedAmount, debit, credit].forEach(select => select.addEventListener('change', validateStrategy));
    form.addEventListener('submit', event => {
      if (validateStrategy()) return;
      event.preventDefault();
      signedAmount.focus();
      signedAmount.reportValidity();
    });
  });
})();
