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

