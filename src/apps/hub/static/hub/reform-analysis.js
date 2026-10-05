(() => {
  const form = document.querySelector('[data-radar-analysis-form]');
  if (!(form instanceof HTMLFormElement)) return;
  const button = form.querySelector('button[type="submit"]');
  const idleLabel = button instanceof HTMLButtonElement ? button.textContent : '';
  const busyLabel = button instanceof HTMLButtonElement
    ? button.dataset.busyLabel || 'Criando atividade…'
    : '';
  const filter = form.querySelector('[data-company-filter]');
  const company = form.querySelector('#id_company');
  const count = form.querySelector('[data-company-count]');
  const companyOptions = company instanceof HTMLSelectElement
    ? [...company.options].filter(option => option.value)
    : [];
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
  const updateCompanyOptions = () => {
    if (!(filter instanceof HTMLInputElement) || !(company instanceof HTMLSelectElement)) return;
    const query = normalize(filter.value.trim());
    let visible = 0;
    companyOptions.forEach(option => {
      const matches = !query || normalize(option.textContent || '').includes(query);
      option.hidden = !matches;
      option.disabled = !matches;
      if (matches) visible += 1;
    });
    if (company.selectedOptions[0]?.disabled) company.value = '';
    if (count instanceof HTMLElement) {
      count.textContent = query
        ? `${visible} empresa${visible === 1 ? '' : 's'} encontrada${visible === 1 ? '' : 's'}`
        : `${companyOptions.length} empresa${companyOptions.length === 1 ? '' : 's'} na sua carteira`;
    }
  };
  if (filter instanceof HTMLInputElement && company instanceof HTMLSelectElement) {
    filter.addEventListener('input', updateCompanyOptions);
    updateCompanyOptions();
  }
  let dirty = false;
  let submitting = false;
  form.addEventListener('input', event => {
    if (event.target !== filter) dirty = true;
  });
  form.addEventListener('change', event => {
    if (event.target !== filter) dirty = true;
  });
  form.addEventListener('submit', () => {
    if (!form.checkValidity()) return;
    submitting = true;
    form.setAttribute('aria-busy', 'true');
    if (button instanceof HTMLButtonElement) {
      button.disabled = true;
      button.textContent = busyLabel;
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
      button.textContent = idleLabel;
    }
  });
})();
