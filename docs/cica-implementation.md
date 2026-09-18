# CICA — implementação em andamento

## Direção aprovada

- Marca: CICA, Central de Inteligência Contábil Avançada; marfim e verde-escuro.
- Domínio escolhido: cicacontabil.com.br. Fornecedora: Mewstack Desenvolvimento de Sistemas Ltda., CNPJ 68.340.160/0001-13.
- Suíte completa; teste automático de 14 dias sem cartão e sem MFA obrigatório no teste; obrigatório após teste/contratação.
- Inferência em servidor Mewstack; API externa somente como fallback, custeado pela Mewstack e limitado.
- Configuração e operação pelo console web do desenvolvedor: IA, cotas, catálogo comercial, e-mail, acessos e registro interno da cobrança. A Mewstack cobra cada escritório fora da CICA; o produto não coleta cartão nem chama gateway de pagamento.
- Lançamento exige suíte completa e homologação Domínio/Siescon. Não há autorização para gerar custos externos.

## Evidências realizadas

- Suíte completa executada em 14/09/2026: 427 testes aprovados e 2 subtestes aprovados. Um cenário de navegador permaneceu marcado como opcional porque o ambiente não disponibilizou Playwright/browser; isso não comprova validação visual.
- A cobertura foi alinhada ao estado então aprovado: Copiloto oculto até a infraestrutura local existir, sem franquia publicada na landing; após o teste, a carência não suspende escritório automaticamente, pois a decisão de cobrança era manual pela Mewstack. A decisão posterior de Claude temporário e Asaas está registrada em `docs/planejamento/`.
- Leitura dos pontos de entrada hub, plataforma e MFA; serviços de cadastro, preços, pagamentos, webhooks e parte do gateway de IA.
- Falha encontrada: link de cadastro consumido retornava o proprietário e permitia autenticação repetida. Removido retorno; testes de replay e expiração passaram (2 testes).
- Estado consumido agora considera verified_at, inclusive quando a organização foi removida.
- Cadastro público simplificado para nome, e-mail e CNPJ. A razão social é consultada no servidor; o e-mail só abre a definição de senha, e a conta é provisionada somente após o POST válido. O teste inicia com a suíte completa, preço zero e sem cobrança automática enquanto o catálogo comercial permanece em revisão.
- Testes cobrem confirmação sem provisionamento no GET, senha posterior e teste completo; 3 testes de cadastro passaram nesta rodada.
- A validação visual precisa ser repetida quando houver navegador Playwright/MCP disponível. Nesta sessão, a ferramenta retornou inventário vazio; não há evidência nova de navegador a declarar.
- Identidade textual substituída nos templates que continham CICA/HubContador; IDs e caminhos técnicos preservados.
- Tokens marfim/verde-escuro introduzidos; revisão visual em andamento, não concluída.
- Console /platform/configuracoes/ permite ao desenvolvedor com MFA editar contatos/horário/endereço da Mewstack, com auditoria; suporte e comercial não podem editar.
- Minutas versionadas de termos, privacidade e tratamento de dados em /legal/. Dados de contato vêm do console. Ainda não são versão final para contratação.
- Migração platform.0012 aplicada localmente, após conferir que o plano continha somente a tabela nova.
- 11 testes passaram: configuração/permissões, segurança do cadastro e pagamentos existentes. Sem divergência de migrações no check.
- O cadastro guarda a versão de termos e privacidade, instante de aceite e hash do IP. O opt-in de marketing é opcional, inicia desligado e fica registrado separadamente; ele nunca condiciona o teste gratuito.
- Playwright MCP: login e três páginas legais em 1440 e 390 px retornaram 200, sem overflow horizontal nem pageerror. Foco de teclado e cores do login conferidos; screenshot mobile inspecionado. Todas as sessões abertas nesta rodada foram fechadas.
- Web Interface Guidelines consultadas na fonte Vercel. Revisão completa de todos os templates alterados e inspeção autenticada do console ainda pendentes; não declarar auditoria visual integral concluída.

## Evidência adicional — Copiloto não lançado

- A chave global `copilot_available_for_offices` inicia desligada. Enquanto estiver desligada, landing, cadastro, teste, navegação, cards, condições e documentos públicos não mostram o Copiloto; URLs diretas, exportações e MCP retornam 404.
- O console de desenvolvedor permite preparar franquia e liberar o recurso com Claude Sonnet temporário ou com infraestrutura local. A liberação exige uma rota utilizável, política por escritório e limites positivos; não basta habilitar a interface.
- Endpoint, modelo e token do runtime textual, além do endpoint privado do adaptador de documentos, são configurados pelo console. A chave Claude central pertence ao ambiente da Mewstack (`CICA_CLAUDE_API_KEY`); nenhum segredo é devolvido pela interface, auditoria ou logs. O runtime local tem precedência quando estiver disponível.
- O nome da imagem/modelo no contêiner multimodal continua sendo uma configuração de implantação, porque inicia um serviço privado antes de o SaaS estar disponível. A ponte entre a CICA e esse adaptador já é configurável pelo console.

## Evidência adicional — e-mail transacional

- A configuração SMTP foi movida para o console de desenvolvedor com servidor, porta, TLS, usuário opcional, segredo cifrado e remetente. O segredo é de escrita única: não aparece na tela, em evento de auditoria ou em logs.
- O botão de teste abre e fecha a conexão SMTP; ele não envia mensagem nem persiste a tentativa. A configuração só é gravada por **Salvar e-mail**.
- Produção usa o backend que lê esta configuração no momento do envio. Confirmações, convites e recuperação de senha deixam de depender de credenciais SMTP em variáveis de ambiente.
- Falhas de entrega não deixam cadastro ou convite parcialmente gravados: o formulário mostra um erro operacional e preserva os dados digitados para nova tentativa.
- Testes focados de configuração, cadastro, recuperação e convite: 69 aprovados em 14/09/2026. Não houve envio para provedor externo.

## Matriz inicial

| Requisito | Entrada | Regra | Evidência / pendência |
|---|---|---|---|
| Confirmação de cadastro | /comecar/verificar/ | Token expira, é de uso único e só provisiona após senha em POST | test_cica_signup_security.py e test_cica_signup_flow.py |
| Teste / MFA | /comecar/, /mfa/ | 14 dias; MFA após teste | Integração contratual a revisar |
| Cobrança | /platform/escritorios/&lt;id&gt;/ e `POST /platform/webhooks/asaas/` | Status interno de contrato/cobrança, restrito ao time da Mewstack; receptor Asaas autenticado e idempotente atualiza apenas tentativas Asaas conhecidas | Ainda não há criação de cliente/cobrança Asaas, checkout, Sandbox homologado nem regra aprovada de carência/suspensão; ver `docs/planejamento/asaas-operacao.md` |
| Marca | Templates públicos/autenticados | CICA marfim/verde | Troca inicial; todas as telas ainda precisam de inspeção |
| Console dev | /platform/ | Configuração restrita e auditada | Expansão pendente |
| E-mail transacional | /platform/configuracoes/ | SMTP cifrado, teste sem envio e remetente central | 69 testes focados; provedor e domínio de envio ainda precisam ser escolhidos e homologados |
| Integra Contador | serviços fiscais Serpro | Credenciais globais ainda são lidas do ambiente | A configuração no console depende de definir se o contrato/certificado é central da Mewstack ou individual por escritório; não migrar sem essa decisão |
| Jornadas internas / Siescon | Jornada / conectores | Jornadas privadas do time; Siescon sem adaptador e sem coleta de credenciais | Siescon pendente de implementação e homologação autorizada |
| Copiloto não lançado | Landing, cadastro, rotas IA/MCP | Flag global desligada por padrão; 404 fora do console dev | Infraestrutura local e configuração dos runtimes no console pendentes |

## Pendências de lançamento

Leitura integral de todos os arquivos próprios e matriz completa; expansão do console; documentos legais e aceite final; recuperação de senha; jornadas internas; implementação e homologação dos conectores; copiloto e cotas; nova pesquisa/preços; processo operacional de cobrança externa; escolha/homologação do provedor SMTP e DNS de envio; backups/restauração; testes ponta a ponta em todas as telas. Contatos/horários de suporte, franquias e preços dependem do fechamento comercial. Revisão jurídica das minutas e homologação externa ainda não realizadas.

Não considerar este registro uma certificação de segurança, auditoria concluída ou autorização para lançamento.
