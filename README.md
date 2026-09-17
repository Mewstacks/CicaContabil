# CICA — Central de Inteligência Contábil Avançada

[Documentação](docs/README.md) · [Planejamento e decisões](docs/planejamento/README.md) · [English](README.en.md)

**Memória vigente na raiz:** [Plano mestre](PLANO-MESTRE.md) · [Decisões](DECISOES.md) · [Validações](VALIDACOES.md) · [Etapas e prompts](docs/planejamento/etapas/README.md).

Em 17/09/2026, o responsável limitou esta entrega à **etapa 00 — consolidar documentação**. As próximas etapas estão planejadas, não concluídas. Consulte esses registros antes de perguntar regras já decididas ou iniciar implementação.

A CICA é o sistema da Mewstack para a operação de escritórios contábeis. O repositório contém o SaaS Django, o console da plataforma, tarefas Celery, integrações fiscais e um agente Windows para leitura autorizada do Domínio. A meta atual é fazer **cada função completar seu trabalho operacional antes da venda**. A existência de uma tela, modelo ou teste isolado não significa que o módulo esteja homologado.

O [estado operacional](docs/planejamento/estado-operacional.md) registra o que foi verificado, o que falta e qual evidência libera cada área. As [decisões confirmadas](docs/planejamento/decisoes.md), as [dúvidas abertas](docs/planejamento/duvidas-abertas.md) e as [ações do responsável](docs/planejamento/acoes-do-responsavel.md) são a referência para regras de produto; planos antigos estão identificados por origem e não viram especificação automaticamente.

O [registro histórico P0 de 15/09](docs/planejamento/execucao-p0-area-de-trabalho-2026-09-15.md) registra correções de tela por tarefa e a prova então alcançada. Não é um plano concorrente: o estado vigente e o próximo trabalho estão no plano mestre. Implementação, testes locais e homologação externa são estados distintos.

## Iniciar no PC local

Requer Python 3.12 a 3.14 e `uv` 0.12.0. Para uma instalação de desenvolvimento com SQLite:

```powershell
python -m pip install uv==0.12.0
uv sync --locked --all-extras
uv run python scripts/init_local.py --sqlite
uv run python manage.py migrate
uv run python manage.py migrate --database=knowledge
uv run python manage.py runserver
```

`init_local.py` cria o `.env` com segredos locais aleatórios e recusa sobrescrever um arquivo existente. Se o `.env` já existir, preserve-o e continue a partir das migrations. O banco `knowledge` é separado dos dados dos escritórios; migre ambos. Redis é opcional no desenvolvimento SQLite; PostgreSQL, Redis e workers Celery são necessários para validar as rotinas em um ambiente semelhante ao de produção.

Abra `http://127.0.0.1:8000/entrar/` para o escritório e `http://127.0.0.1:8000/platform/` para o console Mewstack. A API está em `/api/v1/`, a documentação OpenAPI em `/api/docs/` e o admin Django em `/admin/` quando habilitado. O cadastro público, a confirmação por e-mail, a recuperação de senha e o MFA existem no código, mas dependem de SMTP e homologação para um uso comercial real.

Depois de configurar o segundo fator, o botão de saída dos códigos de recuperação leva à área do escritório ou ao console. Um acesso iniciado pelas configurações volta a elas. As credenciais Serpro da Mewstack são **centrais**: configure `INTEGRA_CONSUMER_KEY`, `INTEGRA_CONSUMER_SECRET`, `INTEGRA_CERTIFICATE_PATH` e `INTEGRA_CONTRATANTE_CNPJ` no `.env` protegido do servidor; o console `/platform/configuracoes/` mostra o estado dessa configuração. Escritórios não devem receber essas chaves. Ter variáveis preenchidas não substitui contrato, tarifa e homologação dos serviços.

Os comandos `uv run python manage.py seed_demo` e `uv run python manage.py seed_personas` criam dados locais de demonstração apenas com `DEBUG` ligado. `seed_personas` imprime credenciais temporárias; use somente em desenvolvimento. Dados de demonstração e testes automatizados não provam a operação dos fornecedores externos.

Para desenvolvimento com PostgreSQL e Redis, crie o `.env` sem `--sqlite`, suba os serviços de `compose.yaml` e aplique as migrations nos dois bancos. Os detalhes de [arquitetura](docs/pt-BR/arquitetura.md), [segurança](docs/pt-BR/seguranca.md), [LGPD](docs/pt-BR/lgpd.md) e [backup](docs/pt-BR/runbooks/backup-restauracao.md) ficam na documentação técnica.

## Claude agora; modelo local depois

A chave Claude é **única da implantação Mewstack**. Ela já foi adicionada ao `.env` como `CICA_CLAUDE_API_KEY`; não a cadastre em cada escritório nem a copie para documentos, logs ou templates. A Anthropic aceitou a chave para `claude-sonnet-5` na **contagem gratuita de tokens** e em **uma geração real, sintética e limitada**, autorizada pelo responsável (16 tokens de entrada, 64 de saída; custo calculado de US$ 0,000672 antes de câmbio/impostos). Isso valida o transporte da API, mas não o Copiloto em uso pelo escritório. O console da plataforma define o modelo permitido, os tetos globais e a liberação do Copiloto. Cada escritório precisa de sua política de acesso e cotas próprias. O Copiloto está oculto por padrão até que limites, consentimento e oferta estejam configurados e validados. A escolha atual é Claude **Sonnet 5**; as franquias comerciais ainda estão em confirmação.

O endpoint e o modelo do futuro PC privado já são configuráveis no console. Quando o runtime local estiver disponível, a aplicação tenta usá-lo primeiro; a política de Claude externo permanece sob controle global e por escritório. A análise de anexos da Triagem também deverá usar essa chave central, mas o fluxo de e-mail e as regras de privacidade/classificação ainda não estão completos. A [memória de IA e custo](docs/planejamento/duvidas-abertas.md#ia-e-custo) separa o que foi decidido do que precisa de resposta.

## Módulos e integração operacional

| Área | Estado verificável nesta versão de trabalho | Para a venda |
| --- | --- | --- |
| NFS-e Inteligente | Coleta ADN por NSU implementada com A1, checkpoint, dedupe, retentativa e operação em lote; classificação/revisão dos XMLs | Homologar certificado e resposta reais no ADN restrito antes de habilitar a coleta externa |
| Central Integra Contador | Entrada com três escolhas confirmadas: Caixa DTE, Parcelamentos e DCTFWeb. A Caixa tem busca/seleção de toda a carteira, preparo local, fila “A abrir” separada de abertura em andamento/ciência a conferir, detalhe sob consentimento jurídico e continuação de páginas por empresa com nova autorização de consumo. Parcelamentos PARCSN tem busca da carteira, seleção em lote, cotação/autorização por tokens, pedidos, detalhe, parcelas, emissão e download do DAS persistido, com retorno incerto sem repetição automática. Guias/DCTFWeb lê apurações da Folha via ODBC e permite preparar declaração completa, recibo e emissão com estado persistido e PDF salvo. | Criar e aceitar a tabela comercial de tokens do escritório e homologar DTE, PARCSN e DCTFWeb em chamadas reais autorizadas com o contrato Mewstack. Modalidades além do PARCSN ordinário continuam fora deste corte. |
| Conciliação OFX × Domínio | Importação e cruzamento determinístico com confirmação de ambiguidades | Validar o espelho Domínio e casos reais por escritório/empresa |
| Radar da Reforma | Coleta de fontes oficiais e alertas com links | Provar rotina, frescor, falha e recuperação em ambiente operacional |
| Copiloto | Conversa por empresa com busca, evidências, anexos e relatórios; envio idempotente, aviso da chamada incerta e roteamento local/Claude; chave e geração sintética Sonnet comprovadas | Resolver reservas incertas no suporte, aprovar cotas/consentimento e validar conversa real do escritório, falhas e futura virada para PC local |
| Triagem de Arquivos (substitui Jornadas) | Domínio e estados, OAuth Microsoft/Google e assistente IMAP testados localmente; leitores incrementais e quarentena sintéticos; lista operacional filtrável de anexos, sem servir binários não verificados; padrão puro da pasta Windows | Ativação guiada, homologar caixas/scanner reais, proteger/analisar anexos e arquivar em biblioteca interna **ou** pastas Windows escolhidas pelo escritório |
| Siescon | Sem adaptador ou contrato técnico homologado | Obter documentação e piloto autorizado antes de liberar |

Para conectar sua caixa, o administrador do escritório cadastra **seu aplicativo OAuth** Microsoft 365/Google Workspace na Triagem seguindo o guia interno e depois autoriza a própria caixa no provedor. **Gmail pessoal** usa um aplicativo Google verificado da Mewstack, quando registrado e homologado, sempre com consentimento da caixa de cada escritório. O segredo do aplicativo e o refresh token ficam cifrados; callback, isolamento por escritório e teste de leitura foram validados com provedores simulados. A Mewstack ainda precisa definir o retorno HTTPS de produção e verificar seu app Gmail pessoal; cada escritório precisa registrar o app Microsoft/Workspace e homologar a caixa real. O assistente IMAP genérico testa TLS/leitura e cifra a credencial, mas também requer piloto com um servidor autorizado. **Conectar não inicia a leitura incremental nem o arquivamento.** A [pesquisa e jornada de conexão](docs/planejamento/conexao-caixas-email.md) registram passos e permissões. Para Windows, o escritório escolherá sua raiz; o [padrão técnico de pasta](docs/planejamento/padrao-pastas-windows.md) calcula `Nome [Domínio código]` com código obrigatório, ainda sem escrita. Falta definir a fonte do nome e regra de renomeação. O agente atual lê o Domínio por ODBC de modo autorizado; escrita documental segura no Windows não está implementada. A [verdade dos módulos](docs/cica-module-truth.md) e o [plano da triagem](docs/plano-triagem-documental.md) descrevem os limites em detalhe.

## Contrato, cobrança e produção

O modelo comercial decidido é **mensalidade mínima por módulo, franquia de tokens separada por módulo e excedente automático até o teto mensal aceito pelo escritório**. Um token CICA terá preço único e consumo em números inteiros; ações custarão pesos diferentes. O [levantamento de mercado, custo e arquitetura](docs/planejamento/precificacao-tokens-modulos.md) usa **R$ 0,05 por token como referência para avaliar**, conforme indicação do responsável, sem publicar preço-base, franquias ou pesos como aprovados. Os pesos Integra devem ser dimensionados pela **faixa mais cara vigente do Serpro**, mesmo que o consumo central Mewstack obtenha desconto de faixa. A carteira técnica de tokens já cota, reserva, liquida e fecha uma fatura com linhas por módulo em testes locais; a flag `TOKEN_BILLING_ENABLED` permanece **desligada** até preço/franquias/pesos aceitos, migração de todas as operações e validação contra dupla cobrança. A área do escritório exibe somente tokens; o medidor legado por unidade permanece apenas como compatibilidade interna das operações ainda não migradas e não aceita nova política comercial pela tela. O [fechamento mensal](docs/planejamento/auditoria-fechamento-competencia-2026-09-15.md) agora espera consultas reservadas e mira sempre o mês completo anterior, inclusive nas tentativas diárias. **Asaas foi escolhido como cobrança padrão** para Pix, boleto e cartão; contratos manuais com preço individual também serão admitidos. O receptor de webhook Asaas já valida token de autenticação, eventos idempotentes e conciliação de uma tentativa conhecida, mas permanece oculto até `ASAAS_WEBHOOK_TOKEN` ser definido. Criação de cliente/cobrança, configuração sandbox/produção, reconciliação e suspensão após carência ainda precisam de implementação e regras finais.

Há configurações para Fly.io e para o servidor Windows Cobalchini. Uma configuração de deploy não prova ambiente publicado. O [runbook Cobalchini](docs/operations-cobalchini.md) descreve Compose, mTLS e rollback; há workflow manual protegido, sem deploy automático, e o destino de produção ainda está em confirmação. No host Cobalchini, defina `COBALCHINI_ENV_FILE` para o arquivo protegido fora do checkout antes de executar o Compose. Nenhum recurso pago é provisionado pela preparação local. A única chamada cobrada executada foi a prova sintética Claude descrita acima, mediante autorização específica.

## Verificar alterações

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

Em 16/09/2026, a suíte local teve **672 testes aprovados, 1 ignorado e 8 subtestes aprovados** após a entrada de anexos de e-mail em quarentena, leitores incrementais IMAP/Microsoft Graph/Gmail, agendamento opt-in e retentativa simulados, veredito antimalware candidato por ClamAV local, fila de anexos com escopo por empresa, continuação autorizada de páginas DTE, carteira técnica de tokens, fechamento mensal por escritório, download íntegro da biblioteca interna, protocolo de arquivamento Windows com prova de raiz/caminho/tamanho/hash e revisão de caso NFS-e com evidência e decisão no mesmo lugar. A demo agora mantém DTE, Guias, Parcelamentos, coleta NFS-e, Triagem e Copiloto na sessão de cada navegador. A Visão Geral abre filas filtradas por área; Guias, Revisões, Triagem e Conciliação pesquisam a carteira do escritório antes de exigir contexto unitário. Também há testes locais para auditoria de tokens Sonnet e recuperação da conversa do Copiloto. Não há caixas reais nem scanner instalado/homologado neste PC; resultados limpos só avançam da quarentena após a validação local de formato e hash. A escrita Windows compila e passa nos testes de isolamento, mas precisa de homologação na pasta real do escritório. Testes locais precisam ser complementados por homologação de Serpro, NFS-e, Domínio, e-mail, pagamento e uso do Copiloto por escritório. O [registro de execução](docs/planejamento/registro-de-execucao.md) e o [P0 em execução](docs/planejamento/execucao-p0-area-de-trabalho-2026-09-15.md) registram resultados e limites; as auditorias específicas de DTE, Triagem, cobrança e IA estão no [índice de planejamento](docs/planejamento/README.md).

O produto ainda precisa de contatos de suporte/privacidade, termos finais, retenção/exportação e prova de backup/restauração. Os controles técnicos de criptografia, auditoria, isolamento e MFA ajudam a operar com segurança; a adequação jurídica depende de decisões e revisão próprias.
