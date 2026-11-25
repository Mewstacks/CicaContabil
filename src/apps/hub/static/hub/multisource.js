// Fechamento do mês (D-413): depois de simular, leva foco e rolagem ao resultado.
document.addEventListener("DOMContentLoaded", () => {
  const result = document.getElementById("multisource-result");
  if (!result) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  result.scrollIntoView({ block: "start", behavior: reduce ? "auto" : "smooth" });
  result.focus({ preventScroll: true });
});

// Movimentos do mês (D-417): filtro por situação, sem recarregar a página.
document.addEventListener("DOMContentLoaded", () => {
  const box = document.querySelector("[data-multisource-movements]");
  if (!box) return;
  const buttons = box.querySelectorAll("[data-filter]");
  const rows = box.querySelectorAll("tr[data-situation]");
  const count = box.querySelector("[data-multisource-count]");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const wanted = button.dataset.filter;
      let shown = 0;
      rows.forEach((row) => {
        const visible = wanted === "all" || row.dataset.situation === wanted;
        row.hidden = !visible;
        shown += visible ? 1 : 0;
      });
      buttons.forEach((other) => other.setAttribute("aria-pressed", String(other === button)));
      if (count) count.textContent = `Mostrando ${shown} movimento${shown === 1 ? "" : "s"}.`;
    });
  });
});
