# Pendências para concluir o projeto CICA

**Teste bancário D-314/V-316 — 05/11/2026:** percurso local com anexos reais
concluído em 42 verificações finais: importação, reenvio/retomada, revisão e
relatório. Duas falhas corrigidas; 134 testes/24 subtestes PostgreSQL aprovados,
zero skips. Testar a entrada bancária não depende mais de material adicional.
Desenvolvimento/contadora ainda completam Razão/títulos/regras/importação;
operação/CONTAD completam implantação, provas D-73, treinamento e aceite.

**Publicação do código D-313/V-314 — 05/11/2026:** commit 4fede1e enviado à
main por autorização expressa e SHA remoto conferido; CI 42067809017 aprovado.
O código está no GitHub. Operador ainda publica aplicação hospedada quando
houver acesso/autorização; desenvolvimento/contadora fecham fontes/regras e
Q-47; percurso real, recuperação, treinamento e aceite CONTAD continuam abertos.

**Continuidade D-312/V-313 — 05/11/2026:** prévia offline de alocação e CLI
privada prontas, 85 testes focados aprovados, nova candidata local preservada.
Razão emitido/salvo no Windows; transferência/extração/revisão pendentes.
Candidato original sem fechamento contábil do mês/controle de títulos;
pesquisa alternativa somente leitura autorizada e iniciada. Alternativa com
fechamento fiscal 09/2026, contábil 11/2014; não elegível por inferência.
A Pagar emitido e PDF conferido no Windows, sem chave de baixa/conta/data de
pagamento na visão. Consultas de baixas/parciais limitadas retornaram sem dados.
Desenvolvimento pesquisa fontes e adapta; contadora revisa regras/período;
operador habilitado publica quando houver acesso/autorização; CONTAD treina
com o responsável e formaliza aceite. PC-19 continua aberto.

**Continuidade D-311/V-312 — 05/11/2026:** proteção de snapshots/reexportação
e preservação de decisão humana sob corrida corrigidas localmente. Contrato
offline de títulos e preparação de DE-PARA determinístico em rascunho entregues;
adaptador Domínio/IA real continuam pendentes. Regressão final: 1.578 testes
Python/151 subtestes, um skip; .NET Mac 43 aprovados/um skip Windows. Release
com manifesto e restore PostgreSQL sintético preparados, sem publicação.
[Matriz vigente e próxima ação](verificacao-conciliador-contad-2026-11-02.md).

Plano de contas encontrado em Downloads: 754 linhas candidatas privadas, não
importadas. O responsável confirmou que os relatórios Domínio solicitados ainda
não existem; desenvolvimento deve obtê-los, sem insistir em seus caminhos.
RDP acessível e login ERP feito pelo responsável. Executável ausente na rede e
pré-requisito da versão anterior superados: versão completa 10.6A-10 instalada
do repositório oficial, com assinatura válida e backup confirmado. Ajuste 2
também concluído. Reabertura pediu novo login direto pelo responsável;
desenvolvimento obtém relatórios após esse acesso, contadora revisa
fonte/regras/layout. Não é problema de DSN a ser reconfigurado.
Publicação autorizada, Q-46/Q-47, IA Q-08/Q-09, recuperação real, D-73,
treinamento e aceite CONTAD mantêm a entrega aberta.

**Autenticação revista — D-310/V-311 (04/11/2026):** o piloto dispensa CA privada
por decisão do responsável. Backend/configurador/serviço 1.0.3 usam HTTPS + HMAC,
sem certificado de cliente, preservando recorte/revogação/DPAPI. Testes locais e
CI Windows aprovados. Falta publicar backend e atualizar PC quando houver acesso;
configurar CA ou ingresso mTLS não faz parte dessa pendência. As referências
anteriores a CA obrigatória foram superadas por D-310.

**Atualização em 04/11/2026 — D-309/V-310:** correções locais de duplicidade,
recorte do agente/API, mTLS e interface/OCR testadas: 1.502 testes Python + 151
subtestes, 38 .NET e 25 checks MSI. Nginx/Django, fila Redis/Celery e restore de
cópia sintética aprovados. MSI 1.0.2 preparado; PC conserva 1.0.1, sem pareamento.
Pesquisa Q-28 escolheu candidato com 115 itens, sem envio; falta confronto de
conta/fechamento/fonte independente. Responsável ainda não tem acesso ao Fly.
Isso mantém publicação/pareamento, Q-46/Q-47 e aceite abertos. [Detalhes](verificacao-conciliador-contad-2026-11-02.md).

**Conexão de teste em 03/11/2026 — D-308/V-309:** agente 1.0.1 atualizado no
PC Windows 11 Pro AMD64 autorizado, serviço Running e teste ODBC do configurador
CICA confirmado. 28 testes .NET e 25 checks CI aprovados. Pareamento bloqueado
por 503 (CA do agente no servidor); procedimento/autorização na etapa 12.
O PC de teste não substitui acesso à cliente CONTAD nem o piloto contábil.

**Complemento em 03/11/2026 — D-305/V-304:** [Razão normalizado e conferência](../conciliacao-razao-normalizado.md)
implementados localmente, incluindo ponte das duas filas. A origem dos títulos
é **Domínio**, e a saída inclui **relatório e arquivo de importação**, conforme
respostas do responsável. Essas escolhas não devem ser solicitadas novamente.

Atualização documental em 02/11/2026, D-304/V-303. Consolidação das etapas e
pacotes PC existentes; não cria plano concorrente ou novas perguntas.
Base: PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md, checklists das etapas 00–14
e auditoria de 10/10/2026. V-302 comprova a regressão local atual, não todos os
aceites de produto. Estados publicados e operacionais não foram consultados
novamente nesta atualização; referências históricas foram reconciliadas com
decisões posteriores. Nenhuma etapa funcional é concluída por este documento.

## Prioridade imediata: contrato CONTAD

| O que falta | Responsável / dependência existente | Condição de conclusão |
|---|---|---|
| Acesso ao PC da cliente e recorte autorizado | Responsável/cliente; Q-28. Domínio local e PC de instalação já confirmados; acesso ainda prometido. | Canal protegido, empresa/conta/período e técnico identificados, sem credenciais no Git/chat. |
| Instalar e parear o agente Windows atual | Desenvolvimento + técnico; PC-17, etapas 03/12 | MSI 1.0.1/checksum/CI e atualização no PC de teste aprovados; configurador conectou ao Domínio (V-309). Pacote sem assinatura de editor. Servidor retorna 503 por CA não configurada. Faltam pareamento/serviço no recorte correto e PC da cliente; não repetir a conexão já confirmada no PC de teste. |
| Extrair partidas independentes do Razão | Desenvolvimento + contadora; PC-19/Q-28 | Fonte/consulta/semântica permitidas e dados confrontados. Itens de extrato Domínio não são partidas contábeis. |
| Implementar contas a pagar/receber | Desenvolvimento; fonte Q-28 e regras Q-46 | Origem Domínio e inclusão confirmadas. Faltam objetos/campos, parcelas, vencimento, baixas, saldo e regras; provar a comparação com o banco. |
| Homologar a integração das duas cadeias | Desenvolvimento + contadora; PC-19 | Ponte local sobre Razão normalizado implementada em D-305/V-304. Conferir a fonte real, sem equivaler extrato Domínio a partidas. |
| Concluir DE-PARA inicial com apoio de IA | Desenvolvimento + contadora; Q-46 e Q-08/Q-09 | Entradas/saídas e plano de contas definidos; sugestões revisadas; conteúdo permitido e custo antes da execução externa. Regras manuais não comprovam essa entrega. |
| Completar diferenças, saldos e exceções | Desenvolvimento + contadora; PC-19/Q-46 | Sobras nos dois sentidos, saldos por conta/período, parciais, agrupamentos, tarifas, estornos e transferências explicados. |
| Homologar o arquivo que retorna ao ERP | Cliente/contadora + desenvolvimento; Q-47 | Relatório e arquivo de importação confirmados em D-305. Conferência privada local implementada; layout/importação contábil no Domínio continuam pendentes. Aceite NFS-e não habilita exportação contábil. |
| Homologar e entregar | Proprietário + equipe CONTAD; D-73, etapa 12 | Amostra independente de 200 itens, qualidade/integridade, recuperação, treinamento inicial e aceite vinculados à release. |

Prazo contratual registrado: **09/11/2026**. Essas dependências não representam
prorrogação ou aceite. O próximo insumo da cliente é o acesso prometido ao PC,
um recorte já conferido de extrato/Razão/títulos e o plano de contas/DE-PARA.
Não repetir se pagar/receber entra ou se o Domínio é local: já foi respondido.

As correções OFX de D-303 foram concluídas localmente e testadas em V-302.
Não precisam ser reimplementadas. Ainda exigem publicação autorizada, revisão
do legado e conferência no cliente. [Detalhes e roteiro CONTAD](verificacao-conciliador-contad-2026-11-02.md).

## Conclusão da suíte CICA, além do contrato CONTAD

| Frente existente | Pendência principal | Referências |
|---|---|---|
| Release e base técnica | Conferir CI remoto da versão enviada, corrigir falhas aplicáveis, preparar release com migração/rollback e validar carga/recuperação reais. `views.py` tem dez erros de tipagem anteriores comprovados em V-302. | PC-01/09/10/30; etapas 01/12 |
| Acesso, equipe e e-mail | Homologar Brevo, confirmação, convites, recuperação e recuperação administrativa MFA; validar perfis/carteira e operação real. Remetente/privacidade remanescentes em Q-29. | PC-06/11/26; etapas 02/11/12 |
| Agente e Domínio | Homologar instalação/atualização/revogação/rede, sincronização completa, backup e pastas quando contratados; provar fonte de cada capacidade. | PC-17; etapas 03/12; Q-28/Q-31 |
| Siescon | Conferir leitura real, semântica, contas/lançamentos e importar/conferir exportação em layout aceito. A base inferida já foi aprovada; não reabrir Q-33/Q-44/Q-45. | PC-25; etapa 04; D-289/D-290/V-292 |
| IA e curadoria | Fechar limites/egressão/governança e curador; demonstrar correções/fontes/versionamento e qualidade independente; homologar relatórios publicados. | PC-21/22/23; etapa 05; Q-08/Q-09/Q-11/Q-34 |
| Triagem | Completar e homologar e-mail → segurança/extração → classificação/revisão → destino → checklist, com caixas, catálogo, políticas e Windows reais. | PC-15/16/17; etapa 06; Q-12–25/Q-31 |
| NFS-e | Completar prova fiscal independente, qualidade/cobertura, tratamento das ambiguidades e recuperação operacional da coleta. Há coleta real e importação aceita; não apresentar todo o módulo como “não iniciado”. | PC-02/04/05; etapa 07; D-295 |
| Integra Contador | Homologar operações assumidas de DTE/DCTFWeb/PARCSN e transmissões aprovadas, credenciais/representação, custos/retornos e incerteza; concluir reemissão e vínculo com atividades conforme regras remanescentes. | PC-18; etapa 08; D-149/Q-40; Q-36 para ampliação de modalidades |
| Conciliação, relatórios e Radar | Além de CONTAD, validar corpus/layouts/OCR reais, outros destinos ERP, escala; provar DRE/caixa/folha e renderer Node publicados; Radar com completude/frescor e fonte oficial. | PC-19/20/21/24; etapa 09 |
| Cobrança | Reconciliar capacidade, IA e custo efetivo Integra ao modelo D-109; completar Asaas e pagamento → acesso; homologar Pix/boleto/cartão, atraso, reativação, estorno e eventos fora de ordem. | PC-07/08; etapa 10; somente valores realmente ausentes precisam decisão |
| Jornadas do escritório | Homologar modelos, responsáveis, prazos e critérios reais; concluir ligações entre módulos e atividades, interfaces/permissões/estados, usabilidade com contadores e oferta coerente com capacidade. | PC-11–14/26/27/29/30; etapa 11 |
| Operação, privacidade e liberação | Medir restore/rollback, retomada e carga; alarmes de fontes/filas; executar retenção/portabilidade/exclusão e termos; manuais, suporte e aceite por módulo/release. Fly+Neon já escolhidos. | PC-09/10/28/30; etapa 12; Q-24/Q-29 |
| Rentabilidade | Fonte de honorários, cobertura mínima de horas, comercial, critérios reais e homologação operacional/acessível; conciliar a exigência de cobertura de testes com o resultado histórico V-291 (80,09% ante 85%, não reexecutado agora). | Etapa 14; Q-41/Q-42/Q-43 |
| IA local definitiva | Hardware/modelo, treino, avaliação, capacidade, isolamento e virada com rollback aprovados. É etapa posterior e não bloqueia venda inicial por API. | PC-31; etapa 13; D-50/D-51; Q-35 somente máquina de IA |

## O que já está resolvido e não deve voltar como bloqueio

- **Q-39/PC-03 NFS-e:** o proprietário confirmou concluída a importação externa
  em D-295. Não exigir comprovante ou repetição. Exportação contábil tem aceite próprio.
- **Q-33/Q-44/Q-45:** base Siescon inferida aceita e agente unificado .NET 8
  definidos. Falta homologação operacional e layout de importação contábil.
- **Infraestrutura SaaS:** Fly+Neon definidos e já usados; falta prova por
  release/módulo e recuperação, não escolher provedor de novo.
- **Critérios D-73 e aprovador:** já decididos. Aplicar 200 itens independentes,
  precisão mínima de 95% onde aplicável, integridade e tempos aprovados, sem
  confundir corpus sintético com aprovação do contador.
- **Fedrizzi ODBC:** D-74 confirma a conexão existente; o ambiente CONTAD é outro.
- **Contrato CONTAD:** prazo, condições, DE-PARA com IA e treinamento inicial
  já constam do contrato. Este levantamento não altera regras comerciais.

## Evidência disponível e próximos responsáveis

V-302: suíte integral PostgreSQL **1.423 testes/145 subtestes aprovados**, com
OCR português e Playwright Python opcionais ignorados; UI exercitada por Node;
23 testes .NET e builds aprovados. Isso reduz o risco local, sem concluir fontes,
integrações, precisão, operação publicada ou aceite real.

O responsável fornece acesso/material da CONTAD e resolve somente as decisões
Q remanescentes pertinentes. O desenvolvimento executa os adaptadores e
encadeamentos, prepara a release e produz evidência. Contadora/técnico conferem
as fontes e o retorno no ERP; o proprietário aprova os módulos conforme D-73.

**GitHub é entrega de código.** Push/CI não instala o agente, não aplica a
migração em produção nem homologa o produto. Autorização de publicação/ERP/custo
permanece específica, nos termos de D-304 e decisões anteriores.
