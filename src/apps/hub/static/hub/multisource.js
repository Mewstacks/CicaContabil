// Fechamento do mês (D-413): depois de simular, leva foco e rolagem ao resultado.
document.addEventListener("DOMContentLoaded", () => {
  const result = document.getElementById("multisource-result");
  if (!result) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  result.scrollIntoView({ block: "start", behavior: reduce ? "auto" : "smooth" });
  result.focus({ preventScroll: true });
});
