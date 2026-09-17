let lastTrigger = null;
const dirtyForms = new Set();

const focusables = (root) =>
  [...root.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])')]
    .filter((item) => item.getClientRects().length && !item.closest('[hidden],[inert]') && item.type !== 'hidden');

const closeModal = (modal) => {
  if (!modal) return;
  modal.hidden = true;
  modal.querySelectorAll('form').forEach(form => dirtyForms.delete(form));
  document.querySelectorAll('[data-modal-inert]').forEach((item) => {
    item.inert = false;
    item.removeAttribute('data-modal-inert');
  });
  document.body.style.overflow = '';
  lastTrigger?.focus();
};

const openModal = (modal, trigger) => {
  if (!modal) return;
  lastTrigger = trigger;
  modal.hidden = false;
  let branch = modal;
  while (branch.parentElement && branch !== document.body) {
    [...branch.parentElement.children].forEach((item) => {
      if (item !== branch && !item.inert && !['SCRIPT', 'STYLE'].includes(item.tagName)) {
        item.inert = true;
        item.setAttribute('data-modal-inert', '');
      }
    });
    branch = branch.parentElement;
  }
  document.body.style.overflow = 'hidden';
  const error = modal.querySelector('[data-form-errors], [aria-invalid="true"]');
  const items = focusables(modal);
  const primaryField = items.find(item => item.matches('input, select, textarea'));
  (error || primaryField || items[0])?.focus();
};

document.querySelectorAll('[data-modal-open]').forEach((trigger) => {
  trigger.addEventListener('click', () => openModal(document.getElementById(trigger.dataset.modalOpen), trigger));
});

document.querySelectorAll('[data-modal-close]').forEach((button) =>
  button.addEventListener('click', () => closeModal(button.closest('[data-modal]'))),
);

document.querySelectorAll('[data-modal]').forEach((modal) => {
  modal.addEventListener('click', (event) => {
    if (event.target === modal) closeModal(modal);
  });
  modal.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeModal(modal);
      return;
    }
    if (event.key !== 'Tab') return;
    const items = focusables(modal);
    if (!items.length) return;
    const first = items[0];
    const last = items.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
});

const closePopover = (trigger, panel) => {
  trigger.setAttribute('aria-expanded', 'false');
  panel.hidden = true;
};

document.querySelectorAll('[data-popover-toggle]').forEach((trigger) => {
  const panel = document.getElementById(trigger.dataset.popoverToggle);
  if (!panel) return;
  trigger.addEventListener('click', () => {
    const open = trigger.getAttribute('aria-expanded') === 'true';
    trigger.setAttribute('aria-expanded', String(!open));
    panel.hidden = open;
    if (!open) requestAnimationFrame(() => focusables(panel)[0]?.focus());
  });
  panel.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    closePopover(trigger, panel);
    trigger.focus();
  });
  document.addEventListener('click', (event) => {
    if (!trigger.contains(event.target) && !panel.contains(event.target)) closePopover(trigger, panel);
  });
});

const menuButton = document.querySelector('[data-menu-toggle]');
const mobileNav = document.getElementById('mobile-nav');
if (mobileNav) {
  const activeHref = document.querySelector('.rail-nav a[aria-current="page"]')?.getAttribute('href');
  mobileNav.querySelectorAll('a').forEach((link) => {
    if (link.getAttribute('href') === activeHref) link.setAttribute('aria-current', 'page');
  });
}
if (menuButton && mobileNav) {
  const closeMenu = () => {
    menuButton.setAttribute('aria-expanded', 'false');
    mobileNav.hidden = true;
  };
  menuButton.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') === 'true';
    menuButton.setAttribute('aria-expanded', String(!open));
    mobileNav.hidden = open;
    if (!open) focusables(mobileNav)[0]?.focus();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !mobileNav.hidden) {
      closeMenu();
      menuButton.focus();
    }
  });
  mobileNav.addEventListener('click', (event) => {
    if (event.target.closest('a')) closeMenu();
  });
  document.addEventListener('click', (event) => {
    if (!mobileNav.contains(event.target) && !menuButton.contains(event.target)) closeMenu();
  });
}

const firstError = document.querySelector('[data-form-errors]');
if (firstError) firstError.focus();

const openIntegrationDetails = (target) => {
  if (!(target instanceof HTMLDetailsElement)) return;
  target.open = true;
  requestAnimationFrame(() => target.querySelector('summary')?.focus());
};

document.querySelectorAll('[data-open-details]').forEach((link) => {
  link.addEventListener('click', () => {
    const target = document.querySelector(link.getAttribute('href'));
    openIntegrationDetails(target);
  });
});

if (window.location.hash) openIntegrationDetails(document.querySelector(window.location.hash));

const invalidField = document.querySelector('[data-focus-error] input, [data-focus-error] select');
if (invalidField) invalidField.focus();

let filterTimer;
let filterController;
let filterRequest = 0;
const enhanceAutoFilter = (form) => {
  if (!form || form.dataset.enhanced) return;
  form.dataset.enhanced = 'true';
  const refresh = async (url, push = true) => {
    const panel = form.closest('.registry-panel');
    if (!panel) return;
    filterController?.abort();
    const controller = new AbortController();
    filterController = controller;
    const requestId = ++filterRequest;
    const focusedId = document.activeElement?.id;
    const selectionStart = document.activeElement instanceof HTMLInputElement
      ? document.activeElement.selectionStart
      : null;
    panel.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error('filter request failed');
      const documentFragment = new DOMParser().parseFromString(await response.text(), 'text/html');
      if (requestId !== filterRequest || !panel.isConnected) return;
      const nextPanel = documentFragment.querySelector('.registry-panel');
      if (!nextPanel) throw new Error('filter panel missing');
      panel.replaceWith(nextPanel);
      if (push && String(url) !== window.location.href) history.pushState({}, '', url);
      enhanceAutoFilter(nextPanel.querySelector('[data-auto-filter]'));
      if (focusedId) {
        const focusedField = document.getElementById(focusedId);
        focusedField?.focus();
        if (focusedField instanceof HTMLInputElement && selectionStart !== null) {
          focusedField.setSelectionRange(selectionStart, selectionStart);
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError' && requestId === filterRequest) window.location.assign(url);
    } finally {
      panel.removeAttribute('aria-busy');
    }
  };
  const submit = () => {
    const url = new URL(form.action || window.location.href);
    const fields = new FormData(form);
    url.search = new URLSearchParams(
      [...fields].filter(([, value]) => value !== '').map(([key, value]) => [key, String(value)]),
    ).toString();
    refresh(url);
  };
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    submit();
  });
  form.querySelectorAll('select').forEach((field) => field.addEventListener('change', submit));
  form.querySelectorAll('input[type="search"]').forEach((field) => {
    field.addEventListener('input', () => {
      window.clearTimeout(filterTimer);
      filterController?.abort();
      filterRequest += 1;
      filterTimer = window.setTimeout(submit, 300);
    });
  });
  form.querySelector('[data-filter-clear]')?.addEventListener('click', (event) => {
    event.preventDefault();
    refresh(new URL(event.currentTarget.href, window.location.origin));
  });
};

document.querySelectorAll('[data-auto-filter]').forEach(enhanceAutoFilter);
window.addEventListener('popstate', () => {
  if (!document.querySelector('[data-auto-filter]')) return;
  window.clearTimeout(filterTimer);
  filterController?.abort();
  // A normal GET also restores controls, permissions and all page-level handlers.
  window.location.reload();
});

document.querySelectorAll('[data-company-picker]').forEach((picker) => {
  const select = picker.querySelector('select');
  const search = picker.querySelector('[data-company-search]');
  const options = picker.querySelector('[data-company-options]');
  if (!(select instanceof HTMLSelectElement) || !(search instanceof HTMLInputElement) || !options) return;
  const companies = [...select.options]
    .filter((option) => option.value)
    .map((option) => ({ label: option.text, value: option.value }));
  select.hidden = true;
  search.required = select.required;
  select.required = false;
  search.hidden = false;
  search.id = `${select.id}-search`;
  picker.querySelector('label')?.setAttribute('for', search.id);
  options.id = `${select.id}-options`;
  search.setAttribute('role', 'combobox');
  search.setAttribute('aria-autocomplete', 'list');
  search.setAttribute('aria-controls', options.id);
  const validate = () => search.setCustomValidity(
    search.required && !select.value ? 'Escolha uma empresa da lista.' : '',
  );
  validate();
  const close = () => {
    options.hidden = true;
    search.setAttribute('aria-expanded', 'false');
  };
  const choose = (company) => {
    select.value = company.value;
    search.value = company.label;
    validate();
    close();
    search.focus();
  };
  const selected = companies.find((company) => company.value === select.value);
  if (selected) search.value = selected.label;
  const render = () => {
    const query = search.value.trim().toLocaleLowerCase('pt-BR');
    const results = companies.filter((company) => company.label.toLocaleLowerCase('pt-BR').includes(query)).slice(0, 8);
    options.replaceChildren();
    results.forEach((company) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.role = 'option';
      item.setAttribute('aria-selected', String(company.value === select.value));
      item.textContent = company.label;
      item.addEventListener('click', () => choose(company));
      options.append(item);
    });
    options.hidden = !results.length;
    search.setAttribute('aria-expanded', String(Boolean(results.length)));
  };
  search.addEventListener('input', () => {
    select.value = '';
    validate();
    render();
  });
  search.addEventListener('focus', render);
  search.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') close();
    if (event.key === 'ArrowDown' && !options.hidden) {
      event.preventDefault();
      options.querySelector('button')?.focus();
    }
  });
  options.addEventListener('keydown', (event) => {
    const items = [...options.querySelectorAll('button')];
    const index = items.indexOf(document.activeElement);
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      search.focus();
      close();
    } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      items[(index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length]?.focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (!picker.contains(event.target)) close();
  });
});

document.querySelectorAll('.ofx-file-picker input[type="file"]').forEach((input) => {
  input.addEventListener('change', () => {
    const name = input.closest('.ofx-file-picker')?.querySelector('[data-file-name]');
    if (name) name.textContent = input.files?.[0]?.name || 'Selecionar arquivo';
  });
});

document.querySelectorAll('[data-dominio-sync-form]').forEach((form) => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"]');
    if (!(button instanceof HTMLButtonElement)) return;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.textContent = 'Atualizando…';
  });
});

document.querySelectorAll('[data-imap-connect]').forEach((form) => {
  let dirty = false;
  let submitting = false;
  form.addEventListener('input', () => { dirty = true; });
  window.addEventListener('beforeunload', (event) => {
    if (!dirty || submitting) return;
    event.preventDefault();
    event.returnValue = '';
  });
  form.addEventListener('submit', () => {
    submitting = true;
    const button = form.querySelector('button[type="submit"]');
    if (!(button instanceof HTMLButtonElement)) return;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.textContent = 'Testando caixa…';
    const status = form.querySelector('[data-imap-status]');
    if (status) status.textContent = 'Testando a conexão IMAP…';
  });
});

document.querySelectorAll('[data-oauth-app-form]').forEach((form) => {
  let dirty = false;
  let submitting = false;
  form.addEventListener('input', () => { dirty = true; });
  window.addEventListener('beforeunload', (event) => {
    if (!dirty || submitting) return;
    event.preventDefault();
    event.returnValue = '';
  });
  form.addEventListener('submit', () => {
    submitting = true;
    const button = form.querySelector('button[type="submit"]');
    if (button instanceof HTMLButtonElement) {
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      button.textContent = 'Salvando aplicativo…';
    }
    const status = form.querySelector('[data-oauth-status]');
    if (status) status.textContent = 'Salvando aplicativo…';
  });
});

document.querySelectorAll('[data-modal] form input[name="action"][value="lifecycle"]').forEach((action) => {
  const form = action.closest('form');
  const state = form?.querySelector('select[name="state"]');
  const confirmation = form?.querySelector('[data-lifecycle-confirmation]');
  const checkbox = confirmation?.querySelector('input[name="confirm_lifecycle"]');
  if (!(state instanceof HTMLSelectElement) || !(checkbox instanceof HTMLInputElement)) return;
  const updateConfirmation = () => {
    const destructive = ['suspended', 'archived'].includes(state.value);
    confirmation.hidden = !destructive;
    checkbox.disabled = !destructive;
    if (!destructive) checkbox.checked = false;
  };
  state.addEventListener('change', updateConfirmation);
  updateConfirmation();
});

document.querySelectorAll('[data-guide-bulk-form]').forEach((form) => {
  const selectAll = form.querySelector('[data-guide-select-all]');
  const targets = [...form.querySelectorAll('[data-guide-target]')];
  const count = form.querySelector('[data-guide-selection-count]');
  const submit = form.querySelector('[data-guide-bulk-submit]');
  const actions = form.querySelector('[data-guide-bulk-actions]');
  if (!(selectAll instanceof HTMLInputElement) || !(submit instanceof HTMLButtonElement)) return;

  const update = () => {
    const selected = targets.filter((target) => target.checked).length;
    if (actions) actions.hidden = selected === 0;
    selectAll.checked = selected === targets.length && targets.length > 0;
    selectAll.indeterminate = selected > 0 && selected < targets.length;
    if (count) {
      count.textContent = selected
        ? `${selected} selecionada${selected === 1 ? '' : 's'}`
        : '0 selecionadas';
    }
  };

  selectAll.addEventListener('change', () => {
    targets.forEach((target) => { target.checked = selectAll.checked; });
    update();
  });
  targets.forEach((target) => target.addEventListener('change', update));
  form.addEventListener('submit', (event) => {
    if (!targets.some((target) => target.checked)) {
      event.preventDefault();
      if (count) count.textContent = 'Selecione ao menos uma linha antes de revisar o consumo.';
      selectAll.focus();
      return;
    }
    submit.disabled = true;
    submit.setAttribute('aria-busy', 'true');
    submit.textContent = 'Abrindo revisão…';
  });
  update();
});

document.querySelectorAll('[data-nfse-bulk-form]').forEach((form) => {
  const selectAll = form.querySelector('[data-nfse-select-all]');
  const targets = [...form.querySelectorAll('[data-nfse-target]')];
  const count = form.querySelector('[data-nfse-selection-count]');
  if (!(selectAll instanceof HTMLInputElement)) return;

  const update = () => {
    const selected = targets.filter((target) => target.checked).length;
    selectAll.checked = selected === targets.length && targets.length > 0;
    selectAll.indeterminate = selected > 0 && selected < targets.length;
    if (count) count.textContent = selected
      ? `${selected} empresa${selected === 1 ? '' : 's'} selecionada${selected === 1 ? '' : 's'}.`
      : 'Nenhuma empresa selecionada.';
  };

  selectAll.addEventListener('change', () => {
    targets.forEach((target) => { target.checked = selectAll.checked; });
    update();
  });
  targets.forEach((target) => target.addEventListener('change', update));
  form.addEventListener('submit', (event) => {
    if (!targets.some((target) => target.checked)) {
      event.preventDefault();
      if (count) count.textContent = 'Selecione ao menos uma empresa.';
      selectAll.focus();
      return;
    }
    if (form.dataset.submitting) {
      event.preventDefault();
      return;
    }
    form.dataset.submitting = 'true';
    // Disabled submitters are excluded from native form serialization.
    if (event.submitter?.name) {
      const action = document.createElement('input');
      action.type = 'hidden';
      action.name = event.submitter.name;
      action.value = event.submitter.value;
      form.append(action);
    }
    form.querySelectorAll('button[type="submit"]').forEach((button) => {
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
    });
  });
  update();
});

document.querySelectorAll('#parcelamento-bulk-form').forEach((form) => {
  const targets = [...form.querySelectorAll('.parcelamento-company-check')];
  const selectAll = form.querySelector('#parcelamento-select-all');
  const summary = form.querySelector('#parcelamento-selection-summary');
  const submit = form.querySelector('#parcelamento-submit');
  const approved = form.querySelector('#parcelamento-approved-overage');
  if (!(selectAll instanceof HTMLInputElement)
      || !(submit instanceof HTMLButtonElement)
      || !(approved instanceof HTMLInputElement)) return;
  const weight = Number(form.dataset.tokensPerOperation || 0);
  const included = Number(form.dataset.includedRemaining || 0);
  const price = Number(form.dataset.tokenPriceCents || 0);
  const update = () => {
    const count = targets.filter((target) => target.checked).length;
    const tokens = count * weight;
    const overage = Math.max(0, tokens - included) * price;
    approved.value = String(overage);
    if (summary) {
      const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
      summary.textContent = count
        ? `${count} empresa(s) · ${tokens} tokens · excedente ${currency.format(overage / 100)}`
        : 'Nenhuma empresa selecionada';
    }
    selectAll.checked = count > 0 && count === targets.length;
    selectAll.indeterminate = count > 0 && count < targets.length;
  };
  selectAll.addEventListener('change', () => {
    targets.forEach((target) => { target.checked = selectAll.checked; });
    update();
  });
  targets.forEach((target) => target.addEventListener('change', update));
  form.addEventListener('submit', (event) => {
    if (targets.some((target) => target.checked)) return;
    event.preventDefault();
    if (summary) summary.textContent = 'Marque ao menos uma empresa antes de consultar.';
    selectAll.focus();
  });
  update();
});


// Restore the submitted dialog after server validation, keeping its entered values.
document.querySelectorAll('[data-modal]').forEach((modal) => {
  if (modal.hidden && !modal.querySelector('.field-error, [data-form-errors], .errorlist')) return;
  const trigger = [...document.querySelectorAll('[data-modal-open]')]
    .find(item => item.dataset.modalOpen === modal.id);
  openModal(modal, trigger);
});

// Large permission lists keep selections when the visible search is narrowed.
document.querySelectorAll('.scope-picker').forEach((picker, index) => {
  const labels = [...picker.querySelectorAll('.scope-options label')];
  if (labels.length <= 12) return;
  const search = document.createElement('input');
  search.type = 'search';
  search.name = `scope_search_${index}`;
  search.className = 'scope-search';
  search.id = `scope-search-${index}`;
  search.autocomplete = 'off';
  search.placeholder = 'Buscar empresa…';
  search.setAttribute('aria-label', 'Buscar nas empresas permitidas');
  const summary = document.createElement('p');
  summary.className = 'scope-summary';
  summary.setAttribute('aria-live', 'polite');
  const list = picker.querySelector('.scope-options');
  list.before(search, summary);
  const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
  const update = () => {
    const query = normalize(search.value.trim());
    let visible = 0;
    let selected = 0;
    labels.forEach(label => {
      const match = normalize(label.textContent).includes(query);
      label.hidden = !match;
      if (match) visible += 1;
      if (label.querySelector('input')?.checked) selected += 1;
    });
    summary.textContent = `${selected} selecionadas · ${visible} de ${labels.length} visíveis`;
  };
  search.addEventListener('input', update);
  list.addEventListener('change', update);
  update();
});

document.querySelectorAll('[data-modal] form, .team-form, .review-detail-panel form').forEach(form => {
  form.addEventListener('input', event => {
    if (event.target.type !== 'search') dirtyForms.add(form);
  });
  form.addEventListener('submit', () => dirtyForms.delete(form));
});
window.addEventListener('beforeunload', event => {
  if (!dirtyForms.size) return;
  event.preventDefault();
  event.returnValue = '';
});
