# Contingência de aplicação para vínculos D-373

D-375, 18/11/2026. Esta fonte mantém o percurso da release 100 (`91af8407`)
e acrescenta somente a compatibilidade necessária para usar vínculos mensais
já confirmados pela descoberta. Não é uma nova implementação da descoberta.

- Modelos e migração `hub.0088_account_discovery` são idênticos a `02c13b0`.
- Identidade, validação de linhas e descompressão limitada dos blocos retidos
  preservam as funções originais. Não existe serviço de importar ou confirmar
  descoberta, nem suas rotas, formulários ou telas nesta contingência.
- Solicitação e admissão dos jobs reconferem competência, revisão, identidade
  da conta, escritório, empresa, plano e fatos privados retidos. A prova de um
  mês não permite outro. Alteração da fonte ou UUID malformado recusa o pedido.
- A edição genérica do vínculo recusa `discovered_account_review`, preservando
  confirmação e histórico. Sua revisão exige voltar ao fluxo da descoberta em
  uma versão compatível; esta contingência não permite retirar a guarda mensal.
- Vínculos humanos legados e o piloto respaldado por fonte já importada mantêm
  seu comportamento. Não se cria revisão humana para reutilizar o piloto.

O retorno de aplicação deve preservar a migração 0088, todas as quatro tabelas,
os vínculos, as fontes e as decisões posteriores. Não executar migração inversa,
restaurar banco antigo ou apagar dados para retornar à interface da release 100.
A release 100 original sem estas guardas não é destino seguro após ativar vínculos
da descoberta. A configuração, o canal do agente 1.0.13, as máquinas existentes e
o gate de exportação conservam os valores operacionais conferidos antes do corte.

As provas desta preparação são locais e sintéticas. As evidências privadas ficam
em `.tmp/contingency-evidence/`: testes, conferência da identidade dos arquivos e
funções originais, migrações nos dois aliases e manifesto da fonte. O código de
aplicação não inclui essas evidências nem dados reais da CONTAD.

O ensaio de imagem local foi interrompido: a imagem base constava no inventário,
mas faltavam blobs locais; sua materialização falhou. Não houve pull autorizado
nem imagem de contingência validada. O manifesto da fonte não comprova imagem
publicada, execução em 512 MiB, rollback real, recuperação operacional ou aceite.
Antes de ativar os vínculos em produção, preparar a imagem exata pelo processo
autorizado, conferir hashes e compatibilidade e garantir sua disponibilidade.
