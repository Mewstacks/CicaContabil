# Pacote fiscal — especificação dos quatro módulos (E7, 20/11/2026)

Escopo aprovado em D-306: emissão de NFS-e por procuração, RBT12/Fator R/teto do Simples e do MEI, Reforma IBS/CBS, situação fiscal e pendências. **Nenhum dos quatro tem código nesta entrega.** Motivo, módulo a módulo, abaixo: cada um depende de dado, norma ou custo que ainda não está provado, e módulo fiscal que erra não se desfaz sozinho. Esta página é o ponto de partida de cada PR (um por módulo, D-303).

Regras comuns: fonte oficial citada no código e na tela; aprovação humana antes de qualquer efeito legal; custo Serpro mostrado **antes** da chamada e repassado sem margem (D-109); módulo desligado por padrão (`NOT_SELF_SERVICE_MODULE_CODES`); nada de RPA de tela do Domínio.

## 1. RBT12, Fator R e teto do Simples e do MEI (primeira fatia recomendada)

**O que é.** Alerta de quanto da receita bruta já foi usada em relação ao teto, por empresa, com aviso em 80%, 90% e 100%; e o Fator R (folha dos 12 meses ÷ RBT12) para empresa de serviços do Simples, que decide o Anexo III ou V.

**Dado que já existe.** `NfseDocumentSide` guarda, por nota, `direction`, `competence`, `issued_on`, `service_amount`, `net_amount` e `situation` (ativa, cancelada, substituída) lidos do XML imutável (`hub/nfse_facts.py`). Folha: `PayrollPeriodSnapshot` (totais de folha importados, `hub/payroll.py`).

**O que falta (por isso não foi feito).**
1. Receita de NFS-e é **só serviço**. Venda de mercadoria (ICMS) e receita sem nota não estão no CICA; o RBT12 "de verdade" vem do PGDAS-D (Integra, custo por chamada). Um número parcial apresentado como RBT12 engana. A fatia segura se chama "receita de serviço por NFS-e" e mostra o que ela **não** cobre.
2. Limites vigentes precisam de fonte datada. Pesquisa de 20/11/2026: MEI R$ 81.000 por ano e Simples R$ 4,8 milhões, com sublimite de R$ 3,6 milhões para ICMS e ISS; o portal oficial do teto do MEI ([gov.br/memp/teto-do-mei](https://www.gov.br/memp/pt-br/teto-do-mei), alterado em 04/07/2026) trata de "atualização progressiva" e o trecho lido não trouxe valor novo. **Confirmar o número no Portal do Empreendedor antes de escrever a tabela** (LC 123/2006; Resolução CGSN 140/2018: conferir artigos). A tabela entra no código com fonte e data de vigência, nunca como constante solta.
3. MEI: o teto é proporcional aos meses de atividade no ano de abertura; excesso de até 20% tem regra própria.

**Aceite da primeira fatia.** Por empresa com regime MEI ou Simples (`ClientCompany.tax_regime`): receita de serviço por NFS-e no ano-calendário e nos 12 meses anteriores, percentual do teto, aviso em 80/90/100%, planilha para o Domínio; texto "só NFS-e" visível; teste com nota cancelada e substituída fora da soma; custo zero (sem Serpro).

## 2. Situação fiscal e pendências

Leitura do relatório de situação fiscal pelo Integra Contador (SITFIS), agregada por carteira, só leitura. **Pré-requisitos:** contrato Serpro da conta central; procuração eletrônica no e-CAC do cliente ao escritório para os serviços do Integra (é **outra** procuração, diferente da de NFS-e do Portal de Serviços); custo por chamada (faixa 1: consulta R$ 0,24, fonte em `proposta-precos.md` §2.1). `integra/` já tem o cliente do PGDAS-D e os gatilhos de custo (D-109). Decisão aberta: quem paga o piloto da Serpro e com que franquia.

## 3. Reforma IBS/CBS

As calculadoras oficiais da Receita são código aberto (MIT, repositórios `calculadora-rtc-*`) em Java 25. Rodar o motor localmente exige um sidecar (1 GB em gru ≈ **+R$ 65,85 por mês**, hipótese de `proposta-precos.md`), o que é gate de custo. A alternativa a pesquisar é o serviço público oficial de cálculo, se existir e permitir uso por terceiros. O Radar da Reforma que já existe publica notícia e fonte; o módulo novo calcularia imposto por nota, o que exige aprovação humana e validação por contador antes de qualquer efeito.

## 4. Emissão de NFS-e por procuração

O módulo de maior risco. O EmissaoNFSe provou emissão por procuração (HTTP 201 em 04/11/2026) e leitura ADN de 403 clientes. Para o CICA:

1. **DPS** (declaração de prestação de serviço) no leiaute nacional, assinada em XMLDSig com o e-CNPJ do escritório, enviada à SEFIN por mTLS; DANFSe vem do ADN; lote por CSV ou XLSX; cancelamento por evento.
2. **Pergunta aberta de norma:** a assinatura da DPS pode ser do outorgado (o escritório) por procuração? A Resolução CGNFS-e 003/2023 foi citada em notícia e **não foi lida**. Sem essa resposta o módulo não começa.
3. **Procuração só vale em produção** (EmissaoNFSe, `src/tenant/credencial.ts:82-83`): não há ambiente restrito para testar o caminho real. Cada emissão em produção exige aprovação humana e OK explícito por escritório (D-306). Valor errado, alíquota errada ou código de serviço errado viram nota emitida: o único conserto é cancelar.
4. **Aceite mínimo:** pré-visualização da DPS com todos os campos; botão de emitir só depois de aprovação; trilha de auditoria por nota; limite diário por escritório; desligado por padrão; teste com transporte falso e com a DPS de referência do ADN.

Referências abertas (padrão, não código, D-303): `nfse-nacional/nfse-php` (MIT), `gabrielbuzziv/emissor-nfse-nacional` (MIT), `OpenAC-Net/OpenAC.Net.NFSe.Nacional` (MIT), `lucas-bogos/xsign` (MIT).

## Ordem sugerida e gates do responsável

1. RBT12/teto por NFS-e, sem Serpro e sem emissão: confirmar o valor dos tetos no Portal do Empreendedor.
2. Situação fiscal: contrato Serpro, procuração no e-CAC e franquia do piloto.
3. Reforma IBS/CBS: decisão sobre o sidecar ou o serviço oficial.
4. Emissão: resposta sobre a assinatura da DPS, e OK por escritório para produção.
