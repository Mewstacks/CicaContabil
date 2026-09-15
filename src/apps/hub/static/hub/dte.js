document.addEventListener("DOMContentLoaded", () => {
  document.querySelector("[data-focus-error]")?.focus();

  const search = document.querySelector("#dte-company-search");
  const list = document.querySelector("#dte-company-options");
  const options = [...document.querySelectorAll("#dte-company-options .dte-company-option")];
  const status = document.querySelector("#dte-company-search-status");
  const selected = document.querySelector("#dte-company-selection");
  const more = document.querySelector("#dte-company-more");
  const all = document.querySelector("#dte-select-all");
  const results = document.querySelector("#dte-select-results");
  const clear = document.querySelector("#dte-clear-selection");
  if (!search || !list || !options.length || !status || !selected || !more || !all || !results || !clear) return;

  const normalize = (value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  const announce = (node, value) => { if (node.textContent !== value) node.textContent = value; };
  const checkbox = (option) => option.querySelector("input[type=checkbox]");
  const matching = () => {
    const query = normalize(search.value.trim());
    return options.filter((option) => normalize(option.textContent).includes(query));
  };
  let visibleLimit = 20;
  const render = () => {
    const query = normalize(search.value.trim());
    const matches = matching();
    const matchSet = new Set(matches);
    const limit = query ? 50 : visibleLimit;
    let shown = 0;
    for (const option of options) {
      const visible = matchSet.has(option) && shown < limit;
      option.hidden = !visible;
      if (visible) shown += 1;
    }
    const count = options.filter((option) => checkbox(option)?.checked).length;
    announce(selected, count
      ? `${count} empresa${count === 1 ? "" : "s"} selecionada${count === 1 ? "" : "s"} · ${count} consulta${count === 1 ? "" : "s"} Serpro quando o envio for autorizado. Nenhuma chamada ocorre no preparo.`
      : "Nenhuma empresa selecionada.");
    announce(status, matches.length === 0
      ? "Nenhuma empresa encontrada. Revise nome, código Domínio ou CNPJ."
      : `${shown} de ${matches.length} empresa${matches.length === 1 ? "" : "s"} exibida${shown === 1 ? "" : "s"}.${matches.length > limit ? (query ? " Refine a busca para localizar as demais." : " Use o botão abaixo ou busque pelo nome, código ou CNPJ.") : ""}`);
    all.hidden = false;
    all.textContent = `Selecionar todas (${options.length})`;
    results.hidden = !query || matches.length === 0;
    results.textContent = `Selecionar resultados (${matches.length})`;
    clear.hidden = count === 0;
    more.hidden = Boolean(query) || shown >= matches.length;
  };
  search.addEventListener("input", () => { visibleLimit = 20; list.scrollTop = 0; render(); });
  more.addEventListener("click", () => { visibleLimit += 20; render(); });
  all.addEventListener("click", () => { options.forEach((option) => { checkbox(option).checked = true; }); render(); });
  results.addEventListener("click", () => { matching().forEach((option) => { checkbox(option).checked = true; }); render(); });
  clear.addEventListener("click", () => { options.forEach((option) => { checkbox(option).checked = false; }); render(); });
  options.forEach((option) => checkbox(option)?.addEventListener("change", render));
  render();
});
