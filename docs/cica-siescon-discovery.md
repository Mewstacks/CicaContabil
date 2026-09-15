# CICA — descoberta de integração Siescon

Consulta realizada em 14/09/2026, antes de qualquer tela de credenciais ou promessa comercial.

## Evidência pública

- O portal restrito do Siescon publica manuais, layouts de integração contábil/fiscal, arquivo de troca e materiais para instalação Windows; não foi encontrada documentação pública de uma API CICA/Siescon autenticada para leitura por terceiros.
- A página pública de Escrita Fiscal descreve importação, validação, REINF, SEFAZ e geração de guias dentro do Siescon.
- A página pública de Contabilidade descreve layouts configuráveis e integração com outros sistemas, mas não especifica endpoint, autenticação, escopo de leitura ou ambiente de homologação para a CICA.

Fontes verificadas:

- https://siescon.com.br/restrita/restrita.php
- https://www.siescon.com.br/portal/modulo?modulo=20-escritafiscal
- https://www.siescon.com.br/portal/modulo?modulos=all

## Decisão de produto nesta etapa

Não existe adaptador Siescon, formulário de credenciais ou sincronização ativa na CICA. A interface deve continuar identificando a conexão como indisponível, sem solicitar segredo que não possa ser testado e revogado.

Para iniciar desenvolvimento real, a Mewstack precisa obter do Siescon, por canal autorizado: mecanismo suportado de leitura, documentação técnica, ambiente de homologação, credenciais de teste, campos autorizados, limites, evento de revogação e responsável técnico. Até essa homologação, a CICA não anuncia conexão Siescon como funcional.
