# Pendências para concluir o projeto CICA

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
| Instalar e parear o agente Windows atual | Desenvolvimento + técnico; PC-17, etapas 03/12 | Pacote .NET único, MSI/checksum conferidos, DSN/driver x64, credencial somente leitura, HTTPS/mTLS e tenant corretos. |
| Extrair partidas independentes do Razão | Desenvolvimento + contadora; PC-19/Q-28 | Fonte/consulta/semântica permitidas e dados confrontados. Itens de extrato Domínio não são partidas contábeis. |
| Implementar contas a pagar/receber | Desenvolvimento; fonte Q-28 e regras Q-46 | Inclusão já confirmada. Falta origem, campos, parcelas, vencimento, baixas, saldo e regras; provar a comparação com o banco. |
| Integrar as duas cadeias de conciliação | Desenvolvimento; PC-19 | Fonte de registros e candidatos do fluxo avançado ligados com origem, conta, documento e partidas; uma confirmação não produz conclusões divergentes nas telas. |
| Concluir DE-PARA inicial com apoio de IA | Desenvolvimento + contadora; Q-46 e Q-08/Q-09 | Entradas/saídas e plano de contas definidos; sugestões revisadas; conteúdo permitido e custo antes da execução externa. Regras manuais não comprovam essa entrega. |
| Completar diferenças, saldos e exceções | Desenvolvimento + contadora; PC-19/Q-46 | Sobras nos dois sentidos, saldos por conta/período, parciais, agrupamentos, tarifas, estornos e transferências explicados. |
| Confirmar o resultado que retorna ao ERP | Cliente/contadora + desenvolvimento; Q-47 | Definir conferência/arquivo/operação. Se houver importação, comprovar no Domínio; aceite NFS-e não habilita exportação contábil. |
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
