/* The server cookie is authoritative; system mode follows changes without a reload. */
(() => {
  const root = document.documentElement;

  // Django rotates the CSRF token after login. A tab opened before that rotation
  // otherwise keeps an invalid hidden token until it is reloaded. The CSRF cookie
  // is intentionally HttpOnly here, so obtain a fresh masked token from Django.
  document.querySelectorAll('.theme-picker').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const submitter = event.submitter;
      if (submitter instanceof HTMLButtonElement) submitter.disabled = true;
      try {
        const response = await fetch('/api/v1/auth/csrf/', {
          credentials: 'same-origin',
          headers: { Accept: 'application/json' },
        });
        if (!response.ok) throw new Error('csrf-refresh-failed');
        const payload = await response.json();
        form.querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach((input) => {
          input.value = payload.csrf_token;
        });
      } catch {
        // Submit normally: the server will either accept the existing token or
        // show the branded recovery page configured for CSRF failures.
      } finally {
        if (submitter instanceof HTMLButtonElement) submitter.disabled = false;
      }
      if (submitter instanceof HTMLButtonElement && submitter.name) {
        const choice = document.createElement('input');
        choice.type = 'hidden';
        choice.name = submitter.name;
        choice.value = submitter.value;
        form.append(choice);
      }
      HTMLFormElement.prototype.submit.call(form);
    });
  });

  root.dataset.inputModality = 'pointer';
  addEventListener('pointerdown', () => {
    root.dataset.inputModality = 'pointer';
  }, { capture: true, passive: true });
  addEventListener('keydown', event => {
    if (event.key === 'Tab') root.dataset.inputModality = 'keyboard';
  }, { capture: true });

  const preference = window.matchMedia('(prefers-color-scheme: dark)');
  const sync = () => {
    const explicit = document.documentElement.dataset.theme;
    const dark = explicit === 'dark' || (explicit !== 'light' && preference.matches);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      const canvasSource = document.body || document.documentElement;
      const canvas = getComputedStyle(canvasSource).getPropertyValue('--canvas').trim();
      meta.content = canvas || (dark ? '#101915' : '#f7f3e8');
    }
  };
  sync();
  preference.addEventListener('change', sync);
})();
