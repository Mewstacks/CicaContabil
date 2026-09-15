(() => {
  'use strict';
  document.querySelectorAll('[data-password-toggle]').forEach(button => {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;
    button.hidden = false;
    button.addEventListener('click', () => {
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.textContent = show ? 'Ocultar' : 'Mostrar';
      button.setAttribute('aria-pressed', String(show));
    });
  });
  document.querySelectorAll('.field').forEach(field => {
    const input = field.querySelector('input, select, textarea');
    if (!input) return;
    const descriptions = [...field.querySelectorAll('.field-help, .field-error')].map(item => item.id).filter(Boolean);
    if (descriptions.length) input.setAttribute('aria-describedby', descriptions.join(' '));
    if (field.querySelector('.field-error')) input.setAttribute('aria-invalid', 'true');
  });
  document.querySelector('[data-form-errors]')?.focus();
  document.querySelectorAll('form').forEach(form => form.addEventListener('submit', event => {
    // A form can expose more than one submit action. Preserve feedback on the
    // control the person actually selected (for example, “Testar conexão”).
    const button = event.submitter || form.querySelector('button[type=submit]');
    if (!button || !form.checkValidity()) return;
    button.disabled = true;
    button.dataset.originalLabel = button.textContent;
    button.textContent = 'Aguarde…';
    form.setAttribute('aria-busy', 'true');
  }));
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('button[data-original-label]').forEach(button => {
      button.disabled = false;
      button.textContent = button.dataset.originalLabel;
      button.closest('form')?.removeAttribute('aria-busy');
    });
  });
  const lookupForm = document.querySelector('[data-cnpj-lookup]');
  if (lookupForm) {
    const field = lookupForm.querySelector('[name=cnpj]');
    const result = document.getElementById('registry-result');
    const status = document.getElementById('registry-status');
    const name = document.getElementById('registry-name');
    const place = document.getElementById('registry-place');
    let timer, controller, generation = 0;
    field.addEventListener('input', () => {
      clearTimeout(timer);
      controller?.abort();
      const version = ++generation;
      result.hidden = true;
      name.textContent = '';
      place.textContent = '';
      const cnpj = field.value.replace(/[.\/\-\s]/g, '').toUpperCase();
      if (!/^[A-Z0-9]{12}[0-9]{2}$/.test(cnpj)) return;
      timer = setTimeout(async () => {
        result.hidden = false;
        status.textContent = 'Consultando CNPJ…';
        controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 7000);
        try {
          const body = new URLSearchParams({cnpj});
          const response = await fetch(lookupForm.dataset.cnpjLookup, {method:'POST', body, signal:controller.signal, headers:{'X-CSRFToken':lookupForm.querySelector('[name=csrfmiddlewaretoken]').value}, credentials:'same-origin'});
          const data = await response.json();
          if (version !== generation) return;
          if (response.ok && data.status === 'found') {
            status.textContent = 'Empresa encontrada';
            name.textContent = data.razao_social;
            place.textContent = [data.municipio, data.uf].filter(Boolean).join(' / ');
          } else {
            status.textContent = data.status === 'invalid' ? 'Confira o CNPJ informado.' : 'Consulta indisponível. Você pode enviar o pedido; a equipe confere os dados.';
          }
        } catch {
          if (version === generation) status.textContent = 'Não foi possível consultar agora. Você pode continuar.';
        } finally {
          clearTimeout(timeout);
        }
      }, 450);
    });
  }
})();
