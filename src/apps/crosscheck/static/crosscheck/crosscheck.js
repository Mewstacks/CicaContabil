/* Contraprova: ferramenta e regras na tela nova, fila de envio, andamento e cópia de chaves.
   Sem script inline (CSP `script-src 'self'`) e sem dependência: tudo degrada para o HTML. */
(() => {
  const focusErrors = () => {
    const summary = document.querySelector('[data-form-errors]');
    if (summary instanceof HTMLElement) summary.focus();
  };

  // --- Tela nova: cada ferramenta mostra só as regras que usa -------------------------
  const initToolForm = (form) => {
    const inputs = [...form.querySelectorAll('[data-tool-input]')];
    const blocks = [...form.querySelectorAll('[data-tools]')];
    const apply = () => {
      const current = inputs.find((input) => input.checked)?.value || '';
      blocks.forEach((block) => {
        const show = (block.dataset.tools || '').split(' ').includes(current);
        block.hidden = !show;
        block.querySelectorAll('input, select, textarea').forEach((field) => {
          field.disabled = !show;
        });
      });
    };
    inputs.forEach((input) => input.addEventListener('change', apply));
    apply();
  };
  document.querySelectorAll('[data-crosscheck-form]').forEach(initToolForm);
  focusErrors();

  // --- Envio de arquivos: fila sequencial, uma remessa por requisição -------------------
  const formatSize = (bytes) => (bytes >= 1048576
    ? `${(bytes / 1048576).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} MiB`
    : `${Math.max(1, Math.round(bytes / 1024)).toLocaleString('pt-BR')} KiB`);
  const extensionOf = (name) => (name.includes('.') ? `.${name.split('.').pop().toLowerCase()}` : '');

  const initUpload = (form) => {
    const input = form.querySelector('input[type=file]');
    const queueEl = form.querySelector('.crosscheck-queue');
    const drop = form.querySelector('.crosscheck-drop');
    const token = form.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    if (!(input instanceof HTMLInputElement) || !queueEl || !drop) return;
    const accept = (form.dataset.accept || '').split(',').map((item) => item.trim().toLowerCase());
    const maxBytes = Number(form.dataset.maxBytes || 0);
    const isXml = form.hasAttribute('data-multiple');
    const maxLoose = Number(form.dataset.maxLoose || 100);
    const maxLooseBytes = Number(form.dataset.maxLooseBytes || 0);
    const maxXmlBytes = Number(form.dataset.maxXmlBytes || 0);
    let running = false;
    let delivered = 0;
    const pending = [];

    const addItem = (label, state) => {
      const li = document.createElement('li');
      const name = document.createElement('span');
      name.textContent = label;
      const status = document.createElement('span');
      status.className = 'crosscheck-queue-state';
      status.textContent = state;
      li.append(name, status);
      queueEl.append(li);
      queueEl.hidden = false;
      return { li, status };
    };
    const fail = (item, messages) => {
      item.li.classList.add('is-error');
      item.status.textContent = 'Recusado';
      messages.forEach((text) => {
        const line = document.createElement('span');
        line.className = 'crosscheck-queue-error';
        line.setAttribute('role', 'alert');
        line.textContent = text;
        item.li.append(line);
      });
    };

    const send = (unit) => new Promise((resolve) => {
      const xhr = new XMLHttpRequest();
      const data = new FormData();
      data.append('csrfmiddlewaretoken', token);
      data.append('role', form.dataset.role || '');
      unit.files.forEach((file) => data.append('files', file, file.name));
      const bar = document.createElement('progress');
      bar.max = 100;
      bar.value = 0;
      unit.item.li.append(bar);
      xhr.open('POST', form.action);
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) return;
        const pct = Math.round((event.loaded / event.total) * 100);
        bar.value = pct;
        unit.item.status.textContent = `${pct}%`;
      };
      xhr.onload = () => {
        bar.remove();
        let payload = {};
        try { payload = JSON.parse(xhr.responseText); } catch { payload = {}; }
        const errors = payload.errors || [];
        if (xhr.status === 200 && (payload.stored || []).length) {
          unit.item.li.classList.add('is-done');
          unit.item.status.textContent = 'Enviado';
          delivered += 1;
          if (errors.length) fail(unit.item, errors);
        } else {
          fail(unit.item, errors.length ? errors : [xhr.status === 403
            ? 'Sem permissão para enviar arquivos.'
            : 'Não foi possível enviar. Tente de novo.']);
        }
        resolve();
      };
      xhr.onerror = () => {
        bar.remove();
        fail(unit.item, ['A conexão caiu durante o envio. Tente de novo.']);
        resolve();
      };
      xhr.onabort = () => { bar.remove(); resolve(); };
      xhr.send(data);
    });

    const drain = async () => {
      if (running) return;
      running = true;
      while (pending.length) await send(pending.shift());
      running = false;
      if (delivered) window.setTimeout(() => window.location.reload(), 600);
    };

    const plan = (files) => {
      const units = [];
      const loose = [];
      files.forEach((file) => {
        const extension = extensionOf(file.name);
        const limit = isXml && extension === '.xml' ? maxXmlBytes : maxBytes;
        if (!accept.includes(extension)) {
          fail(addItem(file.name, formatSize(file.size)), [`${file.name}: formato não aceito.`]);
        } else if (limit && file.size > limit) {
          fail(addItem(file.name, formatSize(file.size)), [`${file.name}: acima de ${formatSize(limit)}.`]);
        } else if (isXml && extension === '.xml') {
          loose.push(file);
        } else {
          units.push({ files: [file], label: file.name, size: file.size });
        }
      });
      let batch = [];
      let bytes = 0;
      const flush = () => {
        if (!batch.length) return;
        units.push({ files: batch, label: `${batch.length} XML`, size: bytes });
        batch = [];
        bytes = 0;
      };
      loose.forEach((file) => {
        if (batch.length >= maxLoose || (maxLooseBytes && bytes + file.size > maxLooseBytes)) flush();
        batch.push(file);
        bytes += file.size;
      });
      flush();
      return units;
    };

    const enqueue = (files) => {
      plan(files).forEach((unit) => {
        unit.item = addItem(unit.label, formatSize(unit.size));
        pending.push(unit);
      });
      input.value = '';
      drain();
    };

    input.addEventListener('change', () => enqueue([...(input.files || [])]));
    ['dragenter', 'dragover'].forEach((name) => drop.addEventListener(name, (event) => {
      event.preventDefault();
      drop.classList.add('is-dragging');
    }));
    ['dragleave', 'drop'].forEach((name) => drop.addEventListener(name, (event) => {
      event.preventDefault();
      drop.classList.remove('is-dragging');
    }));
    drop.addEventListener('drop', (event) => {
      const files = [...(event.dataTransfer?.files || [])];
      if (files.length) enqueue(files);
    });
  };
  document.querySelectorAll('[data-crosscheck-upload]').forEach(initUpload);

  // --- Andamento: consulta o estado até a conferência terminar -------------------------
  const initProgress = (panel) => {
    const url = panel.dataset.statusUrl;
    if (!url) return;
    const stage = panel.querySelector('[data-progress-stage]');
    const count = panel.querySelector('[data-progress-count]');
    const bar = panel.querySelector('[data-progress-bar]');
    const track = panel.querySelector('[data-progress-track]');
    const cancel = panel.querySelector('[data-cancel-button]');
    let failures = 0;
    const tick = async () => {
      if (document.hidden) return;
      try {
        const response = await fetch(url, { headers: { Accept: 'application/json' }, credentials: 'same-origin' });
        if (!response.ok) throw new Error(String(response.status));
        const state = await response.json();
        failures = 0;
        if (state.terminal) {
          window.location.reload();
          return;
        }
        panel.dataset.state = state.state;
        if (stage) stage.textContent = state.stage || state.state_label;
        const hasTotal = Boolean(state.total);
        if (count) count.textContent = hasTotal ? `${state.done} de ${state.total}` : (state.done ? String(state.done) : '');
        if (track) {
          track.classList.toggle('is-indeterminate', !hasTotal);
          if (hasTotal) {
            track.setAttribute('aria-valuemax', String(state.total));
            track.setAttribute('aria-valuenow', String(state.done));
          }
        }
        if (bar && hasTotal) bar.style.setProperty('--pct', String(Math.min(100, Math.round((state.done / state.total) * 100))));
        if (cancel && state.cancel_requested) cancel.textContent = 'Cancelando…';
      } catch {
        failures += 1;
        if (failures >= 5) window.location.reload();
      }
    };
    window.setInterval(tick, 3000);
  };
  document.querySelectorAll('[data-crosscheck-progress]').forEach(initProgress);

  // --- Consulta ao Domínio pelo agente: acompanha até o estado mudar --------------------
  const initAgent = (block) => {
    const url = block.dataset.statusUrl;
    const state = block.dataset.agentState;
    if (!url || !['queued', 'claimed', 'receiving'].includes(state)) return;
    let failures = 0;
    const tick = async () => {
      if (document.hidden) return;
      try {
        const response = await fetch(url, { headers: { Accept: 'application/json' }, credentials: 'same-origin' });
        if (!response.ok) throw new Error(String(response.status));
        const payload = await response.json();
        failures = 0;
        if (payload.agent && payload.agent.state !== state) window.location.reload();
      } catch {
        failures += 1;
        if (failures >= 5) window.location.reload();
      }
    };
    window.setInterval(tick, 4000);
  };
  document.querySelectorAll('[data-agent-block]').forEach(initAgent);

  // --- Copiar chaves da página (delegado: o filtro troca o painel inteiro) -------------
  document.addEventListener('click', async (event) => {
    const button = event.target instanceof Element ? event.target.closest('[data-copy-keys]') : null;
    if (!(button instanceof HTMLButtonElement)) return;
    const keys = [...document.querySelectorAll('[data-finding-key]')]
      .map((node) => node.getAttribute('data-finding-key'))
      .filter(Boolean);
    if (!keys.length) return;
    const original = button.textContent;
    try {
      await navigator.clipboard.writeText([...new Set(keys)].join('\n'));
      button.textContent = `${new Set(keys).size} copiadas`;
    } catch {
      button.textContent = 'Não copiou';
    }
    window.setTimeout(() => { button.textContent = original; }, 2000);
  });
})();
