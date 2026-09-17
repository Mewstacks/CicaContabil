(() => {
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

  document.querySelectorAll('[data-reconciliation-dropzone]').forEach(dropzone => {
    const input = dropzone.querySelector('input[type=file]');
    const feedback = document.getElementById(`${input.id}-files`);
    if (!input || !feedback) return;
    const describeFiles = files => {
      if (!files.length) return 'Nenhum arquivo selecionado.';
      const names = [...files].map(file => file.name).join(', ');
      return `${files.length} arquivo${files.length === 1 ? '' : 's'} selecionado${files.length === 1 ? '' : 's'}: ${names}`;
    };
    const update = () => { feedback.textContent = describeFiles(input.files); };
    input.addEventListener('change', update);
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
  });

  document.querySelectorAll('[data-reconciliation-upload]').forEach(form => {
    const company = form.querySelector('select[name="company"]');
    const account = form.querySelector('[data-financial-account-select]');
    if (!(company instanceof HTMLSelectElement) || !(account instanceof HTMLSelectElement)) return;
    const help = account.closest('.field')?.querySelector('.field-help');
    const updateAccounts = () => {
      const companyId = company.value;
      let available = 0;
      [...account.options].forEach(option => {
        const ownerId = option.dataset.companyId;
        const permitted = !ownerId || !companyId || ownerId === companyId;
        option.hidden = !permitted;
        option.disabled = !permitted;
        if (permitted && ownerId) available += 1;
      });
      if (account.selectedOptions[0]?.disabled) account.value = '';
      if (!help) return;
      help.textContent = companyId
        ? `${available} conta${available === 1 ? '' : 's'} financeira${available === 1 ? '' : 's'} disponível${available === 1 ? '' : 'is'} para a empresa.`
        : 'Escolha a empresa para restringir as contas disponíveis.';
    };
    company.addEventListener('change', updateAccounts);
    updateAccounts();
  });

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
})();
