-- Dicionario relacional (DDF) para o Siescon — RASCUNHO v0, NAO VALIDADO
--
-- Executar com pvddl.exe ou pelo Pervasive Control Center, contra um banco
-- nomeado apontando para S:\Dados. Isso NAO altera os arquivos de dados: cria
-- apenas FILE.DDF/FIELD.DDF/INDEX.DDF, que e o que falta para o Siescon
-- aceitar SELECT via ODBC.
--
-- Origem de cada offset:
--   [chave]      lido de `butil -stat` (definicao de indice do proprio arquivo)
--   [confirmado] hipotese validada por teste independente
--   [candidato]  campo categorico real, semantica AINDA NAO confirmada
--
-- As colunas `filler_*` existem so para posicionar as seguintes; o Pervasive
-- deriva o offset pela ordem e pelo tamanho das colunas declaradas.
--
-- TODA coluna precisa de NOT NULL. Sem isso o Pervasive usa colunas anulaveis
-- de verdade e insere um byte indicador de nulo ANTES de cada uma, empurrando
-- todos os offsets seguintes. Comprovado com dump cru de GER_EMPRESA: com as
-- colunas anulaveis, codi_emp voltava NULL e a razao social vinha 3 bytes
-- adiantada (uma empresa chamada JUSSARA aparecia como SARA), porque ha tres
-- colunas declaradas antes dela.

-- ---------------------------------------------------------------------------
-- Empresas  (S:\Dados\GER_EMPRESA.DAT — 679 registros, 2127 bytes)
-- Equivale a bethadba.geempre do Dominio.
-- ---------------------------------------------------------------------------
CREATE TABLE GER_EMPRESA USING 'GER_EMPRESA.DAT' (
    codi_emp        INTEGER NOT NULL,        -- 1..4      [chave 0] 679 valores unicos
    filler_5        CHAR(1) NOT NULL,        -- 5
    razao_emp       CHAR(120) NOT NULL,      -- 6..125    [chave 1] 672 valores unicos
    nome_fantasia   CHAR(40) NOT NULL,       -- 126..165  [chave 2] 353 valores unicos
    documento       CHAR(20) NOT NULL,       -- 166..185  [chave 3] 678 valores unicos = CNPJ
    filler_186      CHAR(865) NOT NULL,      -- 186..1050
    situacao        CHAR(1) NOT NULL,        -- 1051      [candidato] A=533 I=107 P=39
    filler_1052     CHAR(350) NOT NULL,      -- 1052..1401
    tributacao      CHAR(1) NOT NULL,        -- 1402      [candidato] 0=234 1=197 2=213 3=35
    filler_1403     CHAR(725) NOT NULL       -- 1403..2127
);

-- ---------------------------------------------------------------------------
-- Usuarios  (S:\Dados\ADM_USUARIO.DAT — 51 registros, 1796 bytes)
-- Equivale a bethadba.usConfUsuario do Dominio.
-- ---------------------------------------------------------------------------
CREATE TABLE ADM_USUARIO USING 'ADM_USUARIO.DAT' (
    codi_usuario    SMALLINT NOT NULL,       -- 1..2      [chave 0] 51 valores unicos
    nome            CHAR(50) NOT NULL,       -- 3..52     [chave 1] 51 valores unicos
    filler_53       CHAR(207) NOT NULL,      -- 53..259
    campo_260       INTEGER NOT NULL,        -- 260..263  [chave 2] 26 valores unicos
    documento_num   DOUBLE NOT NULL,         -- 264..271  [chave 3] 26 valores unicos
    filler_272      CHAR(1213) NOT NULL,     -- 272..1484
    flag_1485       CHAR(1) NOT NULL,        -- 1485      [candidato] '0'=30 '1'=20
    filler_1486     CHAR(118) NOT NULL,      -- 1486..1603
    flag_1604       CHAR(1) NOT NULL,        -- 1604      [candidato] 'N'=36 'S'=15
    filler_1605     CHAR(192) NOT NULL       -- 1605..1796
);

-- ---------------------------------------------------------------------------
-- Enquadramento tributario  (S:\Dados\SAEC_ENQ.DAT — 1197 registros, 98 bytes)
-- Equivale a bethadba.EFPARAMETRO_VIGENCIA do Dominio: guarda o historico de
-- vigencias, entao a consulta precisa pegar a mais recente ja em vigor.
-- 530 empresas tem enquadramento; 169 delas tem mais de uma vigencia.
-- ---------------------------------------------------------------------------
CREATE TABLE SAEC_ENQ USING 'SAEC_ENQ.DAT' (
    codi_emp        INTEGER NOT NULL,        -- 1..4    [chave seg 1]
    esfera          CHAR(2) NOT NULL,        -- 5..6    [chave seg 2] 01=Federal 02=Estadual
    vigencia        CHAR(8) NOT NULL,        -- 7..14   [chave seg 4] AAAAMMDD
    enq_federal     CHAR(3) NOT NULL,        -- 15..17  SME / EPP / LPR / LRE
    enq_estadual    CHAR(2) NOT NULL,        -- 18..19  ME / MG / PP
    codigo_enq      CHAR(6) NOT NULL,        -- 20..25  codigo numerico correspondente
    filler_26       CHAR(4) NOT NULL,        -- 26..29
    campo_30        CHAR(6) NOT NULL,        -- 30..35  [chave seg 3]
    filler_36       CHAR(63) NOT NULL        -- 36..98
);

-- Dominio observado (esfera 01, federal):
--   SME = 432 empresas   EPP =  69   LPR = 127   LRE =   3
-- Dominio observado (esfera 02, estadual):
--   ME  = 413 empresas   MG  = 106   PP  =  47
-- Leitura pendente de confirmacao na tela: SME/EPP = Simples Nacional
-- (micro / pequeno porte), LPR = Lucro Presumido, LRE = Lucro Real.

-- ---------------------------------------------------------------------------
-- Colaboradores / folha  (S:\Dados\<NNNN>\SAEC_COL.DAT — 1176 bytes)
-- Uma copia por empresa. Equivale a bethadba.foempregados + foaltesal.
-- ---------------------------------------------------------------------------
CREATE TABLE SAEC_COL USING 'SAEC_COL.DAT' (
    codi_colaborador INTEGER NOT NULL,       -- 1..4      [chave 0]
    filler_5         CHAR(26) NOT NULL,      -- 5..30     (inclui chaves 3 e 4, 10 bytes cada)
    nome             CHAR(50) NOT NULL,      -- 31..80    [chave 1]
    filler_81        CHAR(563) NOT NULL,     -- 81..643   (inclui chave 2 em 378, numerico)
    salario          DOUBLE NOT NULL,        -- 644..651  [confirmado] salario mensal
    salario_hora     DOUBLE NOT NULL,        -- 652..659  [confirmado] = salario / 220
    filler_660       CHAR(517) NOT NULL      -- 660..1176
);

-- Teste que confirmou salario/salario_hora: para os 29 registros da empresa 0577,
-- salario / salario_hora ficou entre 205 e 220,05 — com 220,0 exato na maioria.
-- 220 h/mes e a jornada mensal padrao, entao os dois campos estao identificados.
