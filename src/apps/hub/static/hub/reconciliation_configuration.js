(() => {
  const panels = [...document.querySelectorAll('.reconciliation-create-panel[id]')];

  panels.forEach((panel) => {
    panel.addEventListener('toggle', () => {
      const panelHash = `#${panel.id}`;
      if (panel.open) {
        window.history.replaceState(null, '', panelHash);
      } else if (window.location.hash === panelHash) {
        window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
      }
    });
  });

  if (window.location.hash) {
    let initialPanel = null;
    try {
      initialPanel = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    } catch (_error) {
      initialPanel = null;
    }
    if (initialPanel instanceof HTMLDetailsElement && panels.includes(initialPanel)) {
      initialPanel.open = true;
    }
  }

  let hasUnsavedChanges = false;
  document.querySelectorAll('.reconciliation-create-panel form, .period-state-form').forEach((form) => {
    form.addEventListener('input', () => {
      hasUnsavedChanges = true;
    });
    form.addEventListener('change', () => {
      hasUnsavedChanges = true;
    });
    form.addEventListener('submit', () => {
      hasUnsavedChanges = false;
    });
  });

  window.addEventListener('beforeunload', (event) => {
    if (!hasUnsavedChanges) return;
    event.preventDefault();
    event.returnValue = '';
  });
})();
