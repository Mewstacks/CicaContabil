# Contrato tecnico ? NFS-e, backup Domínio Web e rotina de importacao

**Estado:** aguardando Q-39. Este documento e o pacote de trabalho para o desenvolvedor e para o tecnico do Domínio. Ele nao presume schema, tabela, criptografia, layout ou API.

## Resultado esperado

1. Ler **uma fotografia autorizada** do backup Domínio Web no agente local controlado.
2. Enviar somente dados normalizados permitidos para a CICA, ligados a empresa e ao lote da fotografia.
3. Produzir arquivo de NFS-e somente depois de receber o contrato de importacao versionado.
4. Confirmar importacao somente com retorno verificavel da rotina, nunca pelo download do arquivo.

## O que a CICA ja oferece

- Lote de backup com hash, fonte, instante, empresas e descarte do arquivo/chave ao fim.
- Capacidade allowlisted `accumulator_catalog`, idempotente por lote, empresa e codigo.
- Historico imutavel de acumuladores descobertos, cadastrados e decididos por pessoa.
- Pacote privado de conferencia de XMLs, manifesto e hash. Ele **nao e importavel**.
- Estados separados para pacote gerado e baixado; a confirmacao de importacao esta bloqueada.

## Material tecnico necessario do Domínio

| Item | Exigencia para o adaptador | Evidencia de aceite |
| --- | --- | --- |
| Backup | Formato, versao, protecao, requisito de chave e mecanismo autorizado de leitura. | Um backup descartavel, com instrucoes de abertura e hash. |
| Empresas | Identificador estavel de empresa e relacao com codigo Domínio/CNPJ. | Duas empresas sinteticas, incluindo matriz/filial se o formato suportar. |
| Acumuladores | Origem, codigo, descricao, situacao e vinculo por empresa. | Amostra com ativo/inativo e codigos repetidos entre empresas. |
| Importador | Modulo, tipo de arquivo, versao, codificacao, pasta, competencia e opcao de filtro. | Manual do importador e arquivo de exemplo aceito pelo Domínio. |
| Classificacao | Campo/regra que recebe o acumulador e comportamento para ausencia, duplicidade ou invalidez. | Resultado observavel em ambiente de homologacao. |
| Retorno | Identificador, status, erros, horario e como recuperar uma execucao interrompida. | Importacao de teste com sucesso, erro e repeticao idempotente. |

## Contrato do extrator no agente

O extrator tera versao propria e declarara apenas capacidades autorizadas. Para `accumulator_catalog`, cada linha normalizada deve conter:

```text
company_key       identificador autorizado da empresa no backup
accumulator_code  codigo do acumulador
name              descricao, se existente
active            estado observado, se existente
source_identifier identificador estavel da origem, se existente
```

Campos ausentes devem ser declarados como indisponiveis pela capacidade; nao podem ser inferidos. O agente nao envia SQL, tabelas inteiras, chave, senha nem o arquivo do backup para a CICA.

## Contrato do futuro exportador

O exportador somente sera criado depois que o layout estiver documentado. Seu contrato deve fixar: versao do layout; nome/extensao/codificacao; estrutura de pastas; regra por empresa e competencia; identificador de NFS-e; campo de acumulador; campos obrigatorios; validacoes; semantica de atualizacao; comportamento de duplicata; retorno de erros; e criterio de importacao concluida.

O adaptador recebe uma fotografia imutavel de documentos e classificacoes. A alteracao de documento ou acumulador exige novo pacote. Um timeout ou retorno desconhecido cria estado incerto e exige consulta pelo identificador idempotente; nunca repete importacao cegamente.

## Roteiro de homologacao

1. Validar leitura com backup descartavel e comparar empresas/acumuladores com a tela do Domínio.
2. Reexecutar a mesma fotografia e provar que nao duplica catalogo nem historico.
3. Gerar arquivo pelo layout recebido e validar no importador sem alterar producao.
4. Exercitar erro de acumulador, empresa, competencia, XML, arquivo repetido e interrupcao.
5. Confirmar retorno, protocolo e estado na CICA.
6. Provar isolamento entre dois escritorios e duas empresas.
7. Registrar versao do adaptador, layout, amostra, resultados e procedimento de reversao.

## Limites

O acesso ao backup e a rotina real pertencem a etapa 12. Nenhuma credencial, dado de cliente, arquivo real ou custo deve ser colocado neste documento, no repositorio ou no chat.
