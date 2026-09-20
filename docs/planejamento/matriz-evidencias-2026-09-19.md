# CICA — matriz de evidências de conclusão em 19/09/2026

Esta matriz torna auditável a análise consolidada sem substituir o
[plano mestre](../../PLANO-MESTRE.md), as [decisões](../../DECISOES.md) ou as
[validações](../../VALIDACOES.md). Ela foi composta pela leitura dos checklists
das etapas, dos registros V-001 a V-040, do inventário de código e do estado
atual do checkout em 20/09/2026.

## Como interpretar

- **Implementado:** existe código, configuração ou documento no checkout.
- **Validado localmente:** há teste, build, inspeção ou execução reprodutível
  registrada.
- **Homologado:** a operação foi conferida no sistema, ambiente ou provedor
  alvo autorizado.
- **Liberado para venda:** inclui operação, recuperação de falha, permissões,
  custos, documentação e suporte coerentes; não é inferido de testes locais.

Uma célula de evidência local nunca prova as duas categorias seguintes. O
estado abaixo é o mais alto efetivamente demonstrado por etapa, não uma média
dos seus subitens.

## Objetivo final verificável

A CICA deve ser um SaaS da Mewstack para escritórios contábeis, multiempresa e
auditável, com agente instalado no ambiente Windows do escritório. O resultado
vendável reúne acesso e administração, Domínio, Siescon, IA, Triagem, NFS-e,
Central Integra Contador, Conciliação, Radar e cobrança. Para cada módulo, o
escritório precisa conseguir configurar, executar, conferir evidências e
recuperar uma falha sem obter acesso indevido ou gerar cobrança inesperada.

Essa definição vem de D-02, D-03, D-46, D-47, D-49 e D-58 e é detalhada na
[análise consolidada](analise-projeto-2026-09-19.md).

## Matriz por etapa

| Etapa | Maior nível demonstrado | Evidência canônica | O que ainda impede o próximo nível |
| --- | --- | --- | --- |
| 00 — documentação | Validado localmente e concluído | V-003; plano, decisões, inventário, dúvidas e 14 etapas verificados | Nada para o escopo documental; não prova comportamento de módulo. |
| 01 — base técnica | Validado localmente e concluído | V-004, V-006 e V-031; CI local, migrações, PostgreSQL/Redis históricos, builds e runtime | Homologação de cada provedor pertence à sua etapa; não há atalho de infraestrutura para declarar produto pronto. |
| 02 — acesso e administração | Validado localmente e concluído | V-007 a V-009; permissões, MFA, isolamento, APIs, demo e e-mails locais | Entrega real por Brevo/DNS e suporte operacional estão na etapa 12. |
| 03 — agente e Domínio | Implementado e validado localmente; contrato ODBC autorizado exercitado | V-010, V-017 e V-020 a V-027; D-74 e D-80 a D-86 | Piloto publicado: instalação limpa, mTLS, atualização, queda/retomada de rede, backup `.dom` autorizado e escrita Windows real. |
| 04 — Siescon | Preparação comum local, sem adaptador específico | V-029 a V-031; D-53/D-54; checklist da etapa 04 | Q-33: versão, banco, acesso de leitura, schema, identificador/cursor e layout de importação/exportação. |
| 05 — IA API e pipeline local | Preparação local parcial | V-032; D-89 a D-92; recuperação isolada e proveniência de treino/avaliação | Q-08, Q-09, Q-11 e Q-34: limites, egressão, rotação de chave, curadoria e corpus aprovado. Não há treino, GPU ou artefato real. |
| 06 — Triagem | Controles locais validados parcialmente | V-038; inventário e validações históricas de demo/triagem | Q-12 a Q-25 e Q-31, caixas reais, antimalware, regras documentais e confirmação de arquivamento. |
| 07 — NFS-e | Demonstração local validada | V-005 e V-035; D-62 a D-69 | Certificado, ADN, NSU, retomada, deduplicação, catálogo de acumuladores e amostra fiscal autorizada. |
| 08 — Central Integra Contador | Controles locais validados | V-034; DTE, DCTFWeb e PARCSN com 63 testes | Credenciais/contrato Serpro, certificado, representação, recorte Q-36 e autorização de custo para chamada real. |
| 09 — Conciliação e Radar | Controles locais validados parcialmente | V-037; inventário de conclusão e evidências históricas | Layouts/corpus representativos, OCR português, volume PostgreSQL, importação conferida em Domínio/Siescon e fontes reais do Radar. |
| 10 — contratação e cobrança | Controles locais validados | V-033 e V-040; contrato, tokens, fatura, eventos idempotentes e contrato do cliente Asaas | Orquestração comercial/`PaymentAttempt` e homologação Asaas para Pix, boleto, cartão, atraso, estorno e ordenação real de eventos. |
| 11 — jornadas e interfaces | Inspeção local parcial | V-039, V-005, V-007, V-009 e V-035 | Auditoria completa dos módulos acabados, estados vazios/erro, dispositivos, teclado/foco e aderência da oferta ao que foi homologado. |
| 12 — homologação e venda | Não iniciada | Plano e checklist da etapa 12 | Ambiente publicado, DNS/SMTP, deploy, backup/restauração, pilotos por módulo, manuais e relatório final. |
| 13 — IA local definitiva | Preparação de pipeline somente | V-032 e D-48 a D-51 | Hardware/Q-35, treino e avaliação independente por escritório, métricas de qualidade/latência e aprovação da virada. |

## Caminho crítico atual

1. **Q-33 / Siescon:** é o primeiro bloqueio de dependência técnica. O
   responsável técnico deve fornecer, por canal seguro, versão/banco/método de
   leitura, ambiente/revogação, schema/campos autorizados, chave empresarial e
   cursor, além de layout e amostra sintética de importação/exportação. D-54
   proíbe escrita direta e impede inventar o adaptador.
2. **Governança da IA:** Q-08, Q-09, Q-11 e Q-34 condicionam Copiloto e
   Triagem reais. A estrutura de isolamento e proveniência já reduz risco, mas
   não substitui autorização de egressão, curadoria humana ou teto comercial.
3. **Contratos e acessos externos:** Serpro, ADN, Asaas, caixas de e-mail e
   SMTP/DNS requerem ambiente, amostras e autorização explícita imediatamente
   antes de operações cobradas. A etapa 12 concentra os pilotos e qualquer
   dependência de site em produção por D-87.
4. **Aceite por módulo:** D-73 exige a métrica aplicável, incluindo amostra
   revisada, precisão mínima, nenhuma duplicidade/vazamento, retomada e
   conferência de importação no destino. Testes ou mocks não substituem essa
   prova.

## Conclusão da análise

O checkout está em um estágio de preparação robusta: base, acesso e agente têm
evidência local material; IA, NFS-e, Integra e cobrança também possuem
incrementos locais específicos. Ainda não há evidência que sustente apresentar
o conjunto como liberado para venda. A sequência segura é receber o contrato
Siescon, concluir as lacunas dependentes sem suposição e então executar os
pilotos centralizados na etapa 12 com os critérios de D-73.
