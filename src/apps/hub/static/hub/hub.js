let lastTrigger = null;
const dirtyForms = new Set();

const focusables = (root) =>
  [...root.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])')]
    .filter((item) => item.getClientRects().length && !item.closest('[hidden],[inert]') && item.type !== 'hidden');

const closeModal = (modal) => {
  if (!modal) return;
  modal.dispatchEvent(new CustomEvent('cica:modal-closing'));
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

document.querySelectorAll('[data-modal-invalid]').forEach((modal) => {
  const trigger = document.querySelector(`[data-modal-open="${modal.id}"]`);
  openModal(modal, trigger);
});

document.querySelectorAll('[data-certificate-files]').forEach((input) => {
  const zone = input.closest('.certificate-drop-zone');
  const form = input.closest('[data-certificate-import-form]');
  if (form) form.dataset.certificateQueueReady = 'true';
  const status = form?.querySelector('[data-certificate-file-count]');
  const updateCount = () => {
    if (!status) return;
    const count = input.files?.length || 0;
    status.textContent = count
      ? `${count} arquivo${count === 1 ? '' : 's'} selecionado${count === 1 ? '' : 's'} para validação.`
      : 'Nenhum arquivo selecionado.';
  };
  input.addEventListener('change', updateCount);
  ['dragenter', 'dragover'].forEach(type => input.addEventListener(type, () => zone?.classList.add('is-dragging')));
  ['dragleave', 'drop'].forEach(type => input.addEventListener(type, () => zone?.classList.remove('is-dragging')));
  let activeController = null;
  let cancelPendingChoice = null;
  let cancelled = false;

  const queue = form?.querySelector('[data-certificate-queue]');
  const queueStatus = form?.querySelector('[data-certificate-queue-status]');
  const queueCancel = form?.querySelector('[data-certificate-queue-cancel]');
  const retry = form?.querySelector('[data-certificate-queue-retry]');
  const stopQueue = (message = 'Importação cancelada.') => {
    if (!form?.dataset.queueRunning) return;
    cancelled = true;
    activeController?.abort();
    cancelPendingChoice?.();
    cancelPendingChoice = null;
    if (retry) retry.hidden = true;
    if (queueStatus) queueStatus.textContent = message;
    form.removeAttribute('aria-busy');
    delete form.dataset.queueRunning;
    const submit = form.querySelector('button[type="submit"]');
    if (submit instanceof HTMLButtonElement) {
      submit.disabled = false;
      submit.textContent = 'Importar e vincular';
    }
  };
  queueCancel?.addEventListener('click', () => stopQueue());
  form?.closest('[data-modal]')?.addEventListener('cica:modal-closing', () => stopQueue());

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    if (form.dataset.queueRunning) return;
    const files = [...(input.files || [])];
    if (!files.length) return;
    cancelled = false;
    form.dataset.queueRunning = 'true';
    form.setAttribute('aria-busy', 'true');
    const submit = form.querySelector('button[type="submit"]');
    if (submit instanceof HTMLButtonElement) {
      submit.disabled = true;
      submit.textContent = 'Importando fila…';
    }

    const queueProgress = form.querySelector('[data-certificate-queue-progress]');
    const queueResults = form.querySelector('[data-certificate-queue-results]');
    const retryTitle = form.querySelector('[data-certificate-retry-title]');
    const retryPosition = form.querySelector('[data-certificate-retry-position]');
    const retryMessage = form.querySelector('[data-certificate-retry-message]');
    const retryPasswordFields = form.querySelector('[data-certificate-retry-password-fields]');
    const retryPassword = form.querySelector('[data-certificate-retry-password]');
    const retryError = form.querySelector('[data-certificate-retry-error]');
    const retrySubmit = form.querySelector('[data-certificate-retry-submit]');
    const retrySkip = form.querySelector('[data-certificate-retry-skip]');
    const commonPassword = form.querySelector('[name="common_password"]')?.value || '';
    const csrf = form.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
    if (queue) queue.hidden = false;
    if (queueProgress) queueProgress.max = files.length;

    const upload = async (file, password, position) => {
      const payload = new FormData();
      payload.append('csrfmiddlewaretoken', csrf);
      payload.append('pfx_files', file);
      payload.append('common_password', password);
      payload.append('queue_upload', '1');
      payload.append('queue_position', String(position));
      activeController = new AbortController();
      const response = await fetch(form.action || window.location.href, {
        method: 'POST',
        body: payload,
        headers: { 'X-CICA-CERTIFICATE-QUEUE': '1' },
        signal: activeController.signal,
      });
      const responseText = await response.text();
      let body;
      try {
        body = JSON.parse(responseText);
      } catch {
        throw new Error(response.status >= 500
          ? 'O serviço oscilou. Tente este arquivo novamente.'
          : 'Sua sessão expirou. Atualize a página e entre novamente.');
      } finally {
        activeController = null;
      }
      if (!response.ok) throw new Error(body.error || 'Não foi possível enviar o certificado.');
      return body.result;
    };
    const askPassword = (position, file) => new Promise(resolve => {
      retry.hidden = false;
      retry.scrollIntoView({ block: 'nearest' });
      retryMessage.textContent = 'Informe a senha para continuar.';
      retryPasswordFields.hidden = false;
      retryError.hidden = true;
      retryPosition.textContent = `${position} de ${files.length}`;
      retryTitle.textContent = file.name;
      retryPassword.value = '';
      retryPassword.focus();
      const finish = value => {
        retrySubmit.removeEventListener('click', submitPassword);
        retrySkip.removeEventListener('click', skipFile);
        retryPassword.removeEventListener('keydown', submitOnEnter);
        cancelPendingChoice = null;
        resolve(value);
      };
      const submitPassword = () => {
        if (!retryPassword.value) {
          retryError.textContent = 'Digite a senha para tentar novamente.';
          retryError.hidden = false;
          retryPassword.focus();
          return;
        }
        finish(retryPassword.value);
      };
      const skipFile = () => finish(null);
      const submitOnEnter = keyEvent => {
        if (keyEvent.key !== 'Enter') return;
        keyEvent.preventDefault();
        submitPassword();
      };
      retrySubmit.addEventListener('click', submitPassword);
      retrySkip.addEventListener('click', skipFile);
      retryPassword.addEventListener('keydown', submitOnEnter);
      cancelPendingChoice = skipFile;
    });
    const askUploadRetry = (position, file, message) => new Promise(resolve => {
      retry.hidden = false;
      retry.scrollIntoView({ block: 'nearest' });
      retryPosition.textContent = `${position} de ${files.length}`;
      retryTitle.textContent = file.name;
      retryMessage.textContent = message;
      retryPasswordFields.hidden = true;
      retryError.hidden = true;
      retrySubmit.textContent = 'Tentar novamente';
      const finish = value => {
        retrySubmit.removeEventListener('click', tryAgain);
        retrySkip.removeEventListener('click', skipFile);
        cancelPendingChoice = null;
        resolve(value);
      };
      const tryAgain = () => finish(true);
      const skipFile = () => finish(false);
      retrySubmit.addEventListener('click', tryAgain);
      retrySkip.addEventListener('click', skipFile);
      retrySubmit.focus();
      cancelPendingChoice = skipFile;
    });
    const showResult = (position, file, result) => {
      let row = queueResults.querySelector(`[data-queue-position="${position}"]`);
      if (!row) {
        row = document.createElement('li');
        row.dataset.queuePosition = String(position);
        const filename = document.createElement('span');
        const status = document.createElement('strong');
        row.append(filename, status);
        queueResults.append(row);
      }
      row.querySelector('span').textContent = file.name;
      row.className = `is-${result.status}`;
      row.querySelector('strong').textContent = result.status === 'recognized'
        ? 'Importado'
        : result.reason === 'open_failed' ? 'Precisa de senha' : 'Conferir';
    };

    try {
      for (let index = 0; index < files.length; index += 1) {
        if (cancelled) break;
        const position = index + 1;
        queueStatus.textContent = `Conferindo arquivo ${position} de ${files.length}…`;
        let result = null;
        while (!cancelled && result === null) {
          try {
            result = await upload(files[index], commonPassword, position);
          } catch (error) {
            if (cancelled || error.name === 'AbortError') break;
            const retryUpload = await askUploadRetry(
              position,
              files[index],
              error.message || 'Não foi possível enviar este arquivo.',
            );
            if (!retryUpload) result = { status: 'unrecognized', reason: 'skipped' };
          }
        }
        if (cancelled || result === null) break;
        showResult(position, files[index], result);
        while (!cancelled && result.reason === 'open_failed') {
          const password = await askPassword(position, files[index]);
          if (password === null) break;
          try {
            result = await upload(files[index], password, position);
          } catch (error) {
            if (cancelled || error.name === 'AbortError') break;
            const retryUpload = await askUploadRetry(
              position,
              files[index],
              error.message || 'Não foi possível enviar este arquivo.',
            );
            if (!retryUpload) break;
            continue;
          }
          showResult(position, files[index], result);
          retryError.textContent = 'Senha incorreta. Confira e tente novamente.';
          retryError.hidden = result.reason !== 'open_failed';
        }
        retry.hidden = true;
        queueProgress.value = position;
      }
      if (cancelled) return;
      queueStatus.textContent = 'Fila concluída. Atualizando o resultado…';
      window.location.reload();
    } catch (error) {
      if (cancelled || error.name === 'AbortError') return;
      queueStatus.textContent = 'A fila foi pausada. Você pode tentar novamente ou fechar.';
      form.removeAttribute('aria-busy');
      delete form.dataset.queueRunning;
      if (submit instanceof HTMLButtonElement) {
        submit.disabled = false;
        submit.textContent = 'Tentar novamente';
      }
    }
  });
});

document.querySelectorAll('[data-password-toggle]').forEach((button) => {
  const input = document.getElementById(button.dataset.passwordToggle);
  if (!(input instanceof HTMLInputElement)) return;
  button.addEventListener('click', () => {
    const reveal = input.type === 'password';
    input.type = reveal ? 'text' : 'password';
    button.textContent = reveal ? 'Ocultar' : 'Mostrar';
    button.setAttribute('aria-pressed', String(reveal));
    input.focus();
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

const firstError = document.querySelector('[data-form-errors], [data-activity-errors]');
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

document.querySelectorAll('[data-company-picker]').forEach((picker, pickerIndex) => {
  const select = picker.querySelector('select');
  const search = picker.querySelector('[data-company-search]');
  const options = picker.querySelector('[data-company-options]');
  if (!(select instanceof HTMLSelectElement) || !(search instanceof HTMLInputElement) || !options) return;
  const companies = [...select.options]
    .filter((option) => option.value)
    .map((option) => ({
      label: option.text,
      search: option.dataset.search || option.text,
      value: option.value,
    }));
  const status = picker.querySelector('[data-company-status]');
  let visibleCompanies = [];
  let activeIndex = -1;
  const controlId = select.id || `company-picker-${pickerIndex}`;
  select.hidden = true;
  search.required = select.required;
  select.required = false;
  search.hidden = false;
  select.id = `${controlId}-native`;
  search.id = controlId;
  picker.querySelector('[data-company-label]')?.setAttribute('for', search.id);
  options.id = `${controlId}-options`;
  search.setAttribute('role', 'combobox');
  search.setAttribute('aria-autocomplete', 'list');
  search.setAttribute('aria-controls', options.id);
  search.setAttribute('aria-expanded', 'false');
  ['aria-describedby', 'aria-invalid'].forEach((attribute) => {
    const value = select.getAttribute(attribute);
    if (value) search.setAttribute(attribute, value);
  });
  if (status) {
    status.id = `${controlId}-status`;
    const descriptions = [search.getAttribute('aria-describedby'), status.id].filter(Boolean);
    search.setAttribute('aria-describedby', descriptions.join(' '));
  }
  const validate = () => search.setCustomValidity(
    search.required && !select.value ? 'Escolha uma empresa da lista.' : '',
  );
  validate();
  const close = () => {
    options.hidden = true;
    search.setAttribute('aria-expanded', 'false');
    search.removeAttribute('aria-activedescendant');
    activeIndex = -1;
  };
  const choose = (company) => {
    select.value = company.value;
    search.value = company.label;
    search.removeAttribute('aria-invalid');
    validate();
    close();
    select.dispatchEvent(new Event('change', { bubbles: true }));
    search.focus();
  };
  const selected = companies.find((company) => company.value === select.value);
  if (selected) search.value = selected.label;
  const activate = (index) => {
    if (!visibleCompanies.length) return;
    activeIndex = (index + visibleCompanies.length) % visibleCompanies.length;
    const items = [...options.querySelectorAll('[role="option"]')];
    items.forEach((item, itemIndex) => item.setAttribute('aria-selected', String(itemIndex === activeIndex)));
    const active = items[activeIndex];
    if (!active) return;
    search.setAttribute('aria-activedescendant', active.id);
    active.scrollIntoView({ block: 'nearest' });
  };
  const render = () => {
    const query = search.value.trim().toLocaleLowerCase('pt-BR');
    const matches = companies.filter((company) => company.search.toLocaleLowerCase('pt-BR').includes(query));
    visibleCompanies = matches.slice(0, 8);
    activeIndex = -1;
    search.removeAttribute('aria-activedescendant');
    options.replaceChildren();
    visibleCompanies.forEach((company, index) => {
      const item = document.createElement('li');
      item.id = `${options.id}-${index}`;
      item.role = 'option';
      item.setAttribute('aria-selected', 'false');
      item.textContent = company.label;
      item.addEventListener('pointerdown', (event) => event.preventDefault());
      item.addEventListener('click', () => choose(company));
      options.append(item);
    });
    options.hidden = !visibleCompanies.length;
    search.setAttribute('aria-expanded', String(Boolean(visibleCompanies.length)));
    if (status) {
      const shownCount = visibleCompanies.length;
      const resultLabel = `${matches.length} empresa${matches.length === 1 ? '' : 's'} encontrada${matches.length === 1 ? '' : 's'}.`;
      status.textContent = matches.length > shownCount
        ? `${resultLabel} Mostrando ${shownCount}; continue digitando para refinar.`
        : matches.length
          ? resultLabel
          : 'Nenhuma empresa encontrada. Revise o nome ou o código.';
    }
  };
  search.addEventListener('input', () => {
    select.value = '';
    select.dispatchEvent(new Event('change', { bubbles: true }));
    validate();
    render();
  });
  search.addEventListener('focus', () => {
    if (select.value) search.select();
    render();
  });
  search.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      if (!options.hidden) event.stopPropagation();
      close();
    } else if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && !options.hidden) {
      event.preventDefault();
      activate(activeIndex + (event.key === 'ArrowDown' ? 1 : -1));
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      choose(visibleCompanies[activeIndex]);
    }
  });
  search.addEventListener('blur', () => window.setTimeout(close, 0));
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
  if (!(selectAll instanceof HTMLInputElement) || !(submit instanceof HTMLButtonElement)) return;

  const update = () => {
    const selected = targets.filter((target) => target.checked).length;
    selectAll.checked = selected === targets.length && targets.length > 0;
    selectAll.indeterminate = selected > 0 && selected < targets.length;
    if (count) {
      count.textContent = selected
        ? `${selected} selecionada${selected === 1 ? '' : 's'}`
        : 'Nenhuma selecionada. Marque as linhas abaixo.';
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
  const actions = form.querySelector('[data-nfse-bulk-actions]');
  if (!(selectAll instanceof HTMLInputElement)) return;

  const update = () => {
    const selected = targets.filter((target) => target.checked).length;
    if (actions) actions.hidden = selected === 0;
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

document.querySelectorAll('[data-nfse-live-queue]').forEach((panel) => {
  const endpoint = panel.dataset.endpoint;
  const retryEndpoint = panel.dataset.retryEndpoint;
  const certificatesEndpoint = panel.dataset.certificatesEndpoint;
  const settingsEndpoint = panel.dataset.settingsEndpoint;
  const canManage = panel.dataset.canManage === 'true';
  const csrfToken = panel.dataset.csrfToken;
  const list = panel.querySelector('[data-nfse-queue-list]');
  const updated = panel.querySelector('[data-nfse-queue-updated]');
  const feedback = panel.querySelector('[data-nfse-queue-feedback]');
  const refreshButton = panel.querySelector('[data-nfse-queue-refresh]');
  const retryAllButton = panel.querySelector('[data-nfse-queue-retry-all]');
  if (!endpoint || !list) return;

  let timer = null;
  let loading = false;
  let lastFingerprint = '';
  let hadLoadError = false;

  const formatTime = (value) => {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    }).format(date);
  };

  const render = (payload) => {
    const items = payload.items || [];
    const fingerprint = JSON.stringify({ counts: payload.counts || {}, items });
    const pageScroll = { x: window.scrollX, y: window.scrollY };
    const queueScroll = list.scrollTop;
    if (fingerprint !== lastFingerprint) {
      Object.entries(payload.counts || {}).forEach(([name, value]) => {
        const target = panel.querySelector(`[data-nfse-queue-count="${name}"]`);
        if (target) target.textContent = String(value);
      });
      if (retryAllButton) retryAllButton.hidden = !canManage || !(payload.counts?.attention > 0);
      const existing = new Map(
        [...list.querySelectorAll('[data-nfse-queue-key]')]
          .map((row) => [row.dataset.nfseQueueKey, row]),
      );
      const retained = new Set();
      list.querySelector('.nfse-queue-loading')?.remove();
      items.forEach((item) => {
        const key = String(item.company_id || item.company);
        let row = existing.get(key);
        if (!row) {
          row = document.createElement('article');
          row.dataset.nfseQueueKey = key;
          row.innerHTML = '<span class="nfse-queue-marker" aria-hidden="true"></span><div><strong></strong><small></small></div><div class="nfse-queue-state"><span class="nfse-status"></span><time></time><a class="nfse-queue-action" hidden>Adicionar A1</a><button class="nfse-queue-retry" type="button" data-nfse-queue-retry hidden>Tentar novamente</button></div>';
        }
        row.className = `nfse-queue-item is-${item.state}`;
        const company = row.querySelector('strong');
        const detail = row.querySelector('small');
        const badge = row.querySelector('.nfse-status');
        const time = row.querySelector('time');
        const actionLink = row.querySelector('.nfse-queue-action');
        const retryButton = row.querySelector('[data-nfse-queue-retry]');
        if (company) company.textContent = item.company;
        if (detail) detail.textContent = item.detail;
        if (badge) {
          badge.className = `nfse-status nfse-status-${item.state}`;
          badge.textContent = item.label;
        }
        const formattedTime = formatTime(item.updated_at);
        if (time) {
          time.hidden = !formattedTime;
          time.dateTime = item.updated_at || '';
          time.textContent = formattedTime;
        }
        if (retryButton) {
          retryButton.hidden = !canManage || item.state !== 'failed';
          retryButton.dataset.companyId = item.company_id || '';
        }
        if (actionLink instanceof HTMLAnchorElement) {
          const actionEndpoint = item.state === 'blocked'
            ? certificatesEndpoint
            : item.state === 'ready' ? settingsEndpoint : '';
          actionLink.hidden = !actionEndpoint;
          actionLink.href = actionEndpoint || '#';
          actionLink.textContent = item.state === 'blocked' ? 'Adicionar A1' : 'Configurar';
        }
        retained.add(key);
        list.append(row);
      });
      existing.forEach((row, key) => { if (!retained.has(key)) row.remove(); });
      if (!items.length) {
        const empty = document.createElement('p');
        empty.className = 'nfse-queue-loading';
        empty.textContent = 'Nenhuma empresa disponível para coleta.';
        list.append(empty);
      }
      lastFingerprint = fingerprint;
      list.scrollTop = queueScroll;
      window.requestAnimationFrame(() => {
        list.scrollTop = queueScroll;
        window.scrollTo(pageScroll.x, pageScroll.y);
      });
    }
    list.setAttribute('aria-busy', 'false');
    if (updated) updated.textContent = `Atualizada às ${formatTime(payload.updated_at).split(' ')[1] || 'agora'}`;
    if (hadLoadError && feedback) feedback.textContent = 'A atualização da fila foi restabelecida.';
    hadLoadError = false;
  };

  const schedule = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(load, 5000);
  };

  const load = async () => {
    if (loading || document.hidden) {
      schedule();
      return;
    }
    loading = true;
    if (refreshButton) {
      refreshButton.disabled = true;
      refreshButton.setAttribute('aria-busy', 'true');
    }
    try {
      const response = await fetch(endpoint, {
        headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
        cache: 'no-store',
      });
      if (!response.ok) throw new Error('queue_unavailable');
      render(await response.json());
    } catch (_error) {
      list.setAttribute('aria-busy', 'false');
      if (updated) updated.textContent = 'Não foi possível atualizar. Tentando novamente…';
      if (!hadLoadError && feedback) feedback.textContent = 'A fila não pôde ser atualizada. Os últimos dados continuam visíveis.';
      hadLoadError = true;
    } finally {
      loading = false;
      if (refreshButton) {
        refreshButton.disabled = false;
        refreshButton.removeAttribute('aria-busy');
      }
      schedule();
    }
  };

  const retry = async (button, companyId = '') => {
    if (!retryEndpoint || !csrfToken || button.disabled) return;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    const payload = new URLSearchParams({ csrfmiddlewaretoken: csrfToken });
    if (companyId) payload.set('company_id', companyId);
    else payload.set('all_failed', '1');
    try {
      const response = await fetch(retryEndpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: payload,
      });
      if (!response.ok) throw new Error('retry_unavailable');
      const result = await response.json();
      const resultMessage = result.changed
        ? `${result.changed} coleta${result.changed === 1 ? '' : 's'} reenfileirada${result.changed === 1 ? '' : 's'}.`
        : 'Nenhuma falha pendente para repetir.';
      await load();
      if (updated) updated.textContent = resultMessage;
      if (feedback) feedback.textContent = resultMessage;
    } catch (_error) {
      if (updated) updated.textContent = 'Não foi possível repetir agora. Tente novamente.';
      if (feedback) feedback.textContent = 'Não foi possível repetir a coleta agora.';
    } finally {
      button.disabled = false;
      button.removeAttribute('aria-busy');
    }
  };

  refreshButton?.addEventListener('click', load);
  retryAllButton?.addEventListener('click', () => retry(retryAllButton));
  list.addEventListener('click', (event) => {
    const button = event.target.closest('[data-nfse-queue-retry]');
    if (button instanceof HTMLButtonElement) retry(button, button.dataset.companyId || '');
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) load();
  });
  load();
});

document.querySelectorAll('#parcelamento-bulk-form').forEach((form) => {
  const targets = [...form.querySelectorAll('.parcelamento-company-check')];
  const selectAll = form.querySelector('#parcelamento-select-all');
  const summary = form.querySelector('#parcelamento-selection-summary');
  const review = form.querySelector('#parcelamento-selection-review');
  const submit = form.querySelector('#parcelamento-submit');
  const approved = form.querySelector('#parcelamento-approved-overage');
  const actions = form.querySelector('[data-parcelamento-bulk-actions]');
  if (!(selectAll instanceof HTMLInputElement)
      || !(submit instanceof HTMLButtonElement)
      || !(approved instanceof HTMLInputElement)) return;
  const weight = Number(form.dataset.tokensPerOperation || 0);
  const included = Number(form.dataset.includedRemaining || 0);
  const price = Number(form.dataset.tokenPriceCents || 0);
  const demo = form.dataset.parcelamentoDemo === 'true';
  const update = () => {
    const count = targets.filter((target) => target.checked).length;
    if (actions) actions.hidden = count === 0;
    const tokens = count * weight;
    const overage = Math.max(0, tokens - included) * price;
    approved.value = String(overage);
    const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
    const selectionText = count
      ? demo
        ? `${count} empresa${count === 1 ? '' : 's'} · simulação sem consumo`
        : `${count} empresa${count === 1 ? '' : 's'} · ${tokens} token${tokens === 1 ? '' : 's'} · excedente ${currency.format(overage / 100)}`
      : 'Nenhuma empresa selecionada';
    if (summary) summary.textContent = selectionText;
    if (review) review.textContent = selectionText;
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


const initNfseDownloadForm = (form) => {
  const selectAll = form.querySelector('[data-nfse-download-select-all]');
  const selectPortfolio = form.querySelector('[data-nfse-download-all]');
  const targets = [...form.querySelectorAll('[data-nfse-download-target]')];
  const companySelectors = [...form.querySelectorAll('[data-nfse-company-select]')];
  const count = form.querySelector('[data-nfse-download-selection-count]');
  const actions = form.querySelector('[data-nfse-download-actions]');
  const actionButtons = [...(actions?.querySelectorAll('button') || [])];
  if (!(selectAll instanceof HTMLInputElement)) return;

  const update = () => {
    const selectedTargets = targets.filter((target) => target.checked);
    const selected = selectedTargets.length;
    const selectedCompanies = new Set(selectedTargets.map((target) => target.dataset.companyId));
    const portfolio = selectPortfolio instanceof HTMLInputElement && selectPortfolio.checked;
    actionButtons.forEach((button) => { button.disabled = selected === 0 && !portfolio; });
    selectAll.checked = selected === targets.length && targets.length > 0;
    selectAll.indeterminate = selected > 0 && selected < targets.length;
    companySelectors.forEach((selector) => {
      const companyTargets = targets.filter((target) => target.dataset.companyId === selector.dataset.nfseCompanySelect);
      const checked = companyTargets.filter((target) => target.checked).length;
      selector.checked = !portfolio && checked > 0 && checked === companyTargets.length;
      selector.indeterminate = !portfolio && checked > 0 && checked < companyTargets.length;
    });
    if (selectPortfolio instanceof HTMLInputElement && selectPortfolio.checked) {
      const total = Number(selectPortfolio.dataset.total || 0);
      const companies = Number(selectPortfolio.dataset.companies || 0);
      count.textContent = total
        ? `${total} nota${total === 1 ? '' : 's'} classificada${total === 1 ? '' : 's'} de ${companies} empresa${companies === 1 ? '' : 's'} ${total === 1 ? 'será incluída' : 'serão incluídas'}.`
        : selectPortfolio.dataset.scopeLabel || 'Toda a carteira será incluída no pacote.';
      return;
    }
    if (count) count.textContent = selected
      ? `${selected} nota${selected === 1 ? '' : 's'} de ${selectedCompanies.size} empresa${selectedCompanies.size === 1 ? '' : 's'} selecionada${selected === 1 ? '' : 's'}.`
      : 'Nenhuma nota selecionada.';
  };

  selectAll.addEventListener('change', () => {
    if (selectPortfolio instanceof HTMLInputElement) selectPortfolio.checked = false;
    targets.forEach((target) => { target.checked = selectAll.checked; });
    update();
  });
  if (selectPortfolio instanceof HTMLInputElement) {
    selectPortfolio.addEventListener('change', () => {
      if (selectPortfolio.checked) targets.forEach((target) => { target.checked = false; });
      update();
    });
  }
  companySelectors.forEach((selector) => selector.addEventListener('change', () => {
    if (selectPortfolio instanceof HTMLInputElement) selectPortfolio.checked = false;
    targets
      .filter((target) => target.dataset.companyId === selector.dataset.nfseCompanySelect)
      .forEach((target) => { target.checked = selector.checked; });
    update();
  }));
  targets.forEach((target) => target.addEventListener('change', () => {
    if (selectPortfolio instanceof HTMLInputElement) selectPortfolio.checked = false;
    update();
  }));
  const accumulators = [...form.querySelectorAll('[data-nfse-download-accumulator]')];
  accumulators.forEach((input, index) => {
    const updateClassification = () => {
      const row = input.closest('tr');
      const flag = row?.querySelector('[data-nfse-classification-flag]');
      const hint = row?.querySelector('[data-nfse-accumulator-hint]');
      const empty = input.value.trim().length === 0;
      const defined = !empty && input.value !== input.defaultValue;
      if (flag instanceof HTMLElement) {
        flag.textContent = empty ? 'Não classificada' : 'Classificada';
        flag.className = `nfse-status nfse-status-${empty ? 'muted' : 'success'}`;
      }
      if (hint instanceof HTMLElement) {
        hint.textContent = empty ? 'Sem acumulador: irá para Transitória' : defined
          ? 'Definida pelo contador para este download'
          : hint.dataset.defaultHint || 'Sem acumulador: irá para Transitória';
      }
      row?.classList.toggle('nfse-manual-classification', defined);
    };
    input.addEventListener('input', updateClassification);
    input.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      const row = input.closest('tr');
      const target = row?.querySelector('[data-nfse-download-target]');
      if (target instanceof HTMLInputElement) target.checked = true;
      update();
      accumulators[index + 1]?.focus();
    });
    updateClassification();
  });
  form.addEventListener('submit', (event) => {
    const downloadingPortfolio = selectPortfolio instanceof HTMLInputElement && selectPortfolio.checked;
    if (!downloadingPortfolio && !targets.some((target) => target.checked)) {
      event.preventDefault();
      if (count) count.textContent = 'Selecione ao menos uma NFS-e para baixar.';
      selectAll.focus();
    }
  });
  form.querySelectorAll('[data-nfse-accumulator-edit]').forEach((editor) => {
    const input = editor.querySelector('[data-nfse-accumulator-input]');
    const status = editor.querySelector('[data-nfse-accumulator-status]');
    if (!(input instanceof HTMLInputElement) || !(input.form instanceof HTMLFormElement)) return;
    let timer = 0;
    let saving = false;
    const allowedValues = () => new Set(
      [...(input.list?.options || [])].map((option) => option.value.trim()),
    );
    const persist = async () => {
      window.clearTimeout(timer);
      const value = input.value.trim();
      if (!value || value === input.defaultValue.trim() || saving) return;
      if (!allowedValues().has(value)) {
        if (status) status.textContent = 'Escolha um acumulador da lista.';
        return;
      }
      saving = true;
      input.setAttribute('aria-busy', 'true');
      if (status) status.textContent = 'Salvando…';
      try {
        const response = await fetch(input.form.action, {
          method: 'POST',
          body: new FormData(input.form),
          credentials: 'same-origin',
          headers: { 'X-Requested-With': 'XMLHttpRequest', Accept: 'application/json' },
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) throw new Error(payload.message || 'Não foi possível salvar.');
        input.defaultValue = payload.accumulator;
        if (status) status.textContent = 'Salvo';
      } catch (error) {
        if (status) status.textContent = error.message || 'Não foi possível salvar.';
      } finally {
        saving = false;
        input.removeAttribute('aria-busy');
      }
    };
    input.addEventListener('input', () => {
      window.clearTimeout(timer);
      if (input.value.trim() === input.defaultValue.trim()) {
        if (status) status.textContent = 'Salvamento automático';
        return;
      }
      if (status) status.textContent = 'Aguardando um acumulador válido…';
      if (allowedValues().has(input.value.trim())) timer = window.setTimeout(persist, 500);
    });
    input.addEventListener('change', persist);
    input.addEventListener('blur', persist);
    input.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      persist();
    });
  });
  update();
};

document.querySelectorAll('[data-nfse-download-form]').forEach(initNfseDownloadForm);

// Filters apply as they change, and only the results region is replaced. Swapping a part
// of the page is a local update, not a change of context, so the form keeps its controls,
// its focus and its caret while the table underneath follows the query (WCAG 3.2.2).
const enhanceLiveFilter = (form) => {
  const results = document.querySelector(form.dataset.liveFilter);
  const count = document.querySelector(form.dataset.liveFilterCount);
  if (!results) return;
  form.querySelector('[data-live-filter-submit]')?.setAttribute('hidden', '');
  let controller = null;
  let timer = 0;
  let request = 0;
  const clear = form.querySelector('[data-live-filter-clear]');
  const value = (name) => String(new FormData(form).get(name) || '').trim();
  const filtering = () => Boolean(
    value('q') || value('competence_month') || value('issued_from') || value('issued_to')
    || (value('status') && value('status') !== 'all')
    || (value('direction') && value('direction') !== 'all'),
  );
  const apply = async () => {
    // A half-typed date would send the whole carteira back; wait for a valid one.
    if (form.querySelector('[aria-invalid="true"]')) return;
    if (clear) clear.hidden = !filtering();
    const url = new URL(window.location.href);
    url.search = new URLSearchParams(
      [...new FormData(form)]
        .filter(([, value]) => String(value) !== '')
        .map(([key, value]) => [key, String(value)]),
    ).toString();
    controller?.abort();
    controller = new AbortController();
    const current = ++request;
    results.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error('filter request failed');
      const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
      if (current !== request || !results.isConnected) return;
      const next = parsed.querySelector(form.dataset.liveFilter);
      if (!next) throw new Error('results region missing');
      results.innerHTML = next.innerHTML;
      if (form.dataset.liveFilterRelated) {
        document.querySelectorAll(form.dataset.liveFilterRelated).forEach((region) => {
          const replacement = parsed.getElementById(region.id);
          if (replacement) region.replaceWith(replacement);
        });
      }
      const nextCount = count && parsed.querySelector(form.dataset.liveFilterCount);
      if (count && nextCount) count.textContent = nextCount.textContent;
      if (String(url) !== window.location.href) history.replaceState({}, '', url);
      results.querySelectorAll('[data-nfse-download-form]').forEach(initNfseDownloadForm);
    } catch (error) {
      if (error.name !== 'AbortError' && current === request) window.location.assign(url);
    } finally {
      results.removeAttribute('aria-busy');
    }
  };
  const schedule = (delay) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(apply, delay);
  };
  form.addEventListener('submit', (event) => { event.preventDefault(); schedule(0); });
  form.addEventListener('change', () => schedule(0));
  form.addEventListener('input', (event) => {
    if (event.target instanceof HTMLSelectElement) return;
    schedule(350);
  });
  form.addEventListener('click', (event) => {
    if (event.target.closest('[data-nfse-period]')) schedule(0);
  });
};

document.querySelectorAll('[data-live-filter]').forEach(enhanceLiveFilter);

document.querySelectorAll('[data-nfse-filter-mode]').forEach((fieldSet) => {
  const control = fieldSet.querySelector('[data-nfse-filter-option]');
  const form = fieldSet.closest('form');
  if (!(control instanceof HTMLSelectElement) || !form) return;
  const update = () => {
    const active = control.value;
    form.querySelectorAll('[data-nfse-filter-panel]').forEach((panel) => {
      panel.hidden = panel.dataset.nfseFilterPanel !== active;
      panel.querySelectorAll('input, select, button').forEach(input => { input.disabled = panel.hidden; });
    });
  };
  control.addEventListener('change', update);
  update();
});

document.querySelectorAll('.nfse-issued-range').forEach((range) => {
  const inputs = [...range.querySelectorAll('[data-nfse-date]')];
  const error = range.querySelector('.nfse-date-error');
  const format = date => new Intl.DateTimeFormat('pt-BR').format(date);
  const parse = value => {
    if (!/^\d{2}\/\d{2}\/\d{4}$/.test(value)) return null;
    const [day, month, year] = value.split('/').map(Number);
    const date = new Date(year, month - 1, day);
    return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day ? date : null;
  };
  const validate = () => {
    let firstInvalid = null;
    error.textContent = '';
    inputs.forEach(input => {
      const invalid = input.value && !parse(input.value);
      input.setAttribute('aria-invalid', String(Boolean(invalid)));
      if (invalid && !firstInvalid) firstInvalid = input;
    });
    if (firstInvalid) error.textContent = 'Informe uma data válida no formato DD/MM/AAAA.';
    else if (inputs.every(input => input.value) && parse(inputs[0].value) > parse(inputs[1].value)) {
      error.textContent = 'A data final deve ser igual ou posterior à inicial.';
      firstInvalid = inputs[1];
      firstInvalid.setAttribute('aria-invalid', 'true');
    }
    return firstInvalid;
  };
  inputs.forEach(input => {
    input.addEventListener('input', () => {
      // Format complete numeric entries without moving the caret during editing.
      if (/^\d{8}$/.test(input.value)) input.value = input.value.replace(/^(\d{2})(\d{2})(\d{4})$/, '$1/$2/$3');
      input.removeAttribute('aria-invalid');
      error.textContent = '';
    });
    input.addEventListener('blur', validate);
  });
  range.querySelectorAll('[data-nfse-period]').forEach(button => button.addEventListener('click', () => {
    const now = new Date();
    const month = now.getMonth() - (button.dataset.nfsePeriod === 'previous' ? 1 : 0);
    inputs[0].value = button.dataset.nfsePeriod === 'clear' ? '' : format(new Date(now.getFullYear(), month, 1));
    inputs[1].value = button.dataset.nfsePeriod === 'clear' ? '' : format(new Date(now.getFullYear(), month + 1, 0));
    validate();
  }));
  range.closest('form').addEventListener('submit', event => {
    if (range.hidden) return;
    const invalid = validate();
    if (invalid) { event.preventDefault(); invalid.focus(); }
  });
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

document.querySelectorAll('[data-modal] form, .team-form, .review-detail-panel form, [data-dre-mapping-form], .activity-actions form, .activity-assignment-panel form').forEach(form => {
  form.addEventListener('input', event => {
    if (event.target.type !== 'search') dirtyForms.add(form);
  });
  form.addEventListener('submit', () => dirtyForms.delete(form));
});

// Keep shareable GET URLs readable by omitting controls that carry no filter.
document.querySelectorAll('form[data-clean-query]').forEach((form) => {
  form.addEventListener('submit', () => {
    const emptyControls = [];
    form.querySelectorAll('input[name], select[name], textarea[name]').forEach((control) => {
      if (control.value === '') {
        control.disabled = true;
        emptyControls.push(control);
      }
    });
    window.setTimeout(() => emptyControls.forEach((control) => { control.disabled = false; }), 0);
  });
  form.addEventListener('formdata', (event) => {
    [...event.formData.entries()].forEach(([key, value]) => {
      if (typeof value === 'string' && value === '') event.formData.delete(key);
    });
  });
});

document.querySelector('[data-dre-mapping-form] [aria-invalid="true"]')?.focus();
window.addEventListener('beforeunload', event => {
  if (!dirtyForms.size) return;
  event.preventDefault();
  event.returnValue = '';
});

// Bulk actions on the reconciliation queue only appear once something is selected:
// a destructive-looking "Aplicar aos selecionados" with an empty selection is noise.
document.querySelectorAll('[data-movement-bulk-form]').forEach((form) => {
  const targets = [...form.querySelectorAll('[data-movement-target]')];
  const actions = form.querySelector('[data-movement-bulk-actions]');
  const count = form.querySelector('[data-movement-selection-count]');
  if (!targets.length) return;
  const update = () => {
    const selected = targets.filter((target) => target.checked).length;
    if (actions) actions.hidden = selected === 0;
    if (count) {
      count.textContent = selected
        ? `${selected} movimento${selected === 1 ? '' : 's'} selecionado${selected === 1 ? '' : 's'}`
        : 'Nenhum movimento selecionado';
    }
  };
  targets.forEach((target) => target.addEventListener('change', update));
  update();
});

// Busy state for single-action forms: stop double submission of paid or long requests.
document.querySelectorAll(
  'button[data-busy-label], .reconciliation-export-form button[type="submit"], .reconciliation-export-confirm button[type="submit"]',
).forEach((button) => {
  const form = button.closest('form');
  if (!(button instanceof HTMLButtonElement) || !form) return;
  form.addEventListener('submit', (event) => {
    if (event.defaultPrevented) return;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.textContent = button.dataset.busyLabel || 'Enviando…';
  });
});

// Queued provider work refreshes the page on its own, but never while someone is
// typing or has an open dialog, so no half-filled form is lost.
document.querySelectorAll('[data-auto-refresh]').forEach((marker) => {
  const seconds = Math.max(5, Number(marker.getAttribute('data-auto-refresh')) || 8);
  const tick = () => {
    const active = document.activeElement;
    const typing = active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement
      || active instanceof HTMLSelectElement;
    const dialogOpen = [...document.querySelectorAll('[data-modal]')].some((modal) => !modal.hidden);
    const checked = document.querySelector('input[type="checkbox"]:checked');
    if (document.hidden || typing || dialogOpen || checked) {
      window.setTimeout(tick, seconds * 1000);
      return;
    }
    window.location.reload();
  };
  window.setTimeout(tick, seconds * 1000);
});

// Generic bulk selection (D-277): count, "select page", and only the fields of the chosen
// action. Without JavaScript every control stays visible and the server validates.
document.querySelectorAll('[data-bulk-form]').forEach((form) => {
  const targets = [...document.querySelectorAll('[data-bulk-target]')].filter(
    (target) => target.form === form,
  );
  if (!targets.length) return;
  const all = form.querySelector('[data-bulk-all]');
  const actions = form.querySelector('[data-bulk-actions]');
  const count = form.querySelector('[data-bulk-count]');
  const action = form.querySelector('[data-bulk-action]');
  const fields = [...form.querySelectorAll('[data-bulk-field]')];
  const syncFields = () => {
    const value = action ? action.value : '';
    fields.forEach((field) => {
      const visible = field.dataset.bulkField.split(' ').includes(value);
      field.hidden = !visible;
      field.querySelectorAll('input, select, textarea').forEach((input) => {
        input.disabled = !visible;
        input.required = visible && input.name !== 'assignee';
      });
    });
  };
  const update = () => {
    const selected = targets.filter((target) => target.checked).length;
    if (actions) actions.hidden = selected === 0;
    if (all) {
      all.checked = selected === targets.length;
      all.indeterminate = selected > 0 && selected < targets.length;
    }
    if (count) {
      count.textContent = selected
        ? `${selected} ${selected === 1 ? count.dataset.bulkSingular : count.dataset.bulkPlural}`
        : count.dataset.bulkEmpty;
    }
  };
  targets.forEach((target) => target.addEventListener('change', update));
  if (all) {
    all.addEventListener('change', () => {
      targets.forEach((target) => {
        target.checked = all.checked;
      });
      update();
    });
  }
  if (action) action.addEventListener('change', syncFields);
  syncFields();
  update();
});

// Activity filters on a phone: search stays, the rest opens on demand (D-277). Without
// JavaScript, or with an active filter, every field stays visible.
document.querySelectorAll('[data-toolbar]').forEach((toolbar) => {
  const toggle = toolbar.querySelector('[data-toolbar-toggle]');
  if (!toggle) return;
  toolbar.classList.add('is-collapsible');
  toggle.hidden = false;
  const sync = () => {
    toggle.setAttribute('aria-expanded', String(toolbar.classList.contains('is-expanded')));
  };
  toggle.addEventListener('click', () => {
    toolbar.classList.toggle('is-expanded');
    sync();
  });
  sync();
});

// Workspace search (D-277): Ctrl/Cmd+K or "/" opens a dialog; the header link keeps working
// without JavaScript. Arrow keys move through results, Enter opens, Escape closes.
(() => {
  const dialog = document.getElementById('workspace-search-dialog');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const input = dialog.querySelector('[data-search-input]');
  const results = dialog.querySelector('[data-search-results]');
  const form = dialog.querySelector('form');
  let timer = 0;
  let controller = null;
  const open = () => {
    if (!dialog.open) dialog.showModal();
    input.select();
  };
  const items = () => [...results.querySelectorAll('[data-search-result]')];
  const select = (index) => {
    const list = items();
    list.forEach((item, position) => item.setAttribute('aria-selected', String(position === index)));
    if (list[index]) list[index].scrollIntoView({ block: 'nearest' });
  };
  const search = () => {
    const query = input.value.trim();
    if (controller) controller.abort();
    if (query.length < 2) {
      results.replaceChildren();
      return;
    }
    controller = new AbortController();
    const url = `${form.action}?partial=1&q=${encodeURIComponent(query)}`;
    fetch(url, { signal: controller.signal, headers: { 'X-Requested-With': 'fetch' } })
      .then((response) => (response.ok ? response.text() : ''))
      .then((html) => {
        const fragment = new DOMParser().parseFromString(html, 'text/html');
        results.replaceChildren(...fragment.body.childNodes);
        select(0);
      })
      .catch(() => {});
  };
  document.querySelectorAll('[data-search-open]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      open();
    });
  });
  dialog.querySelector('[data-search-close]').addEventListener('click', () => dialog.close());
  input.addEventListener('input', () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(search, 200);
  });
  input.addEventListener('keydown', (event) => {
    const list = items();
    const current = list.findIndex((item) => item.getAttribute('aria-selected') === 'true');
    if (event.key === 'ArrowDown' && list.length) {
      event.preventDefault();
      select(Math.min(current + 1, list.length - 1));
    } else if (event.key === 'ArrowUp' && list.length) {
      event.preventDefault();
      select(Math.max(current - 1, 0));
    } else if (event.key === 'Enter' && current >= 0) {
      event.preventDefault();
      window.location.assign(list[current].href);
    }
  });
  document.addEventListener('keydown', (event) => {
    const typing = event.target.closest('input, textarea, select, [contenteditable="true"]');
    if ((event.key === 'k' || event.key === 'K') && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      open();
    } else if (event.key === '/' && !typing && !dialog.open) {
      event.preventDefault();
      open();
    }
  });
})();
