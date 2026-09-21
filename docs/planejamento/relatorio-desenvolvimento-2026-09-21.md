# Relatório consolidado de desenvolvimento — 21/09/2026

Este documento consolida as mudanças locais realizadas e verificadas nesta
sequência de desenvolvimento. Ele complementa, sem substituir, o plano mestre,
o registro de decisões e as validações datadas. Não é homologação de integração,
autorização comercial, deploy ou promessa de venda.

## Objetivo e posição no plano

O objetivo do projeto é entregar a CICA como SaaS operacional para escritórios
contábeis: configurar fontes, executar fluxos por empresa, revisar evidências,
recuperar falhas e operar permissões/cobrança compatíveis com o comportamento
real. As etapas 00–03 estão concluídas no nível de implementação e validação
local. A próxima etapa formal é a 04 (Siescon), bloqueada pela Q-33: faltam
versão, banco, mecanismo de acesso autorizado, schema, identificador de empresa
e layout de exportação. Não foram inventados adaptador, conexão ou arquivo.

As melhorias abaixo são frentes locais independentes; não declaram a conclusão
da etapa 04 nem de qualquer homologação externa.

## O que foi desenvolvido e revisado

### Base técnica e controles locais

- A tipagem estática foi estendida a todos os 190 arquivos verificados pelo
  MyPy, sem alterar contratos de integração por suposição.
- As validações Django, o estado de migrações e a suíte de regressão foram
  repetidos a cada entrega relevante.
- A navegação de históricos foi revista para evitar cortes silenciosos, sempre
  preservando filtros e o contexto das demais áreas da mesma tela.

### Triagem, NFS-e, DTE, Conciliação e operação

- Triagem: o histórico persistido de um arquivo é paginado, mostra total e
  mantém retorno; não confunde demonstração de sessão com evidência persistida.
- NFS-e: a revisão aceita acumulador somente quando ele já existe na regra ou
  observação da própria empresa.
- Caixa DTE: mensagens e histórico de consultas têm páginas independentes.
- Conciliação: processamentos, exportações, movimentos, fila OFX, auditoria e
  candidatos de um movimento podem ser percorridos sem ocultar itens antigos ou
  reiniciar as outras listas.
- Radar e console de cobrança: alertas, faturas, fechamentos e tentativas
  incertas foram revisados para não cortar históricos de forma silenciosa.
- Onboarding e ficha de empresa: históricos de importação, NFS-e, revisões e
  DTE foram separados em páginas independentes.

Essas provas usam dados sintéticos e não equivalem a arquivos reais, ERP,
Serpro, ADN, Asaas, caixa de e-mail ou fonte oficial homologados.

### Jornadas substituída pela Triagem

Conforme a decisão D-43, Jornadas deixou de ser oferta, item de navegação,
catálogo e rota. Nesta sequência, a limpeza foi concluída em duas partes:

1. V-095 removeu a definição do catálogo efetivamente usado pelo produto e
   preservou os testes de rotas legadas como 404.
2. V-096 removeu formulários, views e o template operacional órfão
   `journey.html`.

Não foi removida a demonstração isolada da CICA. O arquivo removido era somente
a antiga tela de Jornadas, já inacessível; enum, modelos, tabelas e migrações
históricos permanecem para evitar uma remoção destrutiva sem revisão explícita.

### Robustez da importação de Conciliação (V-097)

- XLSX agora é aberto antes de ser persistido. Conteúdo corrompido com extensão
  e assinatura aparentes é recusado com erro claro, sem criar fonte, lote ou
  processamento inválido.
- A prévia de CSV consome apenas as 51 linhas exibidas, evitando carregar todo o
  arquivo apenas para apresentar a amostra inicial.
- PDF malformado também é recusado antes de persistir fonte, lote ou
  processamento; PDF digitalizado válido mantém o caminho de OCR local.
- A demonstração isolada de Conciliação foi reaberta em banco temporário,
  verificada em desktop e celular sem overflow horizontal ou erros de console,
  sem enviar arquivo ou acessar serviço externo.

## Evidências desta sequência

| Entrega | Resultado local | Limite que permanece |
| --- | --- | --- |
| V-079 a V-094 | Paginação/contexto de históricos e carteiras em módulos operacionais | Evidência sintética; integrações e volumes reais pendentes |
| V-095 e V-096 | Jornadas removida do produto e do código operacional | Schema/migrações preservados; não há migração de produção |
| V-097 | XLSX corrompido rejeitado antes de persistência; prévia CSV limitada | Sem validação com layout/arquivo real ou OCR disponível |
| V-098 | PDF malformado rejeitado antes de persistência | Sem OCR, arquivo real, ERP ou exportação homologados |
| V-099 | Demonstração de Conciliação revisada em desktop e celular | Sem upload, integração ou homologação |

Os comandos, contagens de testes e limites de cada versão estão em
[VALIDACOES.md](../../VALIDACOES.md) e
[registro de execução](registro-de-execucao.md). A matriz de etapas e as
dependências permanecem em [PLANO-MESTRE.md](../../PLANO-MESTRE.md).

## Bloqueios que não foram atravessados

- **Q-33 / etapa 04:** contrato técnico Siescon.
- **Etapas 06, 07, 08, 09 e 10:** homologações de caixa/antimalware/destino,
  ADN, Serpro, arquivos/ERP, fontes do Radar e Asaas.
- **Etapa 12:** site publicado, SMTP/DNS, HTTPS/mTLS, rede, atualização
  distribuída, backup Domínio Web e escrita Windows definitiva.
- **Etapa 13:** máquina definitiva, hardware e avaliação real da IA local.

Nenhum desses bloqueios foi tratado como concluído por haver código, telas ou
testes locais.

## Próximo trabalho responsável

Enquanto Q-33 não for fornecida por canal seguro, o trabalho local pode seguir
em robustez, testes e coerência de interface dos módulos já implementados. A
implementação específica de Siescon só começa após o contrato técnico, sem
credenciais ou dados de cliente no repositório.
