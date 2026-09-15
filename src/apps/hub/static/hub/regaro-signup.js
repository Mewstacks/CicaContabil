(() => {
  const form = document.querySelector('.signup-form[data-cnpj-lookup]');
  const field = form?.querySelector('#id_cnpj');
  const result = document.querySelector('#registry-result');
  const status = document.querySelector('#registry-status');
  const name = document.querySelector('#registry-name');
  const place = document.querySelector('#registry-place');
  if (!form || !field || !result || !status || !name || !place) return;

  let latest = '';
  const clean = value => value.replace(/\D/g, '');
  const isValidCnpj = cnpj => {
    if (!/^\d{14}$/.test(cnpj) || /^(\d)\1{13}$/.test(cnpj)) return false;
    const checkDigit = (base, weights) => {
      const total = [...base].reduce((sum, digit, index) => sum + Number(digit) * weights[index], 0);
      const remainder = total % 11;
      return String(remainder < 2 ? 0 : 11 - remainder);
    };
    const first = checkDigit(cnpj.slice(0, 12), [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
    const second = checkDigit(cnpj.slice(0, 12) + first, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
    return cnpj.endsWith(first + second);
  };
  const lookup = async () => {
    const cnpj = clean(field.value);
    if (cnpj.length !== 14) return;
    if (!isValidCnpj(cnpj)) {
      latest = '';
      status.textContent = 'Confira os dígitos do CNPJ informado.';
      name.textContent = '';
      place.textContent = '';
      result.hidden = false;
      return;
    }
    if (cnpj === latest) return;
    latest = cnpj;
    status.textContent = 'Consultando CNPJ…';
    name.textContent = '';
    place.textContent = '';
    result.hidden = false;
    try {
      const response = await fetch(form.dataset.cnpjLookup, {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value},
        body: new URLSearchParams({cnpj}),
      });
      const data = await response.json();
      if (data.status === 'not_found') {
        status.textContent = 'CNPJ não localizado. Confira o número informado.';
        return;
      }
      if (data.status === 'limited') {
        status.textContent = data.message || 'Aguarde um minuto antes de consultar novamente.';
        return;
      }
      if (!response.ok || data.status === 'unavailable') {
        status.textContent = 'Não foi possível consultar agora. Você ainda pode continuar.';
        return;
      }
      status.textContent = 'CNPJ localizado';
      name.textContent = data.razao_social || 'Empresa encontrada';
      place.textContent = [data.municipio, data.uf].filter(Boolean).join(' · ');
    } catch (_) {
      status.textContent = 'Não foi possível consultar agora. Você ainda pode continuar.';
    }
  };
  field.addEventListener('change', lookup);
  field.addEventListener('blur', lookup);
  form.addEventListener('submit', () => {
    if (!form.checkValidity()) return;
    const submit = form.querySelector('button[type="submit"]');
    if (!submit) return;
    submit.disabled = true;
    submit.textContent = 'Enviando…';
  });
  const errors = form.querySelector('[data-form-errors]');
  if (errors) requestAnimationFrame(() => errors.focus({preventScroll: true}));
})();
