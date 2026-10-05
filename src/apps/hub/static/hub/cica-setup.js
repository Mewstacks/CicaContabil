(() => {
  const form = document.querySelector('[data-import-form]');
  if (!form) return;
  const kind = form.querySelector('[data-import-field="kind"] select');
  const company = form.querySelector('[data-import-field="company"]');
  const snapshot = form.querySelector('[data-import-field="source_snapshot_at"]');
  const key = form.querySelector('[data-import-field="backup_key"]');
  const errorSummary = form.querySelector('[data-form-errors]');
  const upload = form.querySelector('[data-import-field="upload"] input[type="file"]');
  const fileFeedback = form.querySelector('[data-file-feedback]');
  const guidanceTitle = form.querySelector('[data-import-guidance-title]');
  const guidanceCopy = form.querySelector('[data-import-guidance-copy]');
  const payrollModel = form.querySelector('[data-payroll-model]');
  const guidance = {
    payroll_totals: ['Totais da folha', 'Use código da empresa, competência AAAA-MM-01 e uma referência única. Pessoas e totais podem ficar vazios, mas pelo menos um deles deve existir.'],
    companies: ['Cadastro de empresas', 'Envie CSV ou XLSX com nome e código da empresa. O CNPJ é opcional, mas deve ter 14 dígitos quando informado.'],
    accounting_balances: ['Saldos para DRE', 'Cada linha representa uma conta. Empresa, competência, referência, código da conta e saldo são obrigatórios.'],
    cash_scenario: ['Cenário de caixa', 'Use uma linha por movimento e mantenha empresa, cenário, visão e datas conforme o modelo do escritório.'],
    dre_mapping: ['Mapa DRE', 'Informe conta, grupo e sinal. A confirmação cria uma nova versão e preserva as anteriores.'],
    fiscal_xml: ['Documentos fiscais XML', 'Selecione a empresa à qual o XML pertence antes de analisar o arquivo.'],
    bank_ofx: ['Extrato bancário', 'Selecione a empresa e envie um arquivo OFX ou QFX da conta correta.'],
    dominio_backup: ['Backup Domínio Web', 'Envie o backup completo, a data em que ele foi gerado e a chave mostrada no Onvio.'],
  };
  function render() {
    const value = kind.value;
    company.hidden = !['fiscal_xml','bank_ofx'].includes(value);
    snapshot.hidden = value !== 'dominio_backup';
    key.hidden = value !== 'dominio_backup';
    const copy = guidance[value] || ['Arquivo tabular', 'Confira o tipo escolhido e use um arquivo CSV ou XLSX com cabeçalhos na primeira linha.'];
    guidanceTitle.textContent = copy[0];
    guidanceCopy.textContent = copy[1];
    payrollModel.hidden = value !== 'payroll_totals';
  }
  function renderFile() {
    const file = upload.files && upload.files[0];
    fileFeedback.textContent = file
      ? `${file.name} · ${(file.size / 1024).toLocaleString('pt-BR', {maximumFractionDigits: 1})} KB`
      : 'Nenhum arquivo selecionado.';
  }
  kind.addEventListener('change', render);
  upload.addEventListener('change', renderFile);
  render();
  renderFile();
  if (errorSummary) requestAnimationFrame(() => errorSummary.focus({preventScroll:true}));
})();
