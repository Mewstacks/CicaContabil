# Operação Cobalchini

O HubContador no servidor Cobalchini roda por Docker Compose. O Domínio e seu DSN Windows continuam no host, por meio do agente de borda; containers não acessam nem armazenam o DSN, senhas ou certificados fiscais. O container web fica em loopback: o proxy HTTPS do host aplica mTLS no endpoint do agente usando [`edge-agent-mtls.conf`](../deploy/nginx/edge-agent-mtls.conf).

## Preparação única

1. Copie `.env.cobalchini.example` para `C:\ProgramData\HubContador\cobalchini.env` no servidor, aplique ACL somente à conta técnica e preencha apenas segredos locais. O arquivo fica fora do checkout.
2. Instale Docker Compose, GitHub Actions Runner para Windows e Cosign no host de produção.
3. Restrinja o runner `hub-cobalchini-production` a este repositório privado e ao ambiente GitHub `cobalchini-production`, com revisão obrigatória.
4. No ambiente GitHub, configure as variáveis `HUB_IMAGE_REPOSITORY` (por exemplo, `ghcr.io/organizacao/hubcontador`) e `COBALCHINI_ENV_FILE` (`C:\ProgramData\HubContador\cobalchini.env`), além do segredo `COSIGN_PUBLIC_KEY_B64`, que contém a chave pública Cosign codificada em Base64.
5. Conecte o pacote GHCR ao repositório para que o `GITHUB_TOKEN` efêmero, com `packages: read`, consiga somente baixar a imagem.

## Release aprovada pelo CRMew

O CRMew só deve disparar `repository_dispatch` após uma aprovação humana de release. O payload contém uma única referência no formato `ghcr.io/...@sha256:<digest>`.

O workflow executa nesta ordem:

1. valida que o digest pertence ao repositório GHCR definido no ambiente;
2. autentica no GHCR com o token temporário do job e valida a assinatura Cosign;
3. valida Compose, baixa a imagem e executa migrations compatíveis;
4. inicia web, worker e scheduler, e exige `GET /api/v1/health/ready/` com HTTP 200;
5. persiste a nova referência apenas após o smoke test.

Se uma etapa falhar após iniciar serviços, a imagem anterior é iniciada novamente. Migrations não recebem downgrade automático; releases precisam manter compatibilidade entre versões. A telemetria é adicional: sua falha não bloqueia trabalho fiscal nem rollback local.

Após cada sincronização do CRMew, o Hub confirma por transporte Ed25519 assinado a `configuration_version` efetivamente aplicada. O heartbeat também informa a versão aplicada, a release, saúde e atraso de sync; não leva empresas, documentos, SQL, DSN ou segredos. Falha dessa telemetria é registrada, mas não desfaz um estado já validado nem interrompe o trabalho local.

O contrato entre os dois projetos é fixo: `GET /control/v1/state/` entrega o estado assinado; `POST /control/v1/configuration-ack/` confirma a versão aplicada; `POST /control/v1/heartbeat/` envia a saúde metadata-only; `POST /control/v1/release-ack/` é reservado para a confirmação de release. Mudanças nessas rotas exigem teste de contrato nos dois repositórios.

Nenhum deploy deve ser disparado de pull request, fork, imagem com tag mutável, token pessoal ou segredo salvo no repositório. O checkout pode permanecer limpo porque o arquivo de ambiente não fica no workspace. O risco de runners self-hosted é tratado como operacional: o host é exclusivo, os repositórios permitidos são mínimos e os segredos ficam em ambiente protegido. Consulte a [orientação oficial de segurança para runners](https://docs.github.com/en/actions/concepts/security/compromised-runners).
