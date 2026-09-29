(() => {
  const demo = document.querySelector("[data-product-demo]");
  if (!demo) return;

  const tabs = [...demo.querySelectorAll("[data-demo-target]")];
  const panels = [...demo.querySelectorAll("[data-demo-panel]")];
  const validTargets = new Set(tabs.map((tab) => tab.dataset.demoTarget));
  const hashPrefix = "#demonstracao-";

  const targetFromHash = () => {
    const value = window.location.hash.slice(hashPrefix.length);
    return validTargets.has(value) ? value : "trabalho";
  };

  const selectTarget = (target, { focus = false, writeHash = false } = {}) => {
    if (!validTargets.has(target)) return;
    tabs.forEach((tab) => {
      const selected = tab.dataset.demoTarget === target;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      if (selected && focus) tab.focus();
    });
    panels.forEach((panel) => {
      panel.hidden = panel.dataset.demoPanel !== target;
    });
    if (writeHash && window.location.hash !== `${hashPrefix}${target}`) {
      window.history.pushState(null, "", `${hashPrefix}${target}`);
    }
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => selectTarget(tab.dataset.demoTarget, { writeHash: true }));
    tab.addEventListener("keydown", (event) => {
      const keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
      if (!keys.includes(event.key)) return;
      event.preventDefault();
      let nextIndex = index;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      selectTarget(tabs[nextIndex].dataset.demoTarget, { focus: true, writeHash: true });
    });
  });

  window.addEventListener("hashchange", () => selectTarget(targetFromHash()));
  window.addEventListener("popstate", () => selectTarget(targetFromHash()));
  selectTarget(targetFromHash());
})();
