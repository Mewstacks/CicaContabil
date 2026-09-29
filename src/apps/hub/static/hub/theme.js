/* The server cookie is authoritative; system mode follows changes without a reload. */
(() => {
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
