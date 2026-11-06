# CONTAD — resumo e continuidade

Atualizado em 06/11/2026. Continuidade de **D-320/V-322/V-323**, etapas 03/09/12,
PC-19 e Q-28/Q-46/Q-47.

**Situação:** a prévia está publicada no CICA e o agente está instalado no PC
da cliente. A conexão local funcionou. O agente ainda não foi pareado e o
conciliador ainda não está homologado.

## O que já fizemos

- Implementamos a **prévia privada de conferência**, com controle de acesso,
  hash e auditoria. Publicamos a **release Fly 72**, fonte `f86ae4d`, após CI,
  testes locais, migrações e verificações do servidor.
- Fizemos backup Neon/Tigris e ensaio de restauração antes do deploy.
  Retenção até **13/11/2026**; credencial temporária revogada.
- Criamos o escritório **CONTAD** separado dos demais, em `activation_pending`.
  Acesso ainda pendente; login responsável já informado em evidência privada.
- O operador instalou o **agente 1.0.3** e informou serviço Running/Automatic,
  inicialmente awaiting_configuration. Testes ODBC e do configurador funcionaram
  com **CICA_CONTAD x64 / SQL Anywhere 17 / srvContabil / EXTERNO**.
- Definimos o piloto: **SURIA COMPONENTES E ACESSORIOS PARA MODA LTDA**,
  empresa **212**, conta contábil **8 — BANCO SICREDI**, **09/2026**.
- Conferimos PDF/OFX bancários e Razão real: **163 movimentos coincidem em data
  e valor**, e os saldos dos PDFs coincidem. Há valores repetidos; isso não
  confirma conciliações nem fornece todas as partidas contábeis.
- A consulta restrita, autorizada e executada pelo operador, encontrou um
  cabeçalho desse recorte com 163 itens. O ID está na evidência privada.
- A captura da conta 8 confirmou cadastro analítico/ativo, sem agência ou
  número da conta bancária visíveis.

## O que falta agora

**Esclarecimento humano vigente — V-323:** o responsável informou que a empresa
está fechada e os arquivos foram fornecidos para teste, determinando usá-los
como evidência. Não exigir origem do saldo da tela ou perguntar quem importou
para testar esse corpus. A diferença anterior fica registrada, sem causa presumida.

O leitor do Razão PDF e a CLI local já reproduziram o confronto: 163 movimentos,
159 candidatos únicos, dois grupos ambíguos, zero sobras por data/valor e saldos
dos PDFs iguais. Relatório rastreável por página/linha e hashes, sem confirmar
alocações ou criar partidas. Rodada com 139 testes aprovados/cinco skips
PostgreSQL; execução real sem rede/banco. [Uso e limites](conciliacao-razao-normalizado.md).

1. **Concluir acesso/ativação CONTAD**, sem inventar contrato, condições
   comerciais, papéis ou convites.
2. Para o percurso real do agente, definir/autorizar seu recorte e, após acesso,
   preparar manifesto restrito,
   parear e testar autenticação, ausência de senha no DSN, LocalSystem,
   paginação/repetição/retomada. Teste interativo não comprova o serviço.
3. Completar partidas do Razão, títulos/baixas, regras, DE-PARA, treinamento e
   aceite. Os 163 eventos não atendem os 200 itens independentes de D-73.

## Como continuar

Leia [PLANO-MESTRE](../PLANO-MESTRE.md), [DECISOES](../DECISOES.md) e
[VALIDACOES](../VALIDACOES.md), nessa ordem; depois etapas 03/09/12 e
[dúvidas abertas](planejamento/duvidas-abertas.md). Detalhes técnicos de
publicação/backup: [roteiro de release](contad-release-2026-11-05.md).

A preparação privada está em
`.tmp/contad-development-2026-11-06/contad-suria-pilot-request.json`;
ela aponta fontes, diagnóstico e comparação. **Não é manifesto aprovado.**
O prompt completo está em `/Users/pedromachado/Downloads/CONTAD-prompt-continuidade.txt`,
fora do Git. Originais bancários e Razão permanecem nos Downloads do Mac.

O usuário executa passos guiados no Windows: controle nativo AnyDesk falhou.
Não repetir instalação, sonda ou perguntas respondidas sem motivo. Senha somente
no PC, nunca no chat. Não corrigir saldos, reimportar, ampliar SQL, enviar dados
ou gerar custos por inferência. Exportação Domínio continua desabilitada.

Relatório privado da retomada:
`.tmp/contad-ledger-evidence-2026-11-06/conferencia-final.json`, com verificação
dos originais e bloqueio de conexões em `verification.json` na mesma pasta.

Últimas atualizações e evidências estão no workspace local; preservar mudanças
anteriores. A retomada V-323 implementou apenas a conferência local, sem novo
deploy ou conclusão dos gates.
