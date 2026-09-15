let lastTrigger = null;

const focusables = (root) =>
  [...root.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])')]
    .filter((item) => !item.hidden);

const closeModal = (modal) => {
  if (!modal) return;
  modal.hidden = true;
  document.body.style.overflow = '';
  lastTrigger?.focus();
};

document.querySelectorAll('[data-modal-open]').forEach((trigger) => {
  trigger.addEventListener('click', () => {
    const modal = document.getElementById(trigger.dataset.modalOpen);
    if (!modal) return;
    lastTrigger = trigger;
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    const primaryField = modal.querySelector(
      '[data-modal-initial-focus], input:not([type="hidden"]), select, textarea',
    );
    (primaryField || focusables(modal)[0])?.focus();
  });
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
  mobileNav.addEventListener('click', closeMenu);
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

const enhanceAutoFilter = (form) => {
  let timer;
  let controller;
  const refresh = async (url) => {
    const panel = form.closest('.registry-panel');
    if (!panel) return;
    controller?.abort();
    controller = new AbortController();
    const focusedId = document.activeElement?.id;
    const selectionStart = document.activeElement instanceof HTMLInputElement
      ? document.activeElement.selectionStart
      : null;
    panel.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error('filter request failed');
      const documentFragment = new DOMParser().parseFromString(await response.text(), 'text/html');
      const nextPanel = documentFragment.querySelector('.registry-panel');
      if (!nextPanel) throw new Error('filter panel missing');
      panel.replaceWith(nextPanel);
      history.pushState({}, '', url);
      enhanceAutoFilter(nextPanel.querySelector('[data-auto-filter]'));
      if (focusedId) {
        const focusedField = document.getElementById(focusedId);
        focusedField?.focus();
        if (focusedField instanceof HTMLInputElement && selectionStart !== null) {
          focusedField.setSelectionRange(selectionStart, selectionStart);
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') window.location.assign(url);
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
      window.clearTimeout(timer);
      timer = window.setTimeout(submit, 300);
    });
  });
  form.querySelector('[data-filter-clear]')?.addEventListener('click', (event) => {
    event.preventDefault();
    refresh(new URL(event.currentTarget.href, window.location.origin));
  });
};

document.querySelectorAll('[data-auto-filter]').forEach(enhanceAutoFilter);

document.querySelectorAll('[data-company-picker]').forEach((picker) => {
  const select = picker.querySelector('select');
  const search = picker.querySelector('[data-company-search]');
  const options = picker.querySelector('[data-company-options]');
  if (!(select instanceof HTMLSelectElement) || !(search instanceof HTMLInputElement) || !options) return;
  const companies = [...select.options]
    .filter((option) => option.value)
    .map((option) => ({ label: option.text, value: option.value }));
  select.hidden = true;
  search.hidden = false;
  const close = () => {
    options.hidden = true;
    search.setAttribute('aria-expanded', 'false');
  };
  const choose = (company) => {
    select.value = company.value;
    search.value = company.label;
    close();
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
      item.textContent = company.label;
      item.addEventListener('click', () => choose(company));
      options.append(item);
    });
    options.hidden = !results.length;
    search.setAttribute('aria-expanded', String(Boolean(results.length)));
  };
  search.addEventListener('input', () => {
    select.value = '';
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

