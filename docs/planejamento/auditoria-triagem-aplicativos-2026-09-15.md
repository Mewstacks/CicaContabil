# Triagem: revisão operacional da conexão por aplicativo

Data: 15/09/2026. O operador testado foi um **dono sintético** do escritório Visual QA, sem caixa real; Fedrizzi foi conferido separadamente no console e permaneceu disponível. A inspeção não homologa Microsoft/Google/IMAP externos nem o recebimento de anexos.

## Fluxo alcançado

- A Triagem distingue Microsoft 365, Google Workspace, Gmail pessoal e IMAP. Microsoft/Workspace mostram registro guiado do aplicativo do escritório; Gmail pessoal indica que o aplicativo verificado Mewstack ainda não está disponível. Nenhum botão externo fica habilitado sem retorno configurado/app pronto.
- O formulário cadastra Client ID/Secret e Tenant ID Microsoft. O segredo não é reexibido; a prova de cifragem no banco ocorreu em teste automatizado. O cadastro local positivo foi visto no navegador, e o estado posterior informou corretamente que o retorno HTTPS da Mewstack falta.
- Um Tenant ID inválido retornou erro ao lado do campo. O foco passou ao campo inválido, com contorno visível e `aria-describedby` ligado à mensagem. Os três formulários na página usam IDs distintos. A abertura/fechamento de `<details>` por teclado e a ausência de overflow horizontal foram inspecionadas.
- Viewport desktop **1366 × 900** e celular **390 × 844**: as opções fechadas cabem e mantêm hierarquia legível. O guia aberto passa a ocupar a largura inteira no desktop; no celular segue uma coluna. O estado vazio de caixas foi visto. Não houve erro de JavaScript no console da página normal. A navegação HTTP 400 do caso inválido aparece como erro de recurso esperado no Playwright.

## Decisões de interface e fontes

O desenho segue os cartões e formulários já usados na CICA. O `ui-ux-pro-max` orientou hierarquia de integração, alvos móveis, estados e foco. O catálogo Watermelon foi consultado para dashboards de configuração/conexão (sem analogias próximas) e blocos de integração; a tela não copiou blocos de marketing. Referências reais da revisão anterior de **SaaSFrame/Superlist Connect** e Pageflows foram usadas para separar conexão, consentimento e estado de recebimento. Refero MCP não estava disponível nesta sessão. A auditoria de código usa a [versão consultada das Vercel Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md); foram corrigidos IDs duplicados, foco e associação de erros, largura do guia e ausência de aviso ao sair com formulário preenchido.

## Estados não alcançados

Não foi possível inspecionar login/consentimento externos, caixa autorizada com token real, primeiro corte/cursor, sincronização, anexo em quarentena, antimalware, classificação Claude, revisão e escrita Windows. Esses estados requerem os conectores e credenciais de piloto. O app Gmail pessoal da Mewstack ainda precisa ser registrado/verificado; `TRIAGE_GOOGLE_PERSONAL_VERIFIED=false` é o padrão de segurança.
