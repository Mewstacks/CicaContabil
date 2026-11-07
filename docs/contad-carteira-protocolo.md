# Carteira CONTAD — contrato de integração em implementação

**Estado verificado em V-328:** backend publicado na release 75, fonte c8b0c50,
[CI 42355490505 aprovado](https://github.com/Mewstacks/CicaContabil/actions/runs/42355490505).
MSI 1.0.4 aprovado em Windows descartável; upgrade no PC e inventário real
aguardam o operador, que confirmou indisponibilidade. Manifesto real continua
piloto, com uma empresa/conta e 163 eventos. Esta fase não conclui o projeto.

| Capacidade | Implementada/testada | Publicada | Provada na CONTAD | Homologada/aceita |
|---|---|---|---|---|
| Protocolo/recepção da carteira de empresas | Sim; PostgreSQL, reenvio e concorrência | Backend 75 | Ainda sem scan real | Não |
| Inventário de metadados/contagens | Roteiro preparado/parser Windows aprovado | Arquivo local preparado | Não executado | Não |
| Agente 1.0.4 | 52 testes/26 checks Windows, MSI/hash aprovados | Artefato CI/cópia local | PC mantém 1.0.3 | Não |
| Contas/referências/Razão/títulos | Contratos anteriores não equivalem a adaptadores reais | Nenhuma fonte nova ativada | Piloto bancário anterior preservado | Não |
| Treinamento | [Guia preparado](pt-BR/contad-conciliacao.md) | Documento disponível | Não executado | Não |

D-323, PC-19, etapas 03/09/12, Q-28/Q-46/Q-47. Histórico financeiro solicitado:
**01/09/2026 em diante**. Cadastros e contas devem ser inventariados integralmente.
Este documento descreve o contrato técnico; não é um segundo plano de execução.

## Capacidade desta implementação

O manifesto `dominio-portfolio-v1` identifica o UUID do escritório, fontes
permitidas, período financeiro e mapa revisado de situações do cadastro. Sua
revisão SHA-256 cobre todos os campos. A versão inicial aceita **somente
`companies`**: não afirma ler contas, Razão ou títulos. Cada fonte adicional
exige contrato e semântica conferidos no Domínio real antes de ser habilitada.
O início financeiro do manifesto não restringe a leitura dos cadastros.

O agente novo mantém `scoped-v1` enquanto estiver no manifesto piloto, inclusive
para retorno à release 73. No manifesto de carteira usa `scoped-v2`. O servidor
permite buscar configuração/heartbeat com o protocolo anterior para a transição,
mas recusa ingestão de carteira por cliente antigo. Códigos de carteira não
são consumidos por pareamento incompatível. **Não é necessário novo pareamento.**

`POST /api/agent/v2/dominio/portfolio/companies` oferece abertura/retomada e
confirmação de páginas de até 500 empresas, na ordem numérica de `CODI_EMP`.
A consulta projeta somente código, nome, identificação cadastral e situação de
`GEEMPRE`, incluindo situações não ativas. A ordenação usa parâmetro numérico,
não o cursor textual que ordenaria 100 antes de 20.

`AgentCompanyScan` registra escritório/agente/revisão, contagem de origem,
cursor confirmado, contagem recebida, páginas e último recibo/digest. Página,
cadastros e cursor são uma transação. Reenvio idêntico da última página devolve
o recibo, sem reaplicar; falha antes do commit conserva o cursor. Reinício
retoma do cursor guardado no servidor. Uma página inválida rejeita todo o lote.
Trava do agente serializa requisições concorrentes e revalida revogação/recorte.

A conclusão exige declaração de fim, contagem inicial/final igual e quantidade
recebida igual. Mudança de contagem abandona a varredura anterior, conservando
histórico/dados, e a próxima abertura começa do zero. Após conclusão, o ciclo
seguinte relê os cadastros e aplica correções de origem sem duplicar identidades.
Isto é **varredura por chave**, não snapshot transacional do ERP: mudanças com
contagem igual durante a leitura podem exigir o ciclo seguinte. Não comprova
uma fotografia consistente nem substitui a homologação de atualização real.
O teto de um milhão de cadastros é explícito e recusa a carga; não corta dados.

V-328 corrige a leitura que podia permanecer presa quando uma divergência
de cobertura era seguida pelo retorno da contagem original. A recusa 409 com
`code=source_count_changed` ou `coverage_mismatch` abandona a leitura aberta
atomicamente, guarda erro/horário e conserva as páginas anteriores. A próxima
abertura começa do zero, mesmo com a mesma contagem. Solicitação atrasada não
abandona o progresso atual; recibo de carga concluída continua repetível.
O protocolo e o MSI 1.0.4 anterior permanecem compatíveis.

## Diagnóstico administrativo de cobertura

No ambiente administrativo do servidor, o comando somente leitura
`python manage.py portfolio_sync_status --organization <UUID-ou-slug>` apresenta
estado do agente, último heartbeat/idade, contagens, conclusão/abandono e erros.
`--agent <UUID>` limita ao agente do mesmo escritório; `--limit 1..100` limita
scans por agente e informa quantos foram omitidos. Não imprime segredos, DSN,
nomes de empresas, documentos ou valores financeiros. No PostgreSQL usa
transação própria REPEATABLE READ/READ ONLY; recusa chamada dentro de outra
transação. O diagnóstico não marca sincronização ou aceite como concluídos.

A execução real em V-328 retornou manifesto piloto e zero scans da carteira.
Os testes de reinício/erro/concorrência são PostgreSQL sintéticos, ainda sem
prova dessa carga no Windows. O uso normal pela Grazi continua pela interface;
este comando é para operação técnica e não exige ação da cliente.

Código é único dentro do escritório. O mapa aprovado define `active` e a
situação bruta fica em `ClientCompany.dominio_status`. Situação desconhecida,
identificação fora do contrato, nome excessivo ou chave inválida interrompem
a página com erro; não são ignorados. Ausência em página/varredura não apaga
nem desativa cadastro. Semântica A/I dos testes é **sintética**, não aprovação
do mapa real da CONTAD. O novo caminho não escreve movimentos, partidas ou
decisões de conciliação e não habilita exportação/IA.

## Inventário para o operador

`agent-windows/inspect-contad-schema.ps1` executa no PowerShell x64, usa o DSN
CICA_CONTAD existente e solicita a credencial **somente no próprio Windows**.
Não lê senha do registro/configuração do agente. Lê metadados de GEEMPRE, CT*
e objetos EF pertinentes a títulos/contas; consulta apenas contagens agrupadas
por situação em GEEMPRE, após verificar suas colunas. Não consulta históricos,
nomes de clientes, documentos ou valores financeiros nessa sonda.

Limites explícitos: 1.500 objetos, 50.000 colunas, vinte situações; excesso
interrompe sem apresentar resultado parcial como completo. Resultado JSON em
nova pasta Downloads restrita ao usuário, SYSTEM e Administradores, sem upload.
Metadados não aprovam chaves/relações, interpretação de baixas, cancelamentos,
sinais ou equivalência de situações. Documentação usada para a API de metadados:
[Microsoft OdbcConnection.GetSchema](https://learn.microsoft.com/dotnet/api/system.data.odbc.odbcconnection.getschema).

`agent-windows/upgrade-configured-contad.ps1` é específico para **1.0.3 → 1.0.4**,
com MSI/manifesto/hash conferidos, sem novo código, descriptografia da configuração
ou alteração do DSN. Confere preservação dos bytes criptografados, versão real,
serviço e ciclo novo. Diferentemente do roteiro de PC de teste, aceita a
configuração já existente. Não usar `test-installer.ps1` no PC CONTAD: ele instala
e remove serviços somente em runner descartável. Bytes aprovados estão em
Downloads/CICA-CONTAD-1.0.4-e9311eb; upgrade real aguarda o operador. Retorno funcional:
manifesto piloto e imagem anterior, mantendo dados e esquema aditivo.

## Condições para avançar

Inventário real e confronto de situação/contas/fontes são o próximo insumo
Q-28. A recepção de cadastros não homologa Razão, títulos/parcelas/baixas,
DE-PARA Q-46, saída Q-47, D-73 ou treinamento/aceite. O manifesto instalado
permanece piloto até alteração operacional validada. Cada verificação pertence
à versão e ao ambiente registrados em VALIDACOES.md.
