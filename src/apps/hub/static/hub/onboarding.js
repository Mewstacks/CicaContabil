// Guided first-use orientation. The native <dialog> gives focus containment and Escape;
// this only advances steps, records completion once and returns focus to the trigger.
(() => {
  const dialog = document.querySelector('[data-onboarding]');
  if (!(dialog instanceof HTMLDialogElement)) return;

  const trigger = document.querySelector('[data-onboarding-open]');
  const steps = [...dialog.querySelectorAll('[data-onboarding-step]')];
  const back = dialog.querySelector('[data-onboarding-back]');
  const next = dialog.querySelector('[data-onboarding-next]');
  const done = dialog.querySelector('[data-onboarding-done]');
  const skip = dialog.querySelector('[data-onboarding-skip]');
  const close = dialog.querySelector('[data-onboarding-close]');
  const tourId = dialog.dataset.onboardingId || '';
  const version = dialog.dataset.onboardingVersion || '1';
  const sessionOnly = dialog.dataset.onboardingSessionOnly === 'true';
  const storageKey = `cica-onboarding:${tourId}:${version}`;
  let index = 0;

  const show = (position) => {
    const focused = document.activeElement;
    index = Math.min(Math.max(position, 0), steps.length - 1);
    steps.forEach((step, order) => { step.hidden = order !== index; });
    if (back) back.hidden = index === 0;
    const last = index === steps.length - 1;
    if (next) next.hidden = last;
    if (done) done.hidden = !last;
    // The step text is announced by the live region, never focused: per the CSS spec a
    // programmatic focus on a tabindex="-1" element matches :focus-visible, so a heading
    // focused on open draws a ring around the copy on every screen. Focus only moves when
    // the button the person is standing on disappears with the step.
    if (focused instanceof HTMLElement && focused.hidden) {
      (last ? done : next)?.focus({ preventScroll: true });
    }
  };

  const remember = () => {
    // The demonstration keeps progress in the browser session only; nothing is stored
    // for a visitor who is not a real person in an office.
    if (sessionOnly) {
      try { sessionStorage.setItem(storageKey, 'done'); } catch { /* private mode */ }
      return;
    }
    const url = dialog.dataset.onboardingUrl;
    const token = dialog.querySelector('input[name="csrfmiddlewaretoken"]');
    if (!url || !(token instanceof HTMLInputElement)) return;
    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': token.value },
    }).catch(() => { /* the orientation opening again is not worth an error */ });
  };

  const restoreFocus = () => {
    // setTimeout, not requestAnimationFrame: a hidden tab never paints, and the focus
    // still has to come back when the person returns to it.
    setTimeout(() => trigger?.focus({ preventScroll: true }), 0);
  };

  const dismiss = () => {
    if (dialog.open) dialog.close();
    restoreFocus();
  };

  const finish = () => {
    remember();
    dismiss();
  };

  const open = () => {
    show(0);
    if (!dialog.open) dialog.showModal();
  };

  const alreadyDone = () => {
    if (!sessionOnly) return dialog.dataset.onboardingAuto !== 'true';
    try { return sessionStorage.getItem(storageKey) === 'done'; } catch { return false; }
  };

  trigger?.addEventListener('click', open);
  next?.addEventListener('click', () => show(index + 1));
  back?.addEventListener('click', () => show(index - 1));
  done?.addEventListener('click', finish);
  skip?.addEventListener('click', finish);
  close?.addEventListener('click', dismiss);
  // Escape closes without marking it done, so the orientation can come back.
  dialog.addEventListener('close', restoreFocus);

  if (dialog.dataset.onboardingAuto === 'true' && !alreadyDone()) open();
})();
