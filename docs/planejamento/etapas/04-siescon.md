# Etapa 04 — Implementar e homologar Siescon

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento em 28/09/2026. D-117 resolveu Q-33 para a implementação local usando o layout Btrieve inferido no Lucrums. O agente unificado já inclui leitura Siescon via ponte ODBC x86 e contratos de empresas e folha; V-116 confere as colunas do resultado antes de transmitir linhas e exige conector Siescon próprio. Não houve acesso ao ERP nesta estação. Exportação de lançamentos continua bloqueada por falta do layout de importação e a etapa não está homologada.

**Dependências:** 02–03.

**Decisões relacionadas:** D-53, D-54, D-117, D-121.

## Escopo e checklist

- [-] Identificar versão, banco, mecanismo permitido de acesso e ambiente disponibilizado. O levantamento Lucrums identifica Pervasive PSQL v10/Btrieve e ODBC x86 na origem; falta conferir o ambiente autorizado CICA.
- [-] Obter schema e arquivos de referência por acesso autorizado. D-117 aceitou o layout inferido e os DDFs como base técnica, sujeitos a ensaio em cópia e conferência no ERP.
- [-] Preparar leitura, sincronização e diagnóstico. Empresas e folha têm contratos no catálogo e ponte x86; o conector próprio, o limite de linhas, o hash e a conferência de colunas falham visivelmente. Usuários ficam fora de despacho por semântica de atividade desconhecida; tributação segue não validada. Não há prova ODBC real CICA.
- [-] Mapear empresas, contas, lançamentos e demais dados necessários aos fluxos contratados. O levantamento cobre cadastro e folha; não fornece schema confiável de contas e lançamentos.
- [-] Preparar exportação revisada no layout efetivamente suportado. D-88 separou destino e adaptador; Siescon é recusado até existir layout de importação revisado, sem gerar arquivo fictício.
- [x] Generalizar vínculos hoje dependentes exclusivamente do código Domínio. `AccountingExport` passou a registrar destino/versionamento e a fonte Siescon existe no modelo; a compatibilidade permanece bloqueada até a revisão do adaptador.
- [x] Registrar [matriz de capacidades](../../siescon-matriz-capacidades.md): o que funciona com Domínio, Siescon ou ambos.

## Bloqueios e responsabilidade

Q-28 permanece para o escopo operacional. Q-33 foi resolvida por D-117 quanto à base técnica; faltam confirmação semântica dos campos de usuários/tributação, layout de importação de lançamentos e acesso autorizado à instalação CICA. A inspeção local não encontrou DSN ou driver Siescon nesta estação; nenhum script de DDF deve ser aplicado ao share de produção sem autorização específica.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Leitura autorizada, escopo por empresa, cursor/repetição, revogação, exportação revisada e importação conferida no Siescon; sem gravação direta.

**Critério de aceite:** Dados sincronizados conferem com o Siescon; arquivo exportado é importado e conferido no ambiente de homologação. Gerar arquivo não basta.

## Evidências e próximo passo

V-029 registra a ausência de DSN local; V-030, a base de destino/adaptador versionado; V-041, o bloqueio anterior; V-116, as proteções de leitura nesta branch. A [base técnica inferida](../../siescon/README.md) permite desenvolver o caminho local, mas não prova compatibilidade no ambiente CICA. Próximos passos: ensaiar DDFs em cópia autorizada, confirmar campos de atividade e regime na tela, obter layout de importação contábil e conferir leitura, identificação de empresas e arquivo importado no Siescon. Nenhuma homologação nova foi atribuída a esta etapa.

## Prompt de execução

> Execute a etapa 04 usando o servidor/banco Siescon disponibilizado pelo responsável. Descubra e documente o contrato técnico antes de programar o adaptador. Entregue leitura e exportação revisada, valide identificação das empresas e homologue a importação. Não invente endpoints, layouts ou permissões.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
