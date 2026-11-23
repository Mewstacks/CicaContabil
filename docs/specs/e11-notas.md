# E11 Triagem v2, fase A (itens 1 a 3 e CNPJ alfanumérico): notas

Base: worktree em `origin/main` (2cc9c5c8), confirmada pela sessão coordenadora. Spec: `docs/specs/cica-venda-v2.md` (seções 3, 7, 12; só existe em `feat/produto-vendavel`). Não há entradas em `DECISOES.md` nem `VALIDACOES.md` (numeração colide com a branch local); decisões E11-D abaixo.

## Entregue (commits locais, sem push)
- **CNPJ alfanumérico** na extração: candidato por regex, validado por `normalize_cnpj`, só vale se for de empresa do mesmo escritório.
- **Catálogo por escritório** (AC-11.1): `DocumentType` com palavras-chave, esperado (todas as empresas ou por regime) e pasta de destino; tela `app/triagem/catalogo/` (criar, editar, desativar, exceção por empresa, seed contábil opt-in); `hub/views_triage_catalog.py`. A pasta do tipo vale no destino Windows. A extração ranqueia tipos por palavra-chave inteira, sem acento (nome/assunto 2, texto/corpo 1, `@palavra` só no nome/assunto).
- **Ingestão** (AC-11.2): `intake_policy.py` decide ignorar (logo, assinatura, `winmail.dat`, `.ics`), rejeitar com motivo (formato, 25 MB) ou aceitar; IMAP, Graph e Gmail seguem a caixa; corpo e remetente original gravados; conteúdo inválido no scan vira Rejeitado; mensagem IMAP acima de 40 MB vira Rejeitado.
- **Upload manual**: `app/triagem/enviar/` (vários arquivos), mesmo pipeline (quarentena, antimalware, extração, revisão, arquivo); não-administrador precisa escolher empresa do seu escopo.
- **ZIP seguro**: `archives.py` + `archive_expand.py`; limites de entradas, bytes declarados e reais, bytes por membro, razão de compressão e profundidade de pasta; pacote dentro de pacote ignorado; membros lidos um a um com savepoint; só abre depois de antimalware + formato.
- **Formatos extras** (imagem, html, txt, xls) e ZIP por escritório (`TriagePolicy`, tela `app/triagem/entrada/`, padrão desligado).
- **Leitura e OCR** (AC-11.3): `readers.py` (pdf, xlsx por valores em cache, html reduzido, txt/csv/ofx/xml); OCR em `ocr.py`, fila `triage_ocr`, atrás de `TRIAGE_OCR_ENABLED` (padrão desligado), `TriagePolicy.ocr_enabled` e orçamento mensal de páginas reservado ao enfileirar.

## Decisões
- **E11-D1** Pacote aberto fecha como Rejeitado com motivo "Pacote aberto: N arquivos". Status novo exigiria `AlterField`, vetado por `test_migration_safety`. Nova aresta `EXTRACTING -> REJECTED` (dado puro, sem migração).
- **E11-D2** Rejeitar-e-continuar e ignorar logo valem para todos os escritórios (correção de falha, antes a caixa ia a ERRO ou o arquivo ficava em quarentena para sempre). Formatos extras, ZIP e OCR são por escritório.
- **E11-D3** Graph grava só `bodyPreview` (255 caracteres): corpo completo estouraria o limite de 1 MB por página de delta.
- **E11-D4** Sem dependência nova: `.xls` é validado (OLE, sem macro nem objeto embutido) mas não lido; HTML com `html.parser`; OCR chama o binário Tesseract configurado, sem Python novo.
- **E11-D5** `inline` de imagem pequena (< 100 KB, com Content-ID ou inline) é logo; PDF inline continua documento.
- **E11-D6** Sem IA externa e sem Codex. Nada ligado em produção: OCR e formatos extras ficam desligados até decisão do dono.
- **E11-D7** Corpo do e-mail (até 6000 caracteres) é dado pessoal novo em repouso; nunca vai a log nem a serviço externo.

## Para ligar o OCR (decisão de custo do dono)
Definir `TRIAGE_OCR_ENABLED=true`, `TRIAGE_TESSERACT_CMD` e um worker que consuma `-Q celery,triage_ocr`. Nada disso foi alterado em `fly.toml`.

## Fora (fase B, itens 4 a 8 da seção 7)
Motor de empresa por placar, aprendizado, auto-aprovação, tela de checklist e Pendências, assinaturas/banco/período, regras ensinadas, backtest.
