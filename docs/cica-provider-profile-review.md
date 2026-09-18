# Cadastro público da fornecedora

Revisado em 13/09/2026 para a preparação comercial da CICA.

## Fontes e decisão de uso

- Receita/CNPJ via BrasilAPI: razão social, nome fantasia, situação cadastral,
  início da atividade, atividade principal e endereço. O botão **Atualizar pelo
  CNPJ** executa essa consulta pelo próprio SaaS e registra fonte e horário.
- Site oficial `mewstack.com`: canal público `admin@mewstack.com`.
- Perfil da Empresa no Google fornecido pelo responsável: telefone
  `(54) 99657-3455`; atendimento de segunda a sexta, 09:00–19:00, sábado,
  09:00–14:00, e domingo fechado.
- O telefone genérico retornado pelo cadastro público não foi publicado, pois o
  perfil administrado da empresa fornece contato mais específico.
- Não foi encontrada fonte pública confiável para um canal exclusivo de
  privacidade. O campo permanece vazio e precisa de decisão interna antes do
  lançamento.

## Comportamento implementado

- Dados cadastrais verificados aparecem separados dos canais operacionais
  editáveis.
- CNPJ é normalizado no banco e exibido com máscara.
- Complementos duplicados do provedor cadastral são saneados na apresentação.
- Falha da consulta não persiste um cadastro parcial.
- Termos e políticas consomem razão social, CNPJ, telefone, e-mail, endereço e
  horário da configuração, evitando cópias divergentes no código.
- Atualização manual e sincronização geram evento de auditoria.

## Evidências

- Testes: `tests/test_cica_configuration.py` e `tests/test_cica_cnpj.py`.
- Playwright: sincronização real, erro de franquia do Copiloto, foco no resumo
  de erros, desktop 1440×900, mobile 390×844, landscape 844×390, ausência de
  overflow horizontal e ausência de erros/avisos no console.
- Capturas: `cica-configuration-provider-final-desktop.png` e
  `cica-configuration-provider-final-mobile.png`.

## Referências de interface

Watermelon UI foi consultado para blocos e dashboards de configuração, mas o
catálogo disponível não trouxe um padrão relevante além de anúncios e bento.
A solução adotou o padrão B2B observado em Refero/SaaSFrame: resumo verificável
antes dos campos editáveis, ações primária e secundária explícitas, validação
inline e catálogo separado da identidade da fornecedora. A auditoria final seguiu
as Web Interface Guidelines atuais da Vercel.
