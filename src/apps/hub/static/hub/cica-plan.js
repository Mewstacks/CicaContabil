(() => {
  'use strict';
  const root = document.querySelector('.cica-plan');
  if (!root) return;
  const currency = new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'});
  function update() {
    const selected = [...root.querySelectorAll('input[name="plan_module"]:checked')];
    const count = selected.length;
    const discount = ({2: .1, 3: .15, 4: .2, 5: .2, 7: .25})[count] || 0;
    const total = selected.reduce((sum, item) => sum + Number(item.value), 0) * Number(root.querySelector('select').value) * (1 - discount);
    root.querySelector('output').textContent = count === 6 ? 'Sob consulta' : count === 0 ? 'Selecione um módulo' : currency.format(total);
    root.querySelector('#quote-detail').textContent = count === 6 ? '6 módulos · proposta com a equipe' : `${count} ${count === 1 ? 'módulo' : 'módulos'} · ${discount ? Math.round(discount * 100) + '% de desconto' : 'sem desconto'}`;
  }
  root.querySelectorAll('input, select').forEach(input => input.addEventListener('change', update));
  update();
})();
