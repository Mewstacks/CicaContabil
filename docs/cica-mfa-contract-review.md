# MFA e ciclo contratual

Revisão de backend em 13/09/2026.

## Falha encontrada e correção

A regra anterior filtrava apenas perfis com `require_mfa=True`. O cadastro cria perfis com esse campo desligado por padrão. Assim, o fim do teste ou a contratação não bastavam para tornar MFA obrigatório.

`accounts.mfa.is_required` agora verifica o contrato mais recente de cada organização com vínculo ativo do usuário. Um contrato fora do teste exige MFA, independentemente da preferência legada do escritório. Testes sem datas válidas também exigem MFA. A expiração considera o início registrado no perfil mais 14 dias, sem aguardar Celery. A regra legada permanece para organizações sem contrato.

## Cobertura adicionada

- Teste válido dispensa MFA.
- Contrato ativo, carência, suspensão e arquivamento exigem MFA mesmo com preferência desligada.
- Middleware intercepta acesso direto e encaminha à configuração de MFA.
- Expiração em 14 dias e ausência de data final.
- Vínculo inativo não impõe MFA de outro escritório.
- Participar de um teste não anula a exigência de outro escritório contratado.

## Limitações

Não homologa a jornada visual de contratação nem conclui a auditoria de autorização das ferramentas. A obrigatoriedade dos operadores internos ainda tem configuração própria. O fim do teste agora bloqueia novas operações e entra em carência, mas não suspende o escritório automaticamente: a Mewstack decide a condição comercial e a mudança de acesso no console. A aplicação ainda precisa fechar a política comercial de retenção/exportação após encerramento.

## Console operacional: evidência em 14/09/2026

O detalhe do escritório no console da Mewstack agora expõe o estado operacional e suas transições permitidas. Cada mudança exige motivo e gera auditoria. Suspensão e arquivamento também exigem confirmação no servidor; a confirmação não depende apenas do navegador.

Cobrança interna e acesso permanecem deliberadamente separados: marcar um registro de cobrança não reativa nem suspende o escritório. A pessoa autorizada registra o resultado comercial e, quando cabível, altera o acesso em uma segunda ação auditável. Isso evita que um status financeiro externo seja interpretado como autorização automática de acesso.

Ao reativar um escritório cujo contrato esteja em carência ou suspenso, o console atualiza contrato e estado operacional na mesma transação. Assim, a reativação não deixa as ferramentas bloqueadas por um contrato antigo. Sem contrato vigente, o console recusa liberar o acesso.

Validação real: no navegador, um escritório temporário foi suspenso e reativado pelo console. Desktop e viewport de 390 px foram inspecionados; não houve overflow horizontal, o foco permaneceu visível, Escape fechou o modal e o console não registrou erros de JavaScript. Os dados de validação foram removidos depois do teste.
