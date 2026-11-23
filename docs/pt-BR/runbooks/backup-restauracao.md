# Backup e restauração

[English version](../../en/runbooks/backup-restore.md)

A arquitetura vigente usa PostgreSQL no **Neon**, com os aliases `default` e
`knowledge`, e arquivos privados no **Tigris**. Fly executa a aplicação e o
worker; o PostgreSQL legado parado não é o banco de produção. A configuração e
os endpoints precisam ser reconferidos na execução, sem imprimir credenciais.

D-73 exige retomada sem perda em até 15 minutos e restauração conferida de banco
e documentos em até quatro horas. O **RPO de negócio ainda não foi aprovado**:
nenhum intervalo de backup ou valor padrão do provedor resolve essa decisão.
V-322 provou um backup/restauração pontual; seu snapshot expirava em 13/11/2026
às 14:29:44 UTC. Não usá-lo como prova de proteção atual ou de rotina recorrente.

## Registro operacional e rotina

Antes de ativar a rotina, o responsável operacional e seu substituto devem
registrar, no mesmo PC-09/etapa 12:

- RPO máximo aprovado, janela de medição, frequência e retenção;
- responsável, substituto, destino restrito e permissões de recuperação;
- IDs dos backups de ambos os bancos, instante recuperável e expiração;
- manifesto dos objetos com chave, tamanho e SHA-256, ligado ao ponto dos bancos;
- versão da aplicação, migrações e IDs das chaves de criptografia necessárias;
- destino de alerta já autorizado, condição de atraso/falha e evidência de resposta.

A rotina deve verificar o último **conjunto recuperável**, sua idade e expiração,
conferir que cada arquivo referenciado existe e tem hash íntegro, e registrar a
execução mesmo quando falha. Backup de banco sem os arquivos ou chaves do mesmo
recorte fica incompleto. Uma execução com falha não substitui o último conjunto
válido. Frequência, agenda, retenção paga ou canal de mensagens não são ativados
por este documento; dependem das definições e autorizações existentes.

Não grave segredos no manifesto. Preserve a chave ativa e as chaves históricas
necessárias no mecanismo protegido existente, separadamente do backup, e prove
seu acesso pelo substituto. Ter a chave atual não prova recuperar ciphertext
antigo. Não copie dados de clientes para `knowledge`; seu isolamento continua.

## Exercício de restauração

1. Registre operador, substituto, início UTC, incidente simulado, versão e
   conjunto selecionado. Confirme validade e capacidade autorizada antes de
   criar recurso; não substitua o único banco de produção.
2. Isole o destino. Use banco/branch e prefixo distintos, sem conexão com filas,
   agendador, e-mail, IA, agentes oficiais ou escrita no ERP. Não altere os
   endpoints da aplicação em produção para testar.
3. Restaure `default` **e** `knowledge` no ponto definido. Confira tabelas,
   migrações, contagens e hashes de conteúdo do escopo coberto. Hash de esquema
   ou contagem isolada não prova igualdade dos registros.
4. Recupere os arquivos do manifesto em destino restrito; confira SHA-256,
   tamanho, vínculo ao registro de origem e recibo. Uma referência sem arquivo,
   objeto corrompido ou chave ausente impede declarar o conjunto recuperado.
5. Disponibilize somente as chaves históricas necessárias. Leia campos
   criptografados dos dois aliases por meio da aplicação, sem expor plaintext,
   e registre a verificação. Não gere nova chave para tentar ler dados antigos.
6. Inicie a versão compatível em processo novo. Verifique consulta, relatório,
   recibos e reenvio idempotente em cópia isolada. Não confunda resposta HTTP
   saudável com retomada comprovada de trabalho pendente.
7. Registre fim UTC, duração integral desde o início, idade do ponto recuperável,
   perda observada, contagens/hashes, limites e falhas. Compare com os critérios
   aprovados. RPO observado não equivale a RPO de negócio aceito.
8. Só depois de conferência técnica e autorização do corte, proponha a troca
   operacional com imagem/configuração anterior preservadas. Ao encerrar o
   ensaio, remova apenas os recursos temporários criados por ele e revogue
   credenciais temporárias; registre a limpeza.

Falha antes da conferência mantém o destino isolado. Preserve logs sem dados
pessoais, registre o motivo e retome da última etapa comprovada; nunca repita
cegamente uma escrita com resultado incerto. Rollback de código exige esquema
compatível; migrations aditivas não autorizam apagar tabelas ou restaurar uma
base antiga sobre decisões novas. Em incidente real, suspenda os despachos
pertinentes conforme o procedimento aprovado antes de qualquer corte.

Nunca baixe dumps de produção em computadores de desenvolvedores. A cópia e a
verificação reais ocorrem em ambiente protegido autorizado. Não altere a retenção
ou remova o único backup recuperável durante uma validação.

## Ensaio local reproduzível

O [roteiro sintético](../../../scripts/rehearse_contad_recovery.py) cria seu próprio
PostgreSQL 18 a partir de imagem já em cache (`--pull=never`), sem aceitar URL,
credencial, dump ou container de produção. Usa os dois aliases/migrações reais,
fonte nativa fictícia, conhecimento fictício, arquivos privados e chaves de teste.
Restaura em bancos separados e verifica os resultados em processo novo. Remove
somente seu container e arquivos temporários e preserva um recibo JSON privado.

```sh
python scripts/rehearse_contad_recovery.py --output /caminho/privado/recuperacao-nova.json
```

Execute com o ambiente Python de desenvolvimento já instalado, Docker local e
`postgres:18-bookworm` já presente. O comando recusa sobrescrever recibo anterior.
O comando recusa `python -O`: as asserções verificam o ensaio. O recibo distingue tempo de
backup, restauração/verificação, replay e idade do ponto sintético; registra RPO
de produção e meta de negócio como ausentes.

Esta prova complementa V-365 (SQLite). Não testa Neon, Tigris, rotina recorrente,
volume real, queda do worker/serviço Windows, acesso do substituto ou aceite da
cliente. A retomada de rede/worker/agente e o corte reais continuam exigindo
exercício próprio com o mesmo manifesto e medição de ponta a ponta.
