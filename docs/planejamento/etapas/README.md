# Etapas e prompts da CICA

[Plano mestre na raiz](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Escopo atual:** etapas 00–03 concluídas no nível de implementação e validação local. Por D-87, toda dependência de site em produção será executada na etapa 12; as demais etapas seguem preparando e validando localmente seus respectivos módulos. Isso não autoriza deploy, chamadas externas reais ou custos.

| Etapa | Dependências | Estado desta execução |
|---|---|---|
| [00 — Consolidar decisões, inventário e pendências](00-documentacao.md) | Nenhuma | Concluída em 17/09/2026; evidência V-003 em VALIDACOES.md |
| [01 — Estabilizar a base técnica](01-base-tecnica.md) | 00 | Concluída no nível de implementação e validação local; limitações de homologação seguem para a etapa 12 |
| [02 — Fechar cadastro, acesso e administração](02-acesso-administracao.md) | 01 | Concluída no nível de implementação e validação local; SMTP/DNS real seguem para a etapa 12 |
| [03 — Concluir agente Windows e integração Domínio](03-agente-dominio.md) | 01–02 | Concluída no nível de implementação e validação local; piloto com site publicado e ambiente real segue para a etapa 12 (D-86) |
| [04 — Implementar e homologar Siescon](04-siescon.md) | 02–03 | Em andamento: a inspeção local não encontrou configuração Siescon; aguardando contrato técnico de Q-33 |
| [05 — Concluir IA por API e preparação da IA local](05-ia-api-pipeline-local.md) | 02–03; incorporar Siescon após 04 | Em andamento: metadados de escopo e recuperação por empresa preparados localmente (V-032); governança, curadoria e prova de artefato continuam abertas |
| [06 — Concluir Triagem de Arquivos](06-triagem.md) | 03 e 05 | Em andamento: controles locais de entrada, quarentena e destino revalidados (V-038); OAuth, antimalware, regras e destinos reais pendentes |
| [07 — Concluir NFS-e, certificados e revisão fiscal](07-nfse.md) | 03 e 05 | Em andamento: demonstração local de carteira, filtro e ZIP revalidada (V-035); coleta e homologação fiscal permanecem pendentes |
| [08 — Concluir Central Integra Contador](08-integra-contador.md) | 02 e controles de consumo da 10 | Em andamento: DTE, DCTFWeb e PARCSN validados localmente (V-034); contrato/credenciais/piloto Serpro pendentes |
| [09 — Concluir Conciliação e Radar](09-conciliacao-radar.md) | 03–05; exportação Siescon depende de 04 | Em andamento: controles de conciliação e Radar revalidados localmente (V-037); layouts, OCR, volume, fontes e homologações seguem pendentes |
| [10 — Concluir contratação, tokens e cobrança](10-contratacao-cobranca.md) | 02; pode avançar antes das homologações fiscais | Em andamento: controles de contrato, tokens, fatura e webhook (V-033), mais contrato local do cliente Asaas (V-040); orquestração e homologação pendentes |
| [11 — Validar todas as jornadas e interfaces](11-jornadas-interfaces.md) | Módulos implementados | Em andamento: inspeção local parcial de 14 caminhos e Triagem fictícia (V-039); auditoria integral e aderência da oferta pendentes |
| [12 — Homologação integrada e liberação comercial](12-homologacao-venda.md) | 01–11 | Não iniciada nesta execução |
| [13 — Ativar IA local na máquina definitiva](13-ia-local-definitiva.md) | 05 e disponibilidade do equipamento; não bloqueia a venda inicial por API | Não iniciada nesta execução |
