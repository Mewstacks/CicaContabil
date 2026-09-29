# Serviço de relatórios CICA

O serviço Node/TypeScript renderiza uma fotografia já autorizada em `POST /v1/render`
como PDF, XLSX ou SVG. A fotografia conserva filtros, versão do modelo, atualização
da fonte, situação preliminar e pendências. O mesmo conjunto validado alimenta
tabela, gráfico e metadados do arquivo.

Ele não recebe credenciais de ERP ou Serpro, não aceita HTML, SQL ou JavaScript de
usuários e não acessa dados além do corpo enviado. O PDF bloqueia requisições de rede
do renderizador; a planilha protege valores textuais que poderiam ser interpretados
como fórmulas.

## Execução local

```powershell
cd reporting
npm ci --ignore-scripts
npm run check
npm test
$env:CICA_REPORTING_BROWSER_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
$env:CICA_REPORTING_SHARED_SECRET = "segredo-local-de-teste"
npm start
```

O caminho do navegador é obrigatório apenas para PDF. O serviço não baixa navegador
automaticamente. A variável deve apontar para um executável previamente instalado e
homologado no ambiente. A API é deliberadamente apenas de loopback durante esta etapa.

## Estado e limites

O endpoint exige `X-CICA-Reporting-Secret` e responde com `X-CICA-Report-Hash`,
calculado sobre a fotografia validada e o formato solicitado. Django pode ativá-lo
somente com `CICA_REPORTING_URL` e `CICA_REPORTING_SHARED_SECRET`; quando essa
configuração existe, ele confere segredo, tipo e hash e devolve indisponibilidade se o
serviço falhar, em vez de alternar silenciosamente para outro motor. Antes de ativá-lo
em producao, a rotacao/revogacao do segredo e a execucao por Celery precisam estar
configuradas. Para rotacionar sem interromper solicitacoes: configure no renderizador o
novo `CICA_REPORTING_SHARED_SECRET` e o antigo em
`CICA_REPORTING_PREVIOUS_SHARED_SECRET`; atualize Django para enviar o novo valor; confirme
as solicitacoes e remova a variavel anterior. Django nunca envia o segredo anterior. A
fotografia e os hashes do resultado sao persistidos por Django. Este componente nao esta
liberado para producao.

O `overrides` de npm fixa `uuid` 11.1.1 para ExcelJS 4.4.0. A versão corrigida mantém
a entrada CommonJS usada pelo ExcelJS; `npm ls`, `npm audit --omit=dev`, TypeScript e
os testes de PDF/XLSX são obrigatórios em cada atualização do lockfile.
